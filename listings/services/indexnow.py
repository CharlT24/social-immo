"""IndexNow : signale instantanement a Bing (et Yandex, Seznam, Naver...) les URL
creees, modifiees ou retirees, au lieu d'attendre leur prochain passage.

Protocole : https://www.indexnow.org/documentation
  - la cle publique est servie en texte sur /<cle>.txt (vue indexnow_key)
  - POST JSON {host, key, keyLocation, urlList} vers api.indexnow.org,
    10 000 URL max par appel.
Desactive si settings.INDEXNOW_KEY est vide (dev, tests).
"""
import logging
from urllib.parse import urlsplit

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ENDPOINT = 'https://api.indexnow.org/indexnow'
LOT_MAX = 10000


def soumettre(chemins):
    """Soumet une liste de chemins ('/annonce/...') ou d'URL absolues.
    Retourne le nombre d'URL envoyees (0 si desactive ou en erreur).
    Ne leve jamais : l'indexation ne doit pas casser un import."""
    cle = getattr(settings, 'INDEXNOW_KEY', '')
    if not cle:
        return 0
    base = settings.SITE_URL
    urls = sorted({c if c.startswith('http') else f'{base}{c}' for c in chemins if c})
    if not urls:
        return 0
    envoyees = 0
    for i in range(0, len(urls), LOT_MAX):
        lot = urls[i:i + LOT_MAX]
        try:
            r = requests.post(ENDPOINT, timeout=20, json={
                'host': urlsplit(base).netloc,
                'key': cle,
                'keyLocation': f'{base}/{cle}.txt',
                'urlList': lot,
            })
            # 200 = recu, 202 = recu (cle en cours de validation)
            if r.status_code in (200, 202):
                envoyees += len(lot)
            else:
                logger.warning('IndexNow HTTP %s : %s', r.status_code, r.text[:200])
        except requests.RequestException as e:
            logger.warning('IndexNow injoignable : %s', e)
    return envoyees


def vue_cle(request, cle):
    """Sert /<cle>.txt : preuve de propriete du domaine exigee par IndexNow."""
    from django.http import Http404, HttpResponse
    if not settings.INDEXNOW_KEY or cle != settings.INDEXNOW_KEY:
        raise Http404
    return HttpResponse(cle, content_type='text/plain; charset=utf-8')
