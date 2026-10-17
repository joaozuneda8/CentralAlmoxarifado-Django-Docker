import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse

from pedidos.models import Atendimento, ItemPedido, LinhaSaida, Pedido, Sequencia
from pedidos.regras import (
    AB,
    AVULSA,
    EM_LANCAMENTO,
    ERRO,
    LANCADA,
    LIMPEZA,
    NAO_LANCAR,
    PENDENTE,
    VERIFICAR,
)
from pedidos.servicos import proximo_numero, travar_sequencia

pytestmark = pytest.mark.django_db


def test_numeracao_unica_para_p_e_av():
    with transaction.atomic():
        seq = travar_sequencia()
        numeros = [proximo_numero(seq, o) for o in (LIMPEZA, AVULSA, AB)]
    assert numeros == ["P-000001", "AV-000002", "P-000003"]


def test_numeracao_continua_do_ultimo():
    Sequencia.objects.create(nome="PEDIDOS", ultimo=122)
    with transaction.atomic():
        assert proximo_numero(travar_sequencia(), LIMPEZA) == "P-000123"


def test_status_das_linhas_sao_os_das_regras():
    assert set(LinhaSaida.Status.values) == {
        PENDENTE,
        EM_LANCAMENTO,
        LANCADA,
        ERRO,
        VERIFICAR,
        NAO_LANCAR,
    }


def test_situacoes_vem_das_regras():
    usuario = get_user_model().objects.create_user(username="1", password="x")
    p = Pedido.objects.create(id=uuid.uuid4(), numero="P-000001", origem=LIMPEZA)
    assert p.linhas == [] and p.situacao_scpi.chave == "sem"
    assert p.situacao.chave == "aguardando"
    for codigo, entregue in (("023.001.002", 2), ("008.001.002", 0)):
        ItemPedido.objects.create(
            pedido=p, codigo=codigo, material="X", qtd_pedida=2, qtd_entregue=entregue
        )
    a = Atendimento.objects.create(
        id=uuid.uuid4(),
        pedido=p,
        data_efetiva=date(2026, 10, 1),
        recebedor="João",
        centro_custo="ETA II",
        tipo_saida="BALCÃO",
        atendido_por=usuario,
    )
    LinhaSaida.objects.create(
        atendimento=a,
        seq=1,
        data=a.data_efetiva,
        qtd=Decimal(2),
        codigo="023.001.002",
        descricao="X",
        recebedor="João",
        centro_custo="ETA II",
        tipo_saida="BALCÃO",
        lote=p.numero,
        status=LANCADA,
        requisicao_scpi="003354/26",
    )
    p = Pedido.objects.get(pk=p.pk)
    assert p.situacao.chave == "parcial"
    assert p.situacao_scpi.chave == "lancado"


def test_admin_lista_pedidos_e_linhas(admin_client):
    for modelo in ("pedido", "atendimento", "linhasaida"):
        assert admin_client.get(reverse(f"admin:pedidos_{modelo}_changelist")).status_code == 200


# --- item acrescentado pelo almoxarifado e restrições -------------------------------


def _pedido_simples(numero="P-900001"):
    return Pedido.objects.create(
        id=uuid.uuid4(), numero=numero, origem=LIMPEZA, solicitante="Fulano", destino="Sala 1"
    )


def _item(pedido, codigo="001", **extra):
    dados = {
        "pedido": pedido,
        "codigo": codigo,
        "material": "Material",
        "qtd_pedida": Decimal("1"),
    }
    dados.update(extra)
    return ItemPedido(**dados)


def _grava(item):
    with transaction.atomic():
        item.save()


def test_acrescentado_exige_qtd_pedida_nula_e_quem_acrescentou():
    from django.db import IntegrityError

    u = get_user_model().objects.create_user("m1", password="x")
    p = _pedido_simples()
    alm = ItemPedido.Origem.ALMOXARIFADO
    with pytest.raises(IntegrityError):
        _grava(_item(p, origem=alm, qtd_pedida=Decimal("1"), adicionado_por=u))
    with pytest.raises(IntegrityError):
        _grava(_item(p, origem=alm, qtd_pedida=None))
    with pytest.raises(IntegrityError):
        _grava(_item(p, origem=ItemPedido.Origem.PEDIDO, qtd_pedida=None))
    _grava(_item(p, origem=alm, qtd_pedida=None, adicionado_por=u))


