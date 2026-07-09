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

    # Source et proprietaire
    SOURCE_CHOICES = [
        ('agence', 'Agence'),
        ('particulier', 'Particulier'),
    ]
    user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='annonces'
    )
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES,
        default='agence', db_index=True
    )

    # Références
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    client_reference = models.CharField(max_length=50, blank=True)
    # Vraie relation vers l'agence (remplie depuis client_reference a
    # l'import ; client_reference reste la cle texte du flux XML)
    agence = models.ForeignKey(
        'Agence', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='annonces'
    )

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
    mise_en_avant = models.BooleanField(default=False, verbose_name='Mise à la une')
    nb_vues = models.PositiveIntegerField(default=0, verbose_name='Nombre de vues')
    video_url = models.URLField(max_length=500, blank=True, default='', verbose_name='URL Video (YouTube/Vimeo)')
    visite_virtuelle_url = models.URLField(max_length=500, blank=True, default='', verbose_name='URL Visite virtuelle (Matterport/360)')

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
    conseiller = models.ForeignKey(
        'Conseiller',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='annonces'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Annonce'
        verbose_name_plural = 'Annonces'
        indexes = [
            # Recherche/listes : filtres les plus frequents
            models.Index(fields=['is_active', 'type_transaction']),
            models.Index(fields=['is_active', 'mise_en_avant']),
            models.Index(fields=['is_active', 'ville']),
            models.Index(fields=['prix']),
        ]

    def __str__(self):
        return f"{self.reference} - {self.titre[:50]}"

    def get_absolute_url(self):
        """URL canonique riche en mots-cles SEO (ville/type). La reference
        reste la cle de resolution ; le slug final est purement descriptif
        et ignore par la vue -> aucune ancienne URL ne casse."""
        from django.urls import reverse
        from django.utils.text import slugify
        morceaux = [self.libelle_type or '', self.ville or '']
        slug = slugify(' '.join(m for m in morceaux if m))
        if slug:
            return reverse('listings:detail_slug', args=[self.reference, slug])
        return reverse('listings:detail', args=[self.reference])

    @property
    def prix_format(self):
        """Retourne le prix formaté avec espaces (ex: 500 000 €)"""
        return f"{self.prix:,.0f} €".replace(',', ' ')

    @property
    def photo_principale(self):
        """Retourne la première photo de l'annonce"""
        return self.photos.first()

    @property
    def prix_m2(self):
        if self.prix and self.surface and self.surface > 0:
            return f"{self.prix / self.surface:,.0f}".replace(',', ' ')
        return None

    @property
    def frais_notaire(self):
        if self.prix:
            return f"{self.prix * 8 / 100:,.0f}".replace(',', ' ')
        return None

    # ===== Conformite legale (DPE, honoraires Loi Hoguet) =====

    @property
    def est_passoire_thermique(self):
        """Classe F ou G : mention legale obligatoire dans l'annonce."""
        return self.dpe_etiquette_conso in ('F', 'G')

    # Communes appliquant l'encadrement des loyers (loyer de reference majore).
    # Liste des principales zones concernees — a completer/ajuster selon les
    # arretes en vigueur. Cle : prefixe de code postal ou nom de commune (slug).
    ZONES_ENCADREMENT_LOYERS = {
        'paris': [str(d).zfill(2) for d in range(75001, 75021)],  # tout Paris (750xx)
        'lyon': ['6900', '6910'], 'villeurbanne': ['69100'],
        'lille': ['59000', '59260', '59160', '59800'],
        'montpellier': ['34000', '34070', '34080', '34090'],
        'bordeaux': ['33000', '33100', '33200', '33300', '33800'],
        'plaine-commune': [], 'est-ensemble': [],
    }

    @property
    def est_zone_encadree_loyers(self):
        """True si la location est dans une commune ou l'encadrement des loyers
        s'applique -> mention legale a afficher (loyer de reference majore)."""
        if self.type_transaction not in ('L', 'S'):
            return False
        cp = (self.code_postal or '').strip()
        ville = (self.ville or '').strip().lower()
        for cle, cps in self.ZONES_ENCADREMENT_LOYERS.items():
            if cle in ville:
                return True
            for prefixe in cps:
                if cp.startswith(prefixe):
                    return True
        # Paris : tous les codes postaux 75xxx
        if cp.startswith('75') and len(cp) == 5:
            return True
        return False

    @property
    def video_embed_url(self):
        """URL d'integration video en mode sans cookie (RGPD : youtube-nocookie).
        Gere YouTube, Vimeo ; sinon renvoie l'URL telle quelle (Matterport...)."""
        import re
        url = self.video_url or ''
        m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]{11})', url)
        if m:
            return f'https://www.youtube-nocookie.com/embed/{m.group(1)}'
        m = re.search(r'vimeo\.com/(\d+)', url)
        if m:
            return f'https://player.vimeo.com/video/{m.group(1)}'
        return url

    @property
    def honoraires_charge_acquereur(self):
        return 'acqu' in (self.honoraires_payeurs or '').lower()

    @property
    def prix_hors_honoraires(self):
        """Prix hors honoraires (obligatoire si honoraires a la charge de
        l'acquereur — arrete du 10/01/2017)."""
        if self.prix and self.frais_agence and self.honoraires_charge_acquereur:
            hni = float(self.prix) - float(self.frais_agence)
            if hni > 0:
                return f"{hni:,.0f}".replace(',', ' ')
        return None

    @property
    def taux_honoraires_ttc(self):
        """Taux d'honoraires TTC en % du prix hors honoraires."""
        if self.prix and self.frais_agence and self.honoraires_charge_acquereur:
            hni = float(self.prix) - float(self.frais_agence)
            if hni > 0:
                return round(float(self.frais_agence) / hni * 100, 1)
        return None

    @property
    def montant_projet(self):
        if self.prix:
            return f"{self.prix * 108 / 100:,.0f}".replace(',', ' ')
        return None

    @property
    def mensualite_estimee(self):
        if self.prix:
            import math
            capital = float(self.prix) * 0.8
            taux_mensuel = 0.035 / 12
            nb_mois = 20 * 12
            if taux_mensuel > 0:
                mensualite = capital * taux_mensuel / (1 - math.pow(1 + taux_mensuel, -nb_mois))
                return f"{mensualite:,.0f}".replace(',', ' ')
        return None

    @property
    def cout_mensuel_total(self):
        total = 0
        if self.loyer_mensuel:
            total += float(self.loyer_mensuel)
        if self.charges_locatives:
            total += float(self.charges_locatives)
        if total > 0:
            return f"{total:,.0f}".replace(',', ' ')
        return None


