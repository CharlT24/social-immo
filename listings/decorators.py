"""Decorateurs partages pour les vues listings."""
from functools import wraps

from django.http import HttpResponseForbidden


def staff_required(view_func):
    """Restreint une vue aux utilisateurs staff (admins).

    A placer apres @login_required : l'utilisateur est suppose authentifie.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("Acces reserve aux administrateurs.")
        return view_func(request, *args, **kwargs)
    return _wrapped
