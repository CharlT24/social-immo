from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('recherche/', views.search_results, name='search_results'),
    path('api/search/autocomplete/', views.autocomplete, name='autocomplete'),
    path('annonce/<str:reference>/', views.listing_detail, name='detail'),
    # URL riche en mots-cles (slug descriptif ignore) : /annonce/CT-123/appartement-perigueux/
    path('annonce/<str:reference>/<slug:slug>/', views.listing_detail, name='detail_slug'),
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
    path('gestion/cockpit/', views.cockpit, name='cockpit'),
    path('gestion/pros/', views.gestion_pros, name='gestion_pros'),
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
    path('pro/<int:pro_id>/<slug:slug>/', views.pro_profil, name='pro_profil_slug'),
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
    path('agence/<int:agence_id>/<slug:slug>/', views.agence_profil, name='agence_profil_slug'),
    # Locaux pro
    path('locaux-professionnels/', views.locaux_pro, name='locaux_pro'),
    # Mise en avant
    path('gestion/annonce/<int:annonce_id>/une/', views.toggle_mise_en_avant, name='toggle_mise_en_avant'),
    path('gestion/vedette/agence/<int:agence_id>/', views.toggle_vedette_agence, name='toggle_vedette_agence'),
    path('gestion/vedette/pro/<int:pro_id>/', views.toggle_vedette_pro, name='toggle_vedette_pro'),
    path('gestion/options/pro/<int:pro_id>/', views.gestion_options_pro, name='gestion_options_pro'),
    # Moderation
    path('gestion/commentaire/<int:commentaire_id>/supprimer/', views.supprimer_commentaire, name='supprimer_commentaire'),
    # Estimation
    path('estimer/', views.estimation, name='estimation'),
    path('api/estimer/', views.api_estimer, name='api_estimer'),
    path('api/suggerer-annonce/', views.api_suggerer_annonce, name='api_suggerer_annonce'),
    # Alertes de recherche
    path('alertes/creer/', views.sauvegarder_recherche, name='sauvegarder_recherche'),
    path('alertes/<int:recherche_id>/supprimer/', views.supprimer_recherche, name='supprimer_recherche'),
    # SEO villes + longue traine (ville x type x transaction)
    path('immobilier/<slug:ville_slug>/', views.ville_page, name='ville_page'),
    path('immobilier/<slug:ville_slug>/<slug:segment>/', views.ville_segment_page, name='ville_segment_page'),
    # Devis travaux
    path('devis/', views.demande_devis, name='demande_devis'),
    # Barometre des prix
    path('barometre/', views.barometre, name='barometre'),
    # Inscription agence self-service + aide
    path('agence/inscription/', views.agence_inscription, name='agence_inscription'),
    path('aide/', views.aide, name='aide'),
    path('mon-compte/supprimer/', views.supprimer_mon_compte, name='supprimer_mon_compte'),
    path('mon-compte/exporter/', views.exporter_mes_donnees, name='exporter_mes_donnees'),
    # Paiements Stripe
    path('tarifs/', views.tarifs, name='tarifs'),
    path('abonnement/souscrire/<str:type_abonnement>/', views.souscrire, name='souscrire'),
    path('abonnement/succes/', views.abonnement_succes, name='abonnement_succes'),
    path('abonnement/portail/', views.portail_facturation, name='portail_facturation'),
    path('stripe/webhook/', csrf_exempt(views.stripe_webhook), name='stripe_webhook'),
    # Partage inspiration
    path('inspirations/photo/<str:photo_type>/<int:photo_id>/', views.inspiration_partage, name='inspiration_partage'),
    path('gestion/estimation/<int:estimation_id>/assigner/', views.assigner_estimation, name='assigner_estimation'),
    # Page agence immo (landing)
    path('agence-immobiliere/', views.agence_immo, name='agence_immo'),
    # Espace Particulier
    path('messages/', views.messages_inbox, name='messages_inbox'),
    path('messages/<int:conversation_id>/', views.messages_thread, name='messages_thread'),
    path('mon-compte/', views.particulier_dashboard, name='particulier_dashboard'),
    path('mon-compte/deposer/', views.particulier_creer_annonce, name='particulier_creer_annonce'),
    path('mon-compte/annonce/<int:annonce_id>/publiee/', views.annonce_publiee, name='annonce_publiee'),
    path('mon-compte/annonce/<int:annonce_id>/panneau/', views.annonce_panneau, name='annonce_panneau'),
    path('mon-compte/annonce/<int:annonce_id>/republier/', views.particulier_republier_annonce, name='particulier_republier_annonce'),
    path('mon-compte/annonce/<int:annonce_id>/modifier/', views.particulier_modifier_annonce, name='particulier_modifier_annonce'),
    path('mon-compte/annonce/<int:annonce_id>/supprimer/', views.particulier_supprimer_annonce, name='particulier_supprimer_annonce'),
    # Monitoring
    path('health/', views.health, name='health'),
    # PWA / application mobile
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw'),
    path('offline/', TemplateView.as_view(template_name='listings/offline.html'), name='offline'),
    path('.well-known/assetlinks.json', views.assetlinks, name='assetlinks'),
    # Pages legales
    path('cgu/', views.cgu, name='cgu'),
    path('cgv/', views.cgv, name='cgv'),
    path('desabonnement/', views.desabonnement, name='desabonnement'),
    path('api/pros-proches/', views.api_pros_proches, name='api_pros_proches'),
    path('api/demander-pro/', views.api_demander_pro, name='api_demander_pro'),
    path('guide-vendeur/', views.guide_vendeur, name='guide_vendeur'),
    path('guide-acheteur/', views.guide_acheteur, name='guide_acheteur'),
    path('guides/', views.guides, name='guides'),
    path('guide-agence/', views.guide_agence, name='guide_agence'),
    path('guide-pro/', views.guide_pro, name='guide_pro'),
    path('tutoriel-visite-3d/', views.tutoriel_visite_3d, name='tutoriel_visite_3d'),
    path('mentions-legales/', views.mentions_legales, name='mentions_legales'),
    path('confidentialite/', views.confidentialite, name='confidentialite'),
]