class InspirationTag(models.Model):
    """Tags pour les photos inspiration (deco, style, piece, couleur...)"""

    GROUPE_CHOICES = [
        ('style', 'Style'),
        ('piece', 'Piece'),
        ('couleur', 'Couleur'),
        ('materiau', 'Materiau'),
        ('ambiance', 'Ambiance'),
    ]

    nom = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    groupe = models.CharField(max_length=20, choices=GROUPE_CHOICES, default='style')
    icone = models.CharField(max_length=10, blank=True, default='')
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['groupe', 'ordre', 'nom']
        verbose_name = 'Tag inspiration'
        verbose_name_plural = 'Tags inspiration'

    def __str__(self):
        return self.nom


class Photo(models.Model):
    """Photos associées à une annonce"""

    annonce = models.ForeignKey(
        Annonce,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    url = models.URLField(max_length=500, blank=True, default='')
    image = models.ImageField(upload_to='annonces/', blank=True, default='')
    image_thumb = models.ImageField(upload_to='annonces/thumbs/', blank=True, default='')
    ordre = models.PositiveIntegerField(default=1)
    is_inspiration = models.BooleanField(default=False)
    mise_en_avant = models.BooleanField(default=False, verbose_name='A la une inspirations')
    inspiration_categorie = models.CharField(
        max_length=20, blank=True, default='',
        choices=Annonce.INSPIRATION_CHOICES
    )
    tags = models.ManyToManyField(InspirationTag, blank=True, related_name='photos')

    class Meta:
        ordering = ['ordre']
        verbose_name = 'Photo'
        verbose_name_plural = 'Photos'

    def __str__(self):
        return f"Photo {self.ordre} - {self.annonce.reference}"

    @property
    def src(self):
        """Retourne l'URL de la photo (upload ou externe)"""
        if self.image:
            return self.image.url
        return self.url

    @property
    def src_thumb(self):
        """Miniature si disponible (uploads), sinon la photo pleine taille."""
        if self.image_thumb:
            return self.image_thumb.url
        return self.src


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
    # Prix au moment de l'ajout : sert a detecter les baisses de prix
    prix_reference = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
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

    FEED_FORMAT_CHOICES = [
        ('ac3', 'XML (AC3/Ubiflow)'),
        ('poliris', 'CSV (Poliris)'),
    ]

    nom = models.CharField(max_length=200)
    reference = models.CharField(max_length=50, unique=True)
    logo_url = models.URLField(max_length=500, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    feed_url = models.URLField(max_length=500, blank=True)
    feed_type = models.CharField(max_length=10, choices=FEED_TYPE_CHOICES, default='url')
    feed_format = models.CharField(max_length=10, choices=FEED_FORMAT_CHOICES, default='ac3', verbose_name='Format du flux')
    # FTP
    ftp_host = models.CharField(max_length=200, blank=True, default='', verbose_name='Serveur FTP')
    ftp_user = models.CharField(max_length=100, blank=True, default='', verbose_name='Utilisateur FTP')
    ftp_password = models.CharField(max_length=100, blank=True, default='', verbose_name='Mot de passe FTP')
    ftp_path = models.CharField(max_length=500, blank=True, default='/', verbose_name='Chemin FTP')
    contact_nom = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_telephone = models.CharField(max_length=20, blank=True)
    adresse = models.TextField(blank=True)
    ville = models.CharField(max_length=100, blank=True, default='')
    code_postal = models.CharField(max_length=10, blank=True, default='')
    departement = models.CharField(max_length=3, blank=True, default='')
    siret = models.CharField(max_length=20, blank=True, default='', verbose_name='SIRET/RCS')
    description = models.TextField(blank=True, default='')
    site_web = models.URLField(max_length=500, blank=True, default='')
    horaires = models.CharField(max_length=200, blank=True, default='', verbose_name='Horaires d\'ouverture')
    responsable = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='agence'
    )
    is_active = models.BooleanField(default=True)
    mise_en_avant = models.BooleanField(default=False, verbose_name='A la une sur la homepage')
    created_at = models.DateTimeField(auto_now_add=True)
    last_import = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'Agence'

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        from django.urls import reverse
        from django.utils.text import slugify
        slug = slugify(self.nom)
        if slug:
            return reverse('listings:agence_profil_slug', args=[self.id, slug])
        return reverse('listings:agence_profil', args=[self.id])


class Conseiller(models.Model):
    """Conseiller/agent individuel rattaché à une agence (IAD, Capifrance, etc.)"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='conseiller_profile'
    )
    agence = models.ForeignKey(
        'Agence',
        on_delete=models.CASCADE,
        related_name='conseillers'
    )
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'Conseiller'
        verbose_name_plural = 'Conseillers'

    def __str__(self):
        return f"{self.nom} ({self.agence.nom})"


class ProProfile(models.Model):
    """Profil professionnel auto-enregistre (decorateur, artisan, etc.)"""

    METIER_CHOICES = [
        # Design & decoration
        ('decorateur', 'Decorateur d\'interieur'),
        ('architecte', 'Architecte d\'interieur'),
        ('home_stager', 'Home stager'),
        ('cuisiniste', 'Cuisiniste'),
        # Gros oeuvre
        ('macon', 'Macon'),
        ('charpentier', 'Charpentier'),
        ('couvreur', 'Couvreur'),
        ('facadier', 'Facadier / Ravalement'),
        # Second oeuvre
        ('peintre', 'Peintre'),
        ('plombier', 'Plombier'),
        ('electricien', 'Electricien'),
        ('carreleur', 'Carreleur'),
        ('menuisier', 'Menuisier'),
        ('plaquiste', 'Plaquiste / Platrier'),
        ('serrurier', 'Serrurier'),
        ('vitrier', 'Vitrier'),
        ('storiste', 'Storiste / Fermetures'),
        # Energie & confort
        ('chauffagiste', 'Chauffagiste / Climatisation'),
        ('isolation', 'Isolation / RGE'),
        ('domotique', 'Domotique'),
        # Exterieur
        ('paysagiste', 'Paysagiste / Jardinier'),
        ('pisciniste', 'Pisciniste'),
        # Services immobiliers
        ('photographe', 'Photographe immobilier'),
        ('diagnostiqueur', 'Diagnostiqueur immobilier'),
        ('geometre', 'Geometre-expert'),
        ('courtier_travaux', 'Courtier en travaux'),
        ('demenageur', 'Demenageur'),
        ('nettoyage', 'Nettoyage / Conciergerie'),
        # General
        ('tous_corps_etat', "Tous corps d'etat"),
        ('renovation', 'Renovation generale'),
        ('autre', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pro_profile')
    nom_entreprise = models.CharField(max_length=200)
    metier = models.CharField(max_length=50, choices=METIER_CHOICES)
    autres_metiers = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='Autres corps de metier',
        help_text="Specialites supplementaires, separees par des virgules (entreprises tous corps d'etat)."
    )
    description = models.TextField(blank=True)
    photo_url = models.URLField(max_length=500, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    ville = models.CharField(max_length=100, blank=True)
    site_web = models.URLField(max_length=500, blank=True)
    departement = models.CharField(max_length=3, blank=True, default='')
    code_postal = models.CharField(max_length=10, blank=True, default='')
    siret = models.CharField(max_length=20, blank=True, default='', verbose_name='SIRET/RCS')
    siret_verifie = models.BooleanField(default=False, verbose_name='SIRET verifie (entreprise reelle et active)')
    nom_officiel = models.CharField(max_length=200, blank=True, default='', verbose_name='Raison sociale officielle')
    google_business_url = models.URLField(max_length=500, blank=True, default='', verbose_name='Lien Google (fiche/avis)')
    is_active = models.BooleanField(default=True)
    mise_en_avant = models.BooleanField(default=False, verbose_name='A la une sur la homepage')
    inspiration_a_la_une = models.BooleanField(default=False, verbose_name='Inspirations a la une')
    nb_inspirations_une = models.PositiveIntegerField(
        default=0, verbose_name='Nb inspirations a la une autorisees'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Profil Pro'
        verbose_name_plural = 'Profils Pro'

    def __str__(self):
        return f"{self.nom_entreprise} ({self.get_metier_display()})"

    def get_absolute_url(self):
        from django.urls import reverse
        from django.utils.text import slugify
        slug = slugify(f'{self.nom_entreprise} {self.get_metier_display()}')
        if slug:
            return reverse('listings:pro_profil_slug', args=[self.id, slug])
        return reverse('listings:pro_profil', args=[self.id])

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
    tags = models.ManyToManyField(InspirationTag, blank=True, related_name='realisations')
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
    url = models.URLField(max_length=500, blank=True, default='')
    image = models.ImageField(upload_to='realisations/', blank=True, default='')
    image_thumb = models.ImageField(upload_to='realisations/thumbs/', blank=True, default='')
    mise_en_avant = models.BooleanField(default=False, verbose_name='A la une inspirations')
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"Photo {self.ordre} - {self.realisation.titre}"

    @property
    def src(self):
        """Retourne l'URL de la photo (upload ou externe)"""
        if self.image:
            return self.image.url
        return self.url

    @property
    def src_thumb(self):
        """Miniature si disponible (uploads), sinon la photo pleine taille."""
        if self.image_thumb:
            return self.image_thumb.url
        return self.src


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


class PhotoCommentaire(models.Model):
    """Commentaire sur une photo d'inspiration (agence ou pro)"""

    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photo_commentaires')
    photo = models.ForeignKey(
        Photo, on_delete=models.CASCADE,
        null=True, blank=True, related_name='commentaires'
    )
    photo_pro = models.ForeignKey(
        ProRealisationPhoto, on_delete=models.CASCADE,
        null=True, blank=True, related_name='commentaires'
    )
    texte = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Commentaire Photo'
        verbose_name_plural = 'Commentaires Photos'

    def __str__(self):
        return f"{self.auteur.username}: {self.texte[:50]}"


class DemandeContact(models.Model):
    """Demande de contact envoyee a un agent immo ou un pro.
    L'expediteur peut etre un visiteur anonyme (nom + email captures)."""

    expediteur = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='demandes_envoyees',
        null=True, blank=True,
    )
    # Coordonnees du visiteur anonyme (si expediteur non connecte)
    nom = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(blank=True, default='')
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
    creneau_rappel = models.CharField(max_length=20, blank=True, default='', verbose_name='Creneau de rappel')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Demande de contact'
        verbose_name_plural = 'Demandes de contact'

    @property
    def nom_expediteur(self):
        if self.expediteur:
            return self.expediteur.get_full_name() or self.expediteur.username
        return self.nom or 'Visiteur'

    @property
    def email_expediteur(self):
        return self.expediteur.email if self.expediteur else self.email


