import logging
from pathlib import Path
from zipfile import BadZipFile

from django.core.management import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from openpyxl.utils.exceptions import InvalidFileException

from implantacao.conversao import Carga, converter
from implantacao.migracao import MigracaoRecusada, gravar
from implantacao.planilha import ErroPlanilha, ler_xlsx
from pedidos import regras

logger = logging.getLogger("implantacao")


def resumo(carga: Carga) -> str:
    pendentes = sum(1 for linha in carga.linhas if linha.status == regras.PENDENTE)
    return (
        f"Pedidos: {len(carga.pedidos)} · itens: {len(carga.itens)} · "
        f"atendimentos: {len(carga.atendimentos)} · linhas de saída: {len(carga.linhas)} "
        f"(pendentes: {pendentes}) · centros de custo: {len(carga.centros)} · "
        f"opções: {len(carga.opcoes)} · itens de limpeza: {len(carga.itens_limpeza)} · "
        f"último número: {carga.ultimo_numero}"
    )


class Command(BaseCommand):
    help = (
        "Importa o .xlsx exportado das planilhas do Apps Script (migração única, antes da "
        "virada). Substitui os pedidos, centros de custo, opções e itens de limpeza."
    )

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", required=True, help="Planilha exportada (.xlsx).")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ensaio: grava tudo numa transação e desfaz (nada fica gravado).",
        )

    def handle(self, *args, **opcoes):
        caminho = Path(opcoes["arquivo"])
        if not caminho.is_file():
            raise CommandError(f"Arquivo não encontrado: {caminho}")
        try:
            abas = ler_xlsx(caminho)
        except ErroPlanilha as exc:
            raise CommandError(str(exc)) from exc
        except (BadZipFile, InvalidFileException) as exc:
            raise CommandError(f"{caminho} não é uma planilha .xlsx válida.") from exc

        carga = converter(abas)
        for aviso in carga.avisos:
            self.stdout.write(f"  Aviso: {aviso}")
        if carga.erros:
            problemas = "\n".join(f"- {erro}" for erro in carga.erros)
            raise CommandError(
                f"A planilha tem {len(carga.erros)} problema(s); nada foi gravado:\n{problemas}"
            )

        ensaio = opcoes["dry_run"]
        try:
            with transaction.atomic():
                avisos = gravar(carga)
                if ensaio:
                    # Ensaio fiel: grava de verdade (travas, restrições do banco) e desfaz.
                    transaction.set_rollback(True)
        except MigracaoRecusada as exc:
            raise CommandError(str(exc)) from exc
        except DatabaseError as exc:
            raise CommandError(f"O banco recusou a gravação; nada foi gravado: {exc}") from exc
        for aviso in avisos:
            self.stdout.write(f"  Aviso: {aviso}")
        texto = resumo(carga)
        self.stdout.write(texto)
        logger.info("importar_planilhas%s: %s", " (simulação)" if opcoes["dry_run"] else "", texto)
        if opcoes["dry_run"]:
            self.stdout.write("Simulação: nada foi gravado.")
