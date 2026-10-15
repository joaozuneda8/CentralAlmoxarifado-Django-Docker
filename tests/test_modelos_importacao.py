from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from catalogo.models import Importacao, SaidaSCPI

pytestmark = pytest.mark.django_db


def test_saida_scpi_unica_por_requisicao_material_e_item():
    SaidaSCPI.objects.create(
        id_requi="2", cadpro="013.005.007", data=date(2026, 1, 12), qtd=1, valor=Decimal("3.1")
    )
    SaidaSCPI.objects.create(
        id_requi="2", cadpro="013.005.007", item=2, data=date(2026, 1, 12), qtd=2, valor=0
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        SaidaSCPI.objects.create(
            id_requi="2", cadpro="013.005.007", item=2, data=date(2026, 1, 12), qtd=2, valor=0
        )


def test_valor_guarda_cinco_casas():
    s = SaidaSCPI.objects.create(
        id_requi="9", cadpro="1", data=date(2026, 1, 1), qtd=1, valor=Decimal("2.52976")
    )
    s.refresh_from_db()
    assert s.valor == Decimal("2.52976")


def test_importacao_nasce_em_andamento_com_avisos_vazios():
    i = Importacao.objects.create(tipo=Importacao.Tipo.ESTOQUE)
    i.refresh_from_db()
    assert i.situacao == Importacao.Situacao.ANDAMENTO
    assert i.avisos == [] and i.fim is None


def test_avisos_guardam_acento():
    i = Importacao.objects.create(tipo="CADASTRO", avisos=["Códigos repetidos: 1."])
    i.refresh_from_db()
    assert i.avisos == ["Códigos repetidos: 1."]


def test_sem_trava_so_a_recem_criada_esta_em_andamento():
    agora = timezone.now()
    nova = Importacao.objects.create(tipo="ESTOQUE", inicio=agora - timedelta(seconds=10))
    parada = Importacao.objects.create(tipo="CADASTRO", inicio=agora - timedelta(minutes=2))
    Importacao.objects.create(tipo="SAIDAS", situacao="SUCESSO", inicio=agora)
    assert list(Importacao.em_andamento(agora)) == [nova]
    assert parada.interrompida and not nova.interrompida


def test_com_a_trava_do_tipo_ocupada_importacao_longa_segue_em_andamento(trava_importacao_ocupada):
    trava_importacao_ocupada("CADASTRO")
    agora = timezone.now()
    longa = Importacao.objects.create(tipo="CADASTRO", inicio=agora - timedelta(hours=2))
    # a trava é por tipo: a de outro tipo não segura esta
    outra = Importacao.objects.create(tipo="ESTOQUE", inicio=agora - timedelta(hours=2))
    assert list(Importacao.em_andamento(agora)) == [longa]
    assert not longa.interrompida and outra.interrompida


def test_terminada_nunca_e_interrompida():
    velha = timezone.now() - timedelta(hours=2)
    assert not Importacao(tipo="CADASTRO", inicio=velha, situacao="FALHA").interrompida


@pytest.mark.parametrize("modelo", ["saidascpi", "importacao"])
def test_admin_so_leitura(admin_client, modelo):
    assert admin_client.get(f"/admin/catalogo/{modelo}/").status_code == 200
    assert admin_client.get(f"/admin/catalogo/{modelo}/add/").status_code == 403
