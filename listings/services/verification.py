"""
Verification anti-escroquerie des professionnels via le registre officiel
des entreprises francaises (recherche-entreprises.api.gouv.fr — gratuit,
sans cle, donnees INSEE/INPI).

Confirme qu'un SIRET correspond a une entreprise reelle et ACTIVE, et
renvoie son nom officiel + activite. C'est la meilleure barriere contre
les faux profils pro.
"""
import re

import requests

API = 'https://recherche-entreprises.api.gouv.fr/search'
TIMEOUT = 8


def nettoyer_siret(siret):
    """Ne garde que les chiffres. Un SIRET = 14 chiffres, un SIREN = 9."""
    return re.sub(r'\D', '', siret or '')


def verifier_siret(siret):
    """Verifie un SIRET/SIREN. Retourne un dict :
        {valide, actif, nom, activite, ville, siret}
    ou None si introuvable / erreur reseau.
    valide=True si l'entreprise existe ; actif=True si en activite.
    """
    num = nettoyer_siret(siret)
    if len(num) not in (9, 14):
        return {'valide': False, 'actif': False, 'raison': 'format'}

    try:
        r = requests.get(API, params={'q': num, 'per_page': 1}, timeout=TIMEOUT)
        r.raise_for_status()
        results = r.json().get('results', [])
    except Exception:
        return None  # reseau indisponible : on ne bloque pas, on ne valide pas

    if not results:
        return {'valide': False, 'actif': False, 'raison': 'introuvable'}

    ent = results[0]
    siege = ent.get('siege', {}) or {}
    # etat_administratif : 'A' = active, 'C' = cessee
    etat = siege.get('etat_administratif') or ent.get('etat_administratif') or ''
    actif = etat == 'A'
    return {
        'valide': True,
        'actif': actif,
        'nom': ent.get('nom_complet') or ent.get('nom_raison_sociale') or '',
        'activite': siege.get('activite_principale', ''),
        'ville': siege.get('libelle_commune', '') or siege.get('commune', ''),
        'siret': num,
    }


def appliquer_verification(pro, siret=None):
    """Verifie le SIRET d'un ProProfile et met a jour ses champs de
    confiance. Retourne le resultat de verifier_siret (ou None)."""
    siret = siret or pro.siret
    if not siret:
        return None
    resultat = verifier_siret(siret)
    if resultat is None:
        return None  # reseau KO : on laisse en l'etat, l'autopilot reessaiera
    pro.siret_verifie = bool(resultat.get('valide') and resultat.get('actif'))
    if resultat.get('valide') and resultat.get('nom'):
        pro.nom_officiel = resultat['nom'][:200]
    pro.save(update_fields=['siret_verifie', 'nom_officiel'])
    return resultat
