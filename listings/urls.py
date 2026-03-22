from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('recherche/', views.search_results, name='search_results'),
    path('api/search/autocomplete/', views.autocomplete, name='autocomplete'),
    path('annonce/<str:reference>/', views.listing_detail, name='detail'),
    path('signup/', views.signup, name='signup'),
    path('inspirations/', views.decoration_list, name='decoration_list'),
    path('pros/', views.partenaire_list, name='partenaire_list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/import/', views.run_import, name='run_import'),
    path('mon-agence/', views.agence_dashboard, name='agence_dashboard'),
    path('mon-agence/import/', views.agence_run_import, name='agence_run_import'),
    path('api/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('api/toggle-inspiration/', views.toggle_inspiration, name='toggle_inspiration'),
    path('gestion/', views.gestion_agences, name='gestion_agences'),
    path('gestion/creer-agence/', views.creer_agence, name='creer_agence'),
    path('gestion/import/<int:agence_id>/', views.lancer_import_agence, name='lancer_import_agence'),
    path('gestion/toggle/<int:agence_id>/', views.toggle_agence_active, name='toggle_agence_active'),
    path('gestion/renvoyer-acces/<int:agence_id>/', views.renvoyer_acces, name='renvoyer_acces'),
    # Espace Pro
    path('pro/inscription/', views.pro_inscription, name='pro_inscription'),
    path('pro/dashboard/', views.pro_dashboard, name='pro_dashboard'),
    path('pro/realisation/ajouter/', views.pro_ajouter_realisation, name='pro_ajouter_realisation'),
    path('pro/realisation/<int:realisation_id>/supprimer/', views.pro_supprimer_realisation, name='pro_supprimer_realisation'),
    path('pro/<int:pro_id>/', views.pro_profil, name='pro_profil'),
    # APIs sociales
    path('api/photo-favori/', views.toggle_photo_favori, name='toggle_photo_favori'),
    path('api/photo-note/', views.rate_photo, name='rate_photo'),
    path('api/contact/', views.envoyer_contact, name='envoyer_contact'),
    path('api/pro-avis/', views.submit_pro_avis, name='submit_pro_avis'),
    path('api/contact-read/', views.mark_contact_read, name='mark_contact_read'),
    # Pages legales
    path('cgu/', views.cgu, name='cgu'),
    path('mentions-legales/', views.mentions_legales, name='mentions_legales'),
    path('confidentialite/', views.confidentialite, name='confidentialite'),
]
