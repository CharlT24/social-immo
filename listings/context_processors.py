def user_roles(request):
    """Ajoute is_pro et is_particulier_vendeur au contexte pour la navigation"""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'is_pro': False, 'is_particulier_vendeur': False, 'messages_non_lus': 0}
    from listings.models import ProProfile, Annonce, Message
    from django.db.models import Q
    try:
        non_lus = Message.objects.filter(
            Q(conversation__acheteur=request.user) | Q(conversation__proprietaire=request.user),
            lu=False).exclude(auteur=request.user).count()
    except Exception:
        non_lus = 0
    return {
        'is_pro': ProProfile.objects.filter(user=request.user).exists(),
        'is_particulier_vendeur': Annonce.objects.filter(user=request.user, source='particulier').exists(),
        'messages_non_lus': non_lus,
    }
