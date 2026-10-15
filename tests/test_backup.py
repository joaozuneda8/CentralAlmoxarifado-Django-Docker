import gzip
import io
import subprocess
from datetime import date, datetime
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from implantacao.backup import conteudo_opcoes, nome_backup, vencidos

DUMP = b"-- MySQL dump\nCREATE TABLE x (id int);\n"


@pytest.fixture
def pasta(settings, tmp_path):
    settings.BACKUP_DIR = tmp_path / "backups"
    return settings.BACKUP_DIR


def arquivo_de_opcoes(args) -> Path:
    """O arquivo do `--defaults-extra-file`, que o mysqldump exige como primeira opção."""
    opcao = args[1]
    assert opcao.startswith("--defaults-extra-file=")
    return Path(opcao.removeprefix("--defaults-extra-file="))


def falso_mysqldump(chamadas, codigo=0, saida=DUMP, erro=b""):
    def executar(args, **kwargs):
        chamadas.append((args, kwargs, arquivo_de_opcoes(args).read_text(encoding="utf-8")))
        kwargs["stdout"].write(saida)
        return subprocess.CompletedProcess(args, codigo, stderr=erro)

    return executar


def test_nome_e_vencidos(tmp_path):
    assert nome_backup(datetime(2026, 10, 12, 23, 0, 5)) == "almoxarifado-20261012-230005.sql.gz"
    hoje = date(2026, 10, 12)
    for nome in [
        "almoxarifado-20260812-230000.sql.gz",
        "almoxarifado-20260813-230000.sql.gz",
        "outro.txt",
        "almoxarifado-lixo.sql.gz",
    ]:
        (tmp_path / nome).write_bytes(b"x")
    assert [p.name for p in vencidos(tmp_path, hoje, 60)] == ["almoxarifado-20260812-230000.sql.gz"]


@pytest.mark.django_db
def test_backup_comprime_e_apaga_os_vencidos(monkeypatch, pasta, settings):
    chamadas = []
    monkeypatch.setattr("implantacao.backup.subprocess.run", falso_mysqldump(chamadas))
    pasta.mkdir()
    (pasta / "almoxarifado-20200101-230000.sql.gz").write_bytes(b"velho")
    saida = io.StringIO()
    call_command("backup_banco", stdout=saida)
    arquivos = sorted(p.name for p in pasta.iterdir())
    assert (
        len(arquivos) == 1
        and arquivos[0].startswith("almoxarifado-")
        and arquivos[0].endswith(".sql.gz")
    )
    assert gzip.decompress((pasta / arquivos[0]).read_bytes()) == DUMP
    args, kwargs, opcoes = chamadas[0]
    banco = settings.DATABASES["default"]
    assert "--single-transaction" in args and args[-1] == banco["NAME"]
    # A senha vai num arquivo de opções temporário, nunca nos argumentos nem no ambiente.
    assert opcoes == conteudo_opcoes(str(banco["PASSWORD"]))
    assert "MYSQL_PWD" not in (kwargs.get("env") or {})
    assert not any(a.startswith("-p") or a.startswith("--password") for a in args)
    assert not arquivo_de_opcoes(args).exists()
    assert "Apagados 1 backup(s)" in saida.getvalue()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("codigo", "saida", "erro"), [(2, b"", b"Access denied for user"), (0, b"", b"")]
)
def test_falha_nao_deixa_parcial_nem_apaga_os_antigos(monkeypatch, pasta, codigo, saida, erro):
    monkeypatch.setattr(
        "implantacao.backup.subprocess.run", falso_mysqldump([], codigo, saida, erro)
    )
    pasta.mkdir()
    antigo = pasta / "almoxarifado-20200101-230000.sql.gz"
    antigo.write_bytes(b"velho")
    with pytest.raises(CommandError, match="Access denied" if erro else "vazia"):
        call_command("backup_banco")
    assert list(pasta.iterdir()) == [antigo]


@pytest.mark.django_db
def test_programa_ausente(monkeypatch, pasta, settings):
    settings.MYSQLDUMP = "nao-existe-mysqldump"
    with pytest.raises(CommandError, match="MYSQLDUMP"):
        call_command("backup_banco")


@pytest.mark.django_db
def test_sem_tablespaces_e_com_limite_de_tempo(monkeypatch, pasta):
    chamadas = []
    monkeypatch.setattr("implantacao.backup.subprocess.run", falso_mysqldump(chamadas))
    call_command("backup_banco")
    args, kwargs, _ = chamadas[0]
    assert "--no-tablespaces" in args and kwargs["timeout"] == 3600


@pytest.mark.django_db
def test_mysqldump_que_nao_termina_apaga_os_parciais(monkeypatch, pasta):
    opcoes = []

    def executar(args, **kwargs):
        opcoes.append(arquivo_de_opcoes(args))
        kwargs["stdout"].write(b"-- comecou")
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr("implantacao.backup.subprocess.run", executar)
    pasta.mkdir()
    antigo = pasta / "almoxarifado-20200101-230000.sql.gz"
    antigo.write_bytes(b"velho")
    with pytest.raises(CommandError, match="não terminou em 1 hora"):
        call_command("backup_banco")
    assert list(pasta.iterdir()) == [antigo]
    assert not opcoes[0].exists()


def test_arquivo_de_opcoes_escapa_aspas_e_barras():
    senha = 'a"b\\c#d'  # a"b\c#d
    assert conteudo_opcoes(senha) == '[client]\npassword="a\\"b\\\\c#d"\n'
