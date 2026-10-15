from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from catalogo.models import Importacao
from scpi import relatorios
from scpi.gravacao import gravar_saidas, periodo_saidas
from scpi.leitura import ErroImportacao, ler_saidas
from scpi.management.comum import data_opcao, descartar_arquivo, obter_csv, rodar_importacao


class Command(BaseCommand):
    help = (
        "Importa as requisições de saída do SCPI. Sem --desde, começa 7 dias antes do fim da "
        "última importação bem-sucedida (ou em 1º de janeiro); não duplica (requisição, código)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--desde", help="Início do período (dd/mm/aaaa).")
        parser.add_argument("--ate", help="Fim do período (dd/mm/aaaa); padrão: hoje.")
        parser.add_argument("--arquivo", help="CSV já baixado do SCPI (não abre o navegador).")
        parser.add_argument(
            "--apagar-arquivo",
            action="store_true",
            help="Apaga o CSV de --arquivo ao terminar (usado pelo upload da tela).",
        )

    def handle(self, *args, desde=None, ate=None, arquivo=None, apagar_arquivo=False, **opcoes):
        with descartar_arquivo(arquivo, apagar_arquivo):
            try:
                de, ate = periodo_saidas(timezone.localdate(), data_opcao(desde), data_opcao(ate))
            except ErroImportacao as exc:
                raise CommandError(str(exc)) from None
            rodar_importacao(
                self,
                Importacao.Tipo.SAIDAS,
                obter_csv(arquivo, lambda: relatorios.baixar_saidas(de, ate)),
                lambda conteudo: gravar_saidas(ler_saidas(conteudo)),
                lambda imp: (
                    f"Saídas do SCPI ({de:%d/%m/%Y} a {ate:%d/%m/%Y}): {imp.linhas} linhas novas."
                ),
                periodo=(de, ate),
            )
