from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.listing_list, name='list'),
    path('annonce/<str:reference>/', views.listing_detail, name='detail'),
    path('signup/', views.signup, name='signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/import/', views.run_import, name='run_import'),
    path('api/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),
]
