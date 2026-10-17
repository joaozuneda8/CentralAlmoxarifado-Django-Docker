"""Edição do atendimento (e da saída avulsa) até o lançamento no SCPI."""

import re
import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from catalogo.models import CentroCusto, Material
from pedidos.consultas import fila_do_robo
from pedidos.models import AlteracaoPedido, Atendimento, ItemPedido, LinhaSaida, Pedido
from pedidos.regras import AB, AVULSA, LIMPEZA, Adicionado, EnvioSaida, diferencas_atendimento
from pedidos.servicos import (
    confirmar_atendimento,
    editar_atendimento,
    editar_saida_avulsa,
    estado_enviado,
    estado_gravado,
    registrar_saida_avulsa,
)
from tests.cenario import (
    criar_pedido,
    em_paralelo,
    envio_ab,
    envio_limpeza,
    itens,
    montar_cenario,
    registrar,
    saida,
)

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


# ---------------------------------------------------------------------------
# Serviço `editar_atendimento`
# ---------------------------------------------------------------------------


@pytest.fixture
def atendido(pedido, usuario):
    return atender(pedido, usuario)


def editar(pedido, usuario, versao=None, dados=None, qtds=None, adicionados=(), nao_lancar=False):
    pedido.refresh_from_db()
    return editar_atendimento(
        pedido.id,
        pedido.versao if versao is None else versao,
        dados or saida(),
        TUDO if qtds is None else qtds,
        nao_lancar=nao_lancar,
        adicionados=adicionados,
        usuario=usuario,
        hoje=HOJE,
    )


def ids_das_linhas():
    return set(LinhaSaida.objects.values_list("id", flat=True))


def textos(r):
    return [e.texto for e in r.erros]


def test_edicao_grava_entregas_recria_linhas_e_registra(atendido, usuario):
    antes = ids_das_linhas()
    r = editar(atendido, usuario, qtds={"023.001.002": "2", "008.001.002": "1"})
    assert r.ok, r.erros
    assert r.mensagem == "Alterações salvas no pedido P-000001."
    atendido.refresh_from_db()
    assert atendido.versao == 1
    assert ids_das_linhas().isdisjoint(antes) and len(ids_das_linhas()) == 2
    assert LinhaSaida.objects.get(codigo="008.001.002").qtd == Decimal("1")
    assert ItemPedido.objects.get(codigo="008.001.002").qtd_entregue == Decimal("1")
    alteracao = AlteracaoPedido.objects.get()
    assert alteracao.versao == 1 and alteracao.usuario == usuario
    assert alteracao.diferencas == [
        {
            "codigo": "008.001.002",
            "material": "CAFÉ 500 G",
            "mudanca": "entregue",
            "antes": "1,5",
            "depois": "1",
        }
    ]
    assert r.diferencas == alteracao.diferencas
    for linha in LinhaSaida.objects.all():
        assert linha.status == "PENDENTE"
        assert linha.mensagem.startswith("Refeita na edição de ")
        assert linha.mensagem.endswith(" por 12345.")


def test_edicao_regrava_os_dados_da_saida_nas_linhas(atendido, usuario):
    r = editar(atendido, usuario, dados=saida(recebedor="Ana", centro_custo="ETA I"))
    assert r.ok, r.erros
    a = Atendimento.objects.get()
    assert (a.recebedor, a.centro_custo) == ("Ana", "ETA I")
    assert set(LinhaSaida.objects.values_list("recebedor", "centro_custo")) == {("Ana", "ETA I")}
    assert a.atendido_por == usuario


def test_edicao_zera_recibo_impresso(atendido, usuario):
    Atendimento.objects.update(recibo_impresso_em=timezone.now())
    assert editar(atendido, usuario, dados=saida(recebedor="Ana")).ok
    assert Atendimento.objects.get().recibo_impresso_em is None


