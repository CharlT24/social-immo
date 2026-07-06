"""
Protection des formulaires publics : limitation de debit + honeypot.
Sans dependance (cache Django), compatible o2switch.
"""
from django.core.cache import cache


def ip_client(request):
    """IP reelle du client. SECURITE : on utilise REMOTE_ADDR (pose par le
    serveur), PAS le premier X-Forwarded-For que le client peut falsifier
    pour contourner le rate-limiting. Si un proxy de confiance est declare
    (TRUSTED_PROXY_XFF=True en settings), on prend le dernier hop du XFF."""
    from django.conf import settings
    if getattr(settings, 'TRUSTED_PROXY_XFF', False):
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            return xff.split(',')[-1].strip()  # hop le plus proche du serveur
    return request.META.get('REMOTE_ADDR', 'inconnu')


def trop_de_requetes(request, action, maximum, fenetre_secondes):
    """True si l'IP a depasse `maximum` appels pour `action` dans la fenetre."""
    cle = f'ratelimit:{action}:{ip_client(request)}'
    try:
        compteur = cache.get_or_set(cle, 0, fenetre_secondes)
        if compteur >= maximum:
            return True
        try:
            cache.incr(cle)
        except ValueError:
            cache.set(cle, 1, fenetre_secondes)
    except Exception:
        return False  # cache indisponible : ne jamais bloquer un humain
    return False


def est_un_bot(request):
    """Honeypot : le champ 'site_web_hp' est invisible pour les humains ;
    s'il est rempli, c'est un robot."""
    return bool(request.POST.get('site_web_hp', '').strip())


CHAMP_HONEYPOT = (
    '<div style="position:absolute;left:-9999px;top:-9999px;" aria-hidden="true">'
    '<label>Ne pas remplir<input type="text" name="site_web_hp" tabindex="-1" autocomplete="off"></label>'
    '</div>'
)
