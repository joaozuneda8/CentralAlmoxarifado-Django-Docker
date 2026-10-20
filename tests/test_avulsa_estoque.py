"""Saída avulsa: só material com estoque e quantidade limitada ao saldo do cadastro."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from catalogo.models import Material
from pedidos.carrinho import LinhaCarrinho, adicionar, alterar
from pedidos.fluxos import FLUXOS
from pedidos.models import ItemPedido
from pedidos.regras import LIMPEZA, Adicionado, EnvioSaida
from pedidos.servicos import (
    catalogo_de,
    confirmar_atendimento,
    editar_saida_avulsa,
    registrar_saida_avulsa,
)
from tests.cenario import criar_pedido, itens, montar_cenario, saida
from tests.test_carrinho import item

pytestmark = pytest.mark.django_db
HOJE = date(2026, 10, 9)
AVULSA_F = FLUXOS["avulsa"]
PAPEL = "023.004.001"  # estoque 50
FITA = "016.005.010"  # estoque 10
BOTINA = "013.006.001"  # estoque 2,5
DETERGENTE = "023.001.002"  # estoque 0


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user(username="12345", password="x", first_name="Ana")


@pytest.fixture(autouse=True)
def cenario():
    montar_cenario()


def registrar(usuario, *pares):
    return registrar_saida_avulsa(
        uuid.uuid4(), EnvioSaida(saida(), itens(*pares)), usuario=usuario, hoje=HOJE
    )


def textos(r):
    return [e.texto for e in r.erros]


# --- A lista ---------------------------------------------------------------------------------


def test_catalogo_da_avulsa_so_tem_material_com_estoque():
    codigos = {i.codigo for i in catalogo_de("AVULSA")}
    assert codigos == {PAPEL, FITA, BOTINA}


# --- O registro ------------------------------------------------------------------------------


def test_registra_ate_o_estoque_inclusive(usuario):
    assert registrar(usuario, (FITA, "10")).ok


def test_recusa_acima_do_estoque(usuario):
    r = registrar(usuario, (FITA, "11"))
    assert not r.ok
    assert textos(r) == [f"Saída de {FITA} maior que o estoque (10)."]


def test_estoque_fracionado_vale_exato(usuario):
    assert registrar(usuario, (BOTINA, "2,5")).ok
    r = registrar(usuario, (BOTINA, "2,6"))
    assert textos(r) == [f"Saída de {BOTINA} maior que o estoque (2,5)."]


def test_material_sem_estoque_nao_e_encontrado(usuario):
    r = registrar(usuario, (DETERGENTE, "1"))
    assert not r.ok
    assert textos(r) == [f"Material {DETERGENTE} não encontrado no cadastro."]


def test_soma_do_mesmo_material_conta_no_limite(usuario):
    r = registrar(usuario, (FITA, "6"), (FITA, "5"))
    assert textos(r) == [f"Saída de {FITA} maior que o estoque (10)."]


# --- A edição --------------------------------------------------------------------------------


def editar(pedido, usuario, *pares, dados=None):
    pedido.refresh_from_db()
    return editar_saida_avulsa(
        pedido.id,
        pedido.versao,
        EnvioSaida(dados or saida(), itens(*pares)),
        usuario=usuario,
        hoje=HOJE,
    )


def test_edicao_recusa_acima_do_estoque(usuario):
    pedido = registrar(usuario, (FITA, "2")).pedido
    r = editar(pedido, usuario, (FITA, "11"))
    assert textos(r) == [f"Saída de {FITA} maior que o estoque (10)."]
    assert editar(pedido, usuario, (FITA, "10")).ok


def test_edicao_aceita_o_gravado_mesmo_com_saldo_menor(usuario):
    """O SCPI pode ter abatido parte do saldo: o que já está na saída continua valendo, mas
    a quantidade não sobe além dele."""
    pedido = registrar(usuario, (FITA, "4")).pedido
    Material.objects.filter(codigo=FITA).update(estoque=Decimal(1))
    assert editar(pedido, usuario, (FITA, "4"), dados=saida(recebedor="Ana")).ok
    assert editar(pedido, usuario, (FITA, "3")).ok
    # O teto acompanha o que ficou gravado.
    r = editar(pedido, usuario, (FITA, "4"))
    assert textos(r) == [f"Saída de {FITA} maior que o estoque (3)."]


def test_edicao_aceita_o_gravado_que_zerou(usuario):
    pedido = registrar(usuario, (FITA, "4")).pedido
    Material.objects.filter(codigo=FITA).update(estoque=Decimal(0))
    assert editar(pedido, usuario, (FITA, "4"), dados=saida(recebedor="Ana")).ok
    assert textos(editar(pedido, usuario, (FITA, "5"))) == [
        f"Saída de {FITA} maior que o estoque (4)."
    ]


# --- O acréscimo no atendimento --------------------------------------------------------------


def atender(pedido, usuario, qtds, adicionados):
    return confirmar_atendimento(
        pedido.id,
        uuid.uuid4(),
        saida(),
        qtds,
        nao_lancar=False,
        usuario=usuario,
        hoje=HOJE,
        adicionados=adicionados,
    )


@pytest.fixture
def pedido():
    return criar_pedido(origem=LIMPEZA, itens=((DETERGENTE, "2"),))


def test_acrescimo_acima_do_estoque_e_recusado(pedido, usuario):
    qtds = {DETERGENTE: "2", FITA: "11"}
    r = atender(pedido, usuario, qtds, [Adicionado(FITA)])
    assert textos(r) == [f"Saída de {FITA} maior que o estoque (10)."]
    assert not ItemPedido.objects.filter(origem=ItemPedido.Origem.ALMOXARIFADO).exists()
    assert atender(pedido, usuario, {DETERGENTE: "2", FITA: "10"}, [Adicionado(FITA)]).ok


def test_acrescimo_gravado_continua_aceito_na_edicao_com_saldo_menor(pedido, usuario):
    from pedidos.servicos import editar_atendimento

    qtds = {DETERGENTE: "2", FITA: "4"}
    assert atender(pedido, usuario, qtds, [Adicionado(FITA)]).ok
    Material.objects.filter(codigo=FITA).update(estoque=Decimal(1))
    pedido.refresh_from_db()

    def editar_atend(qtds):
        pedido.refresh_from_db()
        return editar_atendimento(
            pedido.id,
            pedido.versao,
            saida(recebedor="Ana"),
            qtds,
            nao_lancar=False,
            usuario=usuario,
            hoje=HOJE,
            adicionados=[Adicionado(FITA)],
        )

    assert editar_atend(qtds).ok
    assert textos(editar_atend({DETERGENTE: "2", FITA: "5"})) == [
        f"Saída de {FITA} maior que o estoque (4)."
    ]


# --- O carrinho (resposta imediata do Adicionar e do Alterar) --------------------------------

FITA_ITEM = item(FITA, "FITA", 10)
BOTINA_ITEM = item(BOTINA, "BOTINA", Decimal("2.5"))


def test_carrinho_adiciona_ate_o_estoque_e_recusa_acima():
    assert adicionar([], AVULSA_F, FITA_ITEM, "10").erro == ""
    assert adicionar([], AVULSA_F, FITA_ITEM, "11").erro == (
        "Quantidade acima do estoque. Estoque disponível: 10 UN."
    )


def test_carrinho_usa_o_estoque_fracionado():
    assert adicionar([], AVULSA_F, BOTINA_ITEM, "2,5").erro == ""
    assert adicionar([], AVULSA_F, BOTINA_ITEM, "2,6").erro == (
        "Quantidade acima do estoque. Estoque disponível: 2,5 UN."
    )


def test_carrinho_soma_com_o_que_ja_esta_no_pedido():
    linhas = [LinhaCarrinho(FITA, 8, FITA_ITEM)]
    assert adicionar(linhas, AVULSA_F, FITA_ITEM, "3").erro == (
        "Já há 8 UN no pedido; é possível acrescentar no máximo 2 UN."
    )
    assert adicionar(linhas, AVULSA_F, FITA_ITEM, "2").erro == ""


def test_carrinho_altera_dentro_do_estoque_apenas():
    linhas = [LinhaCarrinho(FITA, 2, FITA_ITEM)]
    assert alterar(linhas, AVULSA_F, FITA_ITEM, "10").erro == ""
    assert alterar(linhas, AVULSA_F, FITA_ITEM, "11").erro.startswith("Quantidade acima do estoque")


def test_limpeza_continua_sem_limite_de_estoque():
    assert adicionar([], FLUXOS["limpeza"], item(DETERGENTE, "D", 0), "5").erro == ""


def test_carrinho_da_edicao_deixa_reduzir_quando_o_saldo_caiu(client, usuario):
    """O saldo do SCPI caiu abaixo do gravado: reduzir a quantidade não pode ser recusado. No
    registro (sem `versao`) o saldo continua sendo o teto."""
    client.force_login(usuario)
    Material.objects.filter(codigo=FITA).update(estoque=Decimal(1))
    corpo = {
        "item_codigo": [FITA],
        "item_qtd": ["3"],
        "alterar": FITA,
        "anterior": "4",
    }
    url = reverse("pedidos:avulsa_carrinho")
    editando = client.post(url, {**corpo, "versao": "0"}).text
    assert "Quantidade acima do estoque" not in editando
    assert 'name="item_qtd" value="3"' in editando
    novo = client.post(url, corpo).text
    assert "Quantidade acima do estoque" in novo


# --- O "Adicionar" do atendimento ------------------------------------------------------------


def test_adicionar_do_atendimento_recusa_acima_do_estoque(client, usuario, pedido):
    client.force_login(usuario)
    url = reverse("pedidos:atendimento_adicionar", args=[pedido.numero])
    r = client.post(url, {"adicionar": FITA, f"qtd-{FITA}": "11"})
    assert r["HX-Retarget"] == "#adicionar-erro"
    assert "Quantidade acima do estoque. Estoque disponível: 10 UN." in r.text
    r = client.post(url, {"adicionar": FITA, f"qtd-{FITA}": "10"})
    assert "HX-Retarget" not in r and f'data-adicionado="{FITA}"' in r.text