def test_edicao_nao_muda_cabecalho_nem_qtd_pedida(atendido, usuario):
    qtds = {**TUDO, "999.999.999": "4"}
    assert editar(atendido, usuario, dados=saida(recebedor="Ana"), qtds=qtds).ok
    p = Pedido.objects.get()
    assert (p.solicitante, p.destino, p.obs) == ("Ana", "ETA II", "")
    assert dict(ItemPedido.objects.values_list("codigo", "qtd_pedida")) == {
        "023.001.002": Decimal(2),
        "008.001.002": Decimal("1.5"),
    }


def test_sem_mudanca_nao_grava_nada(atendido, usuario):
    antes = ids_das_linhas()
    r = editar(atendido, usuario)
    assert r.ok and r.mensagem == "Nada mudou; nada foi gravado." and r.diferencas == []
    assert Pedido.objects.get().versao == 0
    assert not AlteracaoPedido.objects.exists()
    assert ids_das_linhas() == antes


@pytest.mark.parametrize(
    "dados, qtds, adicionados, trecho",
    [
        (saida(data="2026-10-10"), TUDO, (), "não pode ser futura"),
        (saida(centro_custo="NÃO EXISTE"), TUDO, (), "não está na lista"),
        (
            saida(),
            {**TUDO, "023.004.001": "1"},
            (Adicionado("023.004.001", "008.001.002"),),
            "foi trocado por outro material",
        ),
    ],
)
def test_recusas_da_validacao(atendido, usuario, dados, qtds, adicionados, trecho):
    r = editar(atendido, usuario, dados=dados, qtds=qtds, adicionados=adicionados)
    assert not r.ok and r.mensagem == "Corrija os dados da saída."
    assert any(trecho in t for t in textos(r)), textos(r)
    assert Pedido.objects.get().versao == 0


def test_zerar_tudo_recusa_ao_menos_um_material(atendido, usuario):
    antes = ids_das_linhas()
    r = editar(atendido, usuario, qtds={"023.001.002": "0", "008.001.002": "0"})
    assert not r.ok
    assert "Informe ao menos um material com quantidade maior que zero." in textos(r)
    assert ids_das_linhas() == antes


@pytest.mark.parametrize("status", ["PENDENTE", "NAO_LANCAR", "ERRO"])
def test_status_que_permitem_editar(atendido, usuario, status):
    LinhaSaida.objects.update(status=status)
    assert editar(atendido, usuario, dados=saida(recebedor="Ana")).ok


@pytest.mark.parametrize(
    "status, requisicao",
    [
        ("EM_LANCAMENTO", ""),
        ("VERIFICAR", ""),
        ("LANCADA", "000123/26"),
        ("PENDENTE", "000123/26"),
    ],
)
def test_status_que_recusam_a_edicao(atendido, usuario, status, requisicao):
    LinhaSaida.objects.update(status=status, requisicao_scpi=requisicao)
    antes = set(LinhaSaida.objects.values_list("id", "status", "requisicao_scpi"))
    r = editar(atendido, usuario, dados=saida(recebedor="Ana"))
    assert not r.ok and r.motivo == "lancamento"
    assert r.diferencas == [{"campo": "Recebedor", "antes": "João", "depois": "Ana"}]
    assert set(LinhaSaida.objects.values_list("id", "status", "requisicao_scpi")) == antes
    assert Atendimento.objects.get().recebedor == "João"


def test_parcialmente_lancado_recusa(atendido, usuario):
    primeira = LinhaSaida.objects.order_by("seq").first()
    LinhaSaida.objects.filter(pk=primeira.pk).update(status="LANCADA", requisicao_scpi="000123/26")
    r = editar(atendido, usuario, dados=saida(recebedor="Ana"))
    assert not r.ok and r.motivo == "lancamento"
    assert r.mensagem.startswith("Lançado na requisição 000123/26")


def test_erro_volta_a_pendente(atendido, usuario):
    LinhaSaida.objects.update(status="ERRO", mensagem="Centro inexistente no SCPI.")
    assert editar(atendido, usuario, dados=saida(recebedor="Ana")).ok
    assert set(LinhaSaida.objects.values_list("status", flat=True)) == {"PENDENTE"}


