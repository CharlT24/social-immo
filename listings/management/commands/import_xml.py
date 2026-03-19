import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from lxml import etree
from decimal import Decimal

from listings.models import Annonce, Photo


# URL par defaut du flux XML
DEFAULT_FEED_URL = 'https://logiciel-immo-clean.vercel.app/api/export/socialimmo/'


class Command(BaseCommand):
    help = 'Importe les annonces depuis le flux XML (HTTP ou fichier local)'

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
            help='URL complete du flux XML (prioritaire sur --agence-id)'
        )
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='Chemin vers un fichier XML local (fallback)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simuler l\'import sans modifier la base'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Determiner la source du XML
        xml_content = self._get_xml_content(options)
        if xml_content is None:
            return

        # Parser le XML
        try:
            root = etree.fromstring(xml_content)
        except etree.XMLSyntaxError as e:
            self.stderr.write(self.style.ERROR(f'Erreur de parsing XML: {e}'))
            return

        # Compteurs
        created = 0
        updated = 0
        errors = 0
        references_recues = set()

        # La racine est <client reference="...">
        # Les annonces sont directement sous <client>
        client_ref = root.get('reference', '')
        if root.tag == 'client':
            annonces_xml = root.findall('annonce')
        else:
            # Fallback : chercher dans l'arbre
            annonces_xml = root.findall('.//annonce')
            client_node = root.find('.//client')
            if client_node is not None:
                client_ref = client_node.get('reference', '')

        self.stdout.write(f'Client: {client_ref} - {len(annonces_xml)} annonce(s) trouvee(s)')

        for annonce_xml in annonces_xml:
            try:
                ref, result = self.process_annonce(annonce_xml, client_ref, dry_run)
                references_recues.add(ref)
                if result == 'created':
                    created += 1
                elif result == 'updated':
                    updated += 1
            except Exception as e:
                errors += 1
                ref = self.get_text(annonce_xml, 'reference', 'INCONNU')
                self.stderr.write(self.style.ERROR(f'Erreur annonce {ref}: {e}'))

        # Annule et remplace : desactiver les biens absents du flux
        deleted = 0
        if not dry_run and references_recues:
            # Trouver les annonces actives de ce client qui ne sont plus dans le flux
            annonces_a_supprimer = Annonce.objects.filter(
                client_reference=client_ref,
                is_active=True
            ).exclude(reference__in=references_recues)

            deleted = annonces_a_supprimer.count()
            if deleted > 0:
                # Log avant la mise a jour (le queryset sera consomme)
                refs_supprimees = list(annonces_a_supprimer.values_list('reference', flat=True))
                annonces_a_supprimer.update(is_active=False)
                for ref in refs_supprimees:
                    self.stdout.write(self.style.WARNING(f'  [DESACTIVE] {ref}'))

        # Resume
        prefix = '[DRY-RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n{prefix}Import termine: {created} creees, {updated} mises a jour, '
            f'{deleted} desactivees, {errors} erreurs'
        ))

    def _get_xml_content(self, options):
        """Recupere le contenu XML depuis URL ou fichier"""

        # Option 1 : URL complete
        if options['url']:
            return self._fetch_url(options['url'])

        # Option 2 : agence-id -> construire l'URL
        agence_id = options['agence_id'] or getattr(settings, 'SOCIALIMMO_AGENCE_ID', None)
        if agence_id:
            base_url = getattr(settings, 'SOCIALIMMO_FEED_URL', DEFAULT_FEED_URL)
            url = f'{base_url.rstrip("/")}/{agence_id}'
            return self._fetch_url(url)

        # Option 3 : fichier local
        file_path = options['file']
        if file_path:
            from pathlib import Path
            path = Path(file_path)
            if not path.exists():
                self.stderr.write(self.style.ERROR(f'Fichier non trouve: {file_path}'))
                return None
            self.stdout.write(f'Lecture du fichier: {file_path}')
            return path.read_bytes()

        # Rien de specifie
        self.stderr.write(self.style.ERROR(
            'Specifie --agence-id, --url, ou --file. '
            'Ou definir SOCIALIMMO_AGENCE_ID dans settings.py'
        ))
        return None

    def _fetch_url(self, url):
        """Telecharge le XML depuis une URL"""
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

    def get_text(self, element, tag, default=''):
        """Recupere le texte d'un sous-element de maniere securisee"""
        child = element.find(f'.//{tag}')
        if child is not None and child.text:
            return child.text.strip()
        return default

    def get_int(self, element, tag, default=None):
        """Recupere un entier d'un sous-element"""
        text = self.get_text(element, tag)
        if text:
            try:
                return int(text)
            except ValueError:
                return default
        return default

    def get_decimal(self, element, tag, default=None):
        """Recupere un decimal d'un sous-element"""
        text = self.get_text(element, tag)
        if text:
            try:
                return Decimal(text.replace(',', '.').replace(' ', ''))
            except Exception:
                return default
        return default

    def process_annonce(self, annonce_xml, client_ref, dry_run=False):
        """Traite une annonce XML et la cree/met a jour en base"""

        reference = self.get_text(annonce_xml, 'reference')
        if not reference:
            raise ValueError('Reference manquante')

        # Recuperer les sous-elements
        bien = annonce_xml.find('.//bien')
        diagnostiques = annonce_xml.find('.//diagnostiques')
        prestation = annonce_xml.find('.//prestation')

        # Donnees de base
        data = {
            'client_reference': client_ref,
            'titre': self.get_text(annonce_xml, 'titre'),
            'texte': self.get_text(annonce_xml, 'texte'),
            'code_type': self.get_text(annonce_xml, 'code_type'),
            'contact_nom': self.get_text(annonce_xml, 'contact_a_afficher'),
            'contact_email': self.get_text(annonce_xml, 'email_a_afficher'),
            'contact_telephone': self.get_text(annonce_xml, 'telephone_a_afficher'),
            'is_active': True,  # Reactiver si le bien revient dans le flux
        }

        # Donnees du bien
        if bien is not None:
            data.update({
                'libelle_type': self.get_text(bien, 'libelle_type'),
                'code_postal': self.get_text(bien, 'code_postal', ''),
                'ville': self.get_text(bien, 'ville', ''),
                'nb_pieces': self.get_int(bien, 'nb_pieces_logement'),
                'nb_chambres': self.get_int(bien, 'nombre_de_chambres'),
                'surface': self.get_decimal(bien, 'surface'),
                'surface_sejour': self.get_decimal(bien, 'surface_sejour'),
                'surface_terrain': self.get_decimal(bien, 'surface_terrain'),
                'annee_construction': self.get_int(bien, 'annee_construction'),
            })

        # Diagnostiques (DPE 2021+)
        if diagnostiques is not None:
            data.update({
                'dpe_etiquette_conso': self.get_text(diagnostiques, 'dpe_etiquette_conso'),
                'dpe_valeur_conso': self.get_int(diagnostiques, 'dpe_valeur_conso'),
                'dpe_etiquette_ges': self.get_text(diagnostiques, 'dpe_etiquette_ges'),
                'dpe_valeur_ges': self.get_int(diagnostiques, 'dpe_valeur_ges'),
                'dpe_date_realisation': self.get_text(diagnostiques, 'dpe_date_realisation'),
                'montant_depenses_energies_min': self.get_decimal(diagnostiques, 'montant_depenses_energies_min'),
                'montant_depenses_energies_max': self.get_decimal(diagnostiques, 'montant_depenses_energies_max'),
            })

        # Prestation (prix)
        if prestation is not None:
            type_trans = self.get_text(prestation, 'type', 'V')
            valid_types = ['V', 'L', 'S', 'F', 'B', 'W', 'G']
            data.update({
                'type_transaction': type_trans if type_trans in valid_types else 'V',
                'prix': self.get_decimal(prestation, 'prix', Decimal('0')),
                'frais_agence': self.get_decimal(prestation, 'frais_agence'),
                'honoraires_payeurs': self.get_text(prestation, 'honoraires_payeurs'),
                # Champs location
                'loyer_mensuel': self.get_decimal(prestation, 'loyer_mensuel'),
                'charges_locatives': self.get_decimal(prestation, 'charges_locatives'),
                'depot_garantie': self.get_decimal(prestation, 'depot_garantie'),
                'honoraires_location': self.get_decimal(prestation, 'honoraires_location'),
            })

        if dry_run:
            action = 'would_create' if not Annonce.objects.filter(reference=reference).exists() else 'would_update'
            self.stdout.write(f'  [{action.upper()}] {reference} - {data.get("titre", "")[:40]}')
            return reference, action

        # Creer ou mettre a jour l'annonce
        annonce, created = Annonce.objects.update_or_create(
            reference=reference,
            defaults=data
        )

        # Gerer les photos
        photos_xml = annonce_xml.find('.//photos')
        if photos_xml is not None:
            annonce.photos.all().delete()
            for photo_xml in photos_xml.findall('photo'):
                url = photo_xml.text
                if url:
                    ordre = int(photo_xml.get('ordre', 1))
                    Photo.objects.create(
                        annonce=annonce,
                        url=url.strip(),
                        ordre=ordre
                    )

        action = 'created' if created else 'updated'
        self.stdout.write(f'  [{action.upper()}] {reference} - {data.get("titre", "")[:40]}')

        return reference, action
