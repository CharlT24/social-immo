"""
Geocode les villes des annonces actives via api-adresse.data.gouv.fr
(gratuit, sans cle). Remplit VilleGeo pour la carte des resultats.

Usage (a lancer apres les imports XML, CRON possible) :
    python manage.py geocoder_villes
"""
import time

import requests
from django.core.management.base import BaseCommand

from listings.models import Annonce, VilleGeo

API = 'https://api-adresse.data.gouv.fr/search/'


class Command(BaseCommand):
    help = "Geocode les villes des annonces actives (API adresse data.gouv)"

    def handle(self, *args, **options):
        couples = set(
            Annonce.objects.filter(is_active=True).exclude(ville='')
            .values_list('ville', 'code_postal')
        )
        connus = set(VilleGeo.objects.values_list('ville', 'code_postal'))
        a_geocoder = [(v, cp or '') for v, cp in couples if (v, cp or '') not in connus]

        ok, echecs = 0, 0
        for ville, cp in a_geocoder:
            params = {'q': ville, 'type': 'municipality', 'limit': 1}
            if cp:
                params['postcode'] = cp
            try:
                r = requests.get(API, params=params, timeout=10)
                r.raise_for_status()
                features = r.json().get('features', [])
                if not features and cp:
                    # Retente sans le code postal (CP parfois errone dans le flux)
                    r = requests.get(API, params={'q': ville, 'type': 'municipality', 'limit': 1}, timeout=10)
                    features = r.json().get('features', [])
                if features:
                    lon, lat = features[0]['geometry']['coordinates']
                    VilleGeo.objects.update_or_create(
                        ville=ville, code_postal=cp,
                        defaults={'latitude': lat, 'longitude': lon},
                    )
                    ok += 1
                    self.stdout.write(f"  {ville} ({cp}) -> {lat:.4f}, {lon:.4f}")
                else:
                    echecs += 1
                    self.stderr.write(f"  Introuvable : {ville} ({cp})")
            except Exception as e:
                echecs += 1
                self.stderr.write(f"  Erreur {ville} : {e}")
            time.sleep(0.15)  # courtoisie API

        self.stdout.write(self.style.SUCCESS(
            f"{ok} ville(s) geocodee(s), {echecs} echec(s), "
            f"{len(couples) - len(a_geocoder)} deja connue(s)"
        ))
