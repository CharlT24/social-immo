"""
Signaux : automatismes declenches par les evenements du site.
"""
from datetime import timedelta

from allauth.account.signals import email_confirmed
from django.dispatch import receiver
from django.utils import timezone


@receiver(email_confirmed)
def activer_annonces_apres_confirmation(request, email_address, **kwargs):
    """Quand un particulier confirme son email, ses annonces en attente
    de verification (creees recemment, inactives) passent en ligne."""
    from .models import Annonce
    seuil = timezone.now() - timedelta(days=7)
    Annonce.objects.filter(
        user=email_address.user, source='particulier',
        is_active=False, created_at__gte=seuil,
    ).update(is_active=True)
