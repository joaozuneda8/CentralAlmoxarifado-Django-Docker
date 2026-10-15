import subprocess
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.utils import timezone

from pedidos.models import ExecucaoRobo
from scpi.disparo import iniciar_lancamento
from scpi.requisicoes import ErroSCPI
from tests.scpi_simulado import SCPISimulado

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _journal_temporario(journal):
    """Nenhum teste grava o journal no `logs/` do repositório."""


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user("00012", password="x")


def test_comando_usa_a_execucao_do_botao(monkeypatch, dois_lotes):
    scpi = SCPISimulado()
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    e = ExecucaoRobo.objects.create()
    call_command("lancar_saidas", "--execucao", str(e.pk))
    e.refresh_from_db()
    assert e.situacao == "SUCESSO" and e.resumo["lancadas"] == 2


def test_dry_run_vence_uma_execucao_real(monkeypatch, dois_lotes):
    scpi = SCPISimulado()
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    e = ExecucaoRobo.objects.create(simulacao=False)
    call_command("lancar_saidas", "--execucao", str(e.pk), "--dry-run")
    e.refresh_from_db()
    assert e.simulacao and not any(c[0] == "salvar" for c in scpi.chamadas)


def test_sem_execucao_cria_registro_de_linha_de_comando(monkeypatch, dois_lotes):
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", SCPISimulado().abrir)
    call_command("lancar_saidas", "--limite", "1")
    e = ExecucaoRobo.objects.get()
    assert e.iniciada_por is None and e.resumo["lancadas"] == 1


def test_execucao_encerrada_e_recusada():
    e = ExecucaoRobo.objects.create(situacao="SUCESSO")
    with pytest.raises(CommandError, match="não encontrada ou já encerrada"):
        call_command("lancar_saidas", "--execucao", str(e.pk))


def test_falhas_viram_codigo_de_saida(monkeypatch, dois_lotes):
    scpi = SCPISimulado()
    scpi.falhas_preencher[dois_lotes[0]] = ErroSCPI("x")
    monkeypatch.setattr("scpi.management.commands.lancar_saidas.navegador", scpi.abrir)
    with pytest.raises(CommandError, match="erros ou linhas a verificar"):
        call_command("lancar_saidas")


def test_disparo_cria_execucao_e_inicia_processo(monkeypatch, usuario):
    chamadas = []
    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: chamadas.append(args))
    e = iniciar_lancamento(usuario, simulacao=True)
    assert e.iniciada_por == usuario and e.simulacao and e.situacao == "ANDAMENTO"
    assert chamadas[0][1:] == [
        str(settings.BASE_DIR / "manage.py"),
        "lancar_saidas",
        "--execucao",
        str(e.pk),
        "--dry-run",
    ]


def test_disparo_recusa_com_execucao_em_andamento_mas_nao_interrompida(monkeypatch, usuario):
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)
    ExecucaoRobo.objects.create()
    assert iniciar_lancamento(usuario, simulacao=False) is None
    ExecucaoRobo.objects.update(inicio=timezone.now() - timedelta(minutes=2))
    assert iniciar_lancamento(usuario, simulacao=False) is not None


@pytest.mark.parametrize("limite", ["0", "-1", "x"])
def test_limite_precisa_ser_inteiro_positivo(limite):
    with pytest.raises(CommandError, match="--limite"):
        call_command("lancar_saidas", "--limite", limite)
    assert not ExecucaoRobo.objects.exists()


def test_disparo_que_nao_inicia_o_processo_encerra_a_execucao_como_falha(monkeypatch, usuario):
    def quebrar(*a, **k):
        raise OSError("python.exe não encontrado")

    monkeypatch.setattr(subprocess, "Popen", quebrar)
    with pytest.raises(OSError):
        iniciar_lancamento(usuario, simulacao=False)
    e = ExecucaoRobo.objects.get()
    assert (e.situacao, e.erro) == ("FALHA", "python.exe não encontrado") and e.fim is not None
    assert not ExecucaoRobo.em_andamento().exists()
