from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User


class Annonce(models.Model):
    """Modèle principal pour une annonce immobilière"""

    # Types de transaction
    TYPE_VENTE = 'V'
    TYPE_LOCATION = 'L'
    TYPE_SAISONNIER = 'S'
    TYPE_FONDS = 'F'
    TYPE_BAIL = 'B'
    TYPE_VIAGER = 'W'
    TYPE_NEUF = 'G'
    TYPE_CHOICES = [
        (TYPE_VENTE, 'Vente'),
        (TYPE_LOCATION, 'Location'),
        (TYPE_SAISONNIER, 'Saisonnier'),
        (TYPE_FONDS, 'Fonds de commerce'),
        (TYPE_BAIL, 'Bail commercial'),
        (TYPE_VIAGER, 'Viager'),
        (TYPE_NEUF, 'Neuf (VEFA)'),
    ]

    # Références
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    client_reference = models.CharField(max_length=50, blank=True)

    # Infos principales
    titre = models.CharField(max_length=255)
    texte = models.TextField(blank=True)
    code_type = models.CharField(max_length=10, blank=True)
    libelle_type = models.CharField(max_length=100, blank=True)

    # Contact
    contact_nom = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_telephone = models.CharField(max_length=20, blank=True)

    # Localisation
    code_postal = models.CharField(max_length=10, blank=True, default='')
    ville = models.CharField(max_length=100, blank=True, default='')

    # Caractéristiques du bien
    nb_pieces = models.PositiveIntegerField(null=True, blank=True)
    nb_chambres = models.PositiveIntegerField(null=True, blank=True)
    surface = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    surface_sejour = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    surface_terrain = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    annee_construction = models.PositiveIntegerField(null=True, blank=True)

    # Diagnostics énergétiques (DPE 2021+)
    dpe_etiquette_conso = models.CharField(max_length=1, blank=True)
    dpe_valeur_conso = models.PositiveIntegerField(null=True, blank=True)
    dpe_etiquette_ges = models.CharField(max_length=1, blank=True)
    dpe_valeur_ges = models.PositiveIntegerField(null=True, blank=True)
    dpe_date_realisation = models.CharField(max_length=20, blank=True)
    montant_depenses_energies_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    montant_depenses_energies_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Prix et transaction
    type_transaction = models.CharField(max_length=1, choices=TYPE_CHOICES, default=TYPE_VENTE)
    prix = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_agence = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    honoraires_payeurs = models.CharField(max_length=50, blank=True)

    # Champs spécifiques location
    loyer_mensuel = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    charges_locatives = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    depot_garantie = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    honoraires_location = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_inspiration = models.BooleanField(default=False)

    INSPIRATION_CHOICES = [
        ('chaleureux', 'Foyer chaleureux'),
        ('architecte', 'Deco architecte'),
        ('moderne', 'Design moderne'),
        ('nature', 'Esprit nature'),
        ('luxe', 'Standing & luxe'),
        ('cosy', 'Ambiance cosy'),
        ('scandinave', 'Style scandinave'),
        ('industriel', 'Loft industriel'),
        ('famille', 'Maison de famille'),
        ('jardin', 'Terrasse & jardin'),
    ]
    inspiration_categorie = models.CharField(
        max_length=20, blank=True, default='',
        choices=INSPIRATION_CHOICES
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Annonce'
        verbose_name_plural = 'Annonces'

    def __str__(self):
        return f"{self.reference} - {self.titre[:50]}"

    @property
    def prix_format(self):
        """Retourne le prix formaté avec espaces (ex: 500 000 €)"""
        return f"{self.prix:,.0f} €".replace(',', ' ')

    @property
    def photo_principale(self):
        """Retourne la première photo de l'annonce"""
        return self.photos.first()


class Photo(models.Model):
    """Photos associées à une annonce"""

    annonce = models.ForeignKey(
        Annonce,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    url = models.URLField(max_length=500)
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['ordre']
        verbose_name = 'Photo'
        verbose_name_plural = 'Photos'

    def __str__(self):
        return f"Photo {self.ordre} - {self.annonce.reference}"


class Commentaire(models.Model):
    """Commentaires sur une annonce"""

    annonce = models.ForeignKey(
        Annonce,
        on_delete=models.CASCADE,
        related_name='commentaires'
    )
    auteur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='commentaires'
    )
    texte = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']  # Plus anciens en premier (style chat)
        verbose_name = 'Commentaire'
        verbose_name_plural = 'Commentaires'

    def __str__(self):
        return f"{self.auteur.username} - {self.texte[:30]}..."


class Favori(models.Model):
    """Favoris : annonces likées par les utilisateurs"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favoris'
    )
    annonce = models.ForeignKey(
        Annonce,
        on_delete=models.CASCADE,
        related_name='favoris'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Favori'
        verbose_name_plural = 'Favoris'
        unique_together = ['user', 'annonce']  # Un seul like par user/annonce

    def __str__(self):
        return f"{self.user.username} ❤ {self.annonce.reference}"


class Agence(models.Model):
    """Représente une agence cliente qui alimente des biens"""

    FEED_TYPE_CHOICES = [
        ('url', 'URL publique'),
        ('ftp', 'FTP'),
    ]

    nom = models.CharField(max_length=200)
    reference = models.CharField(max_length=50, unique=True)
    logo_url = models.URLField(max_length=500, blank=True)
    feed_url = models.URLField(max_length=500, blank=True)
    feed_type = models.CharField(max_length=10, choices=FEED_TYPE_CHOICES, default='url')
    contact_nom = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_telephone = models.CharField(max_length=20, blank=True)
    adresse = models.TextField(blank=True)
    responsable = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='agence'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_import = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'Agence'

    def __str__(self):
        return self.nom


class Decoration(models.Model):
    """Inspiration déco intérieure"""

    titre = models.CharField(max_length=200)
    description = models.TextField()
    image_url = models.URLField(max_length=500)
    auteur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='decorations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Inspiration deco'

    def __str__(self):
        return self.titre


class DecoCommentaire(models.Model):
    """Commentaires sur les posts déco"""

    decoration = models.ForeignKey(
        Decoration,
        on_delete=models.CASCADE,
        related_name='commentaires'
    )
    auteur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='deco_commentaires'
    )
    texte = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.auteur.username} - {self.texte[:30]}"


class Partenaire(models.Model):
    """Annuaire de partenaires professionnels"""

    nom = models.CharField(max_length=200)
    metier = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    site_web = models.URLField(max_length=500, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['metier', 'nom']
        verbose_name = 'Partenaire'

    def __str__(self):
        return f"{self.nom} - {self.metier}"


class ProProfile(models.Model):
    """Profil professionnel auto-enregistre (decorateur, artisan, etc.)"""

    METIER_CHOICES = [
        ('decorateur', 'Decorateur d\'interieur'),
        ('architecte', 'Architecte d\'interieur'),
        ('peintre', 'Peintre'),
        ('plombier', 'Plombier'),
        ('electricien', 'Electricien'),
        ('jardinier', 'Paysagiste'),
        ('cuisiniste', 'Cuisiniste'),
        ('menuisier', 'Menuisier'),
        ('carreleur', 'Carreleur'),
        ('macon', 'Macon'),
        ('couvreur', 'Couvreur'),
        ('serrurier', 'Serrurier'),
        ('domotique', 'Domotique'),
        ('renovation', 'Renovation generale'),
        ('autre', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pro_profile')
    nom_entreprise = models.CharField(max_length=200)
    metier = models.CharField(max_length=50, choices=METIER_CHOICES)
    description = models.TextField(blank=True)
    photo_url = models.URLField(max_length=500, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    ville = models.CharField(max_length=100, blank=True)
    site_web = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Profil Pro'
        verbose_name_plural = 'Profils Pro'

    def __str__(self):
        return f"{self.nom_entreprise} ({self.get_metier_display()})"

    @property
    def note_moyenne(self):
        avg = self.avis.aggregate(avg=Avg('note'))['avg']
        return round(avg, 1) if avg else 0

    @property
    def nb_avis(self):
        return self.avis.count()


class ProRealisation(models.Model):
    """Realisation/projet d'un professionnel"""

    pro = models.ForeignKey(ProProfile, on_delete=models.CASCADE, related_name='realisations')
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    categorie = models.CharField(
        max_length=20, blank=True, default='',
        choices=Annonce.INSPIRATION_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Realisation'

    def __str__(self):
        return f"{self.titre} - {self.pro.nom_entreprise}"


class ProRealisationPhoto(models.Model):
    """Photos d'une realisation pro"""

    realisation = models.ForeignKey(ProRealisation, on_delete=models.CASCADE, related_name='photos')
    url = models.URLField(max_length=500)
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"Photo {self.ordre} - {self.realisation.titre}"


class ProAvis(models.Model):
    """Avis et notation sur un professionnel"""

    pro = models.ForeignKey(ProProfile, on_delete=models.CASCADE, related_name='avis')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avis_donnes')
    note = models.PositiveIntegerField()  # 1 a 5
    commentaire = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['pro', 'auteur']
        verbose_name = 'Avis Pro'
        verbose_name_plural = 'Avis Pro'

    def __str__(self):
        return f"{self.auteur.username} -> {self.pro.nom_entreprise}: {self.note}/5"


class PhotoFavori(models.Model):
    """Favori sur une photo d'inspiration (Pinterest-like)"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photo_favoris')
    photo = models.ForeignKey(
        Photo, on_delete=models.CASCADE,
        null=True, blank=True, related_name='photo_favoris'
    )
    photo_pro = models.ForeignKey(
        ProRealisationPhoto, on_delete=models.CASCADE,
        null=True, blank=True, related_name='photo_favoris'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favori Photo'
        verbose_name_plural = 'Favoris Photos'


class PhotoNote(models.Model):
    """Notation 1-5 etoiles sur une photo d'inspiration"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photo_notes')
    photo = models.ForeignKey(
        Photo, on_delete=models.CASCADE,
        null=True, blank=True, related_name='notes'
    )
    photo_pro = models.ForeignKey(
        ProRealisationPhoto, on_delete=models.CASCADE,
        null=True, blank=True, related_name='notes'
    )
    note = models.PositiveIntegerField()  # 1 a 5
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Note Photo'
        verbose_name_plural = 'Notes Photos'


class DemandeContact(models.Model):
    """Demande de contact envoyee a un agent immo ou un pro"""

    expediteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes_envoyees')
    annonce = models.ForeignKey(
        Annonce, on_delete=models.CASCADE,
        null=True, blank=True, related_name='demandes_contact'
    )
    pro = models.ForeignKey(
        ProProfile, on_delete=models.CASCADE,
        null=True, blank=True, related_name='demandes_contact'
    )
    message = models.TextField()
    telephone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Demande de contact'
        verbose_name_plural = 'Demandes de contact'

    def __str__(self):
        target = self.annonce.reference if self.annonce else self.pro.nom_entreprise
        return f"{self.expediteur.username} -> {target}"