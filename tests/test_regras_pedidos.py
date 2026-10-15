"""Regras dos pedidos de limpeza e AB (casos de `tests/regras.test.cjs` do Apps Script)."""

from decimal import Decimal

import pytest

from catalogo.catalogos import ItemCatalogo
from pedidos.regras import (
    Centro,
    EnvioPedido,
    ItemEnviado,
    data_valida_iso,
    estoque_inteiro,
    normalizar_busca,
    opcoes_destino,
    parse_inteiro,
    parse_qtd_br,
    qtd_br,
    resolver_destino,
    somar_por_codigo,
    validar_pedido_ab,
    validar_pedido_limpeza,
)


def material(codigo, estoque, **extra):
    campos = {
        "codigo": codigo,
        "nome": f"MATERIAL {codigo}",
        "unidade": "UN",
        "categoria": "",
        "grupo": "GRUPO A",
        "subgrupo": "SUB 1",
        "estoque": estoque,
        "disponivel": estoque_inteiro(estoque),
        "duplicado": False,
    }
    campos.update(extra)
    return ItemCatalogo(**campos)


CATALOGO_AB = [
    material("001.000.010", Decimal(10)),
    material("002.000.005", Decimal(5), grupo="GRUPO B"),
    material("003.000.000", Decimal(0)),
    material("004.000.025", Decimal("2.5")),
    material("006.000.006", Decimal(10), duplicado=True),
]

CATALOGO_LIMPEZA = [
    material("023.001.002", Decimal(0), nome="DETERGENTE", categoria="Limpeza"),
    material("023.009.009", Decimal(0), nome="SABÃO", duplicado=True),
]
CENTROS = [
    Centro("ETA I", "12"),
    Centro("ETA II", "14"),
    Centro("PICKUP 01", "31", "ABC1D23"),
]


def itens(*pares):
    return tuple(ItemEnviado(c, q) for c, q in pares)


def ab(*pares, **extra):
    campos = {"solicitante": "Maria", "destino": "ETA II", "itens": itens(*pares)}
    campos.update(extra)
    return EnvioPedido(**campos)


def limpeza(*pares, **extra):
    campos = {"solicitante": "Ana", "destino": "ETA I", "itens": itens(*pares)}
    campos.update(extra)
    return EnvioPedido(**campos)


def textos(r):
    return [e.texto for e in r.erros]


def test_ab_pedido_valido_com_dois_grupos_e_aceito():
    r = validar_pedido_ab(ab(("001.000.010", "2"), ("002.000.005", "1")), CATALOGO_AB, CENTROS)
    assert not r.erros and len(r.validos) == 2


def test_ab_quantidade_igual_ao_estoque_passa_e_um_a_mais_e_recusado():
    assert not validar_pedido_ab(ab(("001.000.010", "10")), CATALOGO_AB, CENTROS).erros
    r = validar_pedido_ab(ab(("001.000.010", "11")), CATALOGO_AB, CENTROS)
    assert textos(r) == ["MATERIAL 001.000.010 (001.000.010): pedido 11 UN, estoque atual 10 UN."]
    assert r.estoque_atual == {"001.000.010": 10}


@pytest.mark.parametrize("q", [Decimal("1.5"), "1.5", "1,5", 0, -1, "abc", "", None, "1000000"])
def test_ab_quantidade_nao_inteira_ou_nao_positiva_e_recusada(q):
    assert len(validar_pedido_ab(ab(("001.000.010", q)), CATALOGO_AB, CENTROS).erros) == 1


def test_ab_aceita_texto_inteiro():
    r = validar_pedido_ab(ab(("001.000.010", "3")), CATALOGO_AB, CENTROS)
    assert r.validos[0].quantidade == 3
    assert r.validos[0].material is CATALOGO_AB[0]


def test_ab_estoque_fracionado_limita_a_parte_inteira():
    assert not validar_pedido_ab(ab(("004.000.025", "2")), CATALOGO_AB, CENTROS).erros
    assert len(validar_pedido_ab(ab(("004.000.025", "3")), CATALOGO_AB, CENTROS).erros) == 1
    assert textos(validar_pedido_ab(ab(("003.000.000", "1")), CATALOGO_AB, CENTROS)) == [
        "MATERIAL 003.000.000 (003.000.000) está sem estoque."
    ]


