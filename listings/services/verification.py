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


def _normaliser(nom):
    """Normalise un nom d'entreprise pour comparaison (minuscules, sans
    accents, sans ponctuation, sans formes juridiques courantes)."""
    import re
    import unicodedata
    n = unicodedata.normalize('NFKD', nom or '').encode('ascii', 'ignore').decode()
    n = n.lower()
    for forme in (' sarl', ' sas', ' sasu', ' eurl', ' sa ', ' ei ', ' eirl',
                  ' sci', ' snc', 'entreprise ', 'monsieur ', 'madame ', ' m '):
        n = n.replace(forme, ' ')
    n = re.sub(r'[^a-z0-9]', '', n)
    return n


def noms_correspondent(declare, officiel):
    """Le nom declare par le pro correspond-il au nom officiel du registre ?
    Tolerant (l'un contient l'autre, ou egalite apres normalisation)."""
    a, b = _normaliser(declare), _normaliser(officiel)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def appliquer_verification(pro, siret=None):
    """Verifie le SIRET d'un ProProfile et met a jour ses champs de
    confiance. Retourne le resultat de verifier_siret (ou None).

    SECURITE anti-usurpation : le badge 'Verifie' n'est accorde que si
    l'entreprise existe, est active, ET que le nom declare correspond au
    nom officiel du registre. Sinon on stocke le nom officiel pour revue
    admin mais on n'accorde PAS le badge (empeche de saisir le SIRET
    public d'une societe connue pour se faire passer pour elle)."""
    siret = siret or pro.siret
    if not siret:
        return None
    resultat = verifier_siret(siret)
    if resultat is None:
        return None  # reseau KO : on laisse en l'etat, l'autopilot reessaiera

    nom_officiel = resultat.get('nom', '') if resultat.get('valide') else ''
    correspond = noms_correspondent(pro.nom_entreprise, nom_officiel)
    pro.siret_verifie = bool(resultat.get('valide') and resultat.get('actif')
                             and correspond)
    if nom_officiel:
        pro.nom_officiel = nom_officiel[:200]
    pro.save(update_fields=['siret_verifie', 'nom_officiel'])
    resultat['correspond'] = correspond
    return resultat
