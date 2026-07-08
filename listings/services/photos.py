"""
Amelioration automatique des photos d'annonces — Pillow uniquement,
compatible o2switch (pas de GPU, pas de dependance lourde).

Pipeline "auto" : correction d'orientation EXIF, recadrage leger du voile
(auto-contraste), rehausse de la luminosite si la photo est sombre,
saturation et nettete douces, redimensionnement web et compression JPEG.
"""
import io

from PIL import Image, ImageEnhance, ImageOps, ImageStat

# Support des photos iPhone (HEIC/HEIF) : sans ceci, Pillow ne sait pas les
# lire et TOUT upload depuis un iPhone echoue silencieusement. On enregistre
# le decodeur si la lib est presente ; sinon l'app fonctionne sans (degrade).
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass

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


def valider_et_reencoder_logo(fichier, max_dimension=512):
    """SECURITE : comme valider_et_reencoder mais pour un LOGO — re-encode en
    PNG (conserve la transparence). Elimine tout contenu actif (SVG/HTML/JS
    deguise en image) en ne gardant que les pixels decodes par Pillow.

    Retourne un io.BytesIO PNG. Leve ImageInvalide si ce n'est pas une image.
    """
    try:
        if hasattr(fichier, 'seek'):
            fichier.seek(0)
        Image.open(fichier).verify()
        if hasattr(fichier, 'seek'):
            fichier.seek(0)
        img = Image.open(fichier)
        img = ImageOps.exif_transpose(img)
        # Conserve l'alpha (logos souvent transparents) ; sinon RGB.
        if img.mode not in ('RGBA', 'RGB'):
            img = img.convert('RGBA' if 'A' in img.getbands() else 'RGB')
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
        sortie = io.BytesIO()
        img.save(sortie, format='PNG', optimize=True)
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
