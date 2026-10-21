"""Recherche en langage naturel : "je veux une maison a Perigueux de 135 m2
a 200 000 euros" -> criteres de /recherche/ (type, bien, ville, prix, surface...).

Deux etages :
  1. analyser_regles() : 100% Python, gratuit, instantane (cas courants).
  2. Claude en secours quand les regles ne comprennent presque rien
     (phrase floue). Dormant sans ANTHROPIC_API_KEY dans le .env.
Le resultat est mis en cache 24 h par texte normalise.
"""
import hashlib
import json
import logging
import re
import unicodedata

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# slug -> (libelle affiche, mots-cles cherches dans libelle_type/titre)
TYPES_BIEN = {
    'maison': ('Maison', ['maison', 'villa', 'pavillon', 'longere', 'mas', 'ferme', 'chalet', 'propriete']),
    'appartement': ('Appartement', ['appart', 'studio', 'duplex', 'loft', 'triplex']),
    'terrain': ('Terrain', ['terrain']),
    'local': ('Local / commerce', ['local', 'commerce', 'bureau', 'entrepot', 'boutique']),
    'parking': ('Parking / garage', ['parking', 'garage', 'box']),
    'immeuble': ('Immeuble', ['immeuble']),
}

# Mots du texte -> type de bien (formes normalisees sans accents)
_MOTS_BIEN = [
    ('appartement', r'appart\w*|studio|duplex|loft|triplex|\b[tf][1-6]\b'),
    ('maison', r'maison\w*|villa\w*|pavillon\w*|longere\w*|ferme\w*|chalet\w*|propriete\w*|\bmas\b'),
    ('terrain', r'terrain\w*'),
    ('local', r'\blocal\b|locaux|commerce\w*|bureau\w*|boutique\w*|entrepot\w*'),
    ('parking', r'parking\w*|garage\w*|\bbox\b'),
    ('immeuble', r'immeuble\w*'),
]

_MOTS_LOCATION = r'\b(louer|location|loyer|locataire|a la location|par mois|/mois|mensuel)\b'
_MOTS_COURTE = r'\b(vacances|courte duree|saisonnier|week-?end|nuitee?s?|airbnb)\b'

# Montant : "200 000", "200.000", "200000", "1,2", suivi d'un multiplicateur
_NOMBRE = r'(\d{1,3}(?:[ .  ]\d{3})+|\d+(?:[.,]\d+)?)'
_MULT = r'\s*(k€?|ke|keur|m€|millions?|mille)?'

_MAX = r'(moins de|max(?:imum)?|jusqu.a|pas plus de|budget(?: de| max)?|au plus|plafond|inferieur a|sous les)'
_MIN = r'(plus de|min(?:imum)?|au moins|a partir de|superieur a|minimum de|des)'


def normaliser(texte):
    """Minuscules sans accents, espaces compactes."""
    t = unicodedata.normalize('NFKD', texte or '').encode('ascii', 'ignore').decode()
    t = t.lower().replace('²', '2').replace('’', "'")
    return re.sub(r'\s+', ' ', t).strip()


def _montant(nombre, mult):
    n = float(re.sub(r'[ .  ]', '', nombre).replace(',', '.')) \
        if re.search(r'[ .  ]\d{3}', nombre) else float(nombre.replace(',', '.'))
    mult = (mult or '').strip()
    if mult.startswith('k') or mult == 'mille':
        n *= 1000
    elif mult.startswith('m'):
        n *= 1_000_000
    return int(n)


def _villes_connues():
    from listings.models import Annonce
    def charger():
        villes = Annonce.objects.filter(is_active=True).exclude(ville='') \
            .values_list('ville', flat=True).distinct()
        # nom normalise -> nom reel ; les plus longs d'abord ("saint-jean-de-luz" avant "luz")
        m = {normaliser(v).replace('-', ' '): v for v in villes}
        return sorted(m.items(), key=lambda kv: -len(kv[0]))
    return cache.get_or_set('recherche_ia:villes', charger, 600)


