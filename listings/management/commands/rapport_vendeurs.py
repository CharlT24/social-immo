"""
Rapport hebdomadaire aux vendeurs particuliers : vues, favoris,
conseil prix vs estimation du secteur.

Usage (CRON o2switch, 1x/semaine, ex. le lundi matin) :
    python manage.py rapport_vendeurs
    python manage.py rapport_vendeurs --dry-run
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Count

from listings.models import Annonce
from listings.services.estimation import estimer_bien


class Command(BaseCommand):
    help = "Envoie le rapport hebdomadaire aux vendeurs particuliers"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--site-url', default='https://social-immo.com')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        site = options['site_url'].rstrip('/')

        annonces = (Annonce.objects
                    .filter(source='particulier', is_active=True, user__isnull=False,
                            user__email__gt='')
                    .annotate(nb_favoris_recus=Count('favoris', distinct=True))
                    .select_related('user'))

        # Regrouper par vendeur
        par_vendeur = {}
        for a in annonces:
            par_vendeur.setdefault(a.user, []).append(a)

        nb_emails = 0
        for user, biens in par_vendeur.items():
            blocs = []
            for a in biens:
                lignes = [
                    f"{a.titre[:70]}",
                    f"  {a.nb_vues} vue(s) au total | {a.nb_favoris_recus} favori(s)",
                ]
                # Conseil prix (ventes reelles DVF en cache si dispo)
                if a.type_transaction == 'V' and a.prix and a.surface:
                    lib = (a.libelle_type or '').lower()
                    type_bien = 'maison' if 'maison' in lib else ('appartement' if 'appart' in lib else 'autre')
                    try:
                        est = estimer_bien(type_bien, a.ville, a.code_postal, float(a.surface), a.nb_pieces)
                    except Exception:
                        est = None
                    if est:
                        ecart = (float(a.prix) - est['prix_estime']) / est['prix_estime'] * 100
                        if ecart > 12:
                            lignes.append(f"  Conseil : votre prix est {ecart:.0f}% au-dessus du marche "
                                          f"({est['prix_estime']:,} EUR estimes)".replace(',', ' '))
                        elif ecart < -12:
                            lignes.append(f"  Conseil : votre prix est {-ecart:.0f}% sous le marche "
                                          f"({est['prix_estime']:,} EUR estimes)".replace(',', ' '))
                        else:
                            lignes.append("  Votre prix est aligne avec le marche de votre secteur.")
                lignes.append(f"  {site}/annonce/{a.reference}/")
                blocs.append("\n".join(lignes))

            corps = (
                f"Bonjour {user.first_name or user.username},\n\n"
                f"Voici le point hebdomadaire sur vo{'s' if len(biens) > 1 else 'tre'} "
                f"annonce{'s' if len(biens) > 1 else ''} :\n\n"
                + "\n\n".join(blocs)
                + f"\n\nGerer mes annonces : {site}/mon-compte/\n\n"
                f"L'equipe Social Immo"
            )

            if dry_run:
                self.stdout.write(f"[dry-run] {user.email} <- {len(biens)} annonce(s)")
            else:
                try:
                    send_mail(
                        subject=f"[Social Immo] Le point sur vo{'s' if len(biens) > 1 else 'tre'} annonce{'s' if len(biens) > 1 else ''} cette semaine",
                        message=corps,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    nb_emails += 1
                except Exception as e:
                    self.stderr.write(f"Echec envoi a {user.email}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"{'[dry-run] ' if dry_run else ''}{len(par_vendeur)} vendeur(s), "
            f"{nb_emails} email(s) envoye(s)"
        ))
