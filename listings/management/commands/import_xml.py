import csv
import io
import ftplib
import zipfile
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from lxml import etree
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Count
from listings.models import Annonce, Photo, Agence, Conseiller


# URL par defaut du flux XML
DEFAULT_FEED_URL = 'https://logiciel-immo-clean.vercel.app/api/export/socialimmo/'


class Command(BaseCommand):
    help = 'Importe les annonces depuis un flux XML (AC3) ou CSV (Poliris), via HTTP, FTP ou fichier local'

    def add_arguments(self, parser):
        parser.add_argument(
            '--agence-id',
            type=str,
            default=None,
            help='ID de l\'agence pour le flux HTTP (ex: OI123)'
        )
        parser.add_argument(
            '--url',
            type=str,
            default=None,
            help='URL complete du flux XML/CSV (prioritaire sur --agence-id)'
        )
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='Chemin vers un fichier XML/CSV local (fallback)'
        )
        parser.add_argument(
            '--format',
            type=str,
            default=None,
            choices=['ac3', 'poliris'],
            help='Format du flux (ac3=XML, poliris=CSV). Auto-detecte si non specifie.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simuler l\'import sans modifier la base'
        )
        parser.add_argument(
            '--all-agences',
            action='store_true',
            help='Importer pour toutes les agences actives'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Mode multi-agences
        if options['all_agences']:
            agences = Agence.objects.filter(is_active=True).exclude(feed_url='')
            if not agences.exists():
                self.stderr.write(self.style.ERROR('Aucune agence active avec un flux configure'))
                return
            for agence in agences:
                self.stdout.write(self.style.MIGRATE_HEADING(
                    f'\n=== Import: {agence.nom} ({agence.reference}) ==='
                ))
                self._import_agence(agence, dry_run)
            return

        # Mode single
        # Si --agence-id, chercher l'agence en BDD pour ses parametres
        agence_id = options['agence_id'] or getattr(settings, 'SOCIALIMMO_AGENCE_ID', None)
        agence = None
        if agence_id:
            try:
                agence = Agence.objects.get(reference=agence_id)
            except Agence.DoesNotExist:
                pass

        feed_format = options['format']

        # Recuperer le contenu
        content = self._get_content(options, agence)
        if content is None:
            return

        # Detecter le format
        if not feed_format:
            if agence and agence.feed_format:
                feed_format = agence.feed_format
            else:
                feed_format = self._detect_format(content)

        client_ref = agence.reference if agence else (agence_id or '')

        self.stdout.write(f'Format detecte: {feed_format.upper()}')

        if feed_format == 'poliris':
            self._import_poliris(content, client_ref, dry_run)
        else:
            self._import_ac3(content, client_ref, dry_run)

    def _import_agence(self, agence, dry_run):
        """Import pour une agence specifique (utilise ses parametres)"""
        content = None

        if agence.feed_type == 'ftp' and agence.ftp_host:
            content = self._fetch_ftp(agence)
        elif agence.feed_url:
            content = self._fetch_url(agence.feed_url)
        else:
            self.stderr.write(self.style.ERROR(f'  Pas de source configuree pour {agence.nom}'))
            return

        if content is None:
            return

        feed_format = agence.feed_format or self._detect_format(content)

        if feed_format == 'poliris':
            self._import_poliris(content, agence.reference, dry_run)
        else:
            self._import_ac3(content, agence.reference, dry_run)

    def _detect_format(self, content):
        """Auto-detecte le format du flux"""
        # Si ca commence par <?xml ou <, c'est du XML
        stripped = content.lstrip()
        if stripped[:1] == b'<' or stripped[:5] == b'<?xml':
            return 'ac3'
        # Si c'est un ZIP (Poliris envoie souvent un ZIP)
        if stripped[:2] == b'PK':
            return 'poliris'
        # Sinon, probablement CSV
        return 'poliris'

    def _get_content(self, options, agence=None):
        """Recupere le contenu depuis URL, FTP ou fichier"""

        # Option 1 : URL complete
        if options['url']:
            return self._fetch_url(options['url'])

        # Option 2 : agence avec FTP
        if agence and agence.feed_type == 'ftp' and agence.ftp_host:
            return self._fetch_ftp(agence)

        # Option 3 : agence-id -> construire l'URL ou utiliser feed_url
        if agence and agence.feed_url:
            return self._fetch_url(agence.feed_url)

        agence_id = options.get('agence_id') or getattr(settings, 'SOCIALIMMO_AGENCE_ID', None)
        if agence_id and not agence:
            base_url = getattr(settings, 'SOCIALIMMO_FEED_URL', DEFAULT_FEED_URL)
            url = f'{base_url.rstrip("/")}/{agence_id}'
            return self._fetch_url(url)

        # Option 4 : fichier local
        file_path = options['file']
        if file_path:
            from pathlib import Path
            path = Path(file_path)
            if not path.exists():
                self.stderr.write(self.style.ERROR(f'Fichier non trouve: {file_path}'))
                return None
            self.stdout.write(f'Lecture du fichier: {file_path}')
            return path.read_bytes()

        self.stderr.write(self.style.ERROR(
            'Specifie --agence-id, --url, ou --file. '
            'Ou definir SOCIALIMMO_AGENCE_ID dans settings.py'
        ))
        return None

    def _fetch_url(self, url):
        """Telecharge depuis une URL"""
        self.stdout.write(f'Telechargement: {url}')
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            self.stdout.write(self.style.SUCCESS(
                f'  OK - {len(response.content)} octets recus'
            ))
            return response.content
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Erreur HTTP: {e}'))
            return None

    def _fetch_ftp(self, agence):
        """Telecharge depuis un serveur FTP"""
        self.stdout.write(f'Connexion FTP: {agence.ftp_host}')
        try:
            ftp = ftplib.FTP(agence.ftp_host, timeout=30)
            ftp.login(agence.ftp_user, agence.ftp_password)
            ftp.cwd(agence.ftp_path or '/')

            # Chercher le fichier le plus recent (XML, CSV, ou ZIP)
            files = []
            ftp.retrlines('LIST', lambda line: files.append(line))

            target = None
            for line in files:
                parts = line.split()
                if not parts:
                    continue
                fname = parts[-1]
                if fname.lower().endswith(('.xml', '.csv', '.zip')):
                    target = fname

            if not target:
                self.stderr.write(self.style.ERROR(
                    f'  Aucun fichier XML/CSV/ZIP trouve dans {agence.ftp_path}'
                ))
                ftp.quit()
                return None

            self.stdout.write(f'  Fichier FTP: {target}')
            buffer = io.BytesIO()
            ftp.retrbinary(f'RETR {target}', buffer.write)
            ftp.quit()

            content = buffer.getvalue()
            self.stdout.write(self.style.SUCCESS(
                f'  OK - {len(content)} octets recus via FTP'
            ))

            # Si ZIP, extraire le premier fichier CSV/XML
            if target.lower().endswith('.zip'):
                content = self._extract_zip(content)

            return content
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erreur FTP: {e}'))
            return None

    def _extract_zip(self, content):
        """Extrait le premier CSV ou XML d'un ZIP"""
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    if name.lower().endswith(('.csv', '.xml')):
                        self.stdout.write(f'  ZIP -> {name}')
                        return zf.read(name)
                # Si pas de CSV/XML, prendre le premier fichier
                if zf.namelist():
                    name = zf.namelist()[0]
                    self.stdout.write(f'  ZIP -> {name}')
                    return zf.read(name)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erreur ZIP: {e}'))
        return content

    # ==================== IMPORT AC3 (XML) ====================

    def _import_ac3(self, content, client_ref, dry_run):
        """Import au format AC3/Ubiflow XML"""
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as e:
            self.stderr.write(self.style.ERROR(f'Erreur de parsing XML: {e}'))
            return

        created = updated = unchanged = errors = 0
        references_recues = set()

        # La racine est <client reference="...">
        xml_client_ref = root.get('reference', '')
        if xml_client_ref:
            client_ref = xml_client_ref

        if root.tag == 'client':
            annonces_xml = root.findall('annonce')
        else:
            annonces_xml = root.findall('.//annonce')
            client_node = root.find('.//client')
            if client_node is not None:
                client_ref = client_node.get('reference', client_ref)

        self.stdout.write(f'Client: {client_ref} - {len(annonces_xml)} annonce(s) trouvee(s)')

        for annonce_xml in annonces_xml:
            try:
                ref, result = self._process_ac3_annonce(annonce_xml, client_ref, dry_run)
                references_recues.add(ref)
                if result == 'created':
                    created += 1
                elif result == 'updated':
                    updated += 1
                elif result == 'unchanged':
                    unchanged += 1
            except Exception as e:
                errors += 1
                ref = self._get_text(annonce_xml, 'reference', 'INCONNU')
                self.stderr.write(self.style.ERROR(f'Erreur annonce {ref}: {e}'))

        deleted = self._deactivate_missing(client_ref, references_recues, dry_run)
        self._auto_set_departement(client_ref, dry_run)
        self._print_summary(created, updated, unchanged, deleted, errors, dry_run)

    # ==================== IMPORT POLIRIS (CSV) ====================

    def _import_poliris(self, content, client_ref, dry_run):
        """Import au format Poliris CSV"""
        # Decoder le contenu (souvent ISO-8859-1 ou UTF-8)
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('iso-8859-1')

        # Detecter le separateur (Poliris utilise ; ou |)
        first_line = text.split('\n')[0]
        if '|' in first_line:
            delimiter = '|'
        elif ';' in first_line:
            delimiter = ';'
        elif '\t' in first_line:
            delimiter = '\t'
        else:
            delimiter = ','

        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

        # Normaliser les noms de colonnes (majuscules, sans espaces)
        if reader.fieldnames:
            reader.fieldnames = [f.strip().upper().replace(' ', '_') for f in reader.fieldnames]

        created = updated = unchanged = errors = 0
        references_recues = set()

        rows = list(reader)
        self.stdout.write(f'Client: {client_ref} - {len(rows)} annonce(s) trouvee(s) (Poliris CSV)')

        for row in rows:
            try:
                ref, result = self._process_poliris_row(row, client_ref, dry_run)
                if ref:
                    references_recues.add(ref)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                    elif result == 'unchanged':
                        unchanged += 1
            except Exception as e:
                errors += 1
                ref = self._csv_get(row, ['REFERENCE', 'REF', 'ID', 'NUMERO'], 'INCONNU')
                self.stderr.write(self.style.ERROR(f'Erreur annonce {ref}: {e}'))

        deleted = self._deactivate_missing(client_ref, references_recues, dry_run)
        self._auto_set_departement(client_ref, dry_run)
        self._print_summary(created, updated, unchanged, deleted, errors, dry_run)

    def _csv_get(self, row, keys, default=''):
        """Cherche une valeur dans le CSV en testant plusieurs noms de colonnes"""
        for key in keys:
            val = row.get(key, '').strip()
            if val:
                return val
        return default

    def _csv_int(self, row, keys, default=None):
        """Recupere un entier depuis le CSV"""
        val = self._csv_get(row, keys)
        if val:
            try:
                return int(float(val))
            except (ValueError, TypeError):
                pass
        return default

    def _csv_decimal(self, row, keys, default=None):
        """Recupere un decimal depuis le CSV"""
        val = self._csv_get(row, keys)
        if val:
            try:
                return Decimal(val.replace(',', '.').replace(' ', ''))
            except Exception:
                pass
        return default

    def _process_poliris_row(self, row, client_ref, dry_run):
        """Traite une ligne CSV Poliris"""
        reference = self._csv_get(row, [
            'REFERENCE', 'REF', 'REFERENCE_ANNONCE', 'ID_ANNONCE', 'NUMERO'
        ])
        if not reference:
            return None, 'skipped'

        # Prefixer la reference avec l'agence pour eviter les collisions
        full_ref = f'{client_ref}-{reference}'

        # Type de transaction
        type_trans = self._csv_get(row, [
            'TYPE_TRANSACTION', 'TRANSACTION', 'TYPE_MANDAT', 'NATURE_TRANSACTION'
        ]).upper()
        type_map = {
            'VENTE': 'V', 'V': 'V', 'LOCATION': 'L', 'L': 'L',
            'SAISONNIER': 'S', 'S': 'S', 'VIAGER': 'W', 'W': 'W',
            'FONDS DE COMMERCE': 'F', 'F': 'F', 'BAIL': 'B', 'B': 'B',
            'NEUF': 'G', 'G': 'G',
        }
        type_trans = type_map.get(type_trans, 'V')

        # Titre
        titre = self._csv_get(row, ['TITRE', 'LIBELLE', 'DESIGNATION'])
        if not titre:
            lib_type = self._csv_get(row, [
                'TYPE_BIEN', 'LIBELLE_TYPE', 'NATURE', 'CATEGORIE'
            ])
            ville = self._csv_get(row, ['VILLE', 'COMMUNE', 'LOCALITE'])
            titre = f'{lib_type} {ville}'.strip() or f'Bien {reference}'

        data = {
            'client_reference': client_ref,
            'titre': titre,
            'texte': self._csv_get(row, [
                'DESCRIPTIF', 'DESCRIPTION', 'TEXTE', 'COMMENTAIRE',
                'DESCRIPTIF_FR', 'TEXTE_FR'
            ]),
            'code_type': self._csv_get(row, [
                'CODE_TYPE', 'TYPE_BIEN_CODE', 'CODE_NATURE'
            ]),
            'libelle_type': self._csv_get(row, [
                'TYPE_BIEN', 'LIBELLE_TYPE', 'NATURE', 'CATEGORIE'
            ]),
            'contact_nom': self._csv_get(row, [
                'CONTACT_NOM', 'NEGOCIATEUR', 'COMMERCIAL', 'AGENT'
            ]),
            'contact_email': self._csv_get(row, [
                'CONTACT_EMAIL', 'EMAIL_NEGOCIATEUR', 'EMAIL_CONTACT', 'EMAIL'
            ]),
            'contact_telephone': self._csv_get(row, [
                'CONTACT_TEL', 'TEL_NEGOCIATEUR', 'TELEPHONE_CONTACT', 'TELEPHONE'
            ]),
            'code_postal': self._csv_get(row, [
                'CODE_POSTAL', 'CP', 'ZIP'
            ]),
            'ville': self._csv_get(row, [
                'VILLE', 'COMMUNE', 'LOCALITE'
            ]),
            'nb_pieces': self._csv_int(row, [
                'NB_PIECES', 'PIECES', 'NOMBRE_PIECES', 'NB_PIECES_LOGEMENT'
            ]),
            'nb_chambres': self._csv_int(row, [
                'NB_CHAMBRES', 'CHAMBRES', 'NOMBRE_CHAMBRES'
            ]),
            'surface': self._csv_decimal(row, [
                'SURFACE', 'SURFACE_HABITABLE', 'SURFACE_CARREZ', 'SURFACE_LOGEMENT'
            ]),
            'surface_terrain': self._csv_decimal(row, [
                'SURFACE_TERRAIN', 'TERRAIN'
            ]),
            'surface_sejour': self._csv_decimal(row, [
                'SURFACE_SEJOUR'
            ]),
            'annee_construction': self._csv_int(row, [
                'ANNEE_CONSTRUCTION', 'ANNEE'
            ]),
            'type_transaction': type_trans,
            'prix': self._csv_decimal(row, [
                'PRIX', 'PRIX_VENTE', 'PRIX_PUBLIC', 'MONTANT'
            ], Decimal('0')),
            'frais_agence': self._csv_decimal(row, [
                'HONORAIRES', 'FRAIS_AGENCE', 'COMMISSION'
            ]),
            'honoraires_payeurs': self._csv_get(row, [
                'HONORAIRES_PAYEURS', 'CHARGE_HONORAIRES'
            ]),
            'loyer_mensuel': self._csv_decimal(row, [
                'LOYER', 'LOYER_MENSUEL', 'LOYER_CC'
            ]),
            'charges_locatives': self._csv_decimal(row, [
                'CHARGES', 'CHARGES_LOCATIVES', 'CHARGES_MENSUELLES'
            ]),
            'depot_garantie': self._csv_decimal(row, [
                'DEPOT_GARANTIE', 'GARANTIE', 'CAUTION'
            ]),
            'honoraires_location': self._csv_decimal(row, [
                'HONORAIRES_LOCATION', 'FRAIS_LOCATION'
            ]),
            # DPE
            'dpe_etiquette_conso': self._csv_get(row, [
                'DPE_CONSO_LETTRE', 'DPE_ETIQUETTE_CONSO', 'ETIQUETTE_DPE',
                'DPE_ENERGIE_LETTRE', 'CLASSE_ENERGIE'
            ])[:1],
            'dpe_valeur_conso': self._csv_int(row, [
                'DPE_CONSO_VALEUR', 'DPE_VALEUR_CONSO', 'VALEUR_DPE',
                'DPE_ENERGIE_VALEUR', 'CONSO_ENERGIE'
            ]),
            'dpe_etiquette_ges': self._csv_get(row, [
                'DPE_GES_LETTRE', 'DPE_ETIQUETTE_GES', 'ETIQUETTE_GES',
                'CLASSE_GES'
            ])[:1],
            'dpe_valeur_ges': self._csv_int(row, [
                'DPE_GES_VALEUR', 'DPE_VALEUR_GES', 'VALEUR_GES',
                'EMISSION_GES'
            ]),
            'is_active': True,
        }

        # Photos (Poliris: PHOTO_1, PHOTO_2, ..., PHOTO_N ou URL_PHOTO_1, etc.)
        photos = []
        for i in range(1, 30):
            url = self._csv_get(row, [
                f'PHOTO_{i}', f'URL_PHOTO_{i}', f'IMAGE_{i}',
                f'PHOTO{i}', f'IMG_{i}'
            ])
            if url and url.startswith('http'):
                photos.append((url, i))

        if dry_run:
            action = 'would_create' if not Annonce.objects.filter(reference=full_ref).exists() else 'would_update'
            self.stdout.write(f'  [{action.upper()}] {full_ref} - {titre[:40]}')
            return full_ref, action

        # Upsert
        annonce_changed = False
        try:
            annonce = Annonce.objects.get(reference=full_ref)
            is_new = False
            for field, value in data.items():
                if getattr(annonce, field) != value:
                    setattr(annonce, field, value)
                    annonce_changed = True
            if annonce_changed:
                annonce.save()
        except Annonce.DoesNotExist:
            annonce = Annonce.objects.create(reference=full_ref, **data)
            is_new = True
            annonce_changed = True

        # Photos
        photos_changed = False
        if photos:
            existing = set(annonce.photos.values_list('url', 'ordre'))
            if existing != set(photos):
                annonce.photos.all().delete()
                Photo.objects.bulk_create([
                    Photo(annonce=annonce, url=url, ordre=ordre)
                    for url, ordre in photos
                ])
                photos_changed = True

        # Conseiller
        self._attach_conseiller(annonce, data, client_ref)

        if is_new:
            action = 'created'
        elif annonce_changed or photos_changed:
            action = 'updated'
        else:
            action = 'unchanged'

        label = {'created': 'CREE', 'updated': 'MAJ', 'unchanged': 'INCHANGE'}[action]
        self.stdout.write(f'  [{label}] {full_ref} - {titre[:40]}')
        return full_ref, action

    # ==================== SHARED UTILITIES ====================

    def _get_text(self, element, tag, default=''):
        child = element.find(f'.//{tag}')
        if child is not None and child.text:
            return child.text.strip()
        return default

    def _get_int(self, element, tag, default=None):
        text = self._get_text(element, tag)
        if text:
            try:
                return int(text)
            except ValueError:
                return default
        return default

    def _get_decimal(self, element, tag, default=None):
        text = self._get_text(element, tag)
        if text:
            try:
                return Decimal(text.replace(',', '.').replace(' ', ''))
            except Exception:
                return default
        return default

    def _process_ac3_annonce(self, annonce_xml, client_ref, dry_run=False):
        """Traite une annonce XML AC3"""
        reference = self._get_text(annonce_xml, 'reference')
        if not reference:
            raise ValueError('Reference manquante')

        bien = annonce_xml.find('.//bien')
        diagnostiques = annonce_xml.find('.//diagnostiques')
        prestation = annonce_xml.find('.//prestation')

        data = {
            'client_reference': client_ref,
            'titre': self._get_text(annonce_xml, 'titre'),
            'texte': self._get_text(annonce_xml, 'texte'),
            'code_type': self._get_text(annonce_xml, 'code_type'),
            'contact_nom': self._get_text(annonce_xml, 'contact_a_afficher'),
            'contact_email': self._get_text(annonce_xml, 'email_a_afficher'),
            'contact_telephone': self._get_text(annonce_xml, 'telephone_a_afficher'),
            'is_active': True,
        }

        if bien is not None:
            data.update({
                'libelle_type': self._get_text(bien, 'libelle_type'),
                'code_postal': self._get_text(bien, 'code_postal', ''),
                'ville': self._get_text(bien, 'ville', ''),
                'nb_pieces': self._get_int(bien, 'nb_pieces_logement'),
                'nb_chambres': self._get_int(bien, 'nombre_de_chambres'),
                'surface': self._get_decimal(bien, 'surface'),
                'surface_sejour': self._get_decimal(bien, 'surface_sejour'),
                'surface_terrain': self._get_decimal(bien, 'surface_terrain'),
                'annee_construction': self._get_int(bien, 'annee_construction'),
            })

        if diagnostiques is not None:
            data.update({
                'dpe_etiquette_conso': self._get_text(diagnostiques, 'dpe_etiquette_conso'),
                'dpe_valeur_conso': self._get_int(diagnostiques, 'dpe_valeur_conso'),
                'dpe_etiquette_ges': self._get_text(diagnostiques, 'dpe_etiquette_ges'),
                'dpe_valeur_ges': self._get_int(diagnostiques, 'dpe_valeur_ges'),
                'dpe_date_realisation': self._get_text(diagnostiques, 'dpe_date_realisation'),
                'montant_depenses_energies_min': self._get_decimal(diagnostiques, 'montant_depenses_energies_min'),
                'montant_depenses_energies_max': self._get_decimal(diagnostiques, 'montant_depenses_energies_max'),
            })

        if prestation is not None:
            type_trans = self._get_text(prestation, 'type', 'V')
            valid_types = ['V', 'L', 'S', 'F', 'B', 'W', 'G']
            if type_trans not in valid_types:
                type_trans = 'V'

            libelle = data.get('libelle_type', '').lower()
            if libelle == 'local commercial' and type_trans not in ['F', 'B']:
                type_trans = 'F'

            data.update({
                'type_transaction': type_trans,
                'prix': self._get_decimal(prestation, 'prix', Decimal('0')),
                'frais_agence': self._get_decimal(prestation, 'frais_agence'),
                'honoraires_payeurs': self._get_text(prestation, 'honoraires_payeurs'),
                'loyer_mensuel': self._get_decimal(prestation, 'loyer_mensuel'),
                'charges_locatives': self._get_decimal(prestation, 'charges_locatives'),
                'depot_garantie': self._get_decimal(prestation, 'depot_garantie'),
                'honoraires_location': self._get_decimal(prestation, 'honoraires_location'),
            })

        if dry_run:
            action = 'would_create' if not Annonce.objects.filter(reference=reference).exists() else 'would_update'
            self.stdout.write(f'  [{action.upper()}] {reference} - {data.get("titre", "")[:40]}')
            return reference, action

        annonce_changed = False
        try:
            annonce = Annonce.objects.get(reference=reference)
            is_new = False
            for field, value in data.items():
                if getattr(annonce, field) != value:
                    setattr(annonce, field, value)
                    annonce_changed = True
            if annonce_changed:
                annonce.save()
        except Annonce.DoesNotExist:
            annonce = Annonce.objects.create(reference=reference, **data)
            is_new = True
            annonce_changed = True

        # Conseiller
        self._attach_conseiller(annonce, data, client_ref)

        # Photos
        photos_changed = False
        photos_xml = annonce_xml.find('.//photos')
        if photos_xml is not None:
            new_photos = []
            for photo_xml in photos_xml.findall('photo'):
                url = (photo_xml.text or '').strip()
                if url and url.startswith('http'):
                    ordre = int(photo_xml.get('ordre', 1))
                    new_photos.append((url, ordre))

            existing = set(annonce.photos.values_list('url', 'ordre'))
            if existing != set(new_photos):
                annonce.photos.all().delete()
                Photo.objects.bulk_create([
                    Photo(annonce=annonce, url=url, ordre=ordre)
                    for url, ordre in new_photos
                ])
                photos_changed = True

        if is_new:
            action = 'created'
        elif annonce_changed or photos_changed:
            action = 'updated'
        else:
            action = 'unchanged'

        label = {'created': 'CREE', 'updated': 'MAJ', 'unchanged': 'INCHANGE'}[action]
        self.stdout.write(f'  [{label}] {reference} - {data.get("titre", "")[:40]}')
        return reference, action

    def _attach_conseiller(self, annonce, data, client_ref):
        """Rattache un conseiller a l'annonce (auto-creation)"""
        contact_email = data.get('contact_email', '').strip()
        contact_nom = data.get('contact_nom', '').strip()
        if not contact_email:
            return
        try:
            agence = Agence.objects.get(reference=client_ref)
            conseiller = Conseiller.objects.filter(
                email__iexact=contact_email, agence=agence
            ).first()
            if not conseiller:
                username = contact_email.split('@')[0].lower().replace('.', '_')
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                user = User.objects.create_user(
                    username=username,
                    email=contact_email,
                    first_name=contact_nom.split()[0] if contact_nom else '',
                    last_name=' '.join(contact_nom.split()[1:]) if contact_nom and len(contact_nom.split()) > 1 else '',
                )
                user.set_unusable_password()
                user.save()
                conseiller = Conseiller.objects.create(
                    user=user,
                    agence=agence,
                    nom=contact_nom or username,
                    email=contact_email,
                    telephone=data.get('contact_telephone', ''),
                )
                self.stdout.write(self.style.SUCCESS(
                    f'    [CONSEILLER CREE] {conseiller.nom} ({contact_email})'
                ))
            if annonce.conseiller != conseiller:
                annonce.conseiller = conseiller
                annonce.save(update_fields=['conseiller'])
        except Agence.DoesNotExist:
            pass

    def _deactivate_missing(self, client_ref, references_recues, dry_run):
        """Desactive les annonces absentes du flux"""
        if dry_run or not references_recues:
            return 0
        annonces_a_supprimer = Annonce.objects.filter(
            client_reference=client_ref,
            is_active=True
        ).exclude(reference__in=references_recues)
        deleted = annonces_a_supprimer.count()
        if deleted > 0:
            refs_supprimees = list(annonces_a_supprimer.values_list('reference', flat=True))
            annonces_a_supprimer.update(is_active=False)
            for ref in refs_supprimees:
                self.stdout.write(self.style.WARNING(f'  [DESACTIVE] {ref}'))
        return deleted

    def _auto_set_departement(self, client_ref, dry_run):
        """Auto-set departement sur l'agence"""
        if dry_run or not client_ref:
            return
        try:
            agence = Agence.objects.get(reference=client_ref)
            if not agence.departement:
                most_common = (Annonce.objects.filter(
                    client_reference=client_ref, is_active=True
                ).exclude(code_postal='')
                 .values('code_postal')
                 .annotate(n=Count('id'))
                 .order_by('-n')
                 .first())
                if most_common:
                    cp = most_common['code_postal']
                    agence.departement = cp[:2]
                    if not agence.code_postal:
                        agence.code_postal = cp
                    if not agence.ville:
                        first_a = Annonce.objects.filter(
                            code_postal=cp, client_reference=client_ref, is_active=True
                        ).first()
                        if first_a and first_a.ville:
                            agence.ville = first_a.ville
                    agence.save(update_fields=['departement', 'code_postal', 'ville'])
                    self.stdout.write(
                        f'  [AGENCE] Departement auto-defini: {agence.departement} ({agence.ville})'
                    )
        except Agence.DoesNotExist:
            pass

    def _print_summary(self, created, updated, unchanged, deleted, errors, dry_run):
        prefix = '[DRY-RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n{prefix}Import termine: {created} creees, {updated} mises a jour, '
            f'{unchanged} inchangees, {deleted} desactivees, {errors} erreurs'
        ))