class DemandeAgence(models.Model):
    """Demande d'une agence immo souhaitant diffuser ses biens (page vitrine).
    Persistee en base pour ne jamais perdre un lead, meme si l'email echoue."""

    nom_agence = models.CharField(max_length=200, verbose_name="Nom de l'agence")
    ville = models.CharField(max_length=120, blank=True, default='')
    email = models.EmailField()
    telephone = models.CharField(max_length=30, blank=True, default='')
    nb_biens = models.CharField(max_length=50, blank=True, default='', verbose_name='Nombre de biens')
    message = models.TextField(blank=True, default='')
    email_envoye = models.BooleanField(default=False, verbose_name='Email admin envoye')
    is_traitee = models.BooleanField(default=False, verbose_name='Traitee')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande d'agence"
        verbose_name_plural = "Demandes d'agences"

    def __str__(self):
        return f'{self.nom_agence} ({self.email})'

    def __str__(self):
        target = self.annonce.reference if self.annonce else (self.pro.nom_entreprise if self.pro else '?')
        return f"{self.nom_expediteur} -> {target}"


class AgenceOptions(models.Model):
    """Options activables par agence (futures options payantes)"""

    agence = models.OneToOneField(
        Agence, on_delete=models.CASCADE, related_name='options'
    )

    # --- VISIBILITE ---
    mise_en_avant = models.BooleanField(
        default=False, verbose_name='Mise a la une',
        help_text='Permet de mettre des annonces a la une (priorite dans les recherches)'
    )
    nb_mises_en_avant = models.PositiveIntegerField(
        default=0, verbose_name='Nb annonces a la une autorisees'
    )
    remontee_auto = models.BooleanField(
        default=False, verbose_name='Remontee automatique',
        help_text='Remonter les annonces en tete toutes les 48h'
    )
    badge_premium = models.BooleanField(
        default=False, verbose_name='Badge Premium',
        help_text='Badge dore "Premium" sur toutes les annonces de l\'agence'
    )

    # --- INSPIRATIONS ---
    inspiration_a_la_une = models.BooleanField(
        default=False, verbose_name='Inspirations a la une',
        help_text='Permet de mettre des photos inspiration a la une sur la homepage'
    )
    nb_inspirations_une = models.PositiveIntegerField(
        default=0, verbose_name='Nb inspirations a la une autorisees',
        help_text='Quota de photos inspiration pouvant etre mises a la une'
    )

    # --- BRANDING ---
    logo_sur_annonces = models.BooleanField(
        default=False, verbose_name='Logo sur annonces',
        help_text='Afficher le logo de l\'agence sur chaque annonce'
    )
    page_vitrine = models.BooleanField(
        default=False, verbose_name='Page vitrine personnalisee',
        help_text='Page agence enrichie avec description, photos, avis'
    )
    bandeau_exclusif = models.BooleanField(
        default=False, verbose_name='Bandeau Exclusif',
        help_text='Afficher "Exclusivite" sur certaines annonces'
    )

    # --- LEADS & CONTACT ---
    estimation_forward = models.BooleanField(
        default=False, verbose_name='Reception estimations',
        help_text='Recevoir les demandes d\'estimation de sa zone'
    )
    contact_prioritaire = models.BooleanField(
        default=False, verbose_name='Contact prioritaire',
        help_text='Formulaire de contact enrichi avec rappel telephonique'
    )
    alertes_email = models.BooleanField(
        default=False, verbose_name='Alertes email acheteurs',
        help_text='Envoyer les nouvelles annonces aux acheteurs inscrits dans la zone'
    )

    # --- STATS & DATA ---
    stats_avancees = models.BooleanField(
        default=False, verbose_name='Statistiques avancees',
        help_text='Nombre de vues, clics, favoris par annonce + tendances'
    )
    rapport_mensuel = models.BooleanField(
        default=False, verbose_name='Rapport mensuel',
        help_text='Email recapitulatif mensuel avec performances'
    )
    donnees_marche = models.BooleanField(
        default=False, verbose_name='Donnees de marche',
        help_text='Prix au m2, tendances du secteur, comparatifs'
    )

    # --- CONTENU ENRICHI ---
    visite_virtuelle = models.BooleanField(
        default=False, verbose_name='Visite virtuelle',
        help_text='Integration de visites 3D (Matterport, etc.)'
    )
    video = models.BooleanField(
        default=False, verbose_name='Videos',
        help_text='Integrer des videos YouTube/Vimeo sur les annonces'
    )
    photos_illimitees = models.BooleanField(
        default=False, verbose_name='Photos illimitees',
        help_text='Pas de limite sur le nombre de photos par annonce'
    )

    # --- META ---
    updated_at = models.DateTimeField(auto_now=True)
    notes_admin = models.TextField(
        blank=True, default='', verbose_name='Notes internes',
        help_text='Notes visibles uniquement par l\'admin'
    )

    class Meta:
        verbose_name = 'Options agence'
        verbose_name_plural = 'Options agences'

    def __str__(self):
        return f'Options - {self.agence.nom}'

    @property
    def options_actives(self):
        """Retourne la liste des options activees"""
        opts = []
        for f in self._meta.get_fields():
            if isinstance(f, models.BooleanField) and f.name != 'id':
                if getattr(self, f.name):
                    opts.append(f.verbose_name)
        return opts

    @property
    def nb_options_actives(self):
        return len(self.options_actives)


