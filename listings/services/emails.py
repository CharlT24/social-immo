"""Utilitaires emails : desinscription signee (RGPD) + envoi avec en-tete
List-Unsubscribe pour les emails de relance/prospection."""
from django.core import signing
from django.core.mail import EmailMessage
from django.conf import settings

SEL = 'desabo'  # sel de signature


def token_desabo(email):
    return signing.dumps(email.strip().lower(), salt=SEL)


def email_from_token(token, max_age=60 * 60 * 24 * 365):
    """Retourne l'email du token signe, ou None si invalide/expire."""
    try:
        return signing.loads(token, salt=SEL, max_age=max_age)
    except signing.BadSignature:
        return None


def lien_desabo(email, site='https://social-immo.com'):
    return f"{site.rstrip('/')}/desabonnement/?token={token_desabo(email)}"


def envoyer_email_prospection(subject, body, email, site='https://social-immo.com'):
    """Envoie un email de relance/prospection AVEC lien de desinscription et
    en-tete List-Unsubscribe. Retourne False si l'adresse s'est desabonnee."""
    from listings.models import Desabonnement
    if Desabonnement.est_desabonne(email):
        return False
    lien = lien_desabo(email, site)
    corps = f"{body}\n\n---\nNe plus recevoir ces emails : {lien}"
    try:
        msg = EmailMessage(
            subject=subject, body=corps,
            from_email=settings.DEFAULT_FROM_EMAIL, to=[email],
            headers={'List-Unsubscribe': f'<{lien}>',
                     'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click'},
        )
        msg.send(fail_silently=False)
        return True
    except Exception:
        return False
