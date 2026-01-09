from django.contrib import admin
from .models import Annonce, Photo, Commentaire


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