def test_erro_com_lancado_em_volta_sem_data_nem_numero(atendido, usuario):
    LinhaSaida.objects.update(status="ERRO", lancado_em=timezone.now())
    assert editar(atendido, usuario, dados=saida(recebedor="Ana")).ok
    assert set(LinhaSaida.objects.values_list("status", "requisicao_scpi", "lancado_em")) == {
        ("PENDENTE", "", None)
    }


def test_desmarcar_nao_lancar_poe_o_lote_na_fila(pedido, usuario):
    atender(pedido, usuario, nao_lancar=True)
    assert all(r.lote != pedido.numero for r in fila_do_robo().requisicoes)
    assert editar(pedido, usuario, nao_lancar=False).ok
    assert set(LinhaSaida.objects.values_list("status", flat=True)) == {"PENDENTE"}
    assert [r.lote for r in fila_do_robo().requisicoes] == [pedido.numero]


def test_versao_diferente_recusa_com_quem_salvou(atendido, usuario):
    assert editar(atendido, usuario, dados=saida(recebedor="Ana")).ok
    r = editar(atendido, usuario, versao=0, dados=saida(recebedor="Bruno"))
    assert not r.ok and r.motivo == "versao"
    assert re.fullmatch(r"Ana salvou alterações neste pedido às \d\d:\d\d\.", r.mensagem)
    assert r.diferencas == [{"campo": "Recebedor", "antes": "Ana", "depois": "Bruno"}]
    assert Atendimento.objects.get().recebedor == "Ana"


def test_reenvio_igual_com_versao_antiga_e_sucesso(atendido, usuario):
    assert editar(atendido, usuario, dados=saida(recebedor="Ana")).ok
    r = editar(atendido, usuario, versao=0, dados=saida(recebedor="Ana"))
    assert r.ok and r.reenvio
    assert Pedido.objects.get().versao == 1
    assert AlteracaoPedido.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_duas_edicoes_ao_mesmo_tempo(pedido, usuario):
    atender(pedido, usuario)

    def com(recebedor):
        return lambda: editar(pedido, usuario, versao=0, dados=saida(recebedor=recebedor))

    respostas = em_paralelo(com("Ana"), com("Bruno"))
    assert sorted(r.ok for r in respostas) == [False, True]
    assert [r.motivo for r in respostas if not r.ok] == ["versao"]
    assert LinhaSaida.objects.count() == 2
    assert Pedido.objects.get().versao == 1


def test_ab_recusa_decimal(usuario):
    montar_cenario()
    p = registrar(AB, envio_ab()).pedido
    atender(p, usuario, qtds={"016.005.010": "3"})
    r = editar(p, usuario, qtds={"016.005.010": "1,5"})
    assert not r.ok
    assert "Quantidade inválida para 016.005.010." in textos(r)


def test_acrescentado_oculto_inalterado_e_aceito(pedido, usuario):
    qtds = {**TUDO, "023.004.001": "1"}
    acrescimo = (Adicionado("023.004.001"),)
    atender(pedido, usuario, qtds=qtds, adicionados=acrescimo)
    Material.objects.filter(codigo="023.004.001").update(oculto=True)
    r = editar(pedido, usuario, dados=saida(recebedor="Ana"), qtds=qtds, adicionados=acrescimo)
    assert r.ok, r.erros


def test_acrescentado_oculto_novo_e_recusado(atendido, usuario):
    Material.objects.filter(codigo="023.004.001").update(oculto=True)
    r = editar(
        atendido,
        usuario,
        qtds={**TUDO, "023.004.001": "1"},
        adicionados=(Adicionado("023.004.001"),),
    )
    assert not r.ok


def test_edicao_troca_e_acrescenta(atendido, usuario):
    r = editar(
        atendido,
        usuario,
        qtds={"023.001.002": "2", "008.001.002": "0", "023.004.001": "1", "016.005.010": "2"},
        adicionados=(Adicionado("023.004.001", "008.001.002"), Adicionado("016.005.010")),
    )
    assert r.ok, r.erros
    novo = ItemPedido.objects.get(codigo="023.004.001")
    assert novo.origem == "ALMOXARIFADO" and novo.no_lugar_de.codigo == "008.001.002"
    assert novo.adicionado_por == usuario
    assert set(LinhaSaida.objects.values_list("codigo", "qtd")) == {
        ("023.001.002", Decimal(2)),
        ("023.004.001", Decimal(1)),
        ("016.005.010", Decimal(2)),
    }
    # Desfazer a troca e remover o acréscimo voltam ao atendimento original.
    assert editar(atendido, usuario).ok
    assert not ItemPedido.objects.filter(origem="ALMOXARIFADO").exists()
    assert LinhaSaida.objects.count() == 2


