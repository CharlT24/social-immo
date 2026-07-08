"""
Assistant de redaction d'annonce — genere des suggestions de titre et de
description a partir des caracteristiques du bien. 100% Python local.
"""

ACCROCHES_VENTE = {
    'lumineux': "Lumineux et traversant",
    'famille': "Ideal famille",
    'investisseur': "Parfait investisseur",
    'calme': "Au calme absolu",
    'centre': "En plein centre",
}


def _int(valeur):
    """Convertit en entier sans jamais lever (entrees JSON malformees).
    Retourne None si la valeur n'est pas un nombre exploitable."""
    if valeur is None or valeur == '':
        return None
    try:
        return int(float(str(valeur).replace(',', '.')))
    except (ValueError, TypeError):
        return None


def _type_lisible(type_bien, nb_pieces=None):
    t = (type_bien or '').lower()
    if 'appart' in t or t == 'appartement':
        if nb_pieces:
            return f"Appartement T{nb_pieces}"
        return "Appartement"
    if 'maison' in t or 'villa' in t:
        base = "Villa" if 'villa' in t else "Maison"
        if nb_pieces:
            return f"{base} {nb_pieces} pieces"
        return base
    if 'terrain' in t:
        return "Terrain constructible"
    if 'studio' in t:
        return "Studio"
    return (type_bien or "Bien").capitalize()


def suggerer_titres(type_bien, ville, surface=None, nb_pieces=None,
                    nb_chambres=None, surface_terrain=None, transaction='V'):
    """Retourne une liste de 3-4 titres suggerés."""
    tl = _type_lisible(type_bien, nb_pieces)
    verbe = "a louer" if transaction == 'L' else "a vendre"
    titres = []

    surf = _int(surface)
    chambres = _int(nb_chambres)
    terrain = _int(surface_terrain)

    if surf:
        titres.append(f"{tl} de {surf} m2 {verbe} a {ville}")
    titres.append(f"{tl} {verbe} - {ville}")
    if chambres and chambres >= 2:
        titres.append(f"{tl} avec {chambres} chambres a {ville}")
    if terrain and terrain > 100:
        titres.append(f"{tl} sur terrain de {terrain} m2 - {ville}")
    if surf and nb_pieces:
        titres.append(f"A {ville} : {tl.lower()} de {surf} m2")

    # Dedoublonne en gardant l'ordre
    vus, uniques = set(), []
    for t in titres:
        if t not in vus:
            vus.add(t)
            uniques.append(t)
    return uniques[:4]


def suggerer_description(type_bien, ville, surface=None, nb_pieces=None,
                         nb_chambres=None, surface_terrain=None,
                         annee_construction=None, dpe=None, transaction='V'):
    """Genere une trame de description structuree que le particulier
    peut personnaliser."""
    tl = _type_lisible(type_bien, nb_pieces).lower()
    feminin = tl.startswith(('maison', 'villa', 'propriete', 'longere', 'ferme'))
    ce = 'cette' if feminin else 'ce'
    situe = 'situee' if feminin else 'situe'
    lignes = []

    surf = _int(surface)
    terrain = _int(surface_terrain)

    intro = f"Venez decouvrir {ce} {tl} {situe} a {ville}"
    if surf:
        intro += f", offrant une surface de {surf} m2"
    intro += "."
    lignes.append(intro)

    detail = []
    if nb_pieces:
        detail.append(f"{nb_pieces} pieces")
    if nb_chambres:
        detail.append(f"{nb_chambres} chambres")
    if detail:
        pronom = 'Elle' if feminin else 'Il'
        lignes.append(f"{pronom} se compose de {' dont '.join(detail)}, "
                      "avec de beaux volumes et une distribution fonctionnelle.")

    if terrain and terrain > 0:
        lignes.append(f"Le tout sur un terrain de {terrain} m2, "
                      "parfait pour profiter de l'exterieur.")

    if annee_construction:
        lignes.append(f"Construction de {annee_construction}.")

    if dpe:
        lignes.append(f"Diagnostic de performance energetique : classe {dpe}.")

    lignes.append("Proche des commerces, ecoles et transports.")
    if transaction == 'L':
        lignes.append("Disponible rapidement — contactez-nous pour organiser une visite.")
    else:
        lignes.append("Une opportunite rare sur le secteur — contactez-nous pour une visite.")

    return "\n\n".join(lignes)
