import logging

from django.core.management import BaseCommand, CommandError, call_command

from catalogo.curva import INICIO_DADOS_CONFIAVEIS
from scpi import relatorios

logger = logging.getLogger("scpi")

# Cadastro primeiro: o estoque e as saídas se apoiam nos códigos que ele traz.
COMANDOS = ("importar_cadastro", "importar_estoque", "importar_saidas_scpi")

# Opções de cada comando na carga inicial: o cadastro inteiro (a recarga completa, que oculta o
# que sumiu) e as saídas desde o início dos dados confiáveis, em vez de só o que é novo.
CARGA_INICIAL = {
    "importar_cadastro": {"completo": True},
    "importar_saidas_scpi": {"desde": f"{INICIO_DADOS_CONFIAVEIS:%d/%m/%Y}"},
}


class Command(BaseCommand):
    help = (
        "Roda as três importações do SCPI em sequência (cadastro, estoque e saídas), num navegador "
        "só. Uma falha não impede as seguintes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--carga-inicial",
            action="store_true",
            help="Carga inicial completa: o cadastro inteiro e as saídas desde "
            f"{INICIO_DADOS_CONFIAVEIS:%d/%m/%Y}, em vez de só o que é novo.",
        )

    def handle(self, *args, carga_inicial=False, **opcoes):
        falharam = []
        # Um login no SCPI para as três: cada relatório volta à tela de onde partiu.
        with relatorios.sessao_compartilhada():
            for nome in COMANDOS:
                extras = CARGA_INICIAL.get(nome, {}) if carga_inicial else {}
                try:
                    call_command(nome, stdout=self.stdout, stderr=self.stderr, **extras)
                except CommandError as exc:
                    falharam.append(nome)
                    self.stderr.write(f"{nome}: {exc}")
                    logger.error("%s falhou: %s", nome, exc)
        if falharam:
            raise CommandError(f"Falharam: {', '.join(falharam)}.")
