"""
Diagnostic Stripe : teste la creation d'une session Checkout pour CHAQUE
produit et affiche l'erreur exacte renvoyee par Stripe (au lieu de
l'avaler comme le fait le site). Aucun paiement n'est effectue : on cree
juste la session (comme un clic sur le bouton), on lit la reponse, fin.

Usage sur le serveur :
    source ~/virtualenv/social-immo/3.11/bin/activate && cd ~/social-immo
    python manage.py diag_stripe
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from listings.services import paiements

API = 'https://api.stripe.com/v1'


class Command(BaseCommand):
    help = "Teste la creation d'une session Stripe pour chaque produit."

    def handle(self, *args, **options):
        if not paiements.actif():
            self.stderr.write(self.style.ERROR(
                "STRIPE_SECRET_KEY absente : le processus ne voit pas la cle. "
                "Restart necessaire APRES avoir mis la cle dans .env."))
            return

        sk = settings.STRIPE_SECRET_KEY
        self.stdout.write(f"Cle secrete : {sk[:12]}...  (mode {'LIVE' if sk.startswith('sk_live') else 'TEST'})\n")

        for t in sorted(paiements.TYPES_VALIDES):
            pid = paiements.price_id(t)
            mode = 'payment' if t in paiements.UNIQUE else 'subscription'
            if not pid:
                self.stdout.write(self.style.ERROR(
                    f"[{t:24}] price_id VIDE  -> variable STRIPE_PRICE_* manquante dans .env"))
                continue

            data = {
                'mode': mode,
                'line_items[0][price]': pid,
                'line_items[0][quantity]': 1,
                'success_url': 'https://social-immo.com/abonnement/succes/',
                'cancel_url': 'https://social-immo.com/tarifs/',
                'client_reference_id': '1',
                'metadata[type_abonnement]': t,
            }
            if mode == 'subscription':
                data['subscription_data[metadata][type_abonnement]'] = t

            try:
                r = requests.post(f'{API}/checkout/sessions', data=data,
                                  auth=(sk, ''), timeout=15)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{t:24}] {pid[:16]}... reseau: {e}"))
                continue

            if r.status_code == 200:
                self.stdout.write(self.style.SUCCESS(
                    f"[{t:24}] {pid[:16]}... mode={mode:12} OK -> session creee"))
            else:
                try:
                    err = r.json().get('error', {})
                    msg = err.get('message', r.text[:200])
                except Exception:
                    msg = r.text[:200]
                self.stdout.write(self.style.ERROR(
                    f"[{t:24}] {pid[:16]}... mode={mode:12} ECHEC {r.status_code}: {msg}"))
