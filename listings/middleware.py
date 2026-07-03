"""Middleware de mesure d'audience sans cookie."""


class StatsMiddleware:
    """Compte les pages HTML publiques vues (pas les assets, ni l'admin,
    ni les APIs, ni les bots evidents)."""

    PREFIXES_IGNORES = ('/static/', '/media/', '/api/', '/admin/', '/gestion/',
                        '/stripe/', '/favicon', '/robots.txt', '/sitemap')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if (request.method == 'GET'
                    and response.status_code == 200
                    and 'text/html' in response.headers.get('Content-Type', '')
                    and not request.path.startswith(self.PREFIXES_IGNORES)):
                ua = request.META.get('HTTP_USER_AGENT', '').lower()
                if 'bot' not in ua and 'crawler' not in ua and 'spider' not in ua:
                    from .models import StatJour
                    StatJour.incrementer('visites')
        except Exception:
            pass
        return response
