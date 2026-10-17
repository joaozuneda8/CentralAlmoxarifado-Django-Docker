"""Edição do atendimento (e da saída avulsa) até o lançamento no SCPI."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from pedidos.regras import LIMPEZA, Adicionado, diferencas_atendimento
from pedidos.servicos import confirmar_atendimento, estado_enviado, estado_gravado
from tests.cenario import envio_limpeza, montar_cenario, registrar, saida

pytestmark = pytest.mark.django_db
HOJE = date(2026, 10, 9)
TUDO = {"023.001.002": "2", "008.001.002": "1,5"}


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user(username="12345", password="x", first_name="Ana")


@pytest.fixture
def pedido():
    montar_cenario()
    return registrar(LIMPEZA, envio_limpeza()).pedido


def atender(pedido, usuario, qtds=None, adicionados=(), nao_lancar=False):
    r = confirmar_atendimento(
        pedido.id,
        uuid.uuid4(),
        saida(),
        TUDO if qtds is None else qtds,
        nao_lancar=nao_lancar,
        usuario=usuario,
        hoje=HOJE,
        adicionados=adicionados,
    )
    assert r.ok, r.erros
    pedido.refresh_from_db()
    return pedido


def test_estado_gravado_de_um_atendimento_com_troca(pedido, usuario):
    atender(
        pedido,
        usuario,
        {"023.001.002": "2", "008.001.002": "0", "023.004.001": "1"},
        adicionados=[Adicionado("023.004.001", "008.001.002")],
    )
    estado = estado_gravado(pedido)
    assert estado.cabecalho == ("2026-10-09", "João", "ETA II", "BALCÃO", "", "", "")
    assert estado.entregues == {"023.001.002": Decimal(2), "008.001.002": Decimal(0)}
    assert estado.adicionados == {"023.004.001": ("008.001.002", Decimal(1))}
    assert estado.nomes["023.004.001"] == "PAPEL HIGIÊNICO"


def test_estado_enviado_igual_ao_gravado_nao_tem_diferencas(pedido, usuario):
    atender(pedido, usuario)
    enviado = estado_enviado(
        pedido,
        saida(),
        False,
        {"023.001.002": Decimal(2), "008.001.002": Decimal("1.5")},
        [],
        {},
    )
    assert diferencas_atendimento(estado_gravado(pedido), enviado) == []
