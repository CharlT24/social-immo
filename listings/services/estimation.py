"""
Moteur d'estimation immobiliere "maison" — 100% Python, compatible o2switch.

Methode :
1. Comparables : annonces en vente de la meme ville (puis du meme departement)
   -> mediane du prix au m2.
2. Si trop peu de comparables, repli sur un bareme national par type de bien,
   module par departement.
3. Ajustements simples (nombre de pieces vs surface, terrain).
4. Fourchette basse/haute selon la fiabilite (nombre de comparables).
"""
from statistics import median

from django.db.models import Q

# Bareme national indicatif (EUR/m2) par type de bien — repli quand la base
# ne contient pas assez de comparables locaux.
BAREME_NATIONAL = {
    'appartement': 3200,
    'maison': 2400,
    'terrain': 130,
    'commerce': 2000,
    'bureau': 2200,
    'autre': 2300,
}

# Coefficients departementaux indicatifs (base 1.0 = moyenne nationale).
COEF_DEPARTEMENT = {
    '75': 3.10, '92': 2.20, '78': 1.45, '94': 1.55, '93': 1.15, '95': 1.05,
    '91': 1.05, '77': 0.95, '69': 1.45, '13': 1.10, '06': 1.65, '83': 1.35,
    '33': 1.30, '44': 1.20, '31': 1.15, '34': 1.15, '35': 1.15, '74': 1.60,
    '73': 1.30, '64': 1.20, '17': 1.15, '85': 0.95, '29': 0.90, '56': 1.00,
    '67': 1.05, '68': 0.90, '59': 0.90, '62': 0.80, '80': 0.75, '76': 0.85,
    '14': 1.00, '50': 0.80, '61': 0.60, '27': 0.85, '28': 0.80, '45': 0.85,
    '37': 0.95, '49': 0.90, '72': 0.70, '41': 0.70, '18': 0.60, '36': 0.50,
    '87': 0.60, '23': 0.45, '19': 0.65, '24': 0.70, '46': 0.75,
    '63': 0.80, '42': 0.70, '38': 1.05, '26': 0.95, '84': 1.00, '30': 0.90,
    '11': 0.85, '66': 0.90, '09': 0.65, '81': 0.75, '82': 0.75, '32': 0.70,
    '40': 0.95, '47': 0.65, '86': 0.65, '79': 0.65, '16': 0.60, '58': 0.55,
    '71': 0.70, '39': 0.70, '25': 0.85, '70': 0.55, '90': 0.70, '88': 0.55,
    '54': 0.75, '57': 0.80, '55': 0.45, '52': 0.45, '51': 0.80, '10': 0.65,
    '89': 0.60, '21': 0.85, '08': 0.50, '02': 0.55, '60': 0.80, '53': 0.65,
    '22': 0.85, '15': 0.55, '43': 0.55, '48': 0.60, '07': 0.75, '01': 1.00,
    '03': 0.50, '05': 1.00, '04': 0.90, '2A': 1.35, '2B': 1.10,
    '971': 1.00, '972': 1.00, '973': 0.90, '974': 1.00, '976': 0.80,
}

# Correspondance type d'estimation -> codes types d'annonces comparables.
TYPES_COMPARABLES = {
    'appartement': ['appartement', 'appart', 'studio', 'duplex', 'loft'],
    'maison': ['maison', 'villa', 'propriete', 'pavillon', 'longere', 'mas', 'ferme'],
    'terrain': ['terrain'],
    'commerce': ['commerce', 'local', 'boutique', 'fonds'],
    'bureau': ['bureau'],
}


def _departement(code_postal):
    cp = (code_postal or '').strip()
    if cp.startswith('97') or cp.startswith('98'):
        return cp[:3]
    if cp[:2] in ('20',):  # Corse
        return '2A' if cp[:3] <= '201' else '2B'
    return cp[:2]


def _comparables_qs(type_bien, ville=None, departement=None):
    """Annonces en vente comparables (actives ou recemment desactivees)."""
    from listings.models import Annonce

    qs = Annonce.objects.filter(
        type_transaction='V', prix__isnull=False, prix__gt=10000,
        surface__isnull=False, surface__gt=9,
    )
    mots = TYPES_COMPARABLES.get(type_bien)
    if mots:
        cond = Q()
        for mot in mots:
            cond |= Q(libelle_type__icontains=mot) | Q(titre__icontains=mot)
        qs = qs.filter(cond)
    if ville:
        qs = qs.filter(ville__iexact=ville.strip())
    elif departement:
        qs = qs.filter(code_postal__startswith=departement)
    return qs


def _prix_m2_liste(qs, limit=200):
    valeurs = []
    for prix, surface in qs.values_list('prix', 'surface')[:limit]:
        try:
            v = float(prix) / float(surface)
        except (TypeError, ZeroDivisionError):
            continue
        # Ecarte les valeurs aberrantes evidentes
        if 100 <= v <= 30000:
            valeurs.append(v)
    return valeurs


def estimer_bien(type_bien, ville, code_postal, surface, nb_pieces=None):
    """Retourne un dict d'estimation, ou None si surface manquante.

    Cles : prix_estime, prix_min, prix_max, prix_m2, nb_comparables,
           zone ('ville' | 'departement' | 'bareme'), confiance ('haute'|'moyenne'|'indicative')
    """
    try:
        surface = float(surface)
    except (TypeError, ValueError):
        return None
    if surface <= 0:
        return None

    type_bien = type_bien if type_bien in BAREME_NATIONAL else 'autre'
    dep = _departement(code_postal)

    # 1. Comparables dans la ville
    valeurs = _prix_m2_liste(_comparables_qs(type_bien, ville=ville))
    zone = 'ville'

    # 2. Elargir au departement
    if len(valeurs) < 3 and dep:
        valeurs = _prix_m2_liste(_comparables_qs(type_bien, departement=dep))
        zone = 'departement'

    # 3. Bareme national x coefficient departemental
    if len(valeurs) < 3:
        base = BAREME_NATIONAL[type_bien]
        coef = COEF_DEPARTEMENT.get(dep, 0.85)
        prix_m2 = base * coef
        nb_comparables = 0
        zone = 'bareme'
        marge = 0.20
        confiance = 'indicative'
    else:
        prix_m2 = median(valeurs)
        nb_comparables = len(valeurs)
        if nb_comparables >= 10 and zone == 'ville':
            marge, confiance = 0.10, 'haute'
        elif nb_comparables >= 5:
            marge, confiance = 0.15, 'moyenne'
        else:
            marge, confiance = 0.20, 'indicative'

    # Ajustement : petites surfaces se vendent plus cher au m2, grandes moins cher
    if type_bien in ('appartement', 'maison'):
        if surface < 30:
            prix_m2 *= 1.10
        elif surface > 150:
            prix_m2 *= 0.92
        # Beaucoup de pieces pour la surface = bien decoupe, legere decote
        if nb_pieces:
            try:
                ratio = surface / float(nb_pieces)
                if ratio < 15:
                    prix_m2 *= 0.95
                elif ratio > 40:
                    prix_m2 *= 1.03
            except (TypeError, ZeroDivisionError):
                pass

    prix_estime = prix_m2 * surface

    def _arrondi(v):
        # Arrondi commercial au millier
        return int(round(v / 1000.0) * 1000)

    return {
        'prix_estime': _arrondi(prix_estime),
        'prix_min': _arrondi(prix_estime * (1 - marge)),
        'prix_max': _arrondi(prix_estime * (1 + marge)),
        'prix_m2': int(round(prix_m2)),
        'nb_comparables': nb_comparables,
        'zone': zone,
        'confiance': confiance,
    }