def test_ab_duplicado_e_fora_do_catalogo_sao_bloqueados():
    assert textos(validar_pedido_ab(ab(("006.000.006", "1")), CATALOGO_AB, CENTROS)) == [
        "O material 006.000.006 está com cadastro duplicado. Avise o almoxarifado."
    ]
    r = validar_pedido_ab(ab(("999.999.999", "1")), CATALOGO_AB, CENTROS)
    assert textos(r) == ["O material 999.999.999 não está mais disponível no catálogo."]
    assert r.estoque_atual["999.999.999"] == 0


def test_ab_mesmo_codigo_em_duas_linhas_soma_contra_o_estoque():
    r = validar_pedido_ab(ab(("001.000.010", "6"), ("001.000.010", "6")), CATALOGO_AB, CENTROS)
    assert len(r.erros) == 1
    ok = validar_pedido_ab(ab(("001.000.010", "5"), ("001.000.010", "5")), CATALOGO_AB, CENTROS)
    assert len(ok.validos) == 1 and ok.validos[0].quantidade == 10


def test_ab_um_item_invalido_em_tres_lista_so_ele():
    r = validar_pedido_ab(
        ab(("001.000.010", "1"), ("002.000.005", "9"), ("004.000.025", "1")), CATALOGO_AB, CENTROS
    )
    assert [e.codigo for e in r.erros] == ["002.000.005"]


def test_ab_campos_vazios_geram_tres_erros():
    r = validar_pedido_ab(EnvioPedido(solicitante=" ", destino=""), CATALOGO_AB, CENTROS)
    assert textos(r) == [
        "Informe o nome completo.",
        "Escolha o destino dos materiais na lista de centros de custo.",
        "Adicione ao menos um material ao pedido.",
    ]


def test_limpeza_aceita_decimal_br_e_recusa_ponto():
    ok = validar_pedido_limpeza(limpeza(("023.001.002", "1,5")), CATALOGO_LIMPEZA, CENTROS)
    assert not ok.erros and ok.validos[0].quantidade == Decimal("1.5")
    ruim = validar_pedido_limpeza(limpeza(("023.001.002", "1.5")), CATALOGO_LIMPEZA, CENTROS)
    assert textos(ruim) == [
        "Quantidade inválida para DETERGENTE (use vírgula para decimais, ex.: 1,5)."
    ]


def test_destino_tem_de_ser_um_centro_de_custo_nos_dois_formularios():
    par = ("023.001.002", "1")
    aceito = "PICKUP 01 — ABC1D23"
    assert not validar_pedido_limpeza(limpeza(par, destino=aceito), CATALOGO_LIMPEZA, CENTROS).erros
    for destino, erro in (
        ("Lua", 'Destino "Lua" não está na lista de centros de custo.'),
        ("eta ii", 'Destino "eta ii" não está na lista de centros de custo.'),
        ("Outro", 'Destino "Outro" não está na lista de centros de custo.'),
        ("", "Escolha o destino dos materiais na lista de centros de custo."),
    ):
        assert textos(
            validar_pedido_limpeza(limpeza(par, destino=destino), CATALOGO_LIMPEZA, CENTROS)
        ) == [erro]
        assert erro in textos(
            validar_pedido_ab(ab(("001.000.010", "1"), destino=destino), CATALOGO_AB, CENTROS)
        )


def test_limpeza_fora_do_catalogo_e_duplicado():
    r = validar_pedido_limpeza(
        limpeza(("999.999.999", "1"), ("023.009.009", "1")), CATALOGO_LIMPEZA, CENTROS
    )
    assert textos(r) == [
        "O material 999.999.999 não está mais no catálogo.",
        "O material 023.009.009 está com cadastro duplicado. Avise o almoxarifado.",
    ]


