from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from listings.models import Agence


class Command(BaseCommand):
    help = 'Importe les annonces de toutes les agences actives avec un flux URL configure'

    def handle(self, *args, **options):
        agences = Agence.objects.filter(is_active=True).exclude(feed_url='')
        total = agences.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('Aucune agence active avec flux configure.'))
            return

        self.stdout.write(f'Import automatique : {total} agence(s) a traiter')
        self.stdout.write('=' * 50)

        ok = 0
        ko = 0

        for agence in agences:
            self.stdout.write(f'\n--- {agence.nom} (ref: {agence.reference}) ---')
            try:
                out = StringIO()
                call_command('import_xml', url=agence.feed_url, stdout=out)
                output = out.getvalue()

                agence.last_import = timezone.now()
                agence.save(update_fields=['last_import'])

                # Afficher le resume
                lines = output.strip().split('\n')
                for line in lines[-3:]:
                    self.stdout.write(f'  {line}')

                ok += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  ERREUR: {e}'))
                ko += 1

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(
            f'Termine : {ok} reussie(s), {ko} en erreur sur {total} agence(s)'
        ))
