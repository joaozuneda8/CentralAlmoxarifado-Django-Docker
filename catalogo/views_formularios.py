"""A página Formulários (spec 009): o almoxarifado escolhe, por formulário, quais centros de custo
são destino e quais materiais são oferecidos.

Ver é de todo usuário do almoxarifado; gravar exige `is_staff` mais a permissão do cadastro
(`catalogo.acesso`), recusada no servidor. As gravações seguem o padrão POST, mensagem e
redirecionamento, voltando ao mesmo formulário, aba, filtro e página.
"""

from itertools import groupby
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalogo.acesso import exige, pode_alterar_centros, pode_alterar_materiais
from catalogo.catalogos import MODO_DESTINO, MODO_OFICINA, MODO_SEM_PLACA
from catalogo.disponibilidade import (
    ACOES,
    ACRESCENTADO,
    ACRESCENTAR,
    FORA,
    RESTAURAR,
    RETIRADO,
    RETIRAR,
    definir_excecao,
    habilitar_centros,
    materiais_da_tela,
    situacao_do_formulario,
)
from catalogo.forms import FiltrosMateriais
from catalogo.models import CentroCusto, CentroFormulario, Formulario, Material, ParDePara
from pedidos.regras import qtd_br, texto, truncar_qtd

ABAS = [("centros", "Centros de custo"), ("materiais", "Materiais")]
POR_PAGINA = 50
PARAMETROS_DA_VOLTA = ("formulario", "aba", "qc", "q", "grupo", "subgrupo", "estado", "pagina")

# Como o formulário apresenta o destino, em palavras (a ajuda da aba Centros de custo).
EXPLICACAO_DO_MODO = {
    "padrao": (
        "O formulário oferece o centro pela descrição e, para a linha com placa, também como "
        "“descrição — placa”."
    ),
    MODO_SEM_PLACA: (
        "O formulário oferece só a descrição do centro, uma vez; a placa não importa. Por isso a "
        "escolha vale para todas as linhas da descrição."
    ),
    MODO_OFICINA: (
        "O formulário oferece a linha com placa só como “descrição — placa” e a linha sem placa "
        "pela descrição."
    ),
}

ORIGEM_EM_TEXTO = {
    ACRESCENTADO: "acrescentado pelo administrador",
    RETIRADO: "retirado pelo administrador",
    FORA: "fora da regra do formulário",
}


def _formulario(valor) -> str | None:
    return valor if valor in Formulario.values else None


def _url_da_pagina(parametros) -> str:
    """O endereço da página com o estado de quem gravou (formulário, aba, filtros, página)."""
    permitidos = {k: parametros.get(k) for k in PARAMETROS_DA_VOLTA if parametros.get(k)}
    consulta = urlencode(permitidos)
    return reverse("catalogo:formularios") + (f"?{consulta}" if consulta else "")


def _ids(valores) -> list[int]:
    ids = []
    for valor in valores:
        try:
            ids.append(int(valor))
        except (TypeError, ValueError):
            continue
    return ids


# --- A página ----------------------------------------------------------------------------------


def _contexto_centros(origem: str, termo: str, pode_alterar: bool) -> dict:
    habilitadas = set(
        CentroFormulario.objects.filter(formulario=origem).values_list("centro_id", flat=True)
    )
    linhas = CentroCusto.objects.all()
    for palavra in termo.split():
        linhas = linhas.filter(
            Q(descricao__icontains=palavra)
            | Q(codigo__icontains=palavra)
            | Q(placa__icontains=palavra)
        )
    modo = MODO_DESTINO[origem]
    grupos = []
    for descricao, conjunto in groupby(linhas, key=lambda c: c.descricao):
        itens = [{"centro": c, "habilitada": c.pk in habilitadas} for c in conjunto]
        grupos.append(
            {
                "descricao": descricao,
                "linhas": itens,
                "ids": [i["centro"].pk for i in itens],
                "n_habilitadas": sum(1 for i in itens if i["habilitada"]),
                "n_inativas": sum(1 for i in itens if not i["centro"].ativo),
                "codigos": list(dict.fromkeys(i["centro"].codigo for i in itens)),
            }
        )
    return {
        "grupos": grupos,
        "modo": modo,
        "explicacao_do_modo": EXPLICACAO_DO_MODO[modo],
        "por_descricao": modo == MODO_SEM_PLACA,
        "total_linhas": sum(len(g["linhas"]) for g in grupos),
        "total_habilitadas": sum(g["n_habilitadas"] for g in grupos),
        "termo": termo,
        "pode_alterar_centros": pode_alterar,
        "sem_centros": not CentroCusto.objects.exists(),
    }


