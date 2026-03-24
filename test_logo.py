#!/usr/bin/env python
"""Debug: pourquoi le logo agence n'apparait pas sur les annonces"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_immo.settings')
django.setup()

from listings.models import Annonce, Agence, AgenceOptions

print("=== AGENCES ===")
for ag in Agence.objects.filter(is_active=True):
    opts = getattr(ag, 'options', None)
    print(f"  Agence: {ag.nom}")
    print(f"    reference: '{ag.reference}'")
    print(f"    logo_url: '{ag.logo_url}'")
    print(f"    logo_sur_annonces: {opts.logo_sur_annonces if opts else 'PAS D OPTIONS'}")

print("\n=== ANNONCES (5 premieres) ===")
for ann in Annonce.objects.filter(is_active=True)[:5]:
    print(f"  {ann.reference} -> client_reference: '{ann.client_reference}'")

print("\n=== VERIFICATION MATCH ===")
agence_refs = set(Agence.objects.filter(is_active=True).values_list('reference', flat=True))
annonce_refs = set(Annonce.objects.filter(is_active=True).values_list('client_reference', flat=True).distinct())
print(f"  References agences: {agence_refs}")
print(f"  References annonces (distinct): {annonce_refs}")
print(f"  Match: {agence_refs & annonce_refs}")
print(f"  Pas de match: {annonce_refs - agence_refs}")
