def user_roles(request):
    """Ajoute is_pro et is_particulier_vendeur au contexte pour la navigation"""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'is_pro': False, 'is_particulier_vendeur': False}
    from listings.models import ProProfile, Annonce
    return {
        'is_pro': ProProfile.objects.filter(user=request.user).exists(),
        'is_particulier_vendeur': Annonce.objects.filter(user=request.user, source='particulier').exists(),
    }