def test_valor_gravado_que_sumiu_diz_que_nao_existe_mais(atendido, usuario):
    CentroCusto.objects.filter(descricao="ETA II").delete()
    r = editar(atendido, usuario, dados=saida(recebedor="Ana"))
    assert not r.ok
    assert "Centro de custo: o valor gravado não existe mais. Escolha outro." in textos(r)


def test_scpi_antes_guarda_a_situacao_anterior(atendido, usuario):
    LinhaSaida.objects.update(status="ERRO", mensagem="x")
    assert editar(atendido, usuario, dados=saida(recebedor="Ana")).ok
    assert AlteracaoPedido.objects.get().scpi_antes == [
        {"seq": 1, "status": "ERRO", "mensagem": "x", "requisicao_scpi": ""},
        {"seq": 2, "status": "ERRO", "mensagem": "x", "requisicao_scpi": ""},
    ]


def test_editar_atendimento_recusa_pedido_sem_atendimento(pedido, usuario):
    r = editar(pedido, usuario)
    assert not r.ok and r.mensagem == "Pedido não encontrado."


# ---------------------------------------------------------------------------
# Serviço `editar_saida_avulsa`
# ---------------------------------------------------------------------------


@pytest.fixture
def avulsa(usuario):
    montar_cenario()
    r = registrar_saida_avulsa(
        uuid.uuid4(),
        EnvioSaida(saida(), itens(("023.004.001", "1"), ("016.005.010", "2"))),
        usuario=usuario,
        hoje=HOJE,
    )
    assert r.ok, r.erros
    return r.pedido


def editar_avulsa(pedido, usuario, materiais, dados=None, versao=None):
    pedido.refresh_from_db()
    return editar_saida_avulsa(
        pedido.id,
        pedido.versao if versao is None else versao,
        EnvioSaida(dados or saida(), materiais),
        usuario=usuario,
        hoje=HOJE,
    )


def test_avulsa_edita_quantidade_e_inclui_material(avulsa, usuario):
    materiais = itens(("023.004.001", "3"), ("016.005.010", "2"), ("013.006.001", "1"))
    r = editar_avulsa(avulsa, usuario, materiais)
    assert r.ok, r.erros
    assert [(d["codigo"], d["mudanca"]) for d in r.diferencas] == [
        ("023.004.001", "entregue"),
        ("013.006.001", "incluido"),
    ]
    assert dict(ItemPedido.objects.values_list("codigo", "qtd_entregue")) == {
        "023.004.001": Decimal(3),
        "016.005.010": Decimal(2),
        "013.006.001": Decimal(1),
    }
    assert set(LinhaSaida.objects.values_list("codigo", "qtd")) == {
        ("023.004.001", Decimal(3)),
        ("016.005.010", Decimal(2)),
        ("013.006.001", Decimal(1)),
    }
    assert Pedido.objects.get().versao == 1


def test_avulsa_remove_material(avulsa, usuario):
    r = editar_avulsa(avulsa, usuario, itens(("023.004.001", "1")))
    assert r.ok, r.erros
    assert [(d["codigo"], d["mudanca"]) for d in r.diferencas] == [("016.005.010", "removido")]
    assert list(ItemPedido.objects.values_list("codigo", flat=True)) == ["023.004.001"]
    assert LinhaSaida.objects.count() == 1


def test_avulsa_lancada_recusa(avulsa, usuario):
    LinhaSaida.objects.update(status="LANCADA", requisicao_scpi="000123/26")
    r = editar_avulsa(avulsa, usuario, itens(("023.004.001", "5")))
    assert not r.ok and r.motivo == "lancamento"
    assert ItemPedido.objects.get(codigo="023.004.001").qtd_entregue == Decimal(1)


