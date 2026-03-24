#!/usr/bin/env python
"""Debug: pourquoi le logo agence n'apparait pas sur les annonces"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_immo.settings')
django.setup()

from django.conf import settings
from listings.models import Agence

print("=== CONFIG MEDIA ===")
print(f"  MEDIA_URL: {settings.MEDIA_URL}")
print(f"  MEDIA_ROOT: {settings.MEDIA_ROOT}")
print(f"  MEDIA_ROOT existe: {os.path.exists(str(settings.MEDIA_ROOT))}")

print("\n=== AGENCES ===")
for ag in Agence.objects.filter(is_active=True):
    print(f"  Agence: {ag.nom}")
    print(f"    logo (ImageField): '{ag.logo}'")
    print(f"    logo.name: '{ag.logo.name if ag.logo else ''}'")
    print(f"    logo_url (URLField): '{ag.logo_url}'")
    if ag.logo:
        print(f"    logo.url: '{ag.logo.url}'")
        full_path = os.path.join(str(settings.MEDIA_ROOT), ag.logo.name)
        print(f"    Fichier existe: {os.path.exists(full_path)}")
        print(f"    Chemin complet: {full_path}")
    else:
        print(f"    logo est VIDE (bool={bool(ag.logo)})")

    # Test what the view would generate
    logo = ag.logo.url if ag.logo else ag.logo_url
    print(f"    -> Logo final pour annonces: '{logo}'")

print("\n=== FICHIERS MEDIA ===")
media_root = str(settings.MEDIA_ROOT)
if os.path.exists(media_root):
    for root, dirs, files in os.walk(media_root):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, media_root)
            print(f"  {rel} ({os.path.getsize(full)} bytes)")
else:
    print("  MEDIA_ROOT n'existe pas!")
