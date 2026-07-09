"""
Nettoie les annonces particuliers en double (issues d'un double-clic avant le
correctif anti-doublon). Garde la plus ANCIENNE de chaque groupe identique
(meme utilisateur + titre + ville + prix) et desactive les autres.

Usage :
    python manage.py nettoyer_doublons --dry-run   # voir ce qui serait fait
    python manage.py nettoyer_doublons             # desactive les doublons
    python manage.py nettoyer_doublons --delete    # supprime definitivement
"""
from django.core.management.base import BaseCommand
from django.db.models import Count

from listings.models import Annonce


class Command(BaseCommand):
    help = "Desactive (ou supprime) les annonces particuliers en double."

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true',
                            help='Supprime definitivement au lieu de desactiver')
        parser.add_argument('--dry-run', action='store_true',
                            help='Affiche sans rien modifier')

    def handle(self, *args, **options):
        dry = options['dry_run']
        hard = options['delete']

        # Groupes de doublons parmi les annonces particuliers actives
        groupes = (Annonce.objects.filter(source='particulier', is_active=True)
                   .values('user_id', 'titre', 'ville', 'prix')
                   .annotate(n=Count('id')).filter(n__gt=1))

        total = 0
        for g in groupes:
            doublons = list(Annonce.objects.filter(
                source='particulier', is_active=True,
                user_id=g['user_id'], titre=g['titre'],
                ville=g['ville'], prix=g['prix'],
            ).order_by('created_at'))
            garde = doublons[0]
            extras = doublons[1:]  # on garde la plus ancienne
            self.stdout.write(
                f"'{garde.titre}' ({garde.ville}, {garde.prix} €) : "
                f"{len(extras)} doublon(s) — on garde {garde.reference}")
            for a in extras:
                self.stdout.write(f"   -> {a.reference}")
                if not dry:
                    if hard:
                        a.delete()
                    else:
                        a.is_active = False
                        a.save(update_fields=['is_active'])
                total += 1

        verbe = 'seraient traites' if dry else ('supprimes' if hard else 'desactives')
        self.stdout.write(self.style.SUCCESS(f"{total} doublon(s) {verbe}."))
