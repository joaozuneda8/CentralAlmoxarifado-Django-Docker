"""Busca de materiais e carrinho via HTMX, comuns aos formulários públicos e à saída avulsa.

As views só devolvem trechos (`_resultados.html`, `_carrinho.html`) e não guardam estado.
"""

from dataclasses import replace

from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from pedidos import carrinho as carrinho_mod
from pedidos.fluxos import Fluxo, buscar, fluxo_publico, resultados
from pedidos.models import ItemPedido
from pedidos.regras import AVULSA
from pedidos.servicos import catalogo_de, item_catalogo_gravado


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


def _item_da_edicao(post, fluxo: Fluxo, codigo: str, item):
    """Na edição de uma saída avulsa (o formulário leva `versao` e o `pedido`), quem já está na
    saída vale pelo que foi gravado: o teto é o maior entre o saldo e a quantidade gravada, como
    no envio (`servicos._limites_de_estoque`), e o material que saiu do catálogo segue aceito.
    Só na saída avulsa: os endpoints públicos não exigem login, e `versao` e `pedido` vêm do
    navegador, então não podem levantar o teto de um formulário público."""
    if fluxo.origem != AVULSA or "versao" not in post:
        return item
    gravado = ItemPedido.objects.filter(
        pedido__numero=post.get("pedido", ""), pedido__origem=AVULSA, codigo=codigo
    ).first()
    if gravado is None:
        return item
    if item is None:
        return item_catalogo_gravado(gravado)
    return replace(item, estoque=max(item.estoque, gravado.qtd_entregue or 0))


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
        item = _item_da_edicao(request.POST, fluxo, codigo, item)
        resultado = carrinho_mod.alterar(linhas, fluxo, item, enviados.get(codigo, ""))
    elif "remover" in request.POST:
        resultado = carrinho_mod.remover(linhas, request.POST["remover"])
    else:
        resultado = carrinho_mod.Carrinho(linhas)
    contexto = {
        "fluxo": fluxo,
        "carrinho": resultado,
        # Na edição da saída avulsa o formulário leva a versão: o envio diz "Salvar alterações".
        "editando": "versao" in request.POST,
        **urls_do_fluxo(fluxo),
    }
    return render(request, "pedidos/_carrinho.html", contexto)


@require_GET
def materiais(request, fluxo):
    return _materiais(request, fluxo_publico(fluxo))


@require_POST
def carrinho(request, fluxo):
    return _carrinho(request, fluxo_publico(fluxo))
