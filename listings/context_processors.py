def user_roles(request):
    """Ajoute is_pro au contexte pour la navigation"""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'is_pro': False}
    from listings.models import ProProfile
    return {
        'is_pro': ProProfile.objects.filter(user=request.user).exists()
    }