def _texto_do_estado(estado) -> dict:
    """O que a tela diz de um estado: o selo (nível e texto) e a origem em palavras."""
    if estado.oculto:
        selo = ("aviso", "Oculto no cadastro")
    elif estado.disponivel:
        selo = ("ok", "Disponível")
    else:
        selo = ("neutro", "Não disponível")
    origem = (
        "pela regra do formulário" if estado.origem == "regra" else ORIGEM_EM_TEXTO[estado.origem]
    )
    if estado.oculto:
        origem = "o cadastro do SCPI o oculta em todos os formulários"
    return {"nivel": selo[0], "selo": selo[1], "origem": origem}


def _contexto_materiais(request, origem: str, pode_alterar: bool) -> dict:
    formulario_de_filtros = FiltrosMateriais(request.GET)
    filtros = formulario_de_filtros.filtros()
    situacao = situacao_do_formulario(origem)
    consulta = materiais_da_tela(origem, filtros, situacao)
    pagina = Paginator(consulta, POR_PAGINA).get_page(request.GET.get("pagina"))
    materiais = list(pagina.object_list)
    antigos = dict(
        ParDePara.objects.filter(antigo__in=[m.codigo for m in materiais]).values_list(
            "antigo", "novo"
        )
    )
    linhas = []
    for m in materiais:
        estado = situacao.estado(m)
        linhas.append(
            {
                "material": m,
                "estado": estado,
                "texto": _texto_do_estado(estado),
                "tem_excecao": m.codigo in situacao.excecoes,
                "saldo": qtd_br(truncar_qtd(m.estoque)),
                "canonico": antigos.get(m.codigo, ""),
            }
        )
    return {
        "linhas": linhas,
        "pagina": pagina,
        "filtros_materiais": formulario_de_filtros,
        "filtros_ativos": filtros,
        "total_materiais": pagina.paginator.count,
        "pode_alterar_materiais": pode_alterar,
    }


@login_required
def formularios(request):
    origem = _formulario(request.GET.get("formulario")) or Formulario.LIMPEZA
    aba = request.GET.get("aba")
    aba = aba if aba in {chave for chave, _ in ABAS} else "materiais"
    usuario = request.user
    contexto = {
        "formulario": origem,
        "formulario_nome": Formulario(origem).label,
        "lista_de_formularios": [(f.value, f.label) for f in Formulario],
        "aba": aba,
        "abas": ABAS,
        **_contexto_centros(origem, texto(request.GET.get("qc")), pode_alterar_centros(usuario)),
        **_contexto_materiais(request, origem, pode_alterar_materiais(usuario)),
        "pode_alterar_algo": pode_alterar_centros(usuario) or pode_alterar_materiais(usuario),
    }
    return render(request, "catalogo/formularios.html", contexto)


# --- Gravações ---------------------------------------------------------------------------------


@login_required
@require_POST
@exige(pode_alterar_centros)
def formularios_centros(request):
    origem = _formulario(request.POST.get("formulario"))
    if origem is None:
        return HttpResponseBadRequest("Formulário desconhecido.")
    ids = _ids(request.POST.getlist("centro"))
    habilitar = request.POST.get("habilitado") == "1"
    alvo = Formulario(origem).label
    if not ids:
        messages.warning(request, "Nenhum centro de custo foi escolhido.")
    else:
        mudaram = habilitar_centros(origem, ids, habilitar, request.user)
        if not mudaram:
            messages.info(request, "Nada mudou: os centros já estavam assim.")
        else:
            if habilitar:
                feito = "habilitada" if mudaram == 1 else "habilitadas"
            else:
                feito = "desabilitada" if mudaram == 1 else "desabilitadas"
            linhas = "linha" if mudaram == 1 else "linhas"
            messages.success(request, f"{mudaram} {linhas} {feito} em {alvo}.")
    return redirect(_url_da_pagina({**request.POST.dict(), "aba": "centros"}))


@login_required
@require_POST
@exige(pode_alterar_materiais)
def formularios_excecao(request):
    origem = _formulario(request.POST.get("formulario"))
    acao = request.POST.get("acao")
    if origem is None or acao not in ACOES:
        return HttpResponseBadRequest("Pedido inválido.")
    material = get_object_or_404(Material, codigo=request.POST.get("codigo", ""))
    mudou = definir_excecao(origem, material, acao, request.user)
    alvo = Formulario(origem).label
    nome = f"{material.codigo} — {material.nome}"
    if not mudou:
        messages.info(request, f"Nada mudou para {nome}: já estava assim em {alvo}.")
    elif acao == ACRESCENTAR:
        messages.success(request, f"{nome} passou a ser oferecido em {alvo}.")
    elif acao == RETIRAR:
        messages.success(request, f"{nome} deixou de ser oferecido em {alvo}.")
    elif acao == RESTAURAR:
        messages.success(request, f"{nome} voltou à regra de {alvo}.")
    return redirect(_url_da_pagina({**request.POST.dict(), "aba": "materiais"}))
