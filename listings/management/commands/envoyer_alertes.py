"""
Envoie les alertes email des recherches sauvegardees.

Usage (CRON o2switch, 1-2x/jour apres l'import XML) :
    python manage.py envoyer_alertes
    python manage.py envoyer_alertes --dry-run
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.models import RechercheSauvegardee


class Command(BaseCommand):
    help = "Envoie les nouveaux biens correspondant aux recherches sauvegardees"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Affiche ce qui serait envoye sans envoyer")
        parser.add_argument('--site-url', default='https://social-immo.com',
                            help="URL racine du site pour les liens des emails")

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        site = options['site_url'].rstrip('/')
        maintenant = timezone.now()
        nb_emails = 0

        alertes = RechercheSauvegardee.objects.filter(
            is_active=True, user__email__gt=''
        ).select_related('user')

        for alerte in alertes:
            depuis = alerte.derniere_alerte or alerte.created_at
            nouveaux = list(alerte.annonces_correspondantes(depuis=depuis)[:10])
            if not nouveaux:
                continue

            lignes = []
            for a in nouveaux:
                lignes.append(f"- {a.titre[:70]}")
                lignes.append(f"  {a.prix_format} | {a.ville} ({a.code_postal})"
                              + (f" | {a.surface} m2" if a.surface else ""))
                lignes.append(f"  {site}/annonce/{a.reference}/")
                lignes.append("")

            corps = (
                f"Bonjour {alerte.user.first_name or alerte.user.username},\n\n"
                f"{len(nouveaux)} nouveau{'x' if len(nouveaux) > 1 else ''} bien"
                f"{'s' if len(nouveaux) > 1 else ''} correspond"
                f"{'ent' if len(nouveaux) > 1 else ''} a votre alerte "
                f"\"{alerte.resume()}\" :\n\n"
                + "\n".join(lignes)
                + f"\nVoir tous les resultats : {site}{alerte.url_recherche()}\n\n"
                f"Pour gerer vos alertes : {site}/mon-compte/?tab=acquereur\n\n"
                f"L'equipe Social Immo"
            )

            if dry_run:
                self.stdout.write(f"[dry-run] {alerte.user.email} <- {len(nouveaux)} bien(s) "
                                  f"({alerte.resume()})")
            else:
                try:
                    send_mail(
                        subject=f"[Social Immo] {len(nouveaux)} nouveau(x) bien(s) - {alerte.resume()}",
                        message=corps,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[alerte.user.email],
                        fail_silently=False,
                    )
                    alerte.derniere_alerte = maintenant
                    alerte.save(update_fields=['derniere_alerte'])
                    nb_emails += 1
                except Exception as e:
                    self.stderr.write(f"Echec envoi a {alerte.user.email}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f"{'[dry-run] ' if dry_run else ''}{nb_emails if not dry_run else '?'} email(s) envoye(s), "
            f"{alertes.count()} alerte(s) active(s) examinee(s)"
        ))
