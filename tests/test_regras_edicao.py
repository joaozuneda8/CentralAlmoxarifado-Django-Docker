"""Regras puras da edição do atendimento: estado da edição pelas linhas de saída e diferenças."""

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from pedidos.regras import (
    EstadoAtendimento,
    diferencas_atendimento,
    edicao_permitida,
    frase_diferenca,
)

ESTADO = EstadoAtendimento(
    cabecalho=("2026-10-09", "João", "ETA II", "BALCÃO", "", "", ""),
    entregues={"023.001.002": Decimal(2), "008.001.002": Decimal("1.5")},
    adicionados={},
    nomes={
        "023.001.002": "DETERGENTE NEUTRO",
        "008.001.002": "CAFÉ 500 G",
        "023.004.001": "PAPEL HIGIÊNICO",
    },
)


def linha(status, req="", lancado=None):
    return SimpleNamespace(status=status, requisicao_scpi=req, lancado_em=lancado)


@pytest.mark.parametrize(
    "linhas, chave",
    [
        ([linha("PENDENTE")], "editavel"),
        ([linha("NAO_LANCAR")], "editavel"),
        ([linha("ERRO")], "editavel"),
        ([linha("PENDENTE"), linha("EM_LANCAMENTO")], "suspensa"),
        ([linha("VERIFICAR")], "suspensa"),
        ([linha("LANCADA", "000123/26")], "bloqueada"),
        ([linha("PENDENTE"), linha("LANCADA", "000123/26")], "bloqueada"),
        ([linha("PENDENTE", "000123/26")], "bloqueada"),
    ],
)
def test_edicao_permitida_pelas_linhas(linhas, chave):
    assert edicao_permitida(True, linhas).chave == chave


def test_editavel_permite_e_nao_tem_motivo():
    e = edicao_permitida(True, [linha("PENDENTE")])
    assert e.permitida and e.motivo == ""


def test_sem_atendimento_nao_ha_edicao():
    e = edicao_permitida(False, [])
    assert e.chave == "antes_do_atendimento" and not e.permitida


def test_suspensa_manda_resolver_em_automacoes():
    e = edicao_permitida(True, [linha("VERIFICAR")])
    assert not e.permitida
    assert e.motivo == (
        "Edição suspensa: o robô não confirmou se a requisição foi gravada no SCPI. "
        "Resolva em Automações."
    )


def test_bloqueada_diz_requisicao_e_data():
    quando = datetime(2026, 10, 16, 15, 40)
    e = edicao_permitida(True, [linha("LANCADA", "004213/26", quando)])
    assert e.numeros == ("004213/26",) and e.lancado_em == quando and not e.permitida
    assert e.motivo == (
        "Lançado na requisição 004213/26 em 16/10/2026 15:40; correções são feitas no SCPI."
    )


def test_diferencas_vazias_quando_nada_muda():
    assert diferencas_atendimento(ESTADO, ESTADO) == []


def test_diferencas_do_cabecalho_entregue_troca_e_acrescimo():
    enviado = replace(
        ESTADO,
        cabecalho=("2026-10-09", "Ana", "ETA II", "BALCÃO", "", "", "1"),
        entregues={"023.001.002": Decimal(1), "008.001.002": Decimal("0")},
        adicionados={"023.004.001": ("008.001.002", Decimal(2))},
    )
    assert diferencas_atendimento(ESTADO, enviado) == [
        {"campo": "Recebedor", "antes": "João", "depois": "Ana"},
        {"campo": "Não lançar no SCPI", "antes": "Não", "depois": "Sim"},
        {
            "codigo": "023.001.002",
            "material": "DETERGENTE NEUTRO",
            "mudanca": "entregue",
            "antes": "2",
            "depois": "1",
        },
        {
            "codigo": "008.001.002",
            "material": "CAFÉ 500 G",
            "mudanca": "entregue",
            "antes": "1,5",
            "depois": "0",
        },
        {
            "codigo": "023.004.001",
            "material": "PAPEL HIGIÊNICO",
            "mudanca": "incluido",
            "antes": "",
            "depois": "2",
        },
    ]


def test_data_sai_no_formato_brasileiro():
    enviado = replace(ESTADO, cabecalho=("2026-10-01", *ESTADO.cabecalho[1:]))
    assert diferencas_atendimento(ESTADO, enviado) == [
        {"campo": "Data efetiva", "antes": "09/10/2026", "depois": "01/10/2026"}
    ]


def test_acrescentado_removido_e_troca_desfeita():
    gravado = replace(
        ESTADO,
        adicionados={
            "023.004.001": ("008.001.002", Decimal(2)),
            "016.005.010": ("", Decimal(1)),
        },
        nomes={**ESTADO.nomes, "016.005.010": "FITA VEDA ROSCA"},
    )
    enviado = replace(gravado, adicionados={"023.004.001": ("", Decimal(2))})
    assert diferencas_atendimento(gravado, enviado) == [
        {
            "codigo": "023.004.001",
            "material": "PAPEL HIGIÊNICO",
            "mudanca": "troca",
            "antes": "CAFÉ 500 G",
            "depois": "",
        },
        {
            "codigo": "016.005.010",
            "material": "FITA VEDA ROSCA",
            "mudanca": "removido",
            "antes": "1",
            "depois": "",
        },
    ]


def test_material_da_avulsa_incluido_e_removido():
    enviado = replace(ESTADO, entregues={"023.001.002": Decimal(2), "023.004.001": Decimal(3)})
    assert [(d["codigo"], d["mudanca"]) for d in diferencas_atendimento(ESTADO, enviado)] == [
        ("008.001.002", "removido"),
        ("023.004.001", "incluido"),
    ]


@pytest.mark.parametrize(
    "diferenca, frase",
    [
        ({"campo": "Recebedor", "antes": "João", "depois": "Ana"}, "Recebedor: João → Ana"),
        ({"campo": "Placa", "antes": "", "depois": "ABC1D23"}, "Placa: — → ABC1D23"),
        (
            {
                "codigo": "023.001.002",
                "material": "DETERGENTE NEUTRO",
                "mudanca": "entregue",
                "antes": "2",
                "depois": "1",
            },
            "DETERGENTE NEUTRO (023.001.002): entregue 2 → 1",
        ),
        (
            {"codigo": "1", "material": "X", "mudanca": "incluido", "antes": "", "depois": "2"},
            "X (1): incluído, 2",
        ),
        (
            {"codigo": "1", "material": "X", "mudanca": "removido", "antes": "2", "depois": ""},
            "X (1): removido (era 2)",
        ),
        (
            {"codigo": "1", "material": "X", "mudanca": "troca", "antes": "", "depois": "Y"},
            "X (1): agora no lugar de Y",
        ),
        (
            {"codigo": "1", "material": "X", "mudanca": "troca", "antes": "Y", "depois": ""},
            "X (1): deixou de ser troca",
        ),
    ],
)
def test_frase_diferenca(diferenca, frase):
    assert frase_diferenca(diferenca) == frase