class Estimation(models.Model):
    """Demande d'estimation immobiliere"""

    TYPE_BIEN_CHOICES = [
        ('appartement', 'Appartement'),
        ('maison', 'Maison'),
        ('terrain', 'Terrain'),
        ('commerce', 'Local commercial'),
        ('bureau', 'Bureau'),
        ('autre', 'Autre'),
    ]

    type_bien = models.CharField(max_length=50, choices=TYPE_BIEN_CHOICES)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    surface = models.PositiveIntegerField(null=True, blank=True)
    nb_pieces = models.PositiveIntegerField(null=True, blank=True)
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_treated = models.BooleanField(default=False)
    agence_assignee = models.ForeignKey(
        'Agence', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='estimations'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande d'estimation"

    def __str__(self):
        return f"{self.nom} - {self.ville} ({self.get_type_bien_display()})"


class UserProfile(models.Model):
    """Profil utilisateur particulier (complement au User Django)"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telephone = models.CharField(max_length=20, blank=True, default='')
    ville = models.CharField(max_length=100, blank=True, default='')
    code_postal = models.CharField(max_length=10, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Profil utilisateur'
        verbose_name_plural = 'Profils utilisateurs'

    def __str__(self):
        return f"Profil de {self.user.username}"

class RechercheSauvegardee(models.Model):
    """Alerte email : le user sauvegarde une recherche et recoit les
    nouveaux biens correspondants (CRON envoyer_alertes)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recherches')
    # Criteres (memes params que search_results)
    ville = models.CharField(max_length=100, blank=True, default='')
    type_transaction = models.CharField(max_length=2, blank=True, default='')
    prix_min = models.PositiveIntegerField(null=True, blank=True)
    prix_max = models.PositiveIntegerField(null=True, blank=True)
    surface_min = models.PositiveIntegerField(null=True, blank=True)
    pieces_min = models.PositiveIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    derniere_alerte = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Recherche sauvegardee'
        verbose_name_plural = 'Recherches sauvegardees'

    def __str__(self):
        return f"Alerte {self.user.username} - {self.resume()}"

    def resume(self):
        parts = []
        if self.ville:
            parts.append(self.ville)
        if self.type_transaction == 'V':
            parts.append('achat')
        elif self.type_transaction == 'L':
            parts.append('location')
        if self.prix_max:
            parts.append(f"max {self.prix_max:,} EUR".replace(',', ' '))
        if self.surface_min:
            parts.append(f"des {self.surface_min} m2")
        if self.pieces_min:
            parts.append(f"{self.pieces_min}+ pieces")
        return ', '.join(parts) or 'tous les biens'

    def annonces_correspondantes(self, depuis=None):
        qs = Annonce.objects.filter(is_active=True)
        if self.ville:
            qs = qs.filter(ville__icontains=self.ville)
        if self.type_transaction:
            qs = qs.filter(type_transaction=self.type_transaction)
        if self.prix_min:
            qs = qs.filter(prix__gte=self.prix_min)
        if self.prix_max:
            qs = qs.filter(prix__lte=self.prix_max)
        if self.surface_min:
            qs = qs.filter(surface__gte=self.surface_min)
        if self.pieces_min:
            qs = qs.filter(nb_pieces__gte=self.pieces_min)
        if depuis:
            qs = qs.filter(created_at__gte=depuis)
        return qs.order_by('-created_at')

    def url_recherche(self):
        from urllib.parse import urlencode
        params = {}
        if self.ville:
            params['ville'] = self.ville
        if self.type_transaction:
            params['type'] = self.type_transaction
        if self.prix_min:
            params['prix_min'] = self.prix_min
        if self.prix_max:
            params['prix_max'] = self.prix_max
        if self.surface_min:
            params['surface_min'] = self.surface_min
        if self.pieces_min:
            params['pieces_min'] = self.pieces_min
        return '/recherche/' + ('?' + urlencode(params) if params else '')

    def correspond_a(self, annonce):
        """L'annonce entre-t-elle dans les criteres de cette alerte ?"""
        if self.ville and self.ville.lower() not in (annonce.ville or '').lower():
            return False
        if self.type_transaction and annonce.type_transaction != self.type_transaction:
            return False
        prix = float(annonce.prix or 0)
        if self.prix_min and prix < self.prix_min:
            return False
        if self.prix_max and prix > self.prix_max:
            return False
        if self.surface_min and float(annonce.surface or 0) < self.surface_min:
            return False
        if self.pieces_min and (annonce.nb_pieces or 0) < self.pieces_min:
            return False
        return True

    @classmethod
    def acheteurs_pour(cls, annonce):
        """Nombre d'acheteurs (users distincts) dont une alerte active
        correspond a cette annonce — l'effet wow du vendeur.

        Les criteres numeriques/type sont filtres en base (ils reduisent
        drastiquement l'ensemble) ; la regle ville (sous-chaine) est
        verifiee en Python sur le petit ensemble restant."""
        from django.db.models import Q
        prix = float(annonce.prix or 0)
        surface = float(annonce.surface or 0)
        pieces = annonce.nb_pieces or 0

        qs = (cls.objects.filter(is_active=True).exclude(user=annonce.user_id)
              .filter(Q(type_transaction='') | Q(type_transaction=annonce.type_transaction))
              .filter(Q(prix_min__isnull=True) | Q(prix_min__lte=prix))
              .filter(Q(prix_max__isnull=True) | Q(prix_max__gte=prix))
              .filter(Q(surface_min__isnull=True) | Q(surface_min__lte=surface))
              .filter(Q(pieces_min__isnull=True) | Q(pieces_min__lte=pieces)))
        ville_annonce = (annonce.ville or '').lower()
        users = set()
        for ville_alerte, user_id in qs.values_list('ville', 'user_id'):
            if not ville_alerte or ville_alerte.lower() in ville_annonce:
                users.add(user_id)
        return len(users)


class VilleGeo(models.Model):
    """Coordonnees geographiques d'une ville (geocodees via
    api-adresse.data.gouv.fr, commande geocoder_villes)."""

    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10, blank=True, default='')
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('ville', 'code_postal')
        verbose_name = 'Ville geocodee'
        verbose_name_plural = 'Villes geocodees'

    def __str__(self):
        return f"{self.ville} ({self.code_postal})"

    @classmethod
    def villes_dans_rayon(cls, ville, rayon_km):
        """Retourne la liste des noms de villes situees a moins de `rayon_km`
        du centre `ville`. Pre-filtre par boite englobante (rapide, indexe)
        puis distance haversine exacte. Retourne None si la ville centre
        n'est pas geocodee."""
        import math
        centre = cls.objects.filter(ville__iexact=(ville or '').strip()).first()
        if not centre:
            return None
        # Boite englobante approximative pour pre-filtrer en SQL
        dlat = rayon_km / 111.0
        dlon = rayon_km / (111.0 * max(math.cos(math.radians(centre.latitude)), 0.01))
        candidats = cls.objects.filter(
            latitude__gte=centre.latitude - dlat, latitude__lte=centre.latitude + dlat,
            longitude__gte=centre.longitude - dlon, longitude__lte=centre.longitude + dlon,
        )
        proches = []
        for v in candidats:
            # Haversine
            r = 6371.0
            p1, p2 = math.radians(centre.latitude), math.radians(v.latitude)
            dp = math.radians(v.latitude - centre.latitude)
            dl = math.radians(v.longitude - centre.longitude)
            a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
            dist = r * 2 * math.asin(math.sqrt(a))
            if dist <= rayon_km:
                proches.append(v.ville)
        return proches


