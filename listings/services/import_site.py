"""Import des annonces depuis le SITE WEB d'une agence (sans flux XML), avec son
autorisation (Agence.autorisation_site_at). Sans IA : on lit ce que les sites
publient deja pour Google :
  1. donnees structurees JSON-LD (schema.org RealEstateListing, Product, Offer,
     House, Apartment, Residence...) ;
  2. a defaut, balises Open Graph (titre, description, image) + prix et surface
     reperes dans le texte de la page.
Le resultat est converti en XML AC3 et passe a import_xml._import_ac3 : on
reutilise ainsi annule/remplace, garde-fou, photos et IndexNow.

Politesse : robots.txt respecte, 1 requete / DELAI secondes, MAX_PAGES pages
par site, User-Agent identifiable.
Evolution prevue (ROADMAP v8) : repli sur Claude pour les pages sans donnees
structurees.
"""
import hashlib
import json
import logging
import re
import time
from urllib import robotparser
from urllib.parse import urljoin, urlsplit

import requests
from lxml import etree, html

logger = logging.getLogger(__name__)

USER_AGENT = 'SocialImmoBot/1.0 (+https://social-immo.com/agence-immobiliere/)'
DELAI = 1.0
MAX_PAGES = 200
TIMEOUT = 20

# URL qui ressemblent a une fiche annonce (sites d'agences francais courants)
_MOTIF_FICHE = re.compile(
    r'/(annonce|annonces|bien|biens|vente|ventes|location|locations|achat|acheter|louer|'
    r'detail|fiche|propriete|property|properties|listing|immobilier|offre)s?[/-]', re.I)
_MOTIF_EXCLU = re.compile(
    r'\.(jpe?g|png|gif|webp|pdf|css|js|zip)(\?|$)|/(tag|categorie|category|page|blog|actualite|'
    r'contact|mentions|cgu|recrutement|equipe|agence)s?/?$|[?&](page|tri|sort)=', re.I)

_TYPES_LD = {'realestatelisting', 'product', 'offer', 'house', 'apartment', 'residence',
             'singlefamilyresidence', 'accommodation', 'place', 'landmarksorhistoricalbuildings',
             'individualproduct', 'room', 'suite'}


class Lecteur:
    """Session HTTP polie (robots.txt + delai) limitee a un site."""

    def __init__(self, site_url):
        p = urlsplit(site_url if '://' in site_url else f'https://{site_url}')
        self.racine = f'{p.scheme}://{p.netloc}'
        self.hote = p.netloc.lower().removeprefix('www.')
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        self.robots = robotparser.RobotFileParser()
        self.sitemaps_robots = []
        try:
            r = self.session.get(f'{self.racine}/robots.txt', timeout=TIMEOUT)
            lignes = r.text.splitlines() if r.ok else []
            self.robots.parse(lignes)
            self.sitemaps_robots = [l.split(':', 1)[1].strip() for l in lignes
                                    if l.lower().startswith('sitemap:')]
        except requests.RequestException:
            self.robots.parse([])
        self._dernier = 0.0

    def autorise(self, url):
        return self.robots.can_fetch(USER_AGENT, url)

    def meme_site(self, url):
        return urlsplit(url).netloc.lower().removeprefix('www.') == self.hote

    def get(self, url):
        if not self.autorise(url):
            return None
        attente = DELAI - (time.monotonic() - self._dernier)
        if attente > 0:
            time.sleep(attente)
        self._dernier = time.monotonic()
        try:
            r = self.session.get(url, timeout=TIMEOUT)
            return r if r.ok else None
        except requests.RequestException as e:
            logger.info('import_site : %s injoignable (%s)', url, e)
            return None


# ---------- Decouverte des fiches ----------

def _urls_sitemap(lecteur, url, profondeur=0):
    r = lecteur.get(url)
    if r is None or profondeur > 2:
        return []
    try:
        racine = etree.fromstring(r.content)
    except etree.XMLSyntaxError:
        return []
    locs = [e.text.strip() for e in racine.iter('{*}loc') if e.text]
    if racine.tag.endswith('sitemapindex'):
        urls = []
        for sm in locs[:20]:
            urls += _urls_sitemap(lecteur, sm, profondeur + 1)
        return urls
    return locs


def decouvrir_fiches(lecteur):
    """URL des fiches annonces : sitemap(s) d'abord, sinon liens de l'accueil
    et des pages de liste (1 niveau)."""
    candidates = []
    for sm in lecteur.sitemaps_robots or [f'{lecteur.racine}/sitemap.xml']:
        candidates += _urls_sitemap(lecteur, sm)
    if not candidates:
        a_visiter = [lecteur.racine + '/']
        vues = set()
        for page in a_visiter[:15]:
            r = lecteur.get(page)
            if r is None:
                continue
            doc = html.fromstring(r.content, base_url=page)
            for href in doc.xpath('//a/@href'):
                u = urljoin(page, href).split('#')[0]
                if u in vues or not lecteur.meme_site(u):
                    continue
                vues.add(u)
                candidates.append(u)
                # Pages de liste ("/vente/", "/nos-biens/") : un niveau de plus
                if page == lecteur.racine + '/' and _MOTIF_FICHE.search(u + '/'):
                    a_visiter.append(u)
    fiches = []
    for u in dict.fromkeys(candidates):
        if lecteur.meme_site(u) and _MOTIF_FICHE.search(u) and not _MOTIF_EXCLU.search(u):
            fiches.append(u)
    return fiches[:MAX_PAGES]


