import uuid
from dataclasses import replace

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_vary_headers
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalogo.models import CentroCusto, Opcao
from catalogo.saude import saude_do_catalogo
from pedidos import carrinho as carrinho_mod
from pedidos.consultas import (
    FiltrosPainel,
    filtrar_situacao,
    lotes_pendentes,
    lotes_travados,
    pedidos_do_painel,
    unidades_scpi,
)
from pedidos.fluxos import FLUXOS
from pedidos.models import Atendimento, ExecucaoRobo, ItemPedido, Pedido
from pedidos.regras import AB, AVULSA, Adicionado, DadosSaida, EnvioSaida, qtd_br
from pedidos.servicos import (
    catalogo_de,
    confirmar_atendimento,
    erros_de_vinculo,
    marcar_recibos_impressos,
    recibos_alterados,
    registrar_saida_avulsa,
    tipos_saida,
)
from pedidos.views.materiais import _carrinho, _materiais, contexto_busca, urls_do_fluxo

# O atendimento de um pedido sai sempre como balcão: o campo vem fixo no formulário.
TIPO_ATENDIMENTO = "BALCÃO"


@login_required
def painel(request):
    """Pedidos e saídas avulsas, mais recentes primeiro, com filtros e paginação via HTMX."""
    form = FiltrosPainel(request.GET)
    pagina = Paginator(pedidos_do_painel(form.filtros()), 25).get_page(request.GET.get("pagina"))
    contexto = {"pagina": pagina, "filtros": form}
    # Só o trecho para a troca do HTMX; ao restaurar o histórico (botão Voltar) o HTMX também
    # manda HX-Request, mas precisa da página inteira.
    parcial = request.headers.get("HX-Request") and not request.headers.get(
        "HX-History-Restore-Request"
    )
    if parcial:
        resposta = render(request, "pedidos/_painel_lista.html", contexto)
        patch_vary_headers(resposta, ["HX-Request", "HX-History-Restore-Request"])
        return resposta
    contexto["saude"] = [item for item in saude_do_catalogo() if item.nivel != "ok"]
    contexto["recibos_pendentes"] = Atendimento.objects.filter(
        recibo_impresso_em__isnull=True
    ).count()
    contexto["pedidos_aguardando"] = filtrar_situacao(Pedido.objects.all(), "aguardando").count()
    contexto["lancamento_pendentes"] = lotes_pendentes()
    contexto["lancamento_travados"] = len(lotes_travados())
    contexto["lancamento_em_andamento"] = ExecucaoRobo.em_andamento().exists()
    contexto["lancamento_real"] = settings.LANCAMENTO_REAL
    resposta = render(request, "pedidos/painel.html", contexto)
    patch_vary_headers(resposta, ["HX-Request", "HX-History-Restore-Request"])
    return resposta


def opcoes_saida() -> dict:
    """Listas dos campos de uma saída: funcionários, centros, placas e tipos."""
    linhas = list(CentroCusto.objects.all())
    return {
        "funcionarios": Opcao.valores(Opcao.Lista.FUNCIONARIO),
        "centros": list(dict.fromkeys((c.descricao, c.codigo) for c in linhas)),
        "placas": sorted((c.placa, c.descricao) for c in linhas if c.placa),
        "tipos": tipos_saida(),
        "hoje": timezone.localdate().isoformat(),
    }


def dados_saida(post) -> tuple[DadosSaida, bool]:
    dados = DadosSaida(
        data=post.get("data", ""),
        recebedor=post.get("recebedor", ""),
        centro_custo=post.get("centro_custo", ""),
        tipo=post.get("tipo", ""),
        placa=post.get("placa", ""),
        obs=post.get("obs", ""),
    )
    return dados, "nao_lancar" in post


def _dados_do_atendimento(post) -> tuple[DadosSaida, bool]:
    """Dados da saída do atendimento. O tipo é sempre BALCÃO quando ele existe nas opções: o
    formulário o trava, e o servidor não confia no `tipo` enviado. Sem BALCÃO nas opções, o
    formulário libera a escolha (`tipo_fixo` vazio) e vale o que veio."""
    dados, nao_lancar = dados_saida(post)
    if TIPO_ATENDIMENTO in tipos_saida():
        dados = replace(dados, tipo=TIPO_ATENDIMENTO)
    return dados, nao_lancar


def _pedido(numero):
    consulta = Pedido.objects.select_related(
        "atendimento", "atendimento__atendido_por", "registrado_por"
    ).prefetch_related("itens", "atendimento__linhas")
    return get_object_or_404(consulta, numero=numero)


