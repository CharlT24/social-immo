from django.core.management.base import BaseCommand
from django.utils.text import slugify
from listings.models import InspirationTag


TAGS = [
    # Style
    ('Moderne', 'style', 1),
    ('Contemporain', 'style', 2),
    ('Classique', 'style', 3),
    ('Scandinave', 'style', 4),
    ('Industriel', 'style', 5),
    ('Boheme', 'style', 6),
    ('Minimaliste', 'style', 7),
    ('Art deco', 'style', 8),
    ('Rustique', 'style', 9),
    ('Mediterraneen', 'style', 10),
    ('Japandi', 'style', 11),
    ('Vintage', 'style', 12),

    # Piece
    ('Cuisine', 'piece', 1),
    ('Salon', 'piece', 2),
    ('Chambre', 'piece', 3),
    ('Salle de bain', 'piece', 4),
    ('Bureau', 'piece', 5),
    ('Entree', 'piece', 6),
    ('Terrasse', 'piece', 7),
    ('Jardin', 'piece', 8),
    ('Dressing', 'piece', 9),
    ('Suite parentale', 'piece', 10),
    ('Veranda', 'piece', 11),
    ('Cave a vin', 'piece', 12),
    ('Piscine', 'piece', 13),

    # Couleur
    ('Blanc', 'couleur', 1),
    ('Noir', 'couleur', 2),
    ('Beige', 'couleur', 3),
    ('Gris', 'couleur', 4),
    ('Bleu', 'couleur', 5),
    ('Vert', 'couleur', 6),
    ('Terracotta', 'couleur', 7),
    ('Rose', 'couleur', 8),
    ('Dore', 'couleur', 9),

    # Materiau
    ('Bois', 'materiau', 1),
    ('Pierre', 'materiau', 2),
    ('Marbre', 'materiau', 3),
    ('Beton cire', 'materiau', 4),
    ('Metal', 'materiau', 5),
    ('Carrelage', 'materiau', 6),
    ('Parquet', 'materiau', 7),
    ('Verriere', 'materiau', 8),

    # Ambiance
    ('Cosy', 'ambiance', 1),
    ('Luxe', 'ambiance', 2),
    ('Nature', 'ambiance', 3),
    ('Chaleureux', 'ambiance', 4),
    ('Lumineux', 'ambiance', 5),
    ('Familial', 'ambiance', 6),
    ('Epure', 'ambiance', 7),
    ('Coloré', 'ambiance', 8),
    ('Zen', 'ambiance', 9),
    ('Romantique', 'ambiance', 10),
]


class Command(BaseCommand):
    help = 'Peuple les tags inspiration'

    def handle(self, *args, **options):
        created = 0
        for nom, groupe, ordre in TAGS:
            tag, is_new = InspirationTag.objects.get_or_create(
                slug=slugify(nom),
                defaults={'nom': nom, 'groupe': groupe, 'ordre': ordre}
            )
            if is_new:
                created += 1
                self.stdout.write(f'  [CREE] {nom} ({groupe})')
            else:
                tag.groupe = groupe
                tag.ordre = ordre
                tag.save(update_fields=['groupe', 'ordre'])

        self.stdout.write(self.style.SUCCESS(
            f'\n{created} tags crees, {len(TAGS)} total'
        ))
