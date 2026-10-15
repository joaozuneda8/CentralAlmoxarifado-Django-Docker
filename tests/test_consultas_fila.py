"""A fila do robô em SQL (`consultas.fila_do_robo`) concorda com a regra pura do robô
(`requisicoes.agrupar`)."""

import pytest

from pedidos.consultas import fila_do_robo, lotes_pendentes
from pedidos.models import LinhaSaida
from pedidos.regras import PENDENTE
from scpi.requisicoes import ESTADOS_TRAVA, agrupar
from tests.cenario import criar_pedido

pytestmark = pytest.mark.django_db


def lotes_do_robo():
    linhas = LinhaSaida.objects.filter(status__in=(PENDENTE, *ESTADOS_TRAVA)).order_by("id")
    grupos, _ = agrupar(list(linhas))
    return list(grupos)


def test_fila_concorda_com_a_regra_do_robo():
    casos = [
        [("PENDENTE", "")],
        [("PENDENTE", ""), ("VERIFICAR", "")],
        [("PENDENTE", ""), ("ERRO", "")],
        [("PENDENTE", ""), ("EM_LANCAMENTO", "")],
        [("PENDENTE", "003354/26")],
        [("LANCADA", "003355/26")],
        [("NAO_LANCAR", "")],
        [("PENDENTE", ""), ("LANCADA", "003356/26")],
        [("PENDENTE", ""), ("PENDENTE", "")],
        [("PENDENTE", "  ")],
    ]
    for linhas in casos:
        criar_pedido(atendido=True, linhas=linhas, itens=[("023.001.002", "2")])
    esperados = lotes_do_robo()
    assert len(esperados) == 4
    fila = fila_do_robo(limite=100)
    assert [r.lote for r in fila.requisicoes] == esperados
    assert fila.total == len(esperados) == lotes_pendentes()
    assert fila.fora == 0
    assert [r.materiais for r in fila.requisicoes] == [1, 1, 2, 1]
    ultimo = fila.requisicoes[2]
    assert (ultimo.recebedor, ultimo.centro_custo) == ("João", "ETA II")
    assert ultimo.data == LinhaSaida.objects.filter(lote=ultimo.lote).first().data


def test_fila_corta_no_limite_e_conta_o_resto(django_assert_max_num_queries):
    for _ in range(3):
        criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    with django_assert_max_num_queries(3):
        fila = fila_do_robo(limite=2)
    assert len(fila.requisicoes) == 2 and fila.total == 3 and fila.fora == 1
    for _ in range(5):
        criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    with django_assert_max_num_queries(3):
        fila_do_robo(limite=2)


def test_fila_vazia_e_limite_zero_nao_buscam_linhas(django_assert_max_num_queries):
    assert fila_do_robo().total == 0 and fila_do_robo().requisicoes == []
    criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    with django_assert_max_num_queries(1):
        fila = fila_do_robo(limite=0)
    assert fila.total == 1 and fila.requisicoes == [] and fila.fora == 1
