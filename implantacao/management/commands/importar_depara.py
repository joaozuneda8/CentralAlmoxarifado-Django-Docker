import logging
from pathlib import Path
from zipfile import BadZipFile

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils import timezone
from openpyxl.utils.exceptions import InvalidFileException

from catalogo.models import Importacao, Material, ParDePara, trava_importacao
from implantacao.depara import CargaDePara, ler_pares
from implantacao.planilha import ErroPlanilha
from scpi.execucao import trava
from scpi.gravacao import lista_curta

logger = logging.getLogger("implantacao")


class CargaRecusada(Exception):
    pass


def conferir_travas() -> None:
    """Recusa a carga que apagaria trabalho feito no sistema: par criado ou alterado no admin, ou
    qualquer alteração (inclusive exclusão) registrada no histórico depois da última carga."""
    mensagem = (
        "Há pares de/para criados ou alterados no sistema depois da última carga da planilha; a "
        "carga os apagaria. Nada foi gravado. Depois da carga conferida, o sistema é a fonte dos "
        "pares."
    )
    if ParDePara.objects.filter(origem=ParDePara.Origem.SISTEMA).exists():
        raise CargaRecusada(mensagem)
    ultima = (
        Importacao.objects.filter(tipo=Importacao.Tipo.DEPARA, situacao=Importacao.Situacao.SUCESSO)
        .order_by("-fim")
        .first()
    )
    if (
        ultima
        and LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(ParDePara),
            action_time__gt=ultima.fim,
        ).exists()
    ):
        raise CargaRecusada(mensagem)


def gravar(carga: CargaDePara) -> None:
    ParDePara.objects.all().delete()
    ParDePara.objects.bulk_create(
        ParDePara(
            antigo=par.antigo,
            novo=par.novo,
            fator=par.fator,
            observacao=carga.observacoes.get(par.antigo, ""),
            origem=ParDePara.Origem.PLANILHA,
        )
        for par in carga.pares
    )


class Command(BaseCommand):
    help = (
        "Carrega os pares de/para do .xlsx exportado da planilha MAPEAMENTO DE/PARA CONSOLIDADO "
        "(carga única da implantação). Substitui todos os pares."
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
            carga = ler_pares(caminho)
        except ErroPlanilha as exc:
            raise CommandError(str(exc)) from exc
        except (BadZipFile, InvalidFileException) as exc:
            raise CommandError(f"{caminho} não é uma planilha .xlsx válida.") from exc

        ensaio = opcoes["dry_run"]
        with trava(trava_importacao(Importacao.Tipo.DEPARA)) as obtida:
            if not obtida:
                raise CommandError("Outra carga de pares de/para está em andamento.")
            inicio = timezone.now()
            try:
                with transaction.atomic():
                    conferir_travas()
                    gravar(carga)
                    if ensaio:
                        transaction.set_rollback(True)
                    else:
                        # Na mesma transação: a última carga é a referência das travas.
                        Importacao.objects.create(
                            tipo=Importacao.Tipo.DEPARA,
                            inicio=inicio,
                            fim=timezone.now(),
                            situacao=Importacao.Situacao.SUCESSO,
                            linhas=len(carga.pares),
                            avisos=carga.recusados,
                        )
            except CargaRecusada as exc:
                raise CommandError(str(exc)) from exc
            except DatabaseError as exc:
                raise CommandError(f"O banco recusou a gravação; nada foi gravado: {exc}") from exc

        self._relatorio(carga, ensaio)

    def _relatorio(self, carga: CargaDePara, ensaio: bool) -> None:
        def escrever(texto: str) -> None:
            # O console do Windows (cp1252) não tem "→": sem a troca, o comando quebraria ao
            # imprimir o primeiro par recusado.
            self.stdout.write(texto.replace("→", "->"))

        escrever(
            f"Aba de mapeamento: {carga.lidos_mapeamento} linhas lidas ({carga.ignorados} sem par "
            "no formato 000.000.000: PRODUTO NOVO, traço, vazio ou antigo igual ao novo)."
        )
        escrever(f"Aba DEPARA: {carga.correcoes} correções.")
        if carga.recusados:
            escrever(f"Recusados ({len(carga.recusados)}):")
            for recusado in carga.recusados:
                escrever(f"  - {recusado}")
        cadastrados = set(
            Material.objects.filter(codigo__in=[p.novo for p in carga.pares]).values_list(
                "codigo", flat=True
            )
        )
        fora = sorted({p.novo for p in carga.pares} - cadastrados)
        if fora:
            escrever(f"Código novo ainda fora do cadastro ({len(fora)}): {lista_curta(fora)}.")
        if ensaio:
            escrever(f"Pares que seriam gravados: {len(carga.pares)}.")
            escrever("Simulação: nada foi gravado.")
        else:
            escrever(f"Pares gravados: {len(carga.pares)}.")
        logger.info(
            "importar_depara%s: %s pares, %s recusados",
            " (simulação)" if ensaio else "",
            len(carga.pares),
            len(carga.recusados),
        )