# ---------- Extraction d'une fiche ----------

def _nombre(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r'\d[\d\s  .]*(?:,\d+)?', str(v))
    if not m:
        return None
    brut = re.sub(r'[\s  ]', '', m.group(0))
    if re.fullmatch(r'\d{1,3}(\.\d{3})+', brut):
        brut = brut.replace('.', '')
    try:
        return float(brut.replace(',', '.'))
    except ValueError:
        return None


def _objets_ld(doc):
    """Tous les objets JSON-LD de la page, @graph et listes aplatis."""
    objets = []
    for bloc in doc.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            data = json.loads(bloc)
        except ValueError:
            continue
        pile = [data]
        while pile:
            o = pile.pop()
            if isinstance(o, list):
                pile += o
            elif isinstance(o, dict):
                objets.append(o)
                for k in ('@graph', 'itemOffered', 'offers', 'mainEntity', 'about'):
                    if isinstance(o.get(k), (dict, list)):
                        pile.append(o[k])
    return objets


def normaliser_texte(t):
    return re.sub(r'\s+', ' ', (t or '').strip().lower())


def _types(o):
    t = o.get('@type', [])
    return {x.lower() for x in (t if isinstance(t, list) else [t]) if isinstance(x, str)}


def _images(v):
    out = []
    for i in (v if isinstance(v, list) else [v]):
        if isinstance(i, dict):
            i = i.get('url') or i.get('contentUrl')
        if isinstance(i, str) and i.startswith('http'):
            out.append(i)
    return out


def extraire_fiche(url, contenu):
    """Dict annonce (titre, texte, prix, surface, ville, cp, pieces, photos,
    transaction, libelle_type) ou None si la page n'est pas une annonce."""
    if isinstance(contenu, bytes):
        # lxml suppose latin-1 sans <meta charset> : on decode nous-memes
        try:
            contenu = contenu.decode('utf-8')
        except UnicodeDecodeError:
            contenu = contenu.decode('latin-1')
    try:
        doc = html.fromstring(contenu, base_url=url)
    except (etree.ParserError, ValueError):
        return None
    a = {'url': url, 'photos': []}

    for o in _objets_ld(doc):
        if not _types(o) & _TYPES_LD:
            continue
        a.setdefault('titre', o.get('name'))
        a.setdefault('texte', o.get('description'))
        a['photos'] += _images(o.get('image'))
        offre = o.get('offers') if isinstance(o.get('offers'), dict) else o
        if 'prix' not in a and _nombre(offre.get('price')):
            a['prix'] = _nombre(offre.get('price'))
        taille = o.get('floorSize')
        if isinstance(taille, dict):
            taille = taille.get('value')
        if 'surface' not in a and _nombre(taille):
            a['surface'] = _nombre(taille)
        if 'pieces' not in a and _nombre(o.get('numberOfRooms')):
            a['pieces'] = int(_nombre(o.get('numberOfRooms')))
        adr = o.get('address')
        if isinstance(adr, dict):
            a.setdefault('ville', adr.get('addressLocality'))
            a.setdefault('cp', adr.get('postalCode'))
        types = _types(o)
        if 'house' in types or 'singlefamilyresidence' in types:
            a.setdefault('libelle_type', 'Maison')
        elif 'apartment' in types:
            a.setdefault('libelle_type', 'Appartement')

    # Repli Open Graph + texte de la page
    og = lambda p: (doc.xpath(f'//meta[@property="og:{p}"]/@content') or [None])[0]
    a['titre'] = a.get('titre') or og('title') or (doc.xpath('//h1//text()') or [''])[0].strip()
    a['texte'] = a.get('texte') or og('description') or ''
    if og('image'):
        a['photos'].append(og('image'))
    # Galerie de la fiche (carrousel / slider) : complete les photos
    galerie = doc.xpath(
        '//*[contains(@class,"galer") or contains(@class,"gallery") or contains(@class,"carousel")'
        ' or contains(@class,"slider") or contains(@class,"swiper") or contains(@class,"photo")'
        ' or contains(@id,"galer") or contains(@id,"gallery") or contains(@id,"carousel")]'
        '//img/@src | //*[contains(@class,"galer") or contains(@class,"gallery") or contains(@class,"carousel")'
        ' or contains(@class,"slider") or contains(@class,"swiper")]//img/@data-src'
        ' | //*[contains(@class,"galer") or contains(@class,"gallery") or contains(@class,"carousel")]//a/@href')
    a['photos'] += [g for g in galerie if re.search(r'\.(jpe?g|png|webp)(\?|$)', g, re.I)
                    and not re.search(r'logo|icon|avatar|picto|sprite', g, re.I)]
    # Images de la meme annonce : texte alternatif = titre, ou meme dossier
    # (identifiant du bien) que la photo principale
    titre_court = normaliser_texte(a['titre'])[:15]
    dossiers = {seg for p in a['photos'] for seg in urlsplit(urljoin(url, p)).path.split('/')
                if len(seg) >= 8 and not re.search(r'\.(jpe?g|png|webp)$', seg, re.I)}
    for img in doc.xpath('//img'):
        src = img.get('src') or img.get('data-src') or ''
        if not re.search(r'\.(jpe?g|png|webp)(\?|$)', src, re.I) or re.search(r'logo|icon|avatar|picto', src, re.I):
            continue
        alt = normaliser_texte(img.get('alt') or '')
        if (titre_court and alt.startswith(titre_court)) or \
                dossiers & set(urlsplit(urljoin(url, src)).path.split('/')):
            a['photos'].append(src)
    texte_page = ' '.join(doc.xpath('//body//text()'))
    texte_page = re.sub(r'\s+', ' ', texte_page)
    if 'prix' not in a:
        m = re.search(r'(\d{1,3}(?:[\s  .]\d{3})+|\d{3,7})\s*(?:€|euros?)', texte_page, re.I)
        if m:
            a['prix'] = _nombre(m.group(1))
    if 'surface' not in a:
        m = re.search(r'(\d{1,4}(?:[.,]\d{1,2})?)\s*m(?:²|2)\b', texte_page)
        if m:
            a['surface'] = _nombre(m.group(1))
    if not a.get('cp'):
        m = re.search(r'\b((?:0[1-9]|[1-8]\d|9[0-5]|97)\d{3})\s+([A-ZÉÈ][\w\'éèêàâîôûç -]{2,40})', texte_page)
        if m:
            a['cp'] = m.group(1)
            a.setdefault('ville', m.group(2).strip().split('  ')[0])

    # Une annonce doit avoir au moins un prix et un titre
    if not a.get('prix') or not a.get('titre'):
        return None
    contexte = f"{url} {a['titre']} {a['texte'][:300]}".lower()
    a['transaction'] = 'L' if re.search(r'locat|louer|/mois|loyer', contexte) else 'V'
    if not a.get('libelle_type'):
        for mot, lib in (('appartement', 'Appartement'), ('maison', 'Maison'), ('terrain', 'Terrain'),
                         ('studio', 'Appartement'), ('villa', 'Maison'), ('local', 'Local commercial')):
            if mot in contexte:
                a['libelle_type'] = lib
                break
    a['photos'] = list(dict.fromkeys(urljoin(url, p) for p in a['photos']))[:30]
    return a


