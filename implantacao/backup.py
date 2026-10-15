"""Backup diário do banco: mysqldump comprimido com gzip e retenção pelo nome do arquivo."""

import gzip
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings

PADRAO_NOME = re.compile(r"^almoxarifado-(\d{8})-\d{6}\.sql\.gz$")
FIM_DO_ERRO = 500
LIMITE_SEGUNDOS = 3600


class ErroBackup(Exception):
    pass


def nome_backup(momento: datetime) -> str:
    return f"almoxarifado-{momento:%Y%m%d-%H%M%S}.sql.gz"


def vencidos(pasta: Path, hoje: date, dias: int) -> list[Path]:
    """Backups (pelo nome) de data anterior a `hoje - dias`; outros arquivos nunca entram."""
    limite = hoje - timedelta(days=dias)
    achados = []
    for caminho in pasta.iterdir():
        correspondencia = PADRAO_NOME.match(caminho.name)
        if not correspondencia or not caminho.is_file():
            continue
        try:
            data = datetime.strptime(correspondencia.group(1), "%Y%m%d").date()
        except ValueError:
            continue
        if data < limite:
            achados.append(caminho)
    return sorted(achados)


def conteudo_opcoes(senha: str) -> str:
    """Arquivo de opções do cliente MySQL com a senha, entre aspas e com `\\` e `"` escapados."""
    escapada = senha.replace("\\", "\\\\").replace('"', '\\"')
    return f'[client]\npassword="{escapada}"\n'


def fazer_backup(pasta: Path, momento: datetime) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    banco = settings.DATABASES["default"]
    programa = settings.MYSQLDUMP
    destino = pasta / nome_backup(momento)
    dump_parcial = pasta / f"{destino.stem}.parcial"
    gz_parcial = pasta / f"{destino.name}.parcial"
    # A senha vai num arquivo de opções temporário, legível só pela conta que roda o backup
    # (a pasta temporária dela): argumentos aparecem na lista de processos, e o MySQL
    # desaconselha o MYSQL_PWD.
    descritor, nome_opcoes = tempfile.mkstemp(prefix="almoxarifado-", suffix=".cnf")
    opcoes = Path(nome_opcoes)
    with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
        arquivo.write(conteudo_opcoes(str(banco["PASSWORD"])))
    args = [
        programa,
        f"--defaults-extra-file={opcoes}",  # o mysqldump exige esta como a primeira opção
        "--single-transaction",
        "--routines",
        "--triggers",
        "--no-tablespaces",  # o MySQL 8 pede o privilégio PROCESS sem isto
        "--default-character-set=utf8mb4",
        "--host",
        str(banco["HOST"]),
        "--port",
        str(banco["PORT"]),
        "--user",
        str(banco["USER"]),
        banco["NAME"],
    ]
    try:
        try:
            with dump_parcial.open("wb") as saida:
                resultado = subprocess.run(
                    args,
                    stdout=saida,
                    stderr=subprocess.PIPE,
                    timeout=LIMITE_SEGUNDOS,
                )
        except subprocess.TimeoutExpired as erro:
            raise ErroBackup("O mysqldump não terminou em 1 hora.") from erro
        except FileNotFoundError as erro:
            raise ErroBackup(f"Programa não encontrado: {programa} (MYSQLDUMP no .env)") from erro
        if resultado.returncode != 0:
            fim = (resultado.stderr or b"").decode("utf-8", errors="replace").strip()
            raise ErroBackup(
                f"O mysqldump terminou com o código {resultado.returncode}: {fim[-FIM_DO_ERRO:]}"
            )
        if dump_parcial.stat().st_size == 0:
            raise ErroBackup("O mysqldump não gerou nada (saída vazia).")
        with dump_parcial.open("rb") as origem, gzip.open(gz_parcial, "wb") as comprimido:
            shutil.copyfileobj(origem, comprimido)
        gz_parcial.replace(destino)
    finally:
        opcoes.unlink(missing_ok=True)
        dump_parcial.unlink(missing_ok=True)
        gz_parcial.unlink(missing_ok=True)
    return destino
