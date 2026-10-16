import io
import os
import shutil
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

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
    texto = (DEPLOY / "atualizar.sh").read_text(encoding="utf-8")
    assert "set -eu" in texto
    assert "Atualização interrompida: corrija o erro acima e rode de novo." in texto
    ordem = [
        "run --rm web python manage.py robos_em_andamento",
        "git pull --ff-only",
        "docker compose build",
        "run --rm web python manage.py migrate --noinput",
        "run --rm web python manage.py check --deploy --fail-level WARNING",
        "up -d",
    ]
    posicoes = [texto.index(trecho) for trecho in ordem]
    assert posicoes == sorted(posicoes)
    # Com "run --rm" (e não "exec"), a conferência funciona também com o web parado.
    assert "compose exec" not in texto
    verificacoes = [
        i for i in range(len(texto)) if texto.startswith("manage.py robos_em_andamento", i)
    ]
    assert len(verificacoes) == 2
    assert texto.index("check --deploy") < verificacoes[1] < texto.index("up -d")


def test_atualizar_corpo_numa_funcao_chamada_no_fim():
    # O git pull pode trocar o script durante a execução: o bash precisa já ter lido tudo.
    texto = (DEPLOY / "atualizar.sh").read_text(encoding="utf-8")
    linhas = [linha.strip() for linha in texto.splitlines()]
    linhas = [linha for linha in linhas if linha and not linha.startswith("#")]
    assert linhas[-1] in ('atualizar "$@"', "atualizar")
    abre = next(i for i, linha in enumerate(linhas) if linha.startswith("atualizar()"))
    comandos = [i for i, linha in enumerate(linhas) if linha.startswith(("docker ", "git "))]
    assert comandos and all(abre < i < len(linhas) - 1 for i in comandos)


def _linhas_crontab():
    texto = (DEPLOY / "crontab").read_text(encoding="utf-8")
    return [
        linha.split(None, 5)
        for linha in texto.splitlines()
        if linha.strip() and not linha.startswith("#")
    ]


def test_crontab_mantem_os_horarios_do_agendador():
    # O estoque de 30 em 30 minutos das 07:00 às 17:00 só nos dias úteis; o resto todo dia.
    agenda = {tuple(campos[:5]): campos[5] for campos in _linhas_crontab()}
    assert agenda == {
        ("*/30", "7-16", "*", "*", "1-5"): "/app/deploy/tarefa.sh importar_estoque",
        ("0", "17", "*", "*", "1-5"): "/app/deploy/tarefa.sh importar_estoque",
        ("30", "6", "*", "*", "*"): "/app/deploy/tarefa.sh atualizar_catalogo",
        ("0", "23", "*", "*", "*"): "/app/deploy/tarefa.sh backup_banco",
    }


@pytest.mark.parametrize(
    "nome",
    ["deploy/crontab", "deploy/tarefa.sh", "deploy/atualizar.sh", "Dockerfile", "compose.yaml"],
)
def test_arquivos_do_container_com_fim_de_linha_lf(nome):
    # Com CRLF, o bash recusa o script ("set: -\r") e o supercronic lê o comando com \r.
    dados = (RAIZ / nome).read_bytes()
    assert b"\r\n" not in dados and dados.endswith(b"\n")


def _bash() -> str:
    """O bash do Git no Windows (o `bash` do PATH lá é o do WSL); fora dele, o do PATH."""
    if sys.platform == "win32":
        git = shutil.which("git")
        if git:
            for pasta in Path(git).parents:
                candidato = pasta / "bin" / "bash.exe"
                if candidato.exists():
                    return str(candidato)
        pytest.skip("sem o bash do Git")
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("sem bash")
    return bash


def test_tarefa_repassa_o_codigo_de_saida(tmp_path):
    ambiente = {
        **os.environ,
        "TAREFA_LOG": (tmp_path / "agendador.log").as_posix(),
        "TAREFA_PYTHON": Path(sys.executable).as_posix(),
    }
    script = (DEPLOY / "tarefa.sh").as_posix()
    ok = subprocess.run([_bash(), script, "check"], env=ambiente, timeout=120)
    falha = subprocess.run([_bash(), script, "comando_que_nao_existe"], env=ambiente, timeout=120)
    assert ok.returncode == 0 and falha.returncode != 0
    log = (tmp_path / "agendador.log").read_text(encoding="utf-8", errors="replace")
    assert "=== " in log and "comando_que_nao_existe" in log


def test_guias_nao_citam_mais_o_windows():
    for nome in ("INSTALACAO.md", "VIRADA.md"):
        texto = (DEPLOY / nome).read_text(encoding="utf-8")
        for resto in (r".venv\Scripts", "nssm", "schtasks", ".bat", "C:\\"):
            assert resto not in texto, (nome, resto)


def test_instalacao_cobre_os_dois_servidores_e_o_firewall():
    guia = (DEPLOY / "INSTALACAO.md").read_text(encoding="utf-8")
    for trecho in (
        "WSL2",
        "DOCKER-USER",
        "PORTA_PUBLICADA",
        "chown -R 1000:1000",
        "docker compose run --rm web python manage.py createsuperuser",
        "bash deploy/atualizar.sh",
    ):
        assert trecho in guia, trecho


def test_firewall_da_vm_nao_derruba_o_ufw():
    # O iptables-persistent remove o ufw no Ubuntu e grava as cadeias do próprio Docker: a regra
    # do DOCKER-USER é reaplicada por uma unidade do systemd depois do Docker.
    guia = (DEPLOY / "INSTALACAO.md").read_text(encoding="utf-8")
    assert "iptables-persistent" not in guia and "netfilter-persistent" not in guia
    assert "After=docker.service" in guia
