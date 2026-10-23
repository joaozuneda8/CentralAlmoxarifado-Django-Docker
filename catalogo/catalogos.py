"""Catálogos de materiais dos formulários, montados do banco a cada consulta (sem cache).

Traduz `montarCatalogos_` do `Catalogo.gs`: limpeza vem do `ItemLimpeza`; AB, das saídas do
SCPI no período da curva ABC, consolidadas pelo de/para e ordenadas por número de ocorrências; a
saída avulsa, de todo material não oculto e com saldo positivo; o de viaturas, da `PecaViatura`
seguida do catálogo AB (spec 006); o da oficina mecânica, dos grupos da lista `GRUPO_OFICINA` e dos
`MaterialOficina` (spec 007). Em todos, o material `duplicado`
aparece (bloqueado pelo formulário).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from catalogo.consultas_curva import consolidado
from catalogo.curva import periodo
from catalogo.models import (
    CentroCusto,
    ConfiguracaoCurva,
    ItemLimpeza,
    Material,
    Opcao,
    PecaViatura,
)
from pedidos.regras import CENTRO_OFICINA, Centro, estoque_inteiro, norm_u

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
    # A unidade do SCPI (não a exibida) admite fração: decide a regra de quantidade do formulário
    # público. O padrão é o lado seguro, só inteiro.
    fracionavel: bool = False


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


def unidades_fracionaveis() -> set[str]:
    """As unidades do SCPI em que a quantidade pode ter fração (lista mantida no admin),
    normalizadas como `norm_u`. Lista vazia: nenhuma, e todo material aceita só inteiro."""
    return {norm_u(v) for v in Opcao.valores(Opcao.Lista.UNIDADE_FRACIONAVEL)}


def _item(material: Material, fracionaveis: set[str], **outros) -> ItemCatalogo:
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
        # Pela unidade do cadastro do SCPI, antes de `outros` trocar o texto exibido.
        "fracionavel": norm_u(material.unidade) in fracionaveis,
    }
    campos.update(outros)
    return ItemCatalogo(**campos)


def catalogo_limpeza() -> list[ItemCatalogo]:
    """Itens do formulário de limpeza cujo material não está oculto; nome e unidade
    exibidos têm prioridade sobre o cadastro."""
    itens = ItemLimpeza.objects.select_related("material").filter(material__oculto=False)
    fracionaveis = unidades_fracionaveis()
    return [
        _item(
            i.material,
            fracionaveis,
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
    fracionaveis = unidades_fracionaveis()
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
            ab.itens.append(_item(material, fracionaveis))
    return ab


def materiais_avulsa():
    """Materiais da saída avulsa: o cadastro com saldo positivo, menos os ocultos."""
    return Material.objects.filter(oculto=False, estoque__gt=0)


def catalogo_avulsa() -> list[ItemCatalogo]:
    """Itens da saída avulsa: o cadastro com saldo positivo, menos os ocultos (duplicado
    aparece bloqueado)."""
    fracionaveis = unidades_fracionaveis()
    return [_item(m, fracionaveis) for m in materiais_avulsa()]


def formulario_limpeza() -> list[ItemCatalogo] | None:
    """O catálogo do formulário de limpeza, ou None se ele está indisponível: o saldo nunca foi
    importado (o formulário limita pelo saldo) ou não há item algum."""
    return (catalogo_limpeza() if saldo_importado() else None) or None


def formulario_ab() -> list[ItemCatalogo] | None:
    """O catálogo do formulário AB, ou None se ele está indisponível: o saldo nunca foi importado
    ou nenhum material com saída entra no catálogo."""
    ab = catalogo_ab()
    return (ab.itens if ab is not None else None) or None


def formulario_avulsa() -> list[ItemCatalogo] | None:
    """O catálogo da saída avulsa, ou None se nenhum material tem saldo."""
    return catalogo_avulsa() or None


def catalogo_viaturas() -> list[ItemCatalogo]:
    """Peças da lista das viaturas (spec 006), na ordem da lista, sem as de material oculto; o
    nome exibido tem prioridade sobre o do cadastro, e a unidade é sempre a do SCPI."""
    pecas = PecaViatura.objects.select_related("material").filter(material__oculto=False)
    fracionaveis = unidades_fracionaveis()
    return [_item(p.material, fracionaveis, nome=p.nome_exibido or p.material.nome) for p in pecas]


def formulario_viaturas() -> list[ItemCatalogo] | None:
    """O catálogo do formulário de viaturas: a lista e, depois, o catálogo AB sem repetir as peças
    da lista; None se o saldo nunca foi importado ou não há nada a oferecer."""
    if not saldo_importado():
        return None
    lista = catalogo_viaturas()
    na_lista = {norm_u(i.codigo) for i in lista}
    ab = catalogo_ab()
    resto = [i for i in (ab.itens if ab is not None else []) if norm_u(i.codigo) not in na_lista]
    return (lista + resto) or None


def folha_viaturas() -> list[str]:
    """Os códigos da folha do formulário de viaturas: a lista visível, na ordem."""
    return [i.codigo for i in catalogo_viaturas()]


def centros_equipe_manutencao() -> list[Centro]:
    """Destinos do formulário de viaturas: os centros de custo com alguma linha marcada como de
    equipe de manutenção, um por descrição e sem placa (o pedido não identifica a viatura)."""
    centros: dict[str, Centro] = {}
    for c in CentroCusto.objects.filter(equipe_manutencao=True).order_by("descricao", "codigo"):
        centros.setdefault(c.descricao, Centro(c.descricao, c.codigo))
    return list(centros.values())


def grupos_oficina() -> set[str]:
    """Os grupos do formulário da oficina mecânica (spec 007), normalizados como os ocultos do AB.
    Lista vazia: nenhum grupo (sem padrão)."""
    return {_grupo(v) for v in Opcao.valores(Opcao.Lista.GRUPO_OFICINA)}


def catalogo_oficina() -> list[ItemCatalogo]:
    """Materiais do formulário da oficina: os não ocultos dos grupos da oficina e os avulsos
    (`MaterialOficina`), uma vez cada, pelo nome; a unidade é a do SCPI."""
    grupos = grupos_oficina()
    visiveis = Material.objects.filter(oculto=False)
    casados = [
        g for g in visiveis.values_list("grupo", flat=True).distinct() if _grupo(g) in grupos
    ]
    materiais = visiveis.filter(Q(grupo__in=casados) | Q(material_oficina__isnull=False))
    fracionaveis = unidades_fracionaveis()
    return [_item(m, fracionaveis) for m in materiais.distinct().order_by("nome", "codigo")]


def formulario_oficina() -> list[ItemCatalogo] | None:
    """O catálogo do formulário da oficina, ou None se ele está indisponível: o saldo nunca foi
    importado ou a escolha da oficina não tem material visível."""
    return (catalogo_oficina() if saldo_importado() else None) or None


def grupos_epis() -> set[str]:
    """Os grupos do formulário de EPIs (spec 008), normalizados como os da oficina. Lista vazia:
    nenhum grupo (sem padrão)."""
    return {_grupo(v) for v in Opcao.valores(Opcao.Lista.GRUPO_EPI)}


def catalogo_epis() -> list[ItemCatalogo]:
    """Materiais do formulário de EPIs: os não ocultos dos grupos de EPIs e os avulsos
    (`MaterialEpi`), uma vez cada, pelo nome; a unidade é a do SCPI."""
    grupos = grupos_epis()
    visiveis = Material.objects.filter(oculto=False)
    casados = [
        g for g in visiveis.values_list("grupo", flat=True).distinct() if _grupo(g) in grupos
    ]
    materiais = visiveis.filter(Q(grupo__in=casados) | Q(material_epi__isnull=False))
    fracionaveis = unidades_fracionaveis()
    return [_item(m, fracionaveis) for m in materiais.distinct().order_by("nome", "codigo")]


def formulario_epis() -> list[ItemCatalogo] | None:
    """O catálogo do formulário de EPIs, ou None se ele está indisponível: o saldo nunca foi
    importado ou a escolha dos EPIs não tem material visível."""
    return (catalogo_epis() if saldo_importado() else None) or None


def centros_oficina() -> list[Centro]:
    """Destinos do formulário da oficina: o centro OFICINA MECÂNICA (a linha sem placa) e cada
    viatura (centro com placa), esta só como "centro — placa"."""
    oficina = [
        Centro(c.descricao, c.codigo)
        for c in CentroCusto.objects.filter(placa__isnull=True).order_by("codigo")
        if norm_u(c.descricao) == norm_u(CENTRO_OFICINA)
    ][:1]
    viaturas = [
        Centro(c.descricao, c.codigo, c.placa, so_com_placa=True)
        for c in CentroCusto.objects.filter(placa__isnull=False).order_by("descricao", "placa")
    ]
    return oficina + viaturas
