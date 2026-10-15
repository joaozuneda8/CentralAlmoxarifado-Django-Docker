from django.core.management import BaseCommand
from django.utils import timezone

from catalogo.models import Importacao
from scpi import relatorios
from scpi.gravacao import gravar_estoque
from scpi.leitura import ler_estoque
from scpi.management.comum import descartar_arquivo, obter_csv, rodar_importacao


class Command(BaseCommand):
    help = "Importa o saldo de estoque do SCPI; código ausente do relatório fica com estoque 0."

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", help="CSV já baixado do SCPI (não abre o navegador).")
        parser.add_argument(
            "--apagar-arquivo",
            action="store_true",
            help="Apaga o CSV de --arquivo ao terminar (usado pelo upload da tela).",
        )

    def handle(self, *args, arquivo=None, apagar_arquivo=False, **opcoes):
        with descartar_arquivo(arquivo, apagar_arquivo):
            rodar_importacao(
                self,
                Importacao.Tipo.ESTOQUE,
                obter_csv(arquivo, lambda: relatorios.baixar_estoque()),
                lambda conteudo: gravar_estoque(ler_estoque(conteudo), timezone.now()),
                lambda imp: f"Estoque: {imp.linhas} materiais com saldo.",
            )