# ---------- Conversion en XML AC3 ----------

def vers_xml_ac3(reference_agence, annonces):
    """XML au format du flux CRM, consomme tel quel par import_xml._import_ac3."""
    client = etree.Element('client', reference=reference_agence)

    def sous(parent, tag, valeur):
        if valeur not in (None, ''):
            etree.SubElement(parent, tag).text = str(valeur)

    for a in annonces:
        n = etree.SubElement(client, 'annonce')
        cle = hashlib.sha1(a['url'].encode()).hexdigest()[:10].upper()
        sous(n, 'reference', f'{reference_agence}-W-{cle}')
        sous(n, 'titre', (a.get('titre') or '')[:200])
        sous(n, 'texte', a.get('texte'))
        bien = etree.SubElement(n, 'bien')
        sous(bien, 'libelle_type', a.get('libelle_type'))
        sous(bien, 'code_postal', a.get('cp'))
        sous(bien, 'ville', a.get('ville'))
        sous(bien, 'surface', a.get('surface'))
        sous(bien, 'nb_pieces_logement', a.get('pieces'))
        prest = etree.SubElement(n, 'prestation')
        sous(prest, 'type', a['transaction'])
        sous(prest, 'prix', int(a['prix']))
        if a['transaction'] == 'L':
            sous(prest, 'loyer_mensuel', int(a['prix']))
        photos = etree.SubElement(n, 'photos')
        for i, p in enumerate(a['photos'], 1):
            etree.SubElement(photos, 'photo', ordre=str(i)).text = p
    return etree.tostring(client, xml_declaration=True, encoding='UTF-8')


def lire_site(site_url, reference_agence, journal=None):
    """Parcourt le site et retourne (xml_bytes, stats). journal(str) optionnel."""
    log = journal or (lambda m: None)
    lecteur = Lecteur(site_url)
    fiches = decouvrir_fiches(lecteur)
    log(f'  {len(fiches)} page(s) candidate(s) sur {lecteur.racine}')
    annonces = []
    for url in fiches:
        r = lecteur.get(url)
        if r is None:
            continue
        a = extraire_fiche(url, r.content)
        if a:
            annonces.append(a)
    log(f'  {len(annonces)} annonce(s) reconnue(s)')
    return vers_xml_ac3(reference_agence, annonces), {'pages': len(fiches), 'annonces': len(annonces)}