_STOP_VILLE = {'de', 'du', 'des', 'avec', 'pour', 'moins', 'plus', 'max', 'maximum', 'entre',
               'sous', 'budget', 'loyer', 'par', 'et', 'ou', 'prix', 'en', 'a', 'au', 'mois',
               'pas', 'qui', 'dans', 'centre', 'ville', 'proche', 'sans', 'location',
               'mer', 'campagne', 'montagne', 'vendre', 'louer'}
_VERBES = {'louer', 'vendre', 'acheter', 'partir', 'proximite'}


def _forme_originale(texte, mots_normalises):
    """Retrouve dans le texte d'origine (avec accents) les mots normalises donnes."""
    mots = re.findall(r"[\w'-]+", texte)
    n = len(mots_normalises)
    for i in range(len(mots) - n + 1):
        if [normaliser(m) for m in mots[i:i + n]] == mots_normalises:
            return ' '.join(m[:1].upper() + m[1:] for m in mots[i:i + n])
    return ' '.join(mots_normalises).title()


def _trouver_ville(t, texte):
    """Ville du catalogue citee dans le texte, sinon code postal, sinon "a <Nom>"."""
    t_espaces = t.replace('-', ' ')
    for norme, reelle in _villes_connues():
        if len(norme) >= 3 and re.search(rf'\b{re.escape(norme)}\b', t_espaces):
            return reelle
    cp = re.search(r'\b(\d{5})\b', t)
    if cp and not re.search(rf'{cp.group(1)}\s*(€|euro|eur)', t):
        return cp.group(1)
    # Ville hors catalogue : mots qui suivent "a/sur/vers/pres de..."
    for m in re.finditer(r"\b(?:a|au|aux|sur|vers|pres de|autour de|cote de|region de|secteur)\s+(?=([a-z' -]+))", t):
        mots = m.group(1).split()
        while mots and mots[0] in _VERBES:
            mots.pop(0)
        retenus = []
        for mot in mots[:4]:
            if mot in _STOP_VILLE or re.match(r'\d', mot):
                break
            retenus.append(mot)
        if retenus and retenus[-1] not in ('la', 'le', 'les', 'l') and len(''.join(retenus)) >= 3:
            return _forme_originale(texte, retenus)
    return ''


def analyser_regles(texte):
    """Extrait les criteres sans IA externe. Retourne un dict de parametres GET."""
    t = normaliser(texte)
    c = {}

    # Transaction
    if re.search(_MOTS_COURTE, t):
        c['type'] = 'S'
    elif re.search(_MOTS_LOCATION, t):
        c['type'] = 'L'
    else:
        c['type'] = 'V'

    # Type de bien
    for slug, motif in _MOTS_BIEN:
        if re.search(motif, t):
            c['bien'] = slug
            break

    ville = _trouver_ville(t, texte)
    if ville:
        c['ville'] = ville

    # Pieces : "T3", "F4", "3 pieces"
    m = re.search(r'\b[tf]([1-9])\b', t) or re.search(r'\b(\d{1,2})\s*pieces?\b', t)
    if m:
        c['pieces_min'] = int(m.group(1))
    m = re.search(r'\b(\d{1,2})\s*chambres?\b', t)
    if m:
        c['chambres_min'] = int(m.group(1))

    # Surface : "135 m2", "135 metres carres"
    for m in re.finditer(rf'(?:{_MAX}|{_MIN}|entre)?\s*{_NOMBRE}\s*(?:m2|m 2|metres? carres?|mcarres?)', t):
        val = _montant(m.group(3), '')
        if not 5 <= val <= 100000:
            continue
        if m.group(1):
            c['surface_max'] = val
        elif m.group(2):
            c['surface_min'] = val
        else:
            # "135 m2" = souhait approximatif : tolerance -10 %
            c['surface_min'] = int(val * 0.9)
        break

    # Prix : "entre 150 et 200 000 €", "moins de 200k", "a 200 000 euros"
    sans_surface = re.sub(rf'{_NOMBRE}\s*(?:m2|m 2|metres? carres?)', ' ', t)
    sans_surface = re.sub(r'\b\d{1,2}\s*(pieces?|chambres?)\b|\b[tf][1-9]\b|\b\d{5}\b(?!\s*(€|euro|eur))', ' ', sans_surface)
    m = re.search(rf'entre\s+{_NOMBRE}{_MULT}\s*(?:€|euros?|eur)?\s*et\s+{_NOMBRE}{_MULT}', sans_surface)
    if m:
        haut = _montant(m.group(3), m.group(4))
        bas = _montant(m.group(1), m.group(2) or m.group(4))
        if bas < 1000 <= haut and not m.group(2):
            bas *= 1000  # "entre 150 et 200 000" -> 150 000
        c['prix_min'], c['prix_max'] = min(bas, haut), max(bas, haut)
    else:
        for m in re.finditer(rf'(?:{_MAX}|{_MIN})?\s*{_NOMBRE}{_MULT}\s*(€|euros?|eur\b)?', sans_surface):
            if not (m.group(4) or m.group(5) or m.group(1) or m.group(2)):
                # nombre nu sans unite ni qualificatif : prix seulement s'il est gros
                if _montant(m.group(3), '') < 1000:
                    continue
            val = _montant(m.group(3), m.group(4))
            if val < 50:
                continue
            if m.group(2):
                c['prix_min'] = val
            elif m.group(1):
                c['prix_max'] = val
            else:
                # Prix nu = budget vise : tolerance +5 %
                c['prix_max'] = int(val * 1.05)
            break

    # Caracteristiques
    if re.search(r'jardin|terrasse|balcon|exterieur|cour\b', t):
        c['exterieur'] = 1
    if re.search(r'parking|garage|stationnement|\bbox\b', t) and c.get('bien') != 'parking':
        c['parking'] = 1
    if re.search(r'\bmeuble', t):
        c['meuble'] = 1
    if re.search(r'ascenseur', t):
        c['ascenseur'] = 1
    return c


