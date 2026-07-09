"""
Nettoie les annonces particuliers en double (issues d'un double-clic ou d'un
re-depot avant le correctif anti-doublon).

Regroupement par VENDEUR + VILLE + PRIX (le titre peut varier d'un re-depot a
l'autre). Dans chaque groupe, on GARDE la version la plus interessante (active
de preference, puis avec le plus de photos, puis la plus recente) et on
desactive (ou supprime) les autres creees dans la meme fenetre de temps.

Usage :
    python manage.py nettoyer_doublons --dry-run           # voir sans rien faire
    python manage.py nettoyer_doublons                      # desactiver les doublons
    python manage.py nettoyer_doublons --delete            # supprimer definitivement
    python manage.py nettoyer_doublons --fenetre-heures 72 # regrouper si crees a <72h
"""
from datetime import timedelta

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
        parser.add_argument('--fenetre-heures', type=int, default=72,
                            help='Ne regroupe que les annonces creees a moins de N heures '
                                 "d'ecart (evite de fusionner deux vrais biens distincts). Defaut 72.")

    def _score(self, a):
        # Meilleure version : active > inactive, puis plus de photos, puis plus recente.
        return (1 if a.is_active else 0, a.photos.count(), a.created_at)

    def handle(self, *args, **options):
        dry = options['dry_run']
        hard = options['delete']
        fenetre = timedelta(hours=options['fenetre_heures'])

        groupes = (Annonce.objects.filter(source='particulier')
                   .values('user_id', 'ville', 'prix')
                   .annotate(n=Count('id')).filter(n__gt=1))

        total = 0
        for g in groupes:
            items = list(Annonce.objects.filter(
                source='particulier', user_id=g['user_id'],
                ville=g['ville'], prix=g['prix'],
            ).order_by('created_at'))

            garde = max(items, key=self._score)
            # On ne desactive que les doublons crees PROCHES de la version gardee
            # (protege deux vrais biens distincts au meme prix, postes a des mois d'ecart).
            extras = [a for a in items
                      if a.id != garde.id
                      and abs((a.created_at - garde.created_at).total_seconds()) <= fenetre.total_seconds()]
            if not extras:
                continue

            self.stdout.write(
                f"{g['ville']} · {g['prix']} € (vendeur {g['user_id']}) : "
                f"{len(extras)} doublon(s) — on garde #{garde.id} "
                f"'{garde.titre[:30]}' ({garde.photos.count()} photos, "
                f"{'actif' if garde.is_active else 'inactif'})")
            for a in extras:
                self.stdout.write(f"   -> #{a.id} '{a.titre[:30]}' "
                                  f"({a.photos.count()} photos, {'actif' if a.is_active else 'inactif'})")
                if not dry:
                    if hard:
                        a.delete()
                    else:
                        a.is_active = False
                        a.save(update_fields=['is_active'])
                total += 1

        verbe = 'seraient traites' if dry else ('supprimes' if hard else 'desactives')
        self.stdout.write(self.style.SUCCESS(f"{total} doublon(s) {verbe}."))
