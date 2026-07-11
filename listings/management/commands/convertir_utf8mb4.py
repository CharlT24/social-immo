"""
Convertit la base MySQL et toutes ses tables en utf8mb4 (support des emojis
et caracteres 4 octets). Corrige les erreurs d'import du type :
    Incorrect string value: '\\xF0\\x9F...' for column ...

Sans danger : ne touche pas aux donnees, seulement au jeu de caracteres.

Usage :
    python manage.py convertir_utf8mb4 --dry-run   # liste sans rien changer
    python manage.py convertir_utf8mb4             # applique la conversion
"""
from django.core.management.base import BaseCommand
from django.db import connection

COLLATION = 'utf8mb4_unicode_ci'


class Command(BaseCommand):
    help = "Convertit la base MySQL et ses tables en utf8mb4 (emojis)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Affiche les tables sans rien modifier')

    def handle(self, *args, **options):
        if connection.vendor != 'mysql':
            self.stdout.write(self.style.WARNING(
                f"Base {connection.vendor} (pas MySQL) : rien a faire."))
            return

        dry = options['dry_run']
        db = connection.settings_dict['NAME']

        with connection.cursor() as c:
            if not dry:
                c.execute(f"ALTER DATABASE `{db}` CHARACTER SET utf8mb4 COLLATE {COLLATION}")
                self.stdout.write(f"Base `{db}` -> utf8mb4")

            c.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=%s AND table_type='BASE TABLE'", [db])
            tables = [r[0] for r in c.fetchall()]

            ok, echecs = 0, []
            for t in tables:
                if dry:
                    self.stdout.write(f"  (a convertir) {t}")
                    continue
                try:
                    c.execute(f"ALTER TABLE `{t}` CONVERT TO CHARACTER SET utf8mb4 COLLATE {COLLATION}")
                    ok += 1
                    self.stdout.write(f"  [OK] {t}")
                except Exception as e:
                    echecs.append((t, str(e)))
                    self.stderr.write(self.style.ERROR(f"  [ECHEC] {t}: {e}"))

        if dry:
            self.stdout.write(self.style.SUCCESS(f"{len(tables)} table(s) seraient converties."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{ok} table(s) converties en utf8mb4."))
            if echecs:
                self.stderr.write(self.style.WARNING(
                    f"{len(echecs)} table(s) en echec (souvent sans consequence) — voir ci-dessus."))
