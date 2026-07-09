"""Middleware de mesure d'audience sans cookie (RGPD)."""

import hashlib


class StatsMiddleware:
    """Compte les pages HTML publiques vues (pas les assets, ni l'admin, ni les
    APIs, ni les bots). Alimente :
      - StatJour.visites : total quotidien (compteur simple)
      - PageVue : detail par page (visiteurs uniques, sources, sections, mobile)
    Le visiteur est un hash quotidien anonyme (IP+UA+jour+secret), non reversible
    et renouvele chaque jour : aucune donnee personnelle stockee.
    """

    PREFIXES_IGNORES = ('/static/', '/media/', '/api/', '/admin/', '/gestion/',
                        '/stripe/', '/favicon', '/robots.txt', '/sitemap',
                        '/health', '/sw.js', '/.well-known', '/accounts/', '/offline')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._enregistrer(request, response)
        except Exception:
            pass  # la mesure ne doit JAMAIS casser une requete
        return response

    def _enregistrer(self, request, response):
        if request.method != 'GET' or response.status_code != 200:
            return
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return
        path = request.path
        if path.startswith(self.PREFIXES_IGNORES):
            return
        ua = request.META.get('HTTP_USER_AGENT', '').lower()
        if any(b in ua for b in ('bot', 'crawler', 'spider', 'slurp', 'headless')):
            return
        # On ne compte pas nos propres visites (staff connecte).
        if getattr(request, 'user', None) and request.user.is_authenticated and request.user.is_staff:
            return

        from django.conf import settings
        from django.utils import timezone
        from .models import StatJour, PageVue

        StatJour.incrementer('visites')

        # IP (pour l'unicite uniquement, jamais stockee en clair)
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')
        jour = timezone.localdate().isoformat()
        graine = f'{ip}|{ua}|{jour}|{settings.SECRET_KEY}'
        visiteur_hash = hashlib.sha256(graine.encode('utf-8')).hexdigest()

        # Source externe (on ignore le trafic interne)
        referer = request.META.get('HTTP_REFERER', '')
        referer_host = ''
        if referer:
            from urllib.parse import urlparse
            h = urlparse(referer).netloc.lower().replace('www.', '')
            if h and 'social-immo.com' not in h:
                referer_host = h[:200]

        is_mobile = any(m in ua for m in ('mobile', 'android', 'iphone', 'ipad'))

        PageVue.objects.create(
            path=path[:300],
            section=self._section(path),
            referer_host=referer_host,
            visiteur_hash=visiteur_hash,
            is_mobile=is_mobile,
        )

    @staticmethod
    def _section(path):
        if path == '/':
            return 'home'
        rules = [
            ('/annonce/', 'annonce'), ('/recherche/', 'recherche'),
            ('/immobilier/', 'ville'), ('/inspirations/', 'inspirations'),
            ('/estimer/', 'estimer'), ('/pro', 'pro'), ('/agence', 'agence'),
            ('/mon-compte', 'compte'), ('/mon-agence', 'compte'), ('/mon-espace', 'compte'),
        ]
        for prefixe, section in rules:
            if path.startswith(prefixe):
                return section
        return 'autre'
