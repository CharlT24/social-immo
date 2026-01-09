from django.core.management.base import BaseCommand
from lxml import etree
from decimal import Decimal
from pathlib import Path

from listings.models import Annonce, Photo


class Command(BaseCommand):
    help = 'Importe les annonces depuis un fichier XML (format Ubiflow/LeBonCoin)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='export.xml',
            help='Chemin vers le fichier XML (défaut: export.xml)'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f'Fichier non trouvé: {file_path}'))
            return

        self.stdout.write(f'Lecture du fichier: {file_path}')

        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()
        except etree.XMLSyntaxError as e:
            self.stderr.write(self.style.ERROR(f'Erreur de parsing XML: {e}'))
            return

        # Compteurs
        created = 0
        updated = 0
        errors = 0

        # Parcourir les clients
        for client in root.findall('.//client'):
            client_ref = client.get('reference', '')

            # Parcourir les annonces de ce client
            for annonce_xml in client.findall('.//annonce'):
                try:
                    result = self.process_annonce(annonce_xml, client_ref)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                except Exception as e:
                    errors += 1
                    ref = self.get_text(annonce_xml, 'reference', 'INCONNU')
                    self.stderr.write(self.style.ERROR(f'Erreur annonce {ref}: {e}'))

        # Résumé
        self.stdout.write(self.style.SUCCESS(
            f'\nImport terminé: {created} créées, {updated} mises à jour, {errors} erreurs'
        ))

    def get_text(self, element, tag, default=''):
        """Récupère le texte d'un sous-élément de manière sécurisée"""
        child = element.find(f'.//{tag}')
        if child is not None and child.text:
            return child.text.strip()
        return default

    def get_int(self, element, tag, default=None):
        """Récupère un entier d'un sous-élément"""
        text = self.get_text(element, tag)
        if text:
            try:
                return int(text)
            except ValueError:
                return default
        return default

    def get_decimal(self, element, tag, default=None):
        """Récupère un décimal d'un sous-élément"""
        text = self.get_text(element, tag)
        if text:
            try:
                return Decimal(text.replace(',', '.').replace(' ', ''))
            except Exception:
                return default
        return default

    def process_annonce(self, annonce_xml, client_ref):
        """Traite une annonce XML et la crée/met à jour en base"""

        reference = self.get_text(annonce_xml, 'reference')
        if not reference:
            raise ValueError('Référence manquante')

        # Récupérer les sous-éléments
        bien = annonce_xml.find('.//bien')
        diagnostiques = annonce_xml.find('.//diagnostiques')
        prestation = annonce_xml.find('.//prestation')

        # Préparer les données
        data = {
            'client_reference': client_ref,
            'titre': self.get_text(annonce_xml, 'titre'),
            'texte': self.get_text(annonce_xml, 'texte'),
            'code_type': self.get_text(annonce_xml, 'code_type'),
            'contact_nom': self.get_text(annonce_xml, 'contact_a_afficher'),
            'contact_email': self.get_text(annonce_xml, 'email_a_afficher'),
            'contact_telephone': self.get_text(annonce_xml, 'telephone_a_afficher'),
        }

        # Données du bien
        if bien is not None:
            data.update({
                'code_postal': self.get_text(bien, 'code_postal', ''),
                'ville': self.get_text(bien, 'ville', ''),
                'nb_pieces': self.get_int(bien, 'nb_pieces_logement'),
                'nb_chambres': self.get_int(bien, 'nombre_de_chambres'),
                'surface': self.get_decimal(bien, 'surface'),
                'annee_construction': self.get_int(bien, 'annee_construction'),
            })

        # Diagnostiques
        if diagnostiques is not None:
            data.update({
                'dpe_etiquette_conso': self.get_text(diagnostiques, 'dpe_etiquette_conso'),
                'dpe_valeur_conso': self.get_int(diagnostiques, 'dpe_valeur_conso'),
                'dpe_etiquette_ges': self.get_text(diagnostiques, 'dpe_etiquette_ges'),
            })

        # Prestation (prix)
        if prestation is not None:
            type_trans = self.get_text(prestation, 'type', 'V')
            data.update({
                'type_transaction': type_trans if type_trans in ['V', 'L'] else 'V',
                'prix': self.get_decimal(prestation, 'prix', Decimal('0')),
                'honoraires_payeurs': self.get_text(prestation, 'honoraires_payeurs'),
            })

        # Créer ou mettre à jour l'annonce
        annonce, created = Annonce.objects.update_or_create(
            reference=reference,
            defaults=data
        )

        # Gérer les photos
        photos_xml = annonce_xml.find('.//photos')
        if photos_xml is not None:
            # Supprimer les anciennes photos
            annonce.photos.all().delete()

            # Créer les nouvelles
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

        return action
