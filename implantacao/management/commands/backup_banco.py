from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.utils import timezone

from implantacao.backup import ErroBackup, fazer_backup, vencidos


class Command(BaseCommand):
    help = (
        "Faz o backup do banco (mysqldump comprimido) em BACKUP_DIR e apaga os backups "
        "com mais dias que BACKUP_RETENCAO_DIAS. Para o Agendador de Tarefas do Windows."
    )

    def handle(self, *args, **options):
        agora = timezone.localtime()
        try:
            arquivo = fazer_backup(settings.BACKUP_DIR, agora)
        except ErroBackup as erro:
            raise CommandError(str(erro)) from erro
        dias = settings.BACKUP_RETENCAO_DIAS
        antigos = vencidos(settings.BACKUP_DIR, agora.date(), dias)
        for antigo in antigos:
            antigo.unlink()
        kb = round(arquivo.stat().st_size / 1024)
        self.stdout.write(
            f"Backup gravado: {arquivo} ({kb} KB). "
            f"Apagados {len(antigos)} backup(s) com mais de {dias} dias."
        )
