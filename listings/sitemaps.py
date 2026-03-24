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
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        if item == 'listings:homepage':
            return 1.0
        if item == 'listings:search_results':
            return 0.9
        return 0.7


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