def _saida_do_destino(destino: str, opcoes: dict) -> dict:
    """Centro de custo e placa sugeridos pelo destino do pedido ("centro" ou "centro — placa",
    como em `regras.opcoes_destino`). Com placa, o centro é o dela, que o formulário trava."""
    for placa, descricao in opcoes["placas"]:
        if destino == f"{descricao} — {placa}":
            return {"centro_custo": descricao, "placa": placa}
    if any(destino == descricao for descricao, _ in opcoes["centros"]):
        return {"centro_custo": destino}
    return {}


def _formatar_qtd(pedido, q) -> str:
    """Quantidade no campo da entrega: inteira no AB, pt-BR nos demais."""
    return str(int(q)) if pedido.origem == AB else qtd_br(q)


def _contexto_detalhe(pedido, **extra) -> dict:
    contexto = {"pedido": pedido, "atendivel": False, "unidades_scpi": unidades_scpi([pedido])}
    if pedido.origem != AVULSA and pedido.atendimento_ou_none is None:
        opcoes = opcoes_saida()
        contexto.update(
            atendivel=True,
            atendimento_id=uuid.uuid4(),
            campos={
                "data": timezone.localdate().isoformat(),
                **_saida_do_destino(pedido.destino, opcoes),
            },
            entregues={
                i.codigo: _formatar_qtd(pedido, i.qtd_pedida) for i in _itens_pedidos(pedido)
            },
            tipo_fixo=TIPO_ATENDIMENTO if TIPO_ATENDIMENTO in opcoes["tipos"] else "",
            **opcoes,
        )
    contexto.update(extra)
    return contexto


@login_required
def detalhe(request, numero):
    """Recibo do pedido na tela e, enquanto não atendido, o formulário de atendimento."""
    return render(request, "pedidos/detalhe.html", _contexto_detalhe(_pedido(numero)))


@login_required
@require_POST
def atender(request, numero):
    pedido = _pedido(numero)
    try:
        atendimento_id = uuid.UUID(request.POST.get("atendimento_id", ""))
    except ValueError:
        messages.error(request, "Identificador do atendimento inválido. Recarregue a página.")
        return redirect("pedidos:detalhe", numero=numero)
    dados, nao_lancar = _dados_do_atendimento(request.POST)
    qtds = {i.codigo: request.POST.get(f"entregue-{i.codigo}", "") for i in pedido.itens.all()}
    adicionados = _adicionados_enviados(request.POST)
    qtds.update({a.codigo: request.POST.get(f"entregue-{a.codigo}", "") for a in adicionados})
    resposta = confirmar_atendimento(
        pedido.id,
        atendimento_id,
        dados,
        qtds,
        nao_lancar=nao_lancar,
        usuario=request.user,
        adicionados=adicionados,
    )
    if resposta.ok:
        texto = "já estava registrado" if resposta.reenvio else "registrado"
        messages.success(request, f"Atendimento do pedido {numero} {texto}.")
        return redirect("pedidos:detalhe", numero=numero)
    if not resposta.erros:
        messages.error(request, resposta.mensagem)
        return redirect("pedidos:detalhe", numero=numero)
    contexto = _contexto_detalhe(
        pedido,
        atendimento_id=atendimento_id,
        campos=request.POST,
        nao_lancar=nao_lancar,
        entregues=qtds,
        adicionados=_linhas_adicionadas(pedido, adicionados, qtds),
        codigos_erro={e.codigo for e in resposta.erros if e.codigo},
        mensagem=resposta.mensagem,
        erros=resposta.erros,
    )
    return render(request, "pedidos/detalhe.html", contexto)


def _adicionados_enviados(post) -> list[Adicionado]:
    """Os materiais acrescentados na página (`adicionado` repetido, na ordem em que entraram)
    e o item pedido que cada um substitui (`no-lugar-de-<codigo>`, vazio sem troca)."""
    return [Adicionado(c, post.get(f"no-lugar-de-{c}", "")) for c in post.getlist("adicionado")]


def _catalogo_avulsa() -> dict:
    return {i.codigo: i for i in catalogo_de(AVULSA) or []}


def _itens_pedidos(pedido) -> list[ItemPedido]:
    return [i for i in pedido.itens.all() if i.origem == ItemPedido.Origem.PEDIDO]


