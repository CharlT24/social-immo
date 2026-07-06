from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Annonce, Agence, ProProfile


class StaticSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return [
            'listings:homepage',
            'listings:search_results',
            'listings:decoration_list',
            'listings:partenaire_list',
            'listings:estimation',
            'listings:agence_immo',
            'listings:locaux_pro',
            'listings:barometre',
            'listings:demande_devis',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item == 'listings:homepage':
            return 1.0
        if item == 'listings:search_results':
            return 0.9
        return 0.7


class VilleSitemap(Sitemap):
    """Pages SEO /immobilier/<ville>/"""
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        from django.utils.text import slugify
        villes = Annonce.objects.filter(is_active=True).exclude(ville='') \
            .values_list('ville', flat=True).distinct()
        # Slugs uniques, ordonnes pour un sitemap stable
        return sorted({slugify(v) for v in villes if slugify(v)})

    def location(self, slug):
        return reverse('listings:ville_page', args=[slug])


class VilleSegmentSitemap(Sitemap):
    """Pages SEO longue traine /immobilier/<ville>/<segment>/ — seulement
    les combinaisons qui ont au moins une annonce (pas de pages vides)."""
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        from django.utils.text import slugify
        from listings.views import SEGMENTS_SEO
        import re
        combos = []
        villes = Annonce.objects.filter(is_active=True).exclude(ville='') \
            .values_list('ville', flat=True).distinct()
        slugs = sorted({slugify(v) for v in villes if slugify(v)})
        for ville_slug in slugs:
            for segment, (transaction, mots, lib) in SEGMENTS_SEO.items():
                combos.append((ville_slug, segment))
        return combos

    def location(self, combo):
        return reverse('listings:ville_segment_page', args=[combo[0], combo[1]])


class AnnonceSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Annonce.objects.filter(is_active=True).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('listings:detail', args=[obj.reference])


class AgenceSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Agence.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('listings:agence_profil', args=[obj.id])


class ProSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return ProProfile.objects.filter(is_active=True).order_by('-id')

    def location(self, obj):
        return reverse('listings:pro_profil', args=[obj.id])
