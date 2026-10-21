from django.shortcuts import render
from django.urls import reverse

from pedidos import carrinho as carrinho_mod
from pedidos.fluxos import fluxo_publico, opcoes_filtro
from pedidos.models import ItemPedido
from pedidos.protecao import (
    CAMPO_ISCA,
    MENSAGEM_RAPIDO,
    MENSAGEM_RECUSA,
    MENSAGEM_TOKEN_INVALIDO,
    MOTIVO_ISCA,
    emitir,
    ler,
    recusar,
)
from pedidos.regras import EnvioPedido, opcoes_destino, resolver_destino
from pedidos.servicos import catalogo_de, centros, registrar_pedido
from pedidos.views.materiais import contexto_busca, urls_do_fluxo


def inicio(request):
    """Página pública dos funcionários (sem login)."""
    return render(request, "pedidos/inicio.html")


def _contexto(fluxo, catalogo, envio, **extra) -> dict:
    destinos = opcoes_destino(centros())
    contexto = {
        "fluxo": fluxo,
        "envio": envio,
        "indisponivel": catalogo is None,
        # Há itens, mas o máximo pedível de todos é zero: o formulário abre com um aviso no topo.
        "sem_estoque_agora": bool(catalogo)
        and all(carrinho_mod.limite(fluxo, i) <= 0 for i in catalogo),
        "sem_destinos": not destinos,
        "destinos": destinos,
        "filtros": opcoes_filtro(fluxo, catalogo),
        "carrinho": carrinho_mod.Carrinho(),
        "campos": {},
        "codigos_erro": set(),
        "erros_por_campo": {},
        **contexto_busca(fluxo, catalogo or []),
        **urls_do_fluxo(fluxo),
    }
    contexto.update(extra)
    return contexto


def formulario(request, fluxo):
    """Formulário de pedido (limpeza ou AB). O envio vem pelo HTMX, e a resposta substitui o
    formulário: o sucesso não tem URL própria, para o número não virar página pública."""
    fluxo = fluxo_publico(fluxo)
    catalogo = catalogo_de(fluxo.origem)
    parcial = bool(request.headers.get("HX-Request"))
    if request.method != "POST":
        return render(request, "pedidos/formulario.html", _contexto(fluxo, catalogo, emitir()))

    campos = {c: request.POST.get(c, "") for c in ("solicitante", "destino", "obs")}

    def de_volta(envio, **extra):
        contexto = _contexto(
            fluxo,
            catalogo,
            envio,
            campos=campos,
            carrinho=carrinho_mod.Carrinho(
                carrinho_mod.ler(request.POST, fluxo, catalogo, manter_ilegiveis=True)
            ),
            **extra,
        )
        modelo = "pedidos/_formulario.html" if parcial else "pedidos/formulario.html"
        return render(request, modelo, contexto)

    envio = ler(request.POST.get("token", ""))
    if envio is None:
        return de_volta(emitir(), mensagem=MENSAGEM_TOKEN_INVALIDO)
    if motivo := recusar(envio, request.POST.get(CAMPO_ISCA, "")):
        # Só a isca (que uma pessoa nunca preenche) recebe a mensagem genérica.
        return de_volta(
            envio, mensagem=MENSAGEM_RECUSA if motivo == MOTIVO_ISCA else MENSAGEM_RAPIDO
        )

    # O texto como está no cadastro; o que não existe segue como veio, para a validação recusar.
    destino = resolver_destino(campos["destino"], centros()) or campos["destino"]
    pedido = EnvioPedido(
        solicitante=campos["solicitante"],
        destino=destino,
        obs=campos["obs"],
        itens=carrinho_mod.itens_enviados(request.POST),
    )
    resposta = registrar_pedido(
        fluxo.origem,
        envio.id,
        pedido,
        ip=request.META.get("REMOTE_ADDR"),
        url_painel=request.build_absolute_uri(reverse("pedidos:painel")),
    )
    if resposta.ok:
        # `_sucesso.html` lista só o que o funcionário pediu (filtro por segurança).
        itens = list(resposta.pedido.itens.filter(origem=ItemPedido.Origem.PEDIDO))
        contexto = {
            "fluxo": fluxo,
            "resposta": resposta,
            "itens": itens,
            "n_itens": len(itens),
        }
        if parcial:
            return render(request, "pedidos/_sucesso.html", contexto)
        return render(request, "pedidos/formulario.html", {**contexto, "sucesso": True})
    if resposta.divergente:
        envio = emitir(aberto_em=envio.aberto_em)
    return de_volta(
        envio,
        mensagem=resposta.mensagem,
        erros=resposta.erros,
        divergente=resposta.divergente,
        codigos_erro={e.codigo for e in resposta.erros if e.codigo},
        erros_por_campo=_por_campo(resposta.erros),
    )


def _por_campo(erros) -> dict[str, list[str]]:
    """{campo: [textos]} dos erros de um campo do formulário, para mostrá-los junto dele."""
    por_campo: dict[str, list[str]] = {}
    for erro in erros:
        if erro.campo:
            por_campo.setdefault(erro.campo, []).append(erro.texto)
    return por_campo
