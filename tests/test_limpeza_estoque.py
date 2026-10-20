"""Formulário de limpeza: nega pedido acima do estoque e material sem estoque."""

from decimal import Decimal

import pytest
from django.urls import reverse

from catalogo.models import Material
from pedidos.carrinho import LinhaCarrinho, adicionar, alterar
from pedidos.fluxos import FLUXOS
from pedidos.models import Pedido
from pedidos.regras import LIMPEZA
from pedidos.servicos import catalogo_de
from tests.cenario import envio_limpeza, itens, montar_cenario, registrar
from tests.test_carrinho import item

pytestmark = pytest.mark.django_db
LIMPEZA_F = FLUXOS["limpeza"]
DETERGENTE = "023.001.002"  # saldo 100 no cenário
CAFE = "008.001.002"  # saldo 100 no cenário


@pytest.fixture(autouse=True)
def cenario():
    montar_cenario()


def saldo(codigo, estoque):
    Material.objects.filter(codigo=codigo).update(estoque=Decimal(estoque))


def pedir(*pares):
    return registrar(LIMPEZA, envio_limpeza(itens=itens(*pares)))


def textos(r):
    return [e.texto for e in r.erros]


# --- O envio ---------------------------------------------------------------------------------


def test_aceita_ate_o_saldo_inclusive_fracionado():
    saldo(DETERGENTE, 3)
    saldo(CAFE, "2.5")
    assert pedir((DETERGENTE, "3"), (CAFE, "2,5")).ok


def test_nega_acima_do_saldo_e_nao_grava():
    saldo(DETERGENTE, 3)
    r = pedir((DETERGENTE, "4"))
    assert not r.ok
    assert textos(r) == ["DETERGENTE NEUTRO (023.001.002): pedido 4 UN, estoque atual 3 UN."]
    assert not Pedido.objects.exists()


def test_nega_material_sem_estoque():
    saldo(DETERGENTE, 0)
    r = pedir((DETERGENTE, "1"))
    assert textos(r) == ["DETERGENTE NEUTRO (023.001.002) está sem estoque."]


def test_formulario_fica_indisponivel_se_o_saldo_nunca_foi_importado():
    Material.objects.update(estoque_em=None)
    assert catalogo_de(LIMPEZA) is None
    assert not pedir((DETERGENTE, "1")).ok


# --- O carrinho ------------------------------------------------------------------------------

SABAO = item("023.001.002", "SABÃO", 5, unidade="UN")


def test_carrinho_nega_acima_do_saldo_e_soma_o_que_ja_esta():
    assert adicionar([], LIMPEZA_F, SABAO, "5").erro == ""
    assert adicionar([], LIMPEZA_F, SABAO, "6").erro == (
        "Quantidade acima do estoque. Estoque disponível: 5 UN."
    )
    linhas = [LinhaCarrinho(SABAO.codigo, Decimal(4), SABAO)]
    assert adicionar(linhas, LIMPEZA_F, SABAO, "2").erro == (
        "Já há 4 UN no pedido; é possível acrescentar no máximo 1 UN."
    )
    assert alterar(linhas, LIMPEZA_F, SABAO, "6").erro.startswith("Quantidade acima do estoque")
    assert alterar(linhas, LIMPEZA_F, SABAO, "5").erro == ""


def test_carrinho_usa_o_saldo_fracionado_e_nao_o_inteiro():
    meio = item("1", "SABÃO", Decimal("0.5"), unidade="UN")
    assert adicionar([], LIMPEZA_F, meio, "0,5").erro == ""
    assert adicionar([], LIMPEZA_F, meio, "0,6").erro == (
        "Quantidade acima do estoque. Estoque disponível: 0,5 UN."
    )


def test_carrinho_bloqueia_material_sem_estoque():
    zerado = item("1", "SABÃO", 0, unidade="UN")
    assert adicionar([], LIMPEZA_F, zerado, "1").erro == (
        "SABÃO (1): Sem estoque — não pode ser adicionado."
    )


# --- As telas --------------------------------------------------------------------------------


def test_busca_poe_o_sem_estoque_no_fim_com_o_selo(client):
    saldo(DETERGENTE, 0)
    r = client.get(reverse("pedidos:materiais", args=["limpeza"]), {"q": ""}).text
    assert r.index("PAPEL HIGIÊNICO") < r.index("DETERGENTE NEUTRO")
    bloqueado = r[r.index("DETERGENTE NEUTRO") :]
    assert "Sem estoque" in bloqueado[: bloqueado.index("</li>")]


def test_endpoint_do_carrinho_recusa_acima_do_saldo(client):
    saldo(DETERGENTE, 3)
    url = reverse("pedidos:carrinho", args=["limpeza"])
    ruim = client.post(url, {"adicionar": DETERGENTE, f"qtd-{DETERGENTE}": "4"}).text
    assert "Quantidade acima do estoque. Estoque disponível: 3 UN." in ruim
    assert f'name="item_codigo" value="{DETERGENTE}"' not in ruim
    bom = client.post(url, {"adicionar": DETERGENTE, f"qtd-{DETERGENTE}": "3"}).text
    assert f'name="item_codigo" value="{DETERGENTE}"' in bom
