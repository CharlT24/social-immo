"""
Paiements Stripe — implementation REST pure (requests + hmac standard),
zero dependance supplementaire, compatible o2switch.

DORMANT tant que les cles ne sont pas dans le .env :
    STRIPE_SECRET_KEY=sk_live_...
    STRIPE_WEBHOOK_SECRET=whsec_...
    STRIPE_PRICE_AGENCE=price_...      (abonnement mensuel agence)
    STRIPE_PRICE_PRO=price_...         (abonnement mensuel artisan)
    STRIPE_PRICE_PACK=price_...        (paiement unique pack vendeur)

Le webhook active/desactive les options automatiquement : le site
s'auto-gere, les factures et la resiliation passent par le portail Stripe.
"""
import hashlib
import hmac
import time

import requests
from django.conf import settings

API = 'https://api.stripe.com/v1'
TIMEOUT = 15


def actif():
    """Stripe est-il configure ?"""
    return bool(getattr(settings, 'STRIPE_SECRET_KEY', ''))


def price_id(type_abonnement):
    return {
        'agence': getattr(settings, 'STRIPE_PRICE_AGENCE', ''),
        'pro': getattr(settings, 'STRIPE_PRICE_PRO', ''),
        'pack_vendeur': getattr(settings, 'STRIPE_PRICE_PACK', ''),
    }.get(type_abonnement, '')


def _post(endpoint, data):
    r = requests.post(
        f'{API}{endpoint}', data=data,
        auth=(settings.STRIPE_SECRET_KEY, ''),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def creer_session_checkout(type_abonnement, user, success_url, cancel_url, annonce_id=None):
    """Cree une session Stripe Checkout, retourne son URL de paiement."""
    pid = price_id(type_abonnement)
    if not (actif() and pid):
        return None
    mode = 'payment' if type_abonnement == 'pack_vendeur' else 'subscription'
    data = {
        'mode': mode,
        'line_items[0][price]': pid,
        'line_items[0][quantity]': 1,
        'success_url': success_url,
        'cancel_url': cancel_url,
        'client_reference_id': str(user.id),
        'customer_email': user.email,
        'metadata[type_abonnement]': type_abonnement,
        'metadata[user_id]': str(user.id),
    }
    if annonce_id:
        data['metadata[annonce_id]'] = str(annonce_id)
    if mode == 'subscription':
        data['subscription_data[metadata][type_abonnement]'] = type_abonnement
        data['subscription_data[metadata][user_id]'] = str(user.id)
    session = _post('/checkout/sessions', data)
    return session.get('url')


def portail_facturation(customer_id, return_url):
    """URL du portail client Stripe (factures, moyen de paiement, resiliation)."""
    if not (actif() and customer_id):
        return None
    session = _post('/billing_portal/sessions', {
        'customer': customer_id,
        'return_url': return_url,
    })
    return session.get('url')


def annuler_abonnement(subscription_id):
    """Annule un abonnement Stripe (best effort). Utilise notamment a la
    suppression de compte pour ne plus prelever l'utilisateur."""
    if not (actif() and subscription_id):
        return False
    try:
        r = requests.delete(
            f'{API}/subscriptions/{subscription_id}',
            auth=(settings.STRIPE_SECRET_KEY, ''),
            timeout=TIMEOUT,
        )
        return r.status_code == 200
    except Exception:
        return False


def verifier_webhook(payload, sig_header, tolerance=300):
    """Verifie la signature Stripe-Signature (HMAC-SHA256). Retourne bool."""
    secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    if not (secret and sig_header):
        return False
    try:
        parts = dict(p.split('=', 1) for p in sig_header.split(','))
        timestamp = parts.get('t', '')
        signature = parts.get('v1', '')
        if abs(time.time() - int(timestamp)) > tolerance:
            return False
        attendu = hmac.new(
            secret.encode(), f'{timestamp}.'.encode() + payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(attendu, signature)
    except (ValueError, KeyError):
        return False


# ===== Activation / desactivation automatique des avantages =====

OPTIONS_AGENCE_PREMIUM = [
    'badge_premium', 'logo_sur_annonces', 'remontee_auto', 'stats_avancees',
    'donnees_marche', 'contact_prioritaire', 'estimation_forward',
    'visite_virtuelle', 'video', 'photos_illimitees',
]


def activer_avantages(abonnement):
    """Active les avantages lies a un abonnement (appele par le webhook)."""
    from datetime import timedelta
    from django.utils import timezone
    from listings.models import Agence, ProProfile, AgenceOptions

    user = abonnement.user
    if abonnement.type_abonnement == 'agence':
        for agence in Agence.objects.filter(responsable=user):
            agence.mise_en_avant = True
            agence.save(update_fields=['mise_en_avant'])
            options, _ = AgenceOptions.objects.get_or_create(agence=agence)
            for opt in OPTIONS_AGENCE_PREMIUM:
                if hasattr(options, opt):
                    setattr(options, opt, True)
            options.save()
    elif abonnement.type_abonnement == 'pro':
        ProProfile.objects.filter(user=user).update(mise_en_avant=True, nb_inspirations_une=10)
    elif abonnement.type_abonnement == 'pack_vendeur':
        if abonnement.annonce_id:
            from listings.models import Annonce
            Annonce.objects.filter(id=abonnement.annonce_id).update(mise_en_avant=True)
            abonnement.date_fin = timezone.now() + timedelta(days=30)
            abonnement.save(update_fields=['date_fin'])


def desactiver_avantages(abonnement):
    """Retire les avantages (resiliation / impaye)."""
    from listings.models import Agence, ProProfile, AgenceOptions

    user = abonnement.user
    if abonnement.type_abonnement == 'agence':
        for agence in Agence.objects.filter(responsable=user):
            agence.mise_en_avant = False
            agence.save(update_fields=['mise_en_avant'])
            options = getattr(agence, 'options', None)
            if options:
                for opt in OPTIONS_AGENCE_PREMIUM:
                    if hasattr(options, opt):
                        setattr(options, opt, False)
                options.save()
    elif abonnement.type_abonnement == 'pro':
        ProProfile.objects.filter(user=user).update(mise_en_avant=False, nb_inspirations_une=3)
    elif abonnement.type_abonnement == 'pack_vendeur':
        if abonnement.annonce_id:
            from listings.models import Annonce
            Annonce.objects.filter(id=abonnement.annonce_id).update(mise_en_avant=False)
