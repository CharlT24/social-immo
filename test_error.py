#!/usr/bin/env python
"""Script de debug pour trouver l'erreur 500 sur o2switch.
Usage: cd ~/social-immo && python test_error.py
"""
import os, sys, traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_immo.settings')

# Force DEBUG pour voir les erreurs
os.environ['DEBUG'] = 'True'

import django
django.setup()

# Ajouter testserver aux ALLOWED_HOSTS pour le Client
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')
    settings.ALLOWED_HOSTS.append('localhost')

print("=" * 60)
print("DIAGNOSTIC SOCIAL IMMO")
print("=" * 60)

# 1. Check settings
from django.conf import settings
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

    # Test specific fields that were recently added
    a = Annonce.objects.first()
    if a:
        _ = a.mise_en_avant
        _ = a.nb_vues
        _ = a.video_url
        _ = a.visite_virtuelle_url
        print("    OK - Champs Annonce (mise_en_avant, nb_vues, video_url, visite_virtuelle_url)")

    ag = Agence.objects.first()
    if ag:
        _ = ag.mise_en_avant
        print("    OK - Champ Agence.mise_en_avant")
        opts = getattr(ag, 'options', None)
        if opts:
            # Check removed fields don't exist
            print(f"    AgenceOptions exists, logo_sur_annonces={opts.logo_sur_annonces}")

    pp = ProProfile.objects.first()
    if pp:
        _ = pp.mise_en_avant
        print("    OK - Champ ProProfile.mise_en_avant")
except Exception as e:
    print(f"    ERREUR: {e}")
    traceback.print_exc()

# 4. Check URL resolution
print("\n[4] Test URLs...")
try:
    from django.urls import reverse
    urls_to_test = [
        'listings:homepage', 'listings:search_results', 'listings:decoration_list',
        'listings:partenaire_list', 'listings:estimation', 'listings:agence_immo',
        'listings:locaux_pro',
    ]
    for url_name in urls_to_test:
        try:
            url = reverse(url_name)
            print(f"    OK: {url_name} -> {url}")
        except Exception as e:
            print(f"    ERREUR: {url_name} -> {e}")
except Exception as e:
    print(f"    ERREUR: {e}")

# 5. Test views rendering
print("\n[5] Test rendu des vues...")
from django.test import RequestFactory, Client
from django.contrib.auth.models import AnonymousUser

rf = RequestFactory()

views_to_test = [
    ('homepage', '/'),
    ('search_results', '/recherche/'),
    ('agence_immo', '/agence-immobiliere/'),
]

for view_name, path in views_to_test:
    try:
        from listings import views
        view_func = getattr(views, view_name)
        req = rf.get(path)
        req.user = AnonymousUser()
        resp = view_func(req)
        print(f"    OK: {view_name} -> status {resp.status_code}")
    except Exception as e:
        print(f"    ERREUR {view_name}: {e}")
        traceback.print_exc()

# 6. Test full Client (includes middleware, context processors, template rendering)
print("\n[6] Test Client complet (middleware + templates)...")
c = Client()
pages_to_test = [
    ('/', 'Homepage'),
    ('/recherche/', 'Recherche'),
    ('/agence-immobiliere/', 'Agence immo'),
    ('/inspirations/', 'Inspirations'),
    ('/pros/', 'Pros'),
    ('/estimer/', 'Estimation'),
    ('/locaux-professionnels/', 'Locaux pro'),
]
for url, label in pages_to_test:
    try:
        resp = c.get(url)
        print(f"    OK: {label} ({url}) -> status {resp.status_code}")
    except Exception as e:
        print(f"    ERREUR {label} ({url}): {e}")
        traceback.print_exc()

# 7. Check staticfiles manifest
print("\n[7] Test WhiteNoise / staticfiles...")
try:
    from django.contrib.staticfiles.storage import staticfiles_storage
    manifest_path = getattr(staticfiles_storage, 'manifest_name', None)
    if manifest_path:
        static_root = settings.STATIC_ROOT
        full_path = os.path.join(str(static_root), manifest_path) if manifest_path else None
        exists = os.path.exists(full_path) if full_path else False
        print(f"    STATIC_ROOT = {static_root}")
        print(f"    Manifest existe: {exists}")
        if not exists:
            print("    ATTENTION: Le manifest staticfiles n'existe pas!")
            print("    -> Lancez: python manage.py collectstatic --noinput")
    else:
        print("    Pas de manifest (storage simple)")
except Exception as e:
    print(f"    ERREUR: {e}")

print("\n" + "=" * 60)
print("FIN DU DIAGNOSTIC")
print("=" * 60)