def _linha_adicionada(pedido, a: Adicionado, qtd: str, catalogo: dict) -> dict:
    """O que `_adicionado.html` desenha de um acrescentado: o material do catálogo da saída
    avulsa (a unidade é a do SCPI), a quantidade digitada e o item pedido que ele substitui."""
    item = catalogo.get(a.codigo)
    trocado = next((i for i in _itens_pedidos(pedido) if i.codigo == a.no_lugar_de), None)
    return {
        "item": item,
        "codigo": a.codigo,
        "nome": item.nome if item else a.codigo,
        "unidade": item.unidade if item else "",
        "qtd": qtd,
        "no_lugar_de": a.no_lugar_de,
        "no_lugar_de_nome": trocado.material if trocado else a.no_lugar_de,
    }


def _linhas_adicionadas(pedido, adicionados, qtds) -> list[dict]:
    catalogo = _catalogo_avulsa() if adicionados else {}
    return [_linha_adicionada(pedido, a, qtds.get(a.codigo, ""), catalogo) for a in adicionados]


def _pedido_pendente(numero):
    """Pedido ainda por atender (não avulso, sem atendimento): só nele se acrescenta material."""
    pedido = _pedido(numero)
    if pedido.origem == AVULSA or pedido.atendimento_ou_none is not None:
        raise Http404("Pedido sem atendimento pendente.")
    return pedido


@login_required
def atendimento_materiais(request, numero):
    """Busca do material que o almoxarifado acrescenta ao atendimento (troca ou acréscimo):
    catálogo da saída avulsa, com o resultado entrando no grupo dos acrescentados. Na troca
    (`no_lugar_de`), a quantidade já vem com a pedida do item trocado."""
    pedido = _pedido_pendente(numero)
    fluxo = FLUXOS["avulsa"]
    no_lugar_de = request.GET.get("no_lugar_de", "")
    trocado = next((i for i in _itens_pedidos(pedido) if i.codigo == no_lugar_de), None)
    contexto = {
        "fluxo": fluxo,
        **contexto_busca(
            fluxo,
            catalogo_de(fluxo.origem) or [],
            request.GET.get("q", ""),
            request.GET.get("filtro", ""),
        ),
        "url_carrinho": reverse("pedidos:atendimento_adicionar", args=[pedido.numero]),
        # O painel do atendimento já é a escolha: cada resultado adiciona (ou troca) direto.
        "um_passo": True,
        "alvo_resultado": "#adicionados",
        "troca_resultado": "beforeend",
        # Cada clique anexa uma linha: com um pedido em voo, o segundo clique é descartado.
        "sincronia_resultado": "drop",
        # O botão fica no formulário do painel (quantidade, CSRF e `no_lugar_de` vão junto);
        # os acrescentados já na página vêm do formulário do atendimento.
        "inclusao_resultado": (
            "[name=adicionado], [name^=no-lugar-de-], [data-atendimento-painel] [name=no_lugar_de]"
        ),
    }
    if trocado is not None:
        contexto["qtd_inicial"] = _formatar_qtd(pedido, trocado.qtd_pedida)
        # Na troca, a ação dos resultados é "Trocar" (primária), não "Adicionar".
        contexto["acao_rotulo"] = "Trocar"
        contexto["acao_aria"] = f"Trocar {trocado.material} por"
        contexto["acao_primaria"] = True
    return render(request, "pedidos/_resultados.html", contexto)


@login_required
@require_POST
def atendimento_adicionar(request, numero):
    """Linha do material acrescentado, a juntar ao grupo dos acrescentados da página. Recusado
    (fora do catálogo, bloqueado, repetido, troca inválida ou quantidade inválida), devolve só
    a mensagem, com status 200 (o `htmx-config` não troca respostas 4xx) e o alvo trocado para
    `#adicionar-erro`."""
    pedido = _pedido_pendente(numero)
    catalogo = _catalogo_avulsa()
    codigo = request.POST.get("adicionar", "").strip()
    novo = Adicionado(codigo, request.POST.get("no_lugar_de", "").strip())
    item = catalogo.get(codigo)
    erro = ""
    if item is None:
        erro = "Material não encontrado no catálogo."
    elif motivo := carrinho_mod.motivo_bloqueio(FLUXOS["avulsa"], item):
        erro = f"{item.nome} ({item.codigo}): {motivo} — não pode ser adicionado."
    else:
        # Os casos de repetição e troca da confirmação, contra os pedidos e os acrescentados
        # que já estão na página: só os erros que o novo (o último da lista) acrescenta.
        existentes = _adicionados_enviados(request.POST)
        itens = _itens_pedidos(pedido)
        _, antes = erros_de_vinculo(existentes, itens, catalogo)
        _, depois = erros_de_vinculo([*existentes, novo], itens, catalogo)
        if len(depois) > len(antes):
            erro = depois[len(antes)].texto
    if not erro:
        # A regra da quantidade é a da origem do pedido (AB só inteiros), maior que zero.
        regra = FLUXOS["ab"] if pedido.origem == AB else FLUXOS["limpeza"]
        qtd, erro = carrinho_mod.quantidade(regra, request.POST.get(f"qtd-{codigo}", ""))
    if erro:
        resposta = render(request, "pedidos/_adicionado.html", {"erro": erro})
        resposta["HX-Retarget"] = "#adicionar-erro"
        resposta["HX-Reswap"] = "innerHTML"
        return resposta
    linha = _linha_adicionada(pedido, novo, _formatar_qtd(pedido, qtd), catalogo)
    return render(request, "pedidos/_adicionado.html", {"pedido": pedido, "a": linha})


