import io
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from xml.etree import ElementTree

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from catalogo.models import Importacao
from pedidos.models import ExecucaoRobo

RAIZ = Path(__file__).resolve().parent.parent
DEPLOY = RAIZ / "deploy"


@pytest.mark.django_db
def test_sem_robo_em_andamento():
    saida = io.StringIO()
    call_command("robos_em_andamento", stdout=saida)
    assert "Nenhum robô em andamento." in saida.getvalue()


@pytest.mark.django_db
def test_lancamento_ou_importacao_em_andamento_param_a_atualizacao():
    e = ExecucaoRobo.objects.create(simulacao=True)
    Importacao.objects.create(tipo=Importacao.Tipo.ESTOQUE)
    with pytest.raises(CommandError) as erro:
        call_command("robos_em_andamento")
    assert f"Simulação #{e.pk}" in str(erro.value) and "Importação de Estoque" in str(erro.value)


@pytest.mark.django_db
def test_execucao_interrompida_nao_conta():
    ExecucaoRobo.objects.create(inicio=timezone.now() - timedelta(hours=2))
    call_command("robos_em_andamento", stdout=io.StringIO())


def test_atualizar_para_no_primeiro_erro_e_segue_a_ordem():
    texto = (DEPLOY / "atualizar.bat").read_text(encoding="utf-8")
    linhas = [linha.strip() for linha in texto.splitlines()]
    comandos = [linha for linha in linhas if linha.startswith(('".venv', "git ", "uv ", "nssm "))]
    assert comandos and all(linha.endswith(" || goto :falha") for linha in comandos)
    ordem = [
        "robos_em_andamento",
        "git pull --ff-only",
        "uv sync --frozen --no-dev",
        "migrate --noinput",
        "collectstatic --noinput",
        "check --deploy --fail-level WARNING",
        "nssm restart CentralAlmoxarifado",
    ]
    posicoes = [texto.index(trecho) for trecho in ordem]
    assert posicoes == sorted(posicoes)


def test_atualizar_corpo_num_bloco_que_o_cmd_le_inteiro():
    # O git pull pode trocar o atualizar.bat durante a execução: o cmd precisa já ter lido tudo.
    texto = (DEPLOY / "atualizar.bat").read_text(encoding="utf-8")
    linhas = [linha.strip() for linha in texto.splitlines()]
    abre = linhas.index("(")
    fecha = linhas.index(")")
    assert linhas[abre - 1].startswith("rem ")
    assert linhas[abre - 2].startswith("cd /d ")
    assert abre < linhas.index("exit /b 0") < fecha < linhas.index(":falha")
    fora = [
        i
        for i, linha in enumerate(linhas)
        if "manage.py" in linha or linha.startswith(("git ", "nssm "))
    ]
    assert fora and all(abre < i < fecha for i in fora)
    verificacoes = [i for i, linha in enumerate(linhas) if "manage.py robos_em_andamento" in linha]
    assert len(verificacoes) == 2
    depois_do_check = next(i for i, linha in enumerate(linhas) if "check --deploy" in linha)
    reinicio = next(i for i, linha in enumerate(linhas) if linha.startswith("nssm restart"))
    assert depois_do_check < verificacoes[1] < reinicio


@pytest.mark.parametrize("nome", ["tarefa.bat", "atualizar.bat"])
def test_bat_com_fim_de_linha_do_windows(nome):
    dados = (DEPLOY / nome).read_bytes()
    assert dados.count(b"\n") == dados.count(b"\r\n") > 0


@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe")
def test_tarefa_repassa_o_codigo_de_saida(tmp_path):
    ambiente = {**os.environ, "TAREFA_LOG": str(tmp_path / "agendador.log")}
    ok = subprocess.run(
        ["cmd", "/c", str(DEPLOY / "tarefa.bat"), "check"], env=ambiente, timeout=120
    )
    falha = subprocess.run(
        ["cmd", "/c", str(DEPLOY / "tarefa.bat"), "comando_que_nao_existe"],
        env=ambiente,
        timeout=120,
    )
    assert ok.returncode == 0 and falha.returncode != 0
    log = (tmp_path / "agendador.log").read_text(encoding="utf-8", errors="replace")
    assert "=== " in log and "comando_que_nao_existe" in log


def test_tarefa_forca_utf8_antes_do_python():
    linhas = (DEPLOY / "tarefa.bat").read_text(encoding="utf-8").splitlines()
    ambiente = next(i for i, linha in enumerate(linhas) if "PYTHONIOENCODING=utf-8" in linha)
    python = next(i for i, linha in enumerate(linhas) if "python.exe" in linha)
    assert ambiente < python


def test_tarefa_do_estoque_nao_depende_do_idioma_do_windows():
    # O schtasks /XML recusa a declaração UTF-8, e o /D traduz os dias com o Windows.
    dados = (DEPLOY / "tarefa-estoque.xml").read_bytes()
    assert dados.isascii() and b"<?xml" not in dados
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    tarefa = ElementTree.fromstring(dados)
    gatilho = tarefa.find("t:Triggers/t:CalendarTrigger", ns)
    dias = [d.tag.split("}")[1] for d in gatilho.find("t:ScheduleByWeek/t:DaysOfWeek", ns)]
    assert dias == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    assert gatilho.findtext("t:StartBoundary", namespaces=ns).endswith("T07:00:00")
    assert gatilho.findtext("t:Repetition/t:Interval", namespaces=ns) == "PT30M"
    assert gatilho.findtext("t:Repetition/t:Duration", namespaces=ns) == "PT10H1M"
    acao = tarefa.find("t:Actions/t:Exec", ns)
    assert acao.findtext("t:Command", namespaces=ns) == r"C:\CentralAlmoxarifado\deploy\tarefa.bat"
    assert acao.findtext("t:Arguments", namespaces=ns) == "importar_estoque"
    guia = (DEPLOY / "INSTALACAO.md").read_text(encoding="utf-8")
    assert r"/XML C:\CentralAlmoxarifado\deploy\tarefa-estoque.xml" in guia
    assert "schtasks /Create" in guia and " /D " not in guia