def test_avulsa_sem_material_recusa(avulsa, usuario):
    r = editar_avulsa(avulsa, usuario, ())
    assert not r.ok
    assert "Adicione ao menos um material." in textos(r)


def test_avulsa_com_material_oculto_inalterado_e_aceita(avulsa, usuario):
    Material.objects.filter(codigo="016.005.010").update(oculto=True)
    materiais = itens(("023.004.001", "1"), ("016.005.010", "2"))
    assert editar_avulsa(avulsa, usuario, materiais, dados=saida(recebedor="Ana")).ok


def test_editar_atendimento_recusa_avulsa_e_vice_versa(avulsa, atendido, usuario):
    r = editar(avulsa, usuario)
    assert not r.ok and r.mensagem == "Pedido não encontrado."
    r = editar_avulsa(atendido, usuario, itens(("023.001.002", "1")))
    assert not r.ok and r.mensagem == "Pedido não encontrado."


# ---------------------------------------------------------------------------
# Detalhe em leitura: botão de editar, avisos e histórico
# ---------------------------------------------------------------------------


@pytest.fixture
def logado(client, usuario):
    client.force_login(usuario)
    return usuario


def detalhe(client, pedido):
    return client.get(reverse("pedidos:detalhe", args=[pedido.numero])).text


def recibo(html):
    inicio = html.index('<article class="folha-recibo')
    return html[inicio : html.index("</article>", inicio)]


def test_detalhe_mostra_editar_quando_editavel(client, logado):
    p = criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    html = detalhe(client, p)
    assert f'href="{reverse("pedidos:editar", args=[p.numero])}"' in html
    assert "Editar atendimento" in html
    assert "Pode ser editado até o robô lançar no SCPI." in html


def test_detalhe_da_avulsa_diz_editar_saida(client, logado):
    p = criar_pedido(origem=AVULSA, atendido=True, usuario=logado, linhas=[("PENDENTE", "")])
    assert "Editar saída" in detalhe(client, p)


def test_detalhe_desabilita_editar_quando_lancado(client, logado):
    p = criar_pedido(atendido=True, linhas=[("LANCADA", "004213/26")])
    html = detalhe(client, p)
    assert reverse("pedidos:editar", args=[p.numero]) not in html
    assert 'aria-disabled="true"' in html
    assert "Lançado na requisição 004213/26" in html


def test_detalhe_suspenso_mostra_motivo(client, logado):
    p = criar_pedido(atendido=True, linhas=[("VERIFICAR", "")])
    html = detalhe(client, p)
    assert reverse("pedidos:editar", args=[p.numero]) not in html
    assert "Edição suspensa: o robô não confirmou" in html


def test_detalhe_sem_atendimento_nao_tem_editar(client, logado):
    html = detalhe(client, criar_pedido())
    assert "Editar atendimento" not in html
    assert "Pode ser editado até o robô" not in html


def test_aviso_de_recibo_impresso(client, logado):
    p = criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    Atendimento.objects.update(recibo_impresso_em=timezone.now())
    assert "Salvar alterações devolve o recibo para impressão." in detalhe(client, p)


def test_aviso_de_lote_com_erro(client, logado):
    p = criar_pedido(atendido=True, linhas=[("ERRO", "")])
    assert "Corrija e salve: o lote volta para a fila do próximo lançamento." in detalhe(client, p)


def test_historico_no_detalhe_e_fora_do_recibo(client, logado):
    p = criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    AlteracaoPedido.objects.create(
        pedido=p,
        usuario=logado,
        versao=1,
        diferencas=[{"campo": "Recebedor", "antes": "João", "depois": "Ana"}],
    )
    html = detalhe(client, p)
    assert "Alterações depois do atendimento" in html
    assert "Recebedor: João → Ana" in html
    assert "Recebedor: João → Ana" not in recibo(html)


def test_historico_vazio(client, logado):
    p = criar_pedido(atendido=True, linhas=[("PENDENTE", "")])
    assert "Nenhuma alteração registrada." in detalhe(client, p)
