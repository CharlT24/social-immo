"""
Re-verifie les SIRET des pros au registre officiel : capte les entreprises
nouvellement cessees (perte du badge) et rattrape les verifications qui
avaient echoue faute de reseau.

Usage : python manage.py reverifier_siret
"""
import time

from django.core.management.base import BaseCommand

from listings.models import ProProfile
from listings.services.verification import appliquer_verification


class Command(BaseCommand):
    help = "Re-verifie les SIRET des profils pros au registre officiel"

    def add_arguments(self, parser):
        parser.add_argument('--limite', type=int, default=300,
                            help='Nombre max de pros a verifier par execution')

    def handle(self, *args, **options):
        # Priorite : pros avec SIRET mais pas encore verifies, puis les autres
        pros = list(ProProfile.objects.filter(is_active=True).exclude(siret='')
                    .order_by('siret_verifie')[:options['limite']])
        verifies, perdus, echecs = 0, 0, 0
        for pro in pros:
            avant = pro.siret_verifie
            resultat = appliquer_verification(pro)
            if resultat is None:
                echecs += 1
            elif pro.siret_verifie:
                verifies += 1
            elif avant and not pro.siret_verifie:
                perdus += 1  # entreprise cessee depuis
            time.sleep(0.1)  # courtoisie API
        self.stdout.write(self.style.SUCCESS(
            f'{len(pros)} pro(s) examine(s) : {verifies} verifie(s), '
            f'{perdus} badge(s) retire(s), {echecs} echec(s) reseau'
        ))