class CommuneDVF(models.Model):
    """Cache du geocodage INSEE + fraicheur des donnees DVF d'une commune."""

    code_insee = models.CharField(max_length=5, unique=True)
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10, blank=True, default='')
    derniere_maj = models.DateTimeField(null=True, blank=True)
    nb_ventes = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Commune DVF'
        verbose_name_plural = 'Communes DVF'

    def __str__(self):
        return f"{self.ville} ({self.code_insee})"


class VenteDVF(models.Model):
    """Vente reelle issue des Demandes de Valeurs Foncieres (Etalab).
    Alimente l'estimation et les exemples de ventes comparables."""

    TYPE_CHOICES = [('maison', 'Maison'), ('appartement', 'Appartement')]

    commune = models.ForeignKey(CommuneDVF, on_delete=models.CASCADE, related_name='ventes')
    type_local = models.CharField(max_length=15, choices=TYPE_CHOICES)
    surface = models.PositiveIntegerField()
    prix = models.PositiveIntegerField()
    date_mutation = models.DateField()

    class Meta:
        ordering = ['-date_mutation']
        indexes = [models.Index(fields=['commune', 'type_local'])]
        verbose_name = 'Vente DVF'
        verbose_name_plural = 'Ventes DVF'

    def __str__(self):
        return f"{self.get_type_local_display()} {self.surface} m2 - {self.prix} EUR ({self.date_mutation})"

    @property
    def prix_m2(self):
        return round(self.prix / self.surface) if self.surface else None