@login_required
def avulsa_materiais(request):
    return _materiais(request, FLUXOS["avulsa"])


@login_required
@require_POST
def avulsa_carrinho(request):
    return _carrinho(request, FLUXOS["avulsa"])


@login_required
def avulsa(request):
    """Saída registrada direto pelo almoxarifado, sem pedido anterior."""
    fluxo = FLUXOS["avulsa"]
    catalogo = catalogo_de(fluxo.origem)
    contexto = {
        "fluxo": fluxo,
        "indisponivel": catalogo is None,
        "envio_id": uuid.uuid4(),
        "campos": {"data": timezone.localdate().isoformat()},
        "carrinho": carrinho_mod.Carrinho(),
        "codigos_erro": set(),
        "filtros": [],
        **contexto_busca(fluxo, catalogo or []),
        **urls_do_fluxo(fluxo),
        **opcoes_saida(),
    }
    if request.method != "POST":
        return render(request, "pedidos/avulsa.html", contexto)

    dados, nao_lancar = dados_saida(request.POST)
    contexto.update(
        campos=request.POST,
        nao_lancar=nao_lancar,
        carrinho=carrinho_mod.Carrinho(carrinho_mod.ler(request.POST, fluxo, catalogo)),
    )
    try:
        envio_id = uuid.UUID(request.POST.get("envio_id", ""))
    except ValueError:
        contexto["mensagem"] = "Identificador do envio inválido. Recarregue a página."
        return render(request, "pedidos/avulsa.html", contexto)
    envio = EnvioSaida(dados, carrinho_mod.itens_enviados(request.POST), nao_lancar)
    resposta = registrar_saida_avulsa(envio_id, envio, usuario=request.user)
    if resposta.ok:
        if resposta.reenvio:
            texto = f"Saída já registrada (reenvio confirmado): Nº {resposta.numero}."
        else:
            texto = f"Saída avulsa registrada: Nº {resposta.numero}."
        messages.success(request, texto)
        return redirect("pedidos:detalhe", numero=resposta.numero)
    contexto.update(
        envio_id=uuid.uuid4() if resposta.divergente else envio_id,
        divergente=resposta.divergente,
        mensagem=resposta.mensagem,
        erros=resposta.erros,
        codigos_erro={e.codigo for e in resposta.erros if e.codigo},
    )
    return render(request, "pedidos/avulsa.html", contexto)


@login_required
@require_POST
def marcar_impressos(request):
    ids, versoes = [], {}
    for valor in request.POST.getlist("atendimento"):
        try:
            atendimento_id = uuid.UUID(valor)
        except ValueError:
            continue
        ids.append(atendimento_id)
        versao = request.POST.get(f"versao-{valor}", "")
        if versao.isdigit():
            versoes[atendimento_id] = int(versao)
    alterados = recibos_alterados(versoes)
    n = marcar_recibos_impressos(ids, versoes=versoes)
    if alterados:
        messages.warning(
            request, "O pedido foi alterado depois de abrir esta página; imprima de novo."
        )
    if n == 1:
        messages.success(request, "1 recibo marcado como impresso.")
    elif n:
        messages.success(request, f"{n} recibos marcados como impressos.")
    elif not alterados:
        messages.info(
            request, "Nenhum recibo novo para marcar: todos já estavam marcados como impressos."
        )
    voltar = request.POST.get("voltar", "")
    if url_has_allowed_host_and_scheme(
        voltar, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(voltar)
    return redirect("pedidos:painel")