def _nb_criteres_utiles(c):
    return len([k for k in c if k != 'type'])


# ---------- Secours Claude (dormant sans cle) ----------

_SCHEMA = {
    'type': 'object',
    'properties': {
        'type': {'type': 'string', 'enum': ['V', 'L', 'S'],
                 'description': 'V=achat, L=location longue duree, S=location courte duree/vacances'},
        'bien': {'type': 'string', 'enum': [''] + list(TYPES_BIEN)},
        'ville': {'type': 'string', 'description': 'Commune ou code postal, vide si aucun'},
        'prix_min': {'type': 'integer'}, 'prix_max': {'type': 'integer'},
        'surface_min': {'type': 'integer'}, 'surface_max': {'type': 'integer'},
        'pieces_min': {'type': 'integer'}, 'chambres_min': {'type': 'integer'},
        'exterieur': {'type': 'boolean'}, 'parking': {'type': 'boolean'},
        'meuble': {'type': 'boolean'}, 'ascenseur': {'type': 'boolean'},
    },
    'required': ['type', 'bien', 'ville', 'prix_min', 'prix_max', 'surface_min', 'surface_max',
                 'pieces_min', 'chambres_min', 'exterieur', 'parking', 'meuble', 'ascenseur'],
    'additionalProperties': False,
}

_SYSTEME = (
    "Tu convertis la demande d'un particulier qui cherche un bien immobilier en France "
    "en criteres de recherche. Mets 0 (ou chaine vide / false) pour tout critere non exprime : "
    "n'invente rien. Un prix seul est un budget maximum ; une surface seule est un minimum "
    "approximatif (retire 10 %). Les montants sont en euros entiers (200k = 200000). "
    "Pour une location, prix_max est le loyer mensuel."
)


