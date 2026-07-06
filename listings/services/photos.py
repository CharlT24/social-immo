"""
Amelioration automatique des photos d'annonces — Pillow uniquement,
compatible o2switch (pas de GPU, pas de dependance lourde).

Pipeline "auto" : correction d'orientation EXIF, recadrage leger du voile
(auto-contraste), rehausse de la luminosite si la photo est sombre,
saturation et nettete douces, redimensionnement web et compression JPEG.
"""
import io

from PIL import Image, ImageEnhance, ImageOps, ImageStat

MAX_DIMENSION = 1920
JPEG_QUALITY = 85
THUMB_DIMENSION = 480
THUMB_QUALITY = 78

# Securite : bloque les "decompression bombs" (images minuscules qui
# explosent en RAM une fois decodees).
Image.MAX_IMAGE_PIXELS = 50_000_000  # ~50 Mpx


class ImageInvalide(Exception):
    """Le fichier fourni n'est pas une image exploitable."""


def valider_et_reencoder(fichier, max_dimension=MAX_DIMENSION, quality=JPEG_QUALITY):
    """SECURITE : verifie que le fichier est une vraie image, puis la
    re-encode en JPEG propre (EXIF/scripts elimines). A utiliser sur TOUT
    upload utilisateur avant stockage — on ne stocke jamais le fichier brut.

    Retourne un io.BytesIO JPEG. Leve ImageInvalide si ce n'est pas une image.
    """
    try:
        if hasattr(fichier, 'seek'):
            fichier.seek(0)
        # verify() detecte les fichiers corrompus / non-images
        Image.open(fichier).verify()
        if hasattr(fichier, 'seek'):
            fichier.seek(0)
        img = Image.open(fichier)
        img = ImageOps.exif_transpose(img)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
        sortie = io.BytesIO()
        img.save(sortie, format='JPEG', quality=quality, optimize=True, progressive=True)
        sortie.seek(0)
        return sortie
    except ImageInvalide:
        raise
    except Exception as e:
        raise ImageInvalide(str(e))


def _luminosite_moyenne(img):
    return ImageStat.Stat(img.convert('L')).mean[0]


def ameliorer_photo(fichier, max_dimension=MAX_DIMENSION):
    """Ameliore une photo (objet fichier Django ou chemin).

    Retourne un tuple (io.BytesIO pret a etre sauvegarde en JPEG,
    dict des retouches appliquees).
    """
    img = Image.open(fichier)
    retouches = []

    # 1. Orientation EXIF (photos de telephone)
    img = ImageOps.exif_transpose(img)

    # 2. Conversion RGB (gere PNG/HEIC-like avec alpha)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # 3. Auto-contraste doux : enleve le voile gris sans ecraser les tons
    img = ImageOps.autocontrast(img, cutoff=1)
    retouches.append('contraste')

    # 4. Luminosite : on remonte les photos sombres (interieurs)
    lum = _luminosite_moyenne(img)
    if lum < 100:
        facteur = min(1.35, 118.0 / max(lum, 1))
        img = ImageEnhance.Brightness(img).enhance(facteur)
        retouches.append('luminosite')

    # 5. Saturation et nettete legeres (rendu "annonce pro")
    img = ImageEnhance.Color(img).enhance(1.08)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    retouches.append('couleurs')

    # 6. Redimensionnement web
    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
        retouches.append('redimensionnement')

    sortie = io.BytesIO()
    img.save(sortie, format='JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
    sortie.seek(0)
    return sortie, {'retouches': retouches, 'largeur': img.size[0], 'hauteur': img.size[1]}


def generer_miniature(fichier, max_dimension=THUMB_DIMENSION):
    """Genere une miniature JPEG (grilles/listes) depuis un fichier image.

    Retourne un io.BytesIO pret a etre sauvegarde.
    """
    if hasattr(fichier, 'seek'):
        fichier.seek(0)
    img = Image.open(fichier)
    img = ImageOps.exif_transpose(img)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
    sortie = io.BytesIO()
    img.save(sortie, format='JPEG', quality=THUMB_QUALITY, optimize=True, progressive=True)
    sortie.seek(0)
    return sortie
