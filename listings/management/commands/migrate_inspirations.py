"""Migre les anciennes inspirations Annonce vers Photo.
Si une Annonce a is_inspiration=True, on copie le flag sur sa premiere photo.
"""
from django.core.management.base import BaseCommand
from listings.models import Annonce, Photo


class Command(BaseCommand):
    help = 'Migre is_inspiration de Annonce vers Photo (premiere photo du bien)'

    def handle(self, *args, **options):
        annonces = Annonce.objects.filter(is_inspiration=True)
        count = 0
        for annonce in annonces:
            photo = annonce.photos.first()
            if photo and not photo.is_inspiration:
                photo.is_inspiration = True
                photo.inspiration_categorie = annonce.inspiration_categorie
                photo.save(update_fields=['is_inspiration', 'inspiration_categorie'])
                count += 1
                self.stdout.write(f'  {annonce.reference} -> photo #{photo.id}')

        self.stdout.write(self.style.SUCCESS(f'{count} inspiration(s) migree(s) de Annonce vers Photo'))
