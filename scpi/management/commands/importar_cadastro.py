from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from catalogo.models import Importacao
from scpi import relatorios
from scpi.gravacao import gravar_cadastro, periodo_cadastro_padrao
from scpi.leitura import ler_cadastro
from scpi.management.comum import data_opcao, descartar_arquivo, obter_csv, rodar_importacao


class Command(BaseCommand):
    help = (
        "Importa o cadastro de materiais do SCPI. Depois da primeira carga, o padrão é "
        "incremental: pede só os cadastros novos desde a última carga e não oculta ninguém. Com "
        "--completo (ou --forcar, ou sem nenhuma carga anterior, ou com --arquivo sem datas) "
        "importa o cadastro inteiro: insere e atualiza, marca ocultos e duplicados e oculta os "
        "que sumiram."
    )

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", help="CSV já baixado do SCPI (não abre o navegador).")
        parser.add_argument(
            "--forcar",
            action="store_true",
            help="Aceita um cadastro sem mais de 20%% dos materiais visíveis.",
        )
        parser.add_argument(
            "--completo",
            action="store_true",
            help="Recarga completa: pede o cadastro inteiro, mesmo havendo carga anterior.",
        )
        parser.add_argument(
            "--desde",
            help="Início do período do cadastro (dd/mm/aaaa). Com --desde ou --ate a importação é "
            "parcial: grava só os materiais do CSV e não oculta nenhum.",
        )
        parser.add_argument("--ate", help="Fim do período do cadastro (dd/mm/aaaa); padrão: hoje.")
        parser.add_argument(
            "--apagar-arquivo",
            action="store_true",
            help="Apaga o CSV de --arquivo ao terminar (usado pelo upload da tela).",
        )

    def handle(
        self,
        *args,
        arquivo=None,
        forcar=False,
        completo=False,
        desde=None,
        ate=None,
        apagar_arquivo=False,
        **opcoes,
    ):
        with descartar_arquivo(arquivo, apagar_arquivo):
            hoje = timezone.localdate()
            de, fim = data_opcao(desde), data_opcao(ate)
            if (de or fim) and (completo or forcar):
                opcao = "--completo" if completo else "--forcar"
                raise CommandError(
                    f"{opcao} não se aplica a um período: a importação por período não oculta "
                    "nenhum material."
                )
            # Sem datas, baixando do SCPI e sem pedir a recarga completa: só os cadastros novos
            # desde a última carga. Um CSV enviado (--arquivo) sem datas é tratado como completo.
            automatico = False
            if not (de or fim or completo or forcar or arquivo):
                padrao = periodo_cadastro_padrao(hoje)
                if padrao:
                    (de, fim), automatico = padrao, True
            parcial = bool(de or fim)
            de, fim = de or relatorios.INICIO_CADASTRO, fim or hoje
            if de > fim:
                raise CommandError(
                    f"O início do período ({de:%d/%m/%Y}) é depois do fim ({fim:%d/%m/%Y})."
                )
            if fim > hoje:
                raise CommandError(f"O fim do período ({fim:%d/%m/%Y}) é no futuro.")
            sufixo = " (novos desde a última carga)" if automatico else ""
            rodar_importacao(
                self,
                Importacao.Tipo.CADASTRO,
                obter_csv(arquivo, lambda: relatorios.baixar_cadastro(de, fim)),
                lambda conteudo: gravar_cadastro(ler_cadastro(conteudo), forcar, parcial=parcial),
                lambda imp: (
                    f"Cadastro parcial ({de:%d/%m/%Y} a {fim:%d/%m/%Y}){sufixo}: {imp.linhas} "
                    "materiais gravados; nenhum foi ocultado."
                    if parcial
                    else f"Cadastro: {imp.linhas} materiais gravados."
                ),
                periodo=(de, fim) if parcial else (None, None),
            )