def test_pedido_nao_tem_no_lugar_de_nem_adicionado_por():
    from django.db import IntegrityError

    u = get_user_model().objects.create_user("m2", password="x")
    p = _pedido_simples()
    with pytest.raises(IntegrityError):
        _grava(_item(p, adicionado_por=u))
    original = _item(p, "002")
    original.save()
    with pytest.raises(IntegrityError):
        _grava(_item(p, "003", no_lugar_de=original))


def test_codigo_unico_no_pedido():
    from django.db import IntegrityError

    p1, p2 = _pedido_simples("P-900002"), _pedido_simples("P-900003")
    _item(p1, "A").save()
    with pytest.raises(IntegrityError):
        _grava(_item(p1, "A"))
    _item(p2, "A").save()


def test_linha_de_saida_com_quantidade_zero_ou_negativa_e_recusada():
    from django.db import IntegrityError

    u = get_user_model().objects.create_user("m3", password="x")
    p = _pedido_simples("P-900004")
    at = Atendimento.objects.create(
        id=uuid.uuid4(),
        pedido=p,
        data_efetiva=date(2026, 1, 5),
        recebedor="R",
        centro_custo="CC",
        tipo_saida="T",
        atendido_por=u,
    )
    for seq, qtd in enumerate((Decimal("0"), Decimal("-1")), start=1):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                LinhaSaida.objects.create(
                    atendimento=at,
                    seq=seq,
                    data=at.data_efetiva,
                    qtd=qtd,
                    codigo="001",
                    descricao="M",
                    recebedor="R",
                    centro_custo="CC",
                    tipo_saida="T",
                    lote="P-900004",
                )


def test_clean_recusa_no_lugar_de_de_outro_pedido_ou_acrescentado():
    from django.core.exceptions import ValidationError

    u = get_user_model().objects.create_user("m4", password="x")
    p1, p2 = _pedido_simples("P-900005"), _pedido_simples("P-900006")
    original = _item(p1, "X")
    original.save()
    outro = _item(p2, "Y")
    outro.save()
    acrescentado = _item(
        p1,
        "Z",
        origem=ItemPedido.Origem.ALMOXARIFADO,
        qtd_pedida=None,
        adicionado_por=u,
    )
    acrescentado.save()
    alm = ItemPedido.Origem.ALMOXARIFADO
    novo = _item(p1, "W", origem=alm, qtd_pedida=None, adicionado_por=u, no_lugar_de=original)
    novo.full_clean()
    novo.no_lugar_de = outro
    with pytest.raises(ValidationError):
        novo.full_clean()
    novo.no_lugar_de = acrescentado
    with pytest.raises(ValidationError):
        novo.full_clean()


# Edição do atendimento: versão do pedido e histórico de alterações.


def test_pedido_nasce_na_versao_zero():
    from tests.cenario import criar_pedido

    assert criar_pedido().versao == 0


def test_alteracao_guarda_diferencas_e_scpi_antes():
    from pedidos.models import AlteracaoPedido
    from tests.cenario import criar_pedido

    p = criar_pedido(atendido=True)
    u = get_user_model().objects.create_user(username="00001")
    a = AlteracaoPedido.objects.create(
        pedido=p,
        usuario=u,
        versao=1,
        diferencas=[{"campo": "Recebedor", "antes": "João", "depois": "Ana"}],
        scpi_antes=[{"seq": 1, "status": "PENDENTE", "mensagem": "", "requisicao_scpi": ""}],
    )
    assert list(p.alteracoes.all()) == [a]
    assert a.diferencas[0]["depois"] == "Ana"


def test_migration_da_edicao_so_acrescenta():
    from importlib import import_module

    from django.db.migrations import AddField, CreateModel

    m = import_module("pedidos.migrations.0002_edicao_atendimento").Migration
    assert m.operations
    assert {type(op) for op in m.operations} <= {AddField, CreateModel}