class Abonnement(models.Model):
    """Abonnement ou achat Stripe (agence, pro, pack vendeur).
    Cree/mis a jour automatiquement par le webhook Stripe."""

    TYPE_CHOICES = [
        ('agence', 'Abonnement Agence Premium'),
        ('pro', 'Abonnement Artisan Pro'),
        ('pack_vendeur', 'Pack Vendeur Pro (30 jours)'),
    ]
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('impaye', 'Impaye'),
        ('resilie', 'Resilie'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='abonnements')
    type_abonnement = models.CharField(max_length=20, choices=TYPE_CHOICES)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='actif')
    stripe_customer_id = models.CharField(max_length=100, blank=True, default='')
    stripe_subscription_id = models.CharField(max_length=100, blank=True, default='')
    checkout_session_id = models.CharField(max_length=120, blank=True, null=True, default=None, unique=True)
    annonce = models.ForeignKey(
        Annonce, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='boosts', help_text='Annonce boostee (pack vendeur)'
    )
    date_fin = models.DateTimeField(null=True, blank=True, help_text='Fin du boost (pack vendeur)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Abonnement'
        verbose_name_plural = 'Abonnements'

    def __str__(self):
        return f"{self.get_type_abonnement_display()} - {self.user.username} ({self.statut})"


class TicketSupport(models.Model):
    """Message du support (SAV) : accuse de reception automatique,
    notification admin, suivi du traitement."""

    SUJET_CHOICES = [
        ('compte', 'Mon compte'),
        ('annonce', 'Mon annonce'),
        ('paiement', 'Paiement / facturation'),
        ('technique', 'Probleme technique'),
        ('autre', 'Autre'),
    ]

    nom = models.CharField(max_length=100)
    email = models.EmailField()
    sujet = models.CharField(max_length=20, choices=SUJET_CHOICES, default='autre')
    message = models.TextField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    is_traite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ticket support'
        verbose_name_plural = 'Tickets support'

    def __str__(self):
        return f"[{self.get_sujet_display()}] {self.nom} ({self.created_at:%d/%m/%Y})"


class StatJour(models.Model):
    """Compteurs quotidiens sans cookie (pilotage du site)."""

    date = models.DateField(unique=True)
    visites = models.PositiveIntegerField(default=0)
    estimations = models.PositiveIntegerField(default=0)
    depots_annonces = models.PositiveIntegerField(default=0)
    alertes_creees = models.PositiveIntegerField(default=0)
    demandes_devis = models.PositiveIntegerField(default=0)
    inscriptions = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Statistiques du jour'
        verbose_name_plural = 'Statistiques quotidiennes'

    def __str__(self):
        return f"{self.date} : {self.visites} visites"

    @classmethod
    def incrementer(cls, champ):
        """Incremente un compteur du jour de maniere atomique et silencieuse."""
        from django.db.models import F
        from django.utils import timezone
        try:
            obj, _ = cls.objects.get_or_create(date=timezone.localdate())
            cls.objects.filter(pk=obj.pk).update(**{champ: F(champ) + 1})
        except Exception:
            pass  # la stat ne doit jamais casser une requete


class PageVue(models.Model):
    """Analytics maison, sans cookie (RGPD) : une ligne par page vue.
    Le visiteur est identifie par un hash quotidien anonyme (IP+UA+jour+secret),
    non reversible et qui change chaque jour -> pas de donnee personnelle stockee.
    Alimente le cockpit admin (trafic, sources, pages populaires)."""

    SECTION_CHOICES = [
        ('home', 'Accueil'), ('annonce', 'Fiche annonce'), ('recherche', 'Recherche'),
        ('ville', 'Page ville (SEO)'), ('inspirations', 'Inspirations'),
        ('pro', 'Pro / annuaire'), ('agence', 'Agence'), ('estimer', 'Estimation'),
        ('compte', 'Espace compte'), ('autre', 'Autre'),
    ]

    path = models.CharField(max_length=300)
    section = models.CharField(max_length=20, blank=True, default='')
    referer_host = models.CharField(max_length=200, blank=True, default='')
    visiteur_hash = models.CharField(max_length=64)
    is_mobile = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Page vue'
        verbose_name_plural = 'Pages vues'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['visiteur_hash', 'created_at']),
            models.Index(fields=['section', 'created_at']),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.path}"
