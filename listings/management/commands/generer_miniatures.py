"""
Genere les miniatures manquantes pour les photos uploadees
(Photo.image et ProRealisationPhoto.image).

Usage : python manage.py generer_miniatures
"""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from listings.models import Photo, ProRealisationPhoto
from listings.services.photos import generer_miniature


class Command(BaseCommand):
    help = "Genere les miniatures manquantes des images uploadees"

    def handle(self, *args, **options):
        ok, erreurs = 0, 0
        for model in (Photo, ProRealisationPhoto):
            qs = model.objects.exclude(image='').filter(image_thumb='')
            for photo in qs:
                try:
                    thumb = generer_miniature(photo.image.file)
                    nom = photo.image.name.rsplit('/', 1)[-1].rsplit('.', 1)[0] + '_thumb.jpg'
                    photo.image_thumb.save(nom, ContentFile(thumb.read()), save=True)
                    ok += 1
                except Exception as e:
                    erreurs += 1
                    self.stderr.write(f"{model.__name__} #{photo.id}: {e}")
        self.stdout.write(self.style.SUCCESS(f"{ok} miniature(s) generee(s), {erreurs} erreur(s)"))
