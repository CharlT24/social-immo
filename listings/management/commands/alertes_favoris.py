"""
Alertes sur les biens mis en favori : baisse de prix.
Levier de retour n1 (les gens reviennent pour un bien qu'ils suivent).

Usage (dans l'autopilot quotidien) :
    python manage.py alertes_favoris [--dry-run] [--site-url https://social-immo.com]
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from listings.models import Favori


class Command(BaseCommand):
    help = "Envoie les alertes de baisse de prix sur les biens favoris"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--site-url', default='https://social-immo.com')
        parser.add_argument('--seuil', type=float, default=2.0,
                            help='Baisse minimale en %% pour alerter')

    def handle(self, *args, **options):
        site = options['site_url'].rstrip('/')
        seuil = options['seuil']
        nb = 0

        favoris = (Favori.objects.filter(
            annonce__is_active=True, prix_reference__gt=0,
            user__email__gt='',
        ).select_related('annonce', 'user'))

        for fav in favoris:
            ref = float(fav.prix_reference)
            actuel = float(fav.annonce.prix or 0)
            if actuel <= 0 or ref <= 0:
                continue
            baisse_pct = (ref - actuel) / ref * 100
            if baisse_pct < seuil:
                continue

            a = fav.annonce
            if options['dry_run']:
                self.stdout.write(f"[dry-run] {fav.user.email} : {a.reference} -{baisse_pct:.0f}%")
            else:
                try:
                    send_mail(
                        subject=f"[Social Immo] Baisse de prix sur un bien que vous suivez",
                        message=(
                            f"Bonjour {fav.user.first_name or fav.user.username},\n\n"
                            f"Bonne nouvelle : le prix d'un bien de vos favoris a baisse !\n\n"
                            f"{a.titre[:70]}\n{a.ville} ({a.code_postal})\n"
                            f"Ancien prix : {ref:,.0f} EUR\n".replace(',', ' ')
                            + f"Nouveau prix : {actuel:,.0f} EUR  (-{baisse_pct:.0f}%)\n\n".replace(',', ' ')
                            + f"Voir le bien : {site}/annonce/{a.reference}/\n\n"
                            f"Gerer mes favoris : {site}/mon-compte/?tab=acquereur\n\n"
                            f"L'equipe Social Immo"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[fav.user.email],
                        fail_silently=False,
                    )
                    nb += 1
                except Exception as e:
                    self.stderr.write(f"Echec {fav.user.email}: {e}")
            # Met a jour la reference pour ne pas re-alerter sur la meme baisse
            if not options['dry_run']:
                fav.prix_reference = a.prix
                fav.save(update_fields=['prix_reference'])

        self.stdout.write(self.style.SUCCESS(
            f"{'[dry-run] ' if options['dry_run'] else ''}{nb} alerte(s) de baisse envoyee(s)"
        ))
