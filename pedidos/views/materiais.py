"""Busca de materiais e carrinho via HTMX, comuns aos formulários públicos e à saída avulsa.

As views só devolvem trechos (`_resultados.html`, `_carrinho.html`) e não guardam estado.
"""

from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from pedidos import carrinho as carrinho_mod
from pedidos.fluxos import Fluxo, buscar, fluxo_publico, resultados
from pedidos.servicos import catalogo_de


def urls_do_fluxo(fluxo: Fluxo) -> dict:
    if fluxo.publico:
        return {
            "url_materiais": reverse("pedidos:materiais", args=[fluxo.nome]),
            "url_carrinho": reverse("pedidos:carrinho", args=[fluxo.nome]),
        }
    return {
        "url_materiais": reverse("pedidos:avulsa_materiais"),
        "url_carrinho": reverse("pedidos:avulsa_carrinho"),
    }


def contexto_busca(fluxo: Fluxo, catalogo, q: str = "", filtro: str = "") -> dict:
    achados, total = buscar(fluxo, catalogo, q, filtro)
    return {"resultados": resultados(fluxo, achados), "total": total}


def _materiais(request, fluxo: Fluxo):
    catalogo = catalogo_de(fluxo.origem) or []
    contexto = {
        "fluxo": fluxo,
        **contexto_busca(fluxo, catalogo, request.GET.get("q", ""), request.GET.get("filtro", "")),
        **urls_do_fluxo(fluxo),
    }
    return render(request, "pedidos/_resultados.html", contexto)


def _carrinho(request, fluxo: Fluxo):
    catalogo = catalogo_de(fluxo.origem) or []
    linhas = carrinho_mod.ler(request.POST, fluxo, catalogo)
    if "adicionar" in request.POST:
        codigo = request.POST["adicionar"]
        item = next((i for i in catalogo if i.codigo == codigo), None)
        resultado = carrinho_mod.adicionar(
            linhas, fluxo, item, request.POST.get(f"qtd-{codigo}", "")
        )
    elif "alterar" in request.POST:
        codigo = request.POST["alterar"]
        enviados = dict(
            zip(request.POST.getlist("item_codigo"), request.POST.getlist("item_qtd"), strict=False)
        )
        linhas = carrinho_mod.ler(
            request.POST, fluxo, catalogo, {codigo: request.POST.get("anterior", "")}
        )
        item = next((i for i in catalogo if i.codigo == codigo), None)
        resultado = carrinho_mod.alterar(linhas, fluxo, item, enviados.get(codigo, ""))
    elif "remover" in request.POST:
        resultado = carrinho_mod.remover(linhas, request.POST["remover"])
    else:
        resultado = carrinho_mod.Carrinho(linhas)
    contexto = {"fluxo": fluxo, "carrinho": resultado, **urls_do_fluxo(fluxo)}
    return render(request, "pedidos/_carrinho.html", contexto)


@require_GET
def materiais(request, fluxo):
    return _materiais(request, fluxo_publico(fluxo))


@require_POST
def carrinho(request, fluxo):
    return _carrinho(request, fluxo_publico(fluxo))