def analyser_claude(texte):
    """Criteres via Claude, ou None si indisponible/echec (jamais d'exception)."""
    if not getattr(settings, 'ANTHROPIC_API_KEY', ''):
        return None
    try:
        import anthropic
    except ImportError:
        logger.warning('recherche_ia : paquet anthropic absent (pip install anthropic)')
        return None
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=20.0, max_retries=1)
        response = client.beta.messages.create(
            model=settings.RECHERCHE_IA_MODEL,
            max_tokens=2000,
            betas=['server-side-fallback-2026-07-01'],
            fallbacks='default',
            system=_SYSTEME,
            output_config={'effort': 'low', 'format': {'type': 'json_schema', 'schema': _SCHEMA}},
            messages=[{'role': 'user', 'content': texte[:500]}],
        )
        if response.stop_reason != 'end_turn':
            logger.warning('recherche_ia : stop_reason=%s', response.stop_reason)
            return None
        data = json.loads(next(b.text for b in response.content if b.type == 'text'))
    except Exception as e:  # reseau, quota, JSON : on retombe sur les regles
        logger.warning('recherche_ia : echec Claude (%s)', e)
        return None
    c = {'type': data.get('type') or 'V'}
    if data.get('bien') in TYPES_BIEN:
        c['bien'] = data['bien']
    if (data.get('ville') or '').strip():
        c['ville'] = data['ville'].strip()[:80]
    for k in ('prix_min', 'prix_max', 'surface_min', 'surface_max', 'pieces_min', 'chambres_min'):
        if isinstance(data.get(k), int) and data[k] > 0:
            c[k] = data[k]
    for k in ('exterieur', 'parking', 'meuble', 'ascenseur'):
        if data.get(k) is True:
            c[k] = 1
    return c


# ---------- Point d'entree ----------

def _alertes(c):
    alertes = []
    prix, surface = c.get('prix_max'), c.get('surface_min')
    if c.get('type') == 'V' and prix:
        if prix < 15000 and c.get('bien') not in ('parking', 'terrain'):
            alertes.append(f"Un budget de {prix:,} € semble très bas pour un achat : "
                           f"vouliez-vous dire {prix * 10:,} € ?".replace(',', ' '))
        elif surface and prix / surface < 400:
            msg = f"{prix:,} € pour {surface} m² environ, soit moins de 400 €/m² : peu de biens risquent de correspondre."
            if 500 <= prix * 10 / surface <= 15000:
                msg += f" Vouliez-vous dire {prix * 10:,} € ?"
            alertes.append(msg.replace(',', ' '))
    return alertes


def resume(c):
    """Libelles lisibles des criteres compris (chips 'J'ai compris')."""
    lib = {'V': 'Achat', 'L': 'Location', 'S': 'Courte durée'}
    r = [lib.get(c.get('type'), 'Achat')]
    if c.get('bien'):
        r.append(TYPES_BIEN[c['bien']][0])
    if c.get('ville'):
        r.append(f"📍 {c['ville']}")
    fmt = lambda n: f'{n:,}'.replace(',', ' ')
    if c.get('prix_min') and c.get('prix_max'):
        r.append(f"{fmt(c['prix_min'])} – {fmt(c['prix_max'])} €")
    elif c.get('prix_max'):
        r.append(f"≤ {fmt(c['prix_max'])} €")
    elif c.get('prix_min'):
        r.append(f"≥ {fmt(c['prix_min'])} €")
    if c.get('surface_min'):
        r.append(f"≥ {c['surface_min']} m²")
    if c.get('surface_max'):
        r.append(f"≤ {c['surface_max']} m²")
    if c.get('pieces_min'):
        r.append(f"{c['pieces_min']}+ pièces")
    if c.get('chambres_min'):
        r.append(f"{c['chambres_min']}+ chambres")
    for k, l in (('exterieur', 'Extérieur'), ('parking', 'Parking'), ('meuble', 'Meublé'), ('ascenseur', 'Ascenseur')):
        if c.get(k):
            r.append(l)
    return r


def analyser(texte):
    """{'criteres': {...}, 'resume': [...], 'alertes': [...], 'source': 'regles'|'ia'}"""
    texte = (texte or '').strip()[:500]
    cle = 'recherche_ia:' + hashlib.sha1(normaliser(texte).encode()).hexdigest()
    res = cache.get(cle)
    if res is not None:
        return res
    c, source = analyser_regles(texte), 'regles'
    # Phrase floue (< 2 criteres compris sur une vraie phrase) : on demande a Claude
    if _nb_criteres_utiles(c) < 2 and len(texte.split()) >= 4:
        c_ia = analyser_claude(texte)
        if c_ia and _nb_criteres_utiles(c_ia) > _nb_criteres_utiles(c):
            c, source = c_ia, 'ia'
    res = {'criteres': c, 'resume': resume(c), 'alertes': _alertes(c), 'source': source}
    cache.set(cle, res, 86400)
    return res
