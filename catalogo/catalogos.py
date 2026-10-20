"""Catálogos de materiais dos formulários, montados do banco a cada consulta (sem cache).

Traduz `montarCatalogos_` do `Catalogo.gs`: limpeza vem do `ItemLimpeza`; AB, das saídas do
SCPI no período da curva ABC, consolidadas pelo de/para e ordenadas por número de ocorrências; a
saída avulsa, de todo material não oculto e com saldo positivo. Em todos, o material `duplicado`
aparece (bloqueado pelo formulário).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.utils import timezone

from catalogo.consultas_curva import consolidado
from catalogo.curva import periodo
from catalogo.models import ConfiguracaoCurva, ItemLimpeza, Material, Opcao
from pedidos.regras import estoque_inteiro, norm_u

# Usados quando a lista GRUPO_OCULTO_AB está vazia (como `GRUPOS_OCULTOS_PADRAO_`).
GRUPOS_OCULTOS_PADRAO = (
    "GERAL",
    "MATERIAL DE EXPEDIENTE ( ESCRITORIO)",
    "MATERIAL DE CONSUMO",
)


@dataclass(frozen=True)
class ItemCatalogo:
    codigo: str
    nome: str
    unidade: str
    categoria: str
    grupo: str
    subgrupo: str
    estoque: Decimal
    disponivel: int
    duplicado: bool


@dataclass
class CatalogoAB:
    itens: list[ItemCatalogo] = field(default_factory=list)
    codigos: int = 0
    na_limpeza: int = 0
    ocultos: int = 0
    sem_cadastro: list[str] = field(default_factory=list)


def _grupo(texto: str) -> str:
    return norm_u(texto).replace(" ", "")


def grupos_ocultos_ab() -> set[str]:
    """Grupos fora do formulário AB, normalizados (sem acento, maiúsculas, sem espaços)."""
    valores = Opcao.valores(Opcao.Lista.GRUPO_OCULTO_AB) or GRUPOS_OCULTOS_PADRAO
    return {_grupo(v) for v in valores}


def _item(material: Material, **outros) -> ItemCatalogo:
    campos = {
        "codigo": material.codigo,
        "nome": material.nome,
        "unidade": material.unidade,
        "categoria": "",
        "grupo": material.grupo,
        "subgrupo": material.subgrupo,
        "estoque": material.estoque,
        "disponivel": estoque_inteiro(material.estoque),
        "duplicado": material.duplicado,
    }
    campos.update(outros)
    return ItemCatalogo(**campos)


def catalogo_limpeza() -> list[ItemCatalogo]:
    """Itens do formulário de limpeza cujo material não está oculto; nome e unidade
    exibidos têm prioridade sobre o cadastro."""
    itens = ItemLimpeza.objects.select_related("material").filter(material__oculto=False)
    return [
        _item(
            i.material,
            nome=i.nome_exibido or i.material.nome,
            unidade=i.unidade_exibida or i.material.unidade,
            categoria=i.categoria,
        )
        for i in itens
    ]


def saldo_importado() -> bool:
    """Se o saldo de estoque já foi importado do SCPI alguma vez (sem isso, todo material
    apareceria sem estoque)."""
    return Material.objects.filter(estoque_em__isnull=False).exists()


def catalogo_ab(hoje: date | None = None) -> CatalogoAB | None:
    """Itens do formulário AB, ou None se o saldo de estoque nunca foi importado.

    Um item por código canônico, na ordem das ocorrências consolidadas no período da curva ABC,
    com o saldo do canônico (é nele que a saída será lançada)."""
    if not saldo_importado():
        return None
    hoje = hoje or timezone.localdate()
    linhas, _ = consolidado(periodo(hoje, ConfiguracaoCurva.atual().janela_meses))
    ranking = [
        linha.canonico
        for linha in sorted(linhas, key=lambda linha: (-linha.ocorrencias, norm_u(linha.canonico)))
    ]
    materiais = {norm_u(m.codigo): m for m in Material.objects.filter(codigo__in=ranking)}
    na_limpeza = {
        norm_u(c)
        for c in ItemLimpeza.objects.filter(material__codigo__in=ranking).values_list(
            "material__codigo", flat=True
        )
    }
    ocultos = grupos_ocultos_ab()
    ab = CatalogoAB(codigos=len(ranking))
    for codigo in ranking:
        material = materiais.get(norm_u(codigo))
        if material is None:
            ab.sem_cadastro.append(codigo)
        elif norm_u(codigo) in na_limpeza:
            ab.na_limpeza += 1
        elif material.oculto or _grupo(material.grupo) in ocultos:
            ab.ocultos += 1
        else:
            ab.itens.append(_item(material))
    return ab


def materiais_avulsa():
    """Materiais da saída avulsa: o cadastro com saldo positivo, menos os ocultos."""
    return Material.objects.filter(oculto=False, estoque__gt=0)


def catalogo_avulsa() -> list[ItemCatalogo]:
    """Itens da saída avulsa: o cadastro com saldo positivo, menos os ocultos (duplicado
    aparece bloqueado)."""
    return [_item(m) for m in materiais_avulsa()]
