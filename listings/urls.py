from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.listing_list, name='list'),
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
]
