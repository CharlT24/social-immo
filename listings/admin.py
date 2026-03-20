from django.contrib import admin
from .models import Annonce, Photo, Commentaire, Favori, Agence, Decoration, DecoCommentaire, Partenaire


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1


@admin.register(Annonce)
class AnnonceAdmin(admin.ModelAdmin):
    list_display = ['reference', 'titre', 'ville', 'prix', 'type_transaction', 'is_active', 'created_at']
    list_filter = ['type_transaction', 'ville', 'is_active', 'dpe_etiquette_conso']
    search_fields = ['reference', 'titre', 'ville']
    inlines = [PhotoInline]


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['annonce', 'ordre', 'url']
    list_filter = ['annonce']


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    list_display = ['auteur', 'annonce', 'texte', 'created_at']
    list_filter = ['annonce', 'created_at']
    search_fields = ['texte', 'auteur__username']


@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display = ['user', 'annonce', 'created_at']
    list_filter = ['created_at']


@admin.register(Agence)
class AgenceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'reference', 'responsable', 'feed_type', 'is_active', 'last_import']
    list_filter = ['is_active', 'feed_type']
    search_fields = ['nom', 'reference', 'contact_nom']


@admin.register(Decoration)
class DecorationAdmin(admin.ModelAdmin):
    list_display = ['titre', 'auteur', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['titre']


@admin.register(DecoCommentaire)
class DecoCommentaireAdmin(admin.ModelAdmin):
    list_display = ['auteur', 'decoration', 'created_at']
    list_filter = ['created_at']


@admin.register(Partenaire)
class PartenaireAdmin(admin.ModelAdmin):
    list_display = ['nom', 'metier', 'ville', 'is_active']
    list_filter = ['metier', 'is_active', 'ville']
    search_fields = ['nom', 'metier', 'ville']
