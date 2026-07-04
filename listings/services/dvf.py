"""
Ventes reelles DVF (Demandes de Valeurs Foncieres, Etalab / data.gouv.fr).

- Resolution du code INSEE via geo.api.gouv.fr (gratuit, sans cle)
- Telechargement en streaming des CSV geo-dvf par commune, plafonne
  (compatible o2switch : pas de gros fichiers en memoire)
- Cache en base (CommuneDVF + VenteDVF), rafraichi tous les 90 jours

Colonnes CSV utilisees : id_mutation, date_mutation, nature_mutation,
valeur_fonciere, type_local, surface_reelle_bati.
"""
import csv
import io
from datetime import date, timedelta

import requests
from django.utils import timezone

GEO_API = 'https://geo.api.gouv.fr/communes'
DVF_URL = 'https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/communes/{dept}/{code_insee}.csv'

CACHE_JOURS = 90          # fraicheur du cache par commune
MAX_VENTES_STOCKEES = 500  # par commune (les plus recentes)
MAX_LIGNES_CSV = 60000     # garde-fou parsing par millesime
TIMEOUT = 12


def _code_insee(ville, code_postal):
    """Resout (ville, code_postal) -> (code_insee, nom officiel)."""
    try:
        params = {'fields': 'nom,code'}
        if code_postal:
            params['codePostal'] = code_postal
        else:
            params['nom'] = ville
        r = requests.get(GEO_API, params=params, timeout=8)
        r.raise_for_status()
        communes = r.json()
        if not communes:
            return None, None
        # Si plusieurs communes pour le CP, matcher le nom
        ville_low = (ville or '').strip().lower()
        for c in communes:
            if c['nom'].lower() == ville_low:
                return c['code'], c['nom']
        return communes[0]['code'], communes[0]['nom']
    except Exception:
        return None, None


def _iter_ventes_csv(code_insee, annee):
    """Itere les ventes utiles d'un millesime DVF, en streaming."""
    dept = code_insee[:2] if not code_insee.startswith('97') else code_insee[:3]
    url = DVF_URL.format(annee=annee, dept=dept, code_insee=code_insee)
    with requests.get(url, stream=True, timeout=TIMEOUT) as r:
        if r.status_code != 200:
            return
        lignes = (l.decode('utf-8', errors='replace') for l in r.iter_lines() if l)
        reader = csv.DictReader(lignes)
        vus = set()
        for i, row in enumerate(reader):
            if i > MAX_LIGNES_CSV:
                break
            if row.get('nature_mutation') != 'Vente':
                continue
            type_local = (row.get('type_local') or '').strip().lower()
            if type_local not in ('maison', 'appartement'):
                continue
            try:
                prix = float(row.get('valeur_fonciere') or 0)
                surface = float(row.get('surface_reelle_bati') or 0)
            except ValueError:
                continue
            if not (10000 < prix < 10_000_000 and 9 < surface < 1000):
                continue
            prix_m2 = prix / surface
            if not (200 <= prix_m2 <= 30000):
                continue  # aberrations (ventes en lot, terrains agricoles...)
            # Une mutation peut avoir plusieurs lignes (dependances, lots) :
            # on ne garde qu'une ligne bati par mutation.
            mid = row.get('id_mutation')
            if mid in vus:
                continue
            vus.add(mid)
            yield {
                'type_local': type_local,
                'surface': int(surface),
                'prix': int(prix),
                'date_mutation': row.get('date_mutation') or f'{annee}-01-01',
            }


def rafraichir_commune(ville, code_postal, autoriser_telechargement=True):
    """Retourne la CommuneDVF a jour.

    autoriser_telechargement=False (contexte web) : ne telecharge JAMAIS,
    renvoie la commune si elle est deja en cache (meme perimee), sinon None.
    Le telechargement est reserve a l'autopilot (hors requete web) et
    protege par un verrou single-flight pour eviter le thundering herd.
    """
    from django.core.cache import cache
    from listings.models import CommuneDVF, VenteDVF

    if not autoriser_telechargement:
        # Web : AUCUN appel reseau. On retrouve la commune deja connue par
        # ville + code postal (sinon None -> l'estimation retombe sur bareme).
        qs = CommuneDVF.objects.filter(nb_ventes__gt=0)
        if code_postal:
            qs = qs.filter(code_postal=code_postal)
        return qs.filter(ville__iexact=(ville or '').strip()).first()

    code_insee, nom = _code_insee(ville, code_postal)
    if not code_insee:
        return None

    commune = CommuneDVF.objects.filter(code_insee=code_insee).first()
    frais = commune and commune.derniere_maj and \
        commune.derniere_maj > timezone.now() - timedelta(days=CACHE_JOURS)
    if frais:
        return commune

    # Verrou single-flight : un seul worker telecharge une commune a la fois
    lock = f'dvf:lock:{code_insee}'
    if not cache.add(lock, 1, 180):
        return commune  # un autre process s'en charge deja

    try:
        if commune is None:
            commune, _ = CommuneDVF.objects.get_or_create(
                code_insee=code_insee,
                defaults={'ville': nom or ville, 'code_postal': code_postal or ''},
            )
        annee_max = date.today().year
        ventes = []
        for annee in range(annee_max, annee_max - 4, -1):
            try:
                ventes.extend(_iter_ventes_csv(code_insee, annee))
            except Exception:
                continue
            if len(ventes) >= 120:
                break

        if ventes:
            ventes.sort(key=lambda v: v['date_mutation'], reverse=True)
            ventes = ventes[:MAX_VENTES_STOCKEES]
            VenteDVF.objects.filter(commune=commune).delete()
            VenteDVF.objects.bulk_create([
                VenteDVF(commune=commune, **v) for v in ventes
            ])
        commune.derniere_maj = timezone.now()
        commune.nb_ventes = len(ventes)
        commune.save(update_fields=['derniere_maj', 'nb_ventes'])
        return commune
    finally:
        cache.delete(lock)


def ventes_comparables(ville, code_postal, type_bien, surface=None,
                       autoriser_telechargement=True):
    """Retourne (liste de VenteDVF comparables, nb total de ventes du type).

    Comparables = meme commune, meme type, surface a +/-30% si fournie,
    les plus recentes d'abord. En contexte web, passer
    autoriser_telechargement=False (sert uniquement le cache).
    """
    from listings.models import VenteDVF

    if type_bien not in ('maison', 'appartement'):
        return [], 0

    commune = rafraichir_commune(ville, code_postal, autoriser_telechargement)
    if not commune:
        return [], 0

    qs = VenteDVF.objects.filter(commune=commune, type_local=type_bien)
    total = qs.count()
    if surface:
        try:
            s = float(surface)
            proches = qs.filter(surface__gte=int(s * 0.7), surface__lte=int(s * 1.3))
            if proches.count() >= 3:
                qs = proches
        except (TypeError, ValueError):
            pass
    return list(qs[:60]), total
