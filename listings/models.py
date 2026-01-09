from django.db import models
from django.contrib.auth.models import User


class Annonce(models.Model):
    """Modèle principal pour une annonce immobilière"""

    # Types de transaction
    TYPE_VENTE = 'V'
    TYPE_LOCATION = 'L'
    TYPE_CHOICES = [
        (TYPE_VENTE, 'Vente'),
        (TYPE_LOCATION, 'Location'),
    ]

    # Références
    reference = models.CharField(max_length=50, unique=True, db_index=True)
    client_reference = models.CharField(max_length=50, blank=True)

    # Infos principales
    titre = models.CharField(max_length=255)
    texte = models.TextField(blank=True)
    code_type = models.CharField(max_length=10, blank=True)

    # Contact
    contact_nom = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_telephone = models.CharField(max_length=20, blank=True)

    # Localisation
    code_postal = models.CharField(max_length=10)
    ville = models.CharField(max_length=100)

    # Caractéristiques du bien
    nb_pieces = models.PositiveIntegerField(null=True, blank=True)
    nb_chambres = models.PositiveIntegerField(null=True, blank=True)
    surface = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    annee_construction = models.PositiveIntegerField(null=True, blank=True)

    # Diagnostics énergétiques
    dpe_etiquette_conso = models.CharField(max_length=1, blank=True)  # A, B, C, D, E, F, G
    dpe_valeur_conso = models.PositiveIntegerField(null=True, blank=True)
    dpe_etiquette_ges = models.CharField(max_length=1, blank=True)

    # Prix et transaction
    type_transaction = models.CharField(max_length=1, choices=TYPE_CHOICES, default=TYPE_VENTE)
    prix = models.DecimalField(max_digits=12, decimal_places=2)
    honoraires_payeurs = models.CharField(max_length=50, blank=True)

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

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
