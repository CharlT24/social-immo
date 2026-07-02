#!/usr/bin/env python
"""Script de debug pour trouver l'erreur 500 sur o2switch.
Usage: cd ~/social-immo && python test_error.py
"""
import os, sys, traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_immo.settings')

# NE PAS forcer DEBUG - tester en conditions reelles
# os.environ['DEBUG'] = 'True'

import django
django.setup()

from django.conf import settings

# Ajouter testserver aux ALLOWED_HOSTS pour le Client
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')
    settings.ALLOWED_HOSTS.append('localhost')

print("=" * 60)
print("DIAGNOSTIC SOCIAL IMMO (DEBUG=%s)" % settings.DEBUG)
print("=" * 60)

# 1. Check settings
print(f"\n[1] DEBUG = {settings.DEBUG}")
print(f"    ALLOWED_HOSTS = {settings.ALLOWED_HOSTS}")
print(f"    SECURE_SSL_REDIRECT = {getattr(settings, 'SECURE_SSL_REDIRECT', False)}")
print(f"    STATICFILES_STORAGE = {settings.STATICFILES_STORAGE}")
print(f"    DATABASE ENGINE = {settings.DATABASES['default']['ENGINE']}")

# 2. Check database
print("\n[2] Test connexion BDD...")
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("    OK - Connexion BDD fonctionnelle")
except Exception as e:
    print(f"    ERREUR BDD: {e}")

# 3. Check models
print("\n[3] Test modeles...")
try:
    from listings.models import Annonce, Agence, ProProfile, AgenceOptions
    print(f"    Annonces actives: {Annonce.objects.filter(is_active=True).count()}")
    print(f"    Agences actives: {Agence.objects.filter(is_active=True).count()}")
except Exception as e:
    print(f"    ERREUR: {e}")
    traceback.print_exc()

# 4. Test WhiteNoise / staticfiles FIRST (likely culprit)
print("\n[4] Test WhiteNoise / staticfiles...")
try:
    static_root = settings.STATIC_ROOT
    print(f"    STATIC_ROOT = {static_root}")
    print(f"    STATIC_ROOT existe: {os.path.exists(str(static_root))}")

    manifest_path = os.path.join(str(static_root), 'staticfiles.json')
    print(f"    Manifest (staticfiles.json) existe: {os.path.exists(manifest_path)}")

    if os.path.exists(str(static_root)):
        files = os.listdir(str(static_root))
        print(f"    Fichiers dans STATIC_ROOT: {len(files)}")
        for f in files[:10]:
            print(f"      - {f}")
    else:
        print("    !!! STATIC_ROOT n'existe pas !!!")
        print("    -> Lancez: python manage.py collectstatic --noinput")
except Exception as e:
    print(f"    ERREUR: {e}")
    traceback.print_exc()

# 5. Test full Client with DEBUG=False behavior
print("\n[5] Test Client complet (conditions prod)...")
from django.test import Client
c = Client()
pages_to_test = [
    ('/', 'Homepage'),
    ('/recherche/', 'Recherche'),
    ('/agence-immobiliere/', 'Agence immo'),
    ('/inspirations/', 'Inspirations'),
]
for url, label in pages_to_test:
    try:
        resp = c.get(url)
        print(f"    OK: {label} ({url}) -> status {resp.status_code}")
        if resp.status_code >= 400:
            # Try to get more info
            if hasattr(resp, 'content'):
                content = resp.content.decode('utf-8', errors='replace')[:500]
                print(f"    Contenu: {content[:200]}")
    except Exception as e:
        print(f"    ERREUR {label} ({url}): {e}")
        traceback.print_exc()

# 6. Test WSGI application directly
print("\n[6] Test WSGI direct...")
try:
    from social_immo.wsgi import application

    # Simulate a request
    environ = {
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/',
        'SERVER_NAME': 'social-immo.com',
        'SERVER_PORT': '443',
        'HTTP_HOST': 'social-immo.com',
        'wsgi.input': __import__('io').BytesIO(b''),
        'wsgi.errors': sys.stderr,
        'wsgi.url_scheme': 'https',
        'CONTENT_TYPE': '',
        'CONTENT_LENGTH': '0',
        'HTTP_X_FORWARDED_PROTO': 'https',
    }

    response_started = []
    def start_response(status, headers, exc_info=None):
        response_started.append(status)
        return lambda s: None

    body = application(environ, start_response)
    if response_started:
        print(f"    WSGI Response: {response_started[0]}")
    else:
        print("    WSGI: pas de reponse")
except Exception as e:
    print(f"    ERREUR WSGI: {e}")
    traceback.print_exc()

# 7. Check error log
print("\n[7] Fichier django_errors.log...")
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'django_errors.log')
if os.path.exists(log_path):
    with open(log_path) as f:
        content = f.read()
    if content:
        print(f"    CONTENU ({len(content)} chars):")
        # Show last 2000 chars
        print(content[-2000:])
    else:
        print("    (vide)")
else:
    print("    (fichier n'existe pas encore)")

print("\n" + "=" * 60)
print("FIN DU DIAGNOSTIC")
print("=" * 60)
