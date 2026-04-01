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
    path('mon-agence/parametres/', views.agence_settings, name='agence_settings'),
    path('api/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('api/toggle-inspiration/', views.toggle_inspiration, name='toggle_inspiration'),
    path('api/toggle-inspi-une/', views.toggle_inspi_une, name='toggle_inspi_une'),
    path('gestion/', views.gestion_agences, name='gestion_agences'),
    path('gestion/creer-agence/', views.creer_agence, name='creer_agence'),
    path('gestion/agence/<int:agence_id>/parametres/', views.admin_agence_settings, name='admin_agence_settings'),
    path('gestion/import/<int:agence_id>/', views.lancer_import_agence, name='lancer_import_agence'),
    path('gestion/toggle/<int:agence_id>/', views.toggle_agence_active, name='toggle_agence_active'),
    path('gestion/renvoyer-acces/<int:agence_id>/', views.renvoyer_acces, name='renvoyer_acces'),
    path('gestion/conseillers/<int:agence_id>/', views.gestion_conseillers, name='gestion_conseillers'),
    path('gestion/options/<int:agence_id>/', views.gestion_options_agence, name='gestion_options_agence'),
    path('gestion/conseillers/renvoyer/<int:conseiller_id>/', views.renvoyer_acces_conseiller, name='renvoyer_acces_conseiller'),
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
    path('api/photo-comment/', views.post_photo_comment, name='post_photo_comment'),
    path('api/photo-comments/', views.get_photo_comments, name='get_photo_comments'),
    path('api/photo-comment/delete/', views.delete_photo_comment, name='delete_photo_comment'),
    # Gestion utilisateurs (admin)
    path('gestion/utilisateurs/', views.gestion_utilisateurs, name='gestion_utilisateurs'),
    path('gestion/utilisateurs/export/', views.export_utilisateurs_csv, name='export_utilisateurs_csv'),
    path('gestion/utilisateurs/reset-password/<int:user_id>/', views.admin_reset_password, name='admin_reset_password'),
    path('gestion/utilisateurs/supprimer/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    # Espace Conseiller
    path('mon-espace/', views.conseiller_dashboard, name='conseiller_dashboard'),
    path('mon-espace/mot-de-passe/', views.conseiller_set_password, name='conseiller_set_password'),
    # Annuaire
    path('agence/<int:agence_id>/', views.agence_profil, name='agence_profil'),
    # Locaux pro
    path('locaux-professionnels/', views.locaux_pro, name='locaux_pro'),
    # Mise en avant
    path('gestion/annonce/<int:annonce_id>/une/', views.toggle_mise_en_avant, name='toggle_mise_en_avant'),
    path('gestion/vedette/agence/<int:agence_id>/', views.toggle_vedette_agence, name='toggle_vedette_agence'),
    path('gestion/vedette/pro/<int:pro_id>/', views.toggle_vedette_pro, name='toggle_vedette_pro'),
    # Moderation
    path('gestion/commentaire/<int:commentaire_id>/supprimer/', views.supprimer_commentaire, name='supprimer_commentaire'),
    # Estimation
    path('estimer/', views.estimation, name='estimation'),
    path('gestion/estimation/<int:estimation_id>/assigner/', views.assigner_estimation, name='assigner_estimation'),
    # Page agence immo (landing)
    path('agence-immobiliere/', views.agence_immo, name='agence_immo'),
    # Pages legales
    path('cgu/', views.cgu, name='cgu'),
    path('mentions-legales/', views.mentions_legales, name='mentions_legales'),
    path('confidentialite/', views.confidentialite, name='confidentialite'),
]
