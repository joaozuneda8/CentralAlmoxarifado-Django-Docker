from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from pedidos.models import ExecucaoRobo
from tests.cenario import criar_pedido

pytestmark = pytest.mark.django_db


def test_sem_trava_so_a_recem_criada_esta_em_andamento():
    agora = timezone.now()
    nova = ExecucaoRobo.objects.create(inicio=agora - timedelta(seconds=10))
    parada = ExecucaoRobo.objects.create(inicio=agora - timedelta(minutes=2))
    ExecucaoRobo.objects.create(situacao="SUCESSO", fim=agora)
    assert list(ExecucaoRobo.em_andamento(agora)) == [nova]
    assert parada.interrompida and not nova.interrompida


def test_com_a_trava_ocupada_execucao_longa_segue_em_andamento(trava_ocupada):
    agora = timezone.now()
    longa = ExecucaoRobo.objects.create(inicio=agora - timedelta(hours=2))
    ExecucaoRobo.objects.create(situacao="SUCESSO", inicio=agora - timedelta(hours=3), fim=agora)
    assert list(ExecucaoRobo.em_andamento(agora)) == [longa]
    assert not longa.interrompida


def test_terminada_nunca_e_interrompida():
    velha = timezone.now() - timedelta(hours=2)
    assert not ExecucaoRobo(inicio=velha, situacao="FALHA").interrompida


def test_str_diz_o_modo():
    e = ExecucaoRobo.objects.create(simulacao=True)
    assert str(e) == f"Simulação #{e.pk}"
    r = ExecucaoRobo.objects.create()
    assert str(r) == f"Lançamento #{r.pk}"


def test_execucao_e_so_leitura_no_admin(admin_client):
    e = ExecucaoRobo.objects.create()
    url = reverse("admin:pedidos_execucaorobo_change", args=[e.pk])
    assert admin_client.post(url, {"situacao": "SUCESSO"}).status_code == 403


def test_superusuario_corrige_status_da_linha_no_admin(admin_client):
    pedido = criar_pedido(atendido=True, linhas=[("VERIFICAR", "")])
    linha = pedido.atendimento.linhas.get()
    url = reverse("admin:pedidos_linhasaida_change", args=[linha.pk])
    r = admin_client.post(
        url,
        {
            "status": "LANCADA",
            "requisicao_scpi": "003354/26",
            "lancado_em_0": "11/10/2026",
            "lancado_em_1": "10:00:00",
            "mensagem": "conferido",
        },
    )
    assert r.status_code == 302
    linha.refresh_from_db()
    assert (linha.status, linha.requisicao_scpi, linha.codigo) == (
        "LANCADA",
        "003354/26",
        "023.001.002",
    )


def test_equipe_sem_superusuario_nao_edita_linha(client):
    equipe = get_user_model().objects.create_user("00010", password="x", is_staff=True)
    equipe.user_permissions.add(
        *Permission.objects.filter(codename__in=["view_linhasaida", "change_linhasaida"])
    )
    client.force_login(equipe)
    linha = criar_pedido(atendido=True, linhas=[("ERRO", "")]).atendimento.linhas.get()
    url = reverse("admin:pedidos_linhasaida_change", args=[linha.pk])
    assert client.post(url, {"status": "PENDENTE"}).status_code == 403
