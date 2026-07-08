"""
URL configuration for social_immo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import TemplateView
from django.views.static import serve as media_serve

from listings.sitemaps import StaticSitemap, AnnonceSitemap, AgenceSitemap, ProSitemap, VilleSitemap, VilleSegmentSitemap

sitemaps = {
    'static': StaticSitemap,
    'annonces': AnnonceSitemap,
    'agences': AgenceSitemap,
    'pros': ProSitemap,
    'villes': VilleSitemap,
    'villes_segments': VilleSegmentSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('', include('listings.urls')),
]

# Servir les fichiers media (photos uploadees : annonces particuliers, realisations pros).
# IMPORTANT : le helper static() de Django est un no-op quand DEBUG=False. On sert
# donc /media/ explicitement, y compris en prod, sinon toutes les photos uploadees
# renvoient 404 sur o2switch. Django.views.static.serve convient a ce volume ; pour
# monter en charge, ajouter un alias Apache /media/ -> MEDIA_ROOT (voir DEPLOIEMENT.md).
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
]