def test_opcoes_de_destino_sao_os_centros_e_as_placas():
    centros = [*CENTROS, Centro("PICKUP 01", "31", "DEF2G34")]
    assert opcoes_destino(centros) == [
        "ETA I",
        "ETA II",
        "PICKUP 01",
        "PICKUP 01 — ABC1D23",
        "PICKUP 01 — DEF2G34",
    ]
    assert opcoes_destino([]) == []


def test_resolver_destino():
    assert resolver_destino("eta  ii", CENTROS) == "ETA II"
    assert resolver_destino(" ETA I ", CENTROS) == "ETA I"
    assert resolver_destino("pickup 01 — abc1d23", CENTROS) == "PICKUP 01 — ABC1D23"
    assert resolver_destino("abc-1d23", CENTROS) == "PICKUP 01 — ABC1D23"
    assert resolver_destino("Portaria", CENTROS) == ""
    assert resolver_destino("  ", CENTROS) == ""
    assert resolver_destino("---", [Centro("SEM PLACA", "1")]) == ""


def test_resolver_destino_prefere_a_grafia_exata():
    centros = [Centro("Oficina", "1"), Centro("OFICINA", "2")]
    assert resolver_destino("OFICINA", centros) == "OFICINA"
    assert resolver_destino("Oficina", centros) == "Oficina"
    assert resolver_destino("oficina", centros) == "Oficina"


def test_conversoes():
    assert qtd_br(Decimal("1.5")) == "1,5"
    assert qtd_br(3) == "3"
    assert qtd_br(Decimal("2.000")) == "2"
    assert parse_qtd_br("1,5") == Decimal("1.5")
    assert parse_qtd_br(" 2 ") == 2
    assert parse_qtd_br("1.5") is None
    assert parse_qtd_br("1,2345") is None
    assert parse_qtd_br("999999") == 999999
    assert parse_qtd_br("1000000") is None
    assert parse_inteiro("3") == 3
    assert parse_inteiro("1,5") is None
    assert parse_inteiro(True) is None
    assert parse_inteiro(Decimal("2")) == 2
    assert parse_inteiro(Decimal("2.5")) is None
    assert data_valida_iso("2026-02-30") is False
    assert data_valida_iso("09/10/2026") is False
    assert data_valida_iso("2026-10-09") is True
    assert normalizar_busca("PROTEÇÃO") == "protecao"


def test_somar_por_codigo_mantem_a_ordem_e_separa_invalidos():
    s = somar_por_codigo(itens(("B", "1"), ("A", "2"), ("B", "3"), ("C", "x")), parse_inteiro)
    assert s.ordem == ["B", "A"]
    assert s.soma == {"B": 4, "A": 2}
    assert [i.codigo for i in s.invalidos] == ["C"]


def test_erros_de_nome_e_destino_dizem_o_campo_nos_dois_formularios():
    vazio = {"solicitante": " ", "destino": ""}
    for r in (
        validar_pedido_limpeza(limpeza(**vazio), CATALOGO_LIMPEZA, CENTROS),
        validar_pedido_ab(ab(**vazio), CATALOGO_AB, CENTROS),
    ):
        assert [(e.texto, e.campo) for e in r.erros] == [
            ("Informe o nome completo.", "solicitante"),
            ("Escolha o destino dos materiais na lista de centros de custo.", "destino"),
            ("Adicione ao menos um material ao pedido.", None),
        ]
    fora = validar_pedido_limpeza(
        limpeza(("023.001.002", "1"), destino="Lua"), CATALOGO_LIMPEZA, CENTROS
    )
    assert [e.campo for e in fora.erros] == ["destino"]


def test_erros_de_material_nao_tem_campo():
    r = validar_pedido_ab(ab(("003.000.000", "1"), ("999.999.999", "x")), CATALOGO_AB, CENTROS)
    assert r.erros and all(e.campo is None and e.codigo for e in r.erros)
    r = validar_pedido_limpeza(limpeza(("023.001.002", "1.5")), CATALOGO_LIMPEZA, CENTROS)
    assert r.erros and all(e.campo is None for e in r.erros)
