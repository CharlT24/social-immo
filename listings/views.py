from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.db.models import Prefetch, Avg, Sum, Count, F, Value, FloatField
from django.db.models.functions import Cast
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.core.management import call_command
from django.views.decorators.http import require_POST
from datetime import timedelta
import json
import csv

from .models import (
    Annonce, Photo, Commentaire, Favori, Agence, Decoration, DecoCommentaire,
    Partenaire, ProProfile, ProRealisation, ProRealisationPhoto, ProAvis,
    PhotoFavori, PhotoNote, DemandeContact
)
from .forms import CommentaireForm, AgenceCreateForm, ProInscriptionForm, ProRealisationForm


def homepage(request):
    """Page d'accueil avec hero, recherche, dernieres arrivees"""
    total_annonces = Annonce.objects.filter(is_active=True).count()
    count_vente = Annonce.objects.filter(is_active=True, type_transaction='V').count()
    count_location = Annonce.objects.filter(is_active=True, type_transaction='L').count()

    # 6 dernieres annonces
    dernieres_annonces = Annonce.objects.filter(is_active=True).prefetch_related(
        Prefetch('photos', queryset=Photo.objects.order_by('ordre'))
    ).order_by('-created_at')[:6]

    # Villes populaires (top 12 par nombre d'annonces)
    villes_populaires = Annonce.objects.filter(
        is_active=True
    ).exclude(ville='').values('ville').annotate(
        count=Count('id')
    ).order_by('-count')[:12]

    # Favoris user
    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = list(Favori.objects.filter(
            user=request.user
        ).values_list('annonce_id', flat=True))

    context = {
        'total_annonces': total_annonces,
        'count_vente': count_vente,
        'count_location': count_location,
        'dernieres_annonces': dernieres_annonces,
        'villes_populaires': villes_populaires,
        'user_favorites': user_favorites,
    }
    return render(request, 'listings/homepage.html', context)


def search_results(request):
    """Page de resultats de recherche (SERP) avec filtres avances"""
    annonces = Annonce.objects.filter(is_active=True).prefetch_related(
        Prefetch('photos', queryset=Photo.objects.order_by('ordre'))
    )

    # Recuperer tous les parametres de filtre
    ville = request.GET.get('ville', '').strip()
    type_transaction = request.GET.get('type', '').strip()
    prix_min = request.GET.get('prix_min', '').strip()
    prix_max = request.GET.get('prix_max', '').strip()
    surface_min = request.GET.get('surface_min', '').strip()
    surface_max = request.GET.get('surface_max', '').strip()
    pieces_min = request.GET.get('pieces_min', '').strip()
    pieces_max = request.GET.get('pieces_max', '').strip()
    chambres_min = request.GET.get('chambres_min', '').strip()
    chambres_max = request.GET.get('chambres_max', '').strip()
    dpe_list = request.GET.getlist('dpe')
    tri = request.GET.get('tri', 'date').strip()

    # Appliquer les filtres
    if ville:
        annonces = annonces.filter(ville__icontains=ville)

    valid_types = ['V', 'L', 'S', 'F', 'B', 'W', 'G']
    if type_transaction in valid_types:
        annonces = annonces.filter(type_transaction=type_transaction)

    for param, lookup in [
        (prix_min, 'prix__gte'), (prix_max, 'prix__lte'),
        (surface_min, 'surface__gte'), (surface_max, 'surface__lte'),
        (pieces_min, 'nb_pieces__gte'), (pieces_max, 'nb_pieces__lte'),
        (chambres_min, 'nb_chambres__gte'), (chambres_max, 'nb_chambres__lte'),
    ]:
        if param:
            try:
                annonces = annonces.filter(**{lookup: int(param)})
            except ValueError:
                pass

    if dpe_list:
        valid_dpe = [d for d in dpe_list if d in 'ABCDEFG']
        if valid_dpe:
            annonces = annonces.filter(dpe_etiquette_conso__in=valid_dpe)

    # Tri
    sort_map = {
        'prix_asc': 'prix',
        'prix_desc': '-prix',
        'surface': '-surface',
        'date': '-created_at',
    }
    annonces = annonces.order_by(sort_map.get(tri, '-created_at'))

    result_count = annonces.count()

    # Villes pour autocomplete fallback
    villes_disponibles = Annonce.objects.filter(
        is_active=True
    ).exclude(ville='').values_list('ville', flat=True).distinct().order_by('ville')

    # Favoris
    user_favorites = []
    if request.user.is_authenticated:
        user_favorites = list(Favori.objects.filter(
            user=request.user
        ).values_list('annonce_id', flat=True))

    # Seuil "nouveau" = 7 jours
    seuil_nouveau = timezone.now() - timedelta(days=7)

    context = {
        'annonces': annonces,
        'result_count': result_count,
        'villes_disponibles': villes_disponibles,
        'user_favorites': user_favorites,
        'seuil_nouveau': seuil_nouveau,
        # Valeurs actuelles des filtres
        'current_ville': ville,
        'current_type': type_transaction,
        'current_prix_min': prix_min,
        'current_prix_max': prix_max,
        'current_surface_min': surface_min,
        'current_surface_max': surface_max,
        'current_pieces_min': pieces_min,
        'current_pieces_max': pieces_max,
        'current_chambres_min': chambres_min,
        'current_chambres_max': chambres_max,
        'current_dpe': dpe_list,
        'current_tri': tri,
    }
    return render(request, 'listings/search_results.html', context)


def autocomplete(request):
    """API autocomplete pour la recherche de villes"""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    cities = Annonce.objects.filter(
        is_active=True,
        ville__icontains=q
    ).exclude(ville='').values('ville').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    results = []
    for c in cities:
        results.append({
            'label': c['ville'],
            'value': c['ville'],
            'count': c['count'],
            'type': 'Ville',
        })

    return JsonResponse({'results': results})


def listing_detail(request, reference):
    """Vue détail : affiche une annonce spécifique avec commentaires"""
    annonce = get_object_or_404(
        Annonce.objects.prefetch_related('photos', 'commentaires__auteur'),
        reference=reference,
        is_active=True
    )

    # Gestion du formulaire de commentaire
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentaireForm(request.POST)
        if form.is_valid():
            commentaire = form.save(commit=False)
            commentaire.annonce = annonce
            commentaire.auteur = request.user
            commentaire.save()
            return redirect('listings:detail', reference=reference)
    else:
        form = CommentaireForm()

    context = {
        'annonce': annonce,
        'commentaires': annonce.commentaires.all(),
        'form': form,
    }
    return render(request, 'listings/listing_detail.html', context)


def signup(request):
    """Vue inscription : crée un nouveau compte utilisateur"""
    if request.user.is_authenticated:
        return redirect('listings:homepage')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('listings:homepage')
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})


@login_required
def dashboard(request):
    """Dashboard admin : stats et gestion"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Accès réservé aux administrateurs.")

    today = timezone.now().date()

    # Stats générales
    total_annonces = Annonce.objects.filter(is_active=True).count()
    stats = Annonce.objects.filter(is_active=True).aggregate(
        prix_moyen=Avg('prix'),
        valeur_totale=Sum('prix')
    )

    # Derniers commentaires (pour modération)
    derniers_commentaires = Commentaire.objects.select_related(
        'auteur', 'annonce'
    ).order_by('-created_at')[:5]

    # Annonces importées aujourd'hui
    annonces_aujourdhui = Annonce.objects.filter(
        created_at__date=today
    ).order_by('-created_at')

    # Dernières annonces (toutes)
    dernieres_annonces = Annonce.objects.filter(
        is_active=True
    ).order_by('-created_at')[:10]

    # Commentaires non lus (dernières 24h)
    hier = timezone.now() - timedelta(days=1)
    semaine = timezone.now() - timedelta(days=7)
    nouveaux_commentaires = Commentaire.objects.filter(
        created_at__gte=hier
    ).count()

    # Stats utilisateurs
    total_users = User.objects.count()
    total_pros = ProProfile.objects.filter(is_active=True).count()
    total_agences_count = Agence.objects.filter(is_active=True).count()
    nouveaux_users_semaine = User.objects.filter(date_joined__gte=semaine).count()
    derniers_users = User.objects.order_by('-date_joined')[:5]

    context = {
        'total_annonces': total_annonces,
        'prix_moyen': stats['prix_moyen'] or 0,
        'valeur_totale': stats['valeur_totale'] or 0,
        'derniers_commentaires': derniers_commentaires,
        'annonces_aujourdhui': annonces_aujourdhui,
        'dernieres_annonces': dernieres_annonces,
        'nouveaux_commentaires': nouveaux_commentaires,
        'total_users': total_users,
        'total_pros': total_pros,
        'total_agences_count': total_agences_count,
        'nouveaux_users_semaine': nouveaux_users_semaine,
        'derniers_users': derniers_users,
    }
    return render(request, 'listings/dashboard.html', context)


@login_required
def run_import(request):
    """Lance l'import XML manuellement depuis le flux HTTP"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Accès réservé aux administrateurs.")

    try:
        from io import StringIO
        out = StringIO()
        call_command('import_xml', stdout=out)
        output = out.getvalue()
        messages.success(request, f"Import XML terminé ! {output.split(chr(10))[-2] if output.strip() else ''}")
    except Exception as e:
        messages.error(request, f"Erreur lors de l'import : {str(e)}")

    return redirect('listings:dashboard')


@login_required
@require_POST
def toggle_favorite(request):
    """Toggle favori sur une annonce (AJAX)"""
    try:
        data = json.loads(request.body)
        annonce_id = data.get('annonce_id')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    annonce = get_object_or_404(Annonce, id=annonce_id)

    # Toggle: si existe -> supprimer, sinon -> créer
    favori, created = Favori.objects.get_or_create(
        user=request.user,
        annonce=annonce
    )

    if not created:
        # Le favori existait déjà, on le supprime
        favori.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({'liked': liked})


def decoration_list(request):
    """Vue inspirations : biens agences + realisations pro"""
    # Photos d'inspiration agences
    inspirations = Annonce.objects.filter(
        is_active=True, is_inspiration=True
    ).prefetch_related(
        Prefetch('photos', queryset=Photo.objects.order_by('ordre'))
    ).select_related().order_by('-updated_at')

    # Realisations pro
    realisations_pro = ProRealisation.objects.filter(
        is_active=True, pro__is_active=True
    ).prefetch_related('photos').select_related('pro').order_by('-created_at')

    # Filtrer par categorie
    current_categorie = request.GET.get('categorie', '').strip()
    if current_categorie:
        inspirations = inspirations.filter(inspiration_categorie=current_categorie)
        realisations_pro = realisations_pro.filter(categorie=current_categorie)

    # Source filter (agence / pro / all)
    source = request.GET.get('source', '').strip()

    # Categories disponibles
    cat_agent = set(Annonce.objects.filter(
        is_active=True, is_inspiration=True
    ).exclude(inspiration_categorie='').values_list('inspiration_categorie', flat=True))
    cat_pro = set(ProRealisation.objects.filter(
        is_active=True
    ).exclude(categorie='').values_list('categorie', flat=True))
    all_cats = cat_agent | cat_pro
    cat_choices = dict(Annonce.INSPIRATION_CHOICES)
    categories = [(c, cat_choices.get(c, c)) for c in sorted(all_cats)]

    # Favoris et notes de l'utilisateur
    user_photo_favs = set()
    user_photo_notes = {}
    if request.user.is_authenticated:
        user_photo_favs = set(PhotoFavori.objects.filter(
            user=request.user, photo__isnull=False
        ).values_list('photo_id', flat=True))
        user_photo_favs |= set(
            ('pro', pid) for pid in PhotoFavori.objects.filter(
                user=request.user, photo_pro__isnull=False
            ).values_list('photo_pro_id', flat=True)
        )
        for pn in PhotoNote.objects.filter(user=request.user):
            if pn.photo_id:
                user_photo_notes[('annonce', pn.photo_id)] = pn.note
            elif pn.photo_pro_id:
                user_photo_notes[('pro', pn.photo_pro_id)] = pn.note

    # Pros actifs pour le compteur
    total_pros = ProProfile.objects.filter(is_active=True).count()

    context = {
        'inspirations': inspirations if source != 'pro' else [],
        'realisations_pro': realisations_pro if source != 'agence' else [],
        'categories': categories,
        'current_categorie': current_categorie,
        'current_source': source,
        'user_photo_favs': user_photo_favs,
        'user_photo_notes': user_photo_notes,
        'total_pros': total_pros,
    }
    return render(request, 'listings/decoration_list.html', context)


def partenaire_list(request):
    """Vue liste des partenaires pro (admin-created + auto-registered)"""
    partenaires = Partenaire.objects.filter(is_active=True)
    pros = ProProfile.objects.filter(is_active=True).prefetch_related('realisations', 'avis')

    current_metier = request.GET.get('metier', '').strip()

    # Metiers from both sources
    metiers_partenaire = set(Partenaire.objects.filter(is_active=True).values_list('metier', flat=True))
    metiers_pro = set(ProProfile.objects.filter(is_active=True).values_list('metier', flat=True))
    metier_labels = dict(ProProfile.METIER_CHOICES)
    all_metiers = sorted(metiers_partenaire | {metier_labels.get(m, m) for m in metiers_pro})

    if current_metier:
        partenaires = partenaires.filter(metier=current_metier)
        # Match pro by choice value or display label
        pro_key = None
        for k, v in ProProfile.METIER_CHOICES:
            if v == current_metier or k == current_metier:
                pro_key = k
                break
        if pro_key:
            pros = pros.filter(metier=pro_key)
        else:
            pros = pros.none()

    context = {
        'partenaires': partenaires,
        'pros': pros,
        'metiers': all_metiers,
        'current_metier': current_metier,
    }
    return render(request, 'listings/partenaire_list.html', context)


@login_required
def agence_dashboard(request):
    """Dashboard pour une agence : gestion de ses biens (style leboncoin Pro)"""
    try:
        agence = Agence.objects.get(responsable=request.user)
    except Agence.DoesNotExist:
        if request.user.is_staff:
            return redirect('listings:dashboard')
        return HttpResponseForbidden("Vous n'etes pas rattache a une agence.")

    annonces = Annonce.objects.filter(
        client_reference=agence.reference
    ).prefetch_related('photos', 'commentaires', 'favoris').order_by('-updated_at')

    # Stats principales
    annonces_actives = annonces.filter(is_active=True)
    annonces_inactives = annonces.filter(is_active=False)
    total_annonces = annonces_actives.count()
    total_inactives = annonces_inactives.count()

    # KPI 7 derniers jours
    semaine = timezone.now() - timedelta(days=7)
    hier = timezone.now() - timedelta(days=1)

    messages_semaine = Commentaire.objects.filter(
        annonce__client_reference=agence.reference,
        created_at__gte=semaine
    ).count()

    messages_24h = Commentaire.objects.filter(
        annonce__client_reference=agence.reference,
        created_at__gte=hier
    ).count()

    favoris_semaine = Favori.objects.filter(
        annonce__client_reference=agence.reference,
        created_at__gte=semaine
    ).count()

    total_commentaires = Commentaire.objects.filter(
        annonce__client_reference=agence.reference
    ).count()

    total_favoris = Favori.objects.filter(
        annonce__client_reference=agence.reference
    ).count()

    # Annonces sans photo ou sans description (a modifier)
    annonces_a_modifier = annonces_actives.filter(
        models.Q(photos__isnull=True) | models.Q(texte='')
    ).distinct().count()

    # Annonces completes (optimisees)
    annonces_optimisees = total_annonces - annonces_a_modifier

    # Inspirations
    inspirations = annonces_actives.filter(is_inspiration=True)
    total_inspirations = inspirations.count()
    # Annonces avec photo eligible pour inspiration
    annonces_inspirables = annonces_actives.filter(photos__isnull=False).distinct()

    # Derniers commentaires
    derniers_commentaires = Commentaire.objects.filter(
        annonce__client_reference=agence.reference
    ).select_related('auteur', 'annonce').order_by('-created_at')[:10]

    # Dernieres annonces ajoutees/modifiees
    dernieres_annonces = annonces_actives.order_by('-updated_at')[:5]

    # Demandes de contact recues
    demandes_contact = DemandeContact.objects.filter(
        annonce__client_reference=agence.reference
    ).select_related('expediteur', 'annonce').order_by('-created_at')
    demandes_non_lues = demandes_contact.filter(is_read=False).count()

    context = {
        'agence': agence,
        'annonces': annonces,
        'total_annonces': total_annonces,
        'total_inactives': total_inactives,
        'messages_semaine': messages_semaine,
        'messages_24h': messages_24h,
        'favoris_semaine': favoris_semaine,
        'total_commentaires': total_commentaires,
        'total_favoris': total_favoris,
        'annonces_a_modifier': annonces_a_modifier,
        'annonces_optimisees': annonces_optimisees,
        'derniers_commentaires': derniers_commentaires,
        'dernieres_annonces': dernieres_annonces,
        'total_inspirations': total_inspirations,
        'annonces_inspirables': annonces_inspirables,
        'inspiration_choices': Annonce.INSPIRATION_CHOICES,
        'demandes_contact': demandes_contact,
        'demandes_non_lues': demandes_non_lues,
    }
    return render(request, 'listings/agence_dashboard.html', context)


@login_required
def agence_run_import(request):
    """Lance l'import XML pour une agence specifique"""
    try:
        agence = Agence.objects.get(responsable=request.user)
    except Agence.DoesNotExist:
        return HttpResponseForbidden("Agence non trouvee.")

    if not agence.feed_url:
        messages.error(request, "Aucune URL de flux configuree pour votre agence.")
        return redirect('listings:agence_dashboard')

    try:
        from io import StringIO
        out = StringIO()
        call_command('import_xml', url=agence.feed_url, stdout=out)
        agence.last_import = timezone.now()
        agence.save(update_fields=['last_import'])
        messages.success(request, "Import termine avec succes !")
    except Exception as e:
        messages.error(request, f"Erreur lors de l'import : {str(e)}")

    return redirect('listings:agence_dashboard')


@login_required
def gestion_agences(request):
    """Page de gestion admin : liste des agences + creation"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Acces reserve aux administrateurs.")

    agences = Agence.objects.all().select_related('responsable').order_by('-created_at')
    form = AgenceCreateForm()

    context = {
        'agences': agences,
        'form': form,
    }
    return render(request, 'listings/gestion_agences.html', context)


@login_required
def creer_agence(request):
    """Cree une agence + compte utilisateur + envoi mail"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Acces reserve aux administrateurs.")

    if request.method != 'POST':
        return redirect('listings:gestion_agences')

    form = AgenceCreateForm(request.POST)
    if form.is_valid():
        from django.contrib.auth.models import User
        from django.utils.crypto import get_random_string
        from django.core.mail import send_mail
        from django.conf import settings

        # Generer un mot de passe
        password = get_random_string(12, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#')

        # Creer le compte utilisateur
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            email=form.cleaned_data['email'],
            password=password,
        )

        # Creer l'agence
        agence = Agence.objects.create(
            nom=form.cleaned_data['nom_agence'],
            reference=form.cleaned_data['reference_agence'],
            feed_url=form.cleaned_data['feed_url'],
            feed_type=form.cleaned_data['feed_type'],
            logo_url=form.cleaned_data.get('logo_url', ''),
            contact_nom=form.cleaned_data.get('contact_nom', ''),
            contact_email=form.cleaned_data.get('contact_email', ''),
            contact_telephone=form.cleaned_data.get('contact_telephone', ''),
            adresse=form.cleaned_data.get('adresse', ''),
            responsable=user,
            is_active=True,
        )

        # Envoyer le mail
        site_url = request.build_absolute_uri('/')[:-1]
        subject = f"Bienvenue sur Social Immo - Vos acces Pro"
        message = f"""Bonjour {form.cleaned_data['contact_nom'] or form.cleaned_data['username']},

Votre espace professionnel Social Immo a ete cree avec succes.

Voici vos identifiants de connexion :

  Identifiant : {user.username}
  Mot de passe : {password}

Connectez-vous sur : {site_url}/mon-agence/

Votre flux XML est configure et pret a etre importe.

A bientot sur Social Immo !

--
L'equipe Social Immo
"""
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@social-immo.com',
                [form.cleaned_data['email']],
                fail_silently=False,
            )
            messages.success(request, f"Agence '{agence.nom}' creee ! Mail envoye a {user.email}")
        except Exception as e:
            messages.warning(request, f"Agence '{agence.nom}' creee, mais erreur d'envoi du mail : {e}. Identifiants: {user.username} / {password}")

        return redirect('listings:gestion_agences')
    else:
        agences = Agence.objects.all().select_related('responsable').order_by('-created_at')
        return render(request, 'listings/gestion_agences.html', {'agences': agences, 'form': form})


@login_required
def lancer_import_agence(request, agence_id):
    """Lance l'import XML pour une agence specifique (admin)"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Acces reserve aux administrateurs.")

    agence = get_object_or_404(Agence, id=agence_id)

    if not agence.feed_url:
        messages.error(request, f"Aucun flux configure pour {agence.nom}.")
        return redirect('listings:gestion_agences')

    try:
        from io import StringIO
        out = StringIO()
        call_command('import_xml', url=agence.feed_url, stdout=out)
        output = out.getvalue()
        agence.last_import = timezone.now()
        agence.save(update_fields=['last_import'])

        lines = output.strip().split('\n')
        last_line = lines[-1] if lines else ''
        messages.success(request, f"Import '{agence.nom}' termine ! {last_line}")
    except Exception as e:
        messages.error(request, f"Erreur import '{agence.nom}' : {str(e)}")

    return redirect('listings:gestion_agences')


@login_required
def toggle_agence_active(request, agence_id):
    """Active/desactive une agence"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Acces reserve aux administrateurs.")

    agence = get_object_or_404(Agence, id=agence_id)
    agence.is_active = not agence.is_active
    agence.save(update_fields=['is_active'])

    status = "activee" if agence.is_active else "desactivee"
    messages.success(request, f"Agence '{agence.nom}' {status}.")
    return redirect('listings:gestion_agences')


@login_required
def renvoyer_acces(request, agence_id):
    """Regenere un mot de passe et renvoie les acces par mail"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Acces reserve aux administrateurs.")

    from django.utils.crypto import get_random_string
    from django.core.mail import send_mail
    from django.conf import settings

    agence = get_object_or_404(Agence, id=agence_id)

    if not agence.responsable:
        messages.error(request, f"Aucun responsable associe a {agence.nom}.")
        return redirect('listings:gestion_agences')

    user = agence.responsable

    if not user.email:
        messages.error(request, f"Le responsable {user.username} n'a pas d'adresse email.")
        return redirect('listings:gestion_agences')

    # Nouveau mot de passe
    password = get_random_string(12, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#')
    user.set_password(password)
    user.save()

    site_url = request.build_absolute_uri('/')[:-1]
    subject = "Social Immo - Vos nouveaux acces Pro"
    message = f"""Bonjour {agence.contact_nom or user.username},

Vos identifiants de connexion Social Immo ont ete reinitialises.

Voici vos nouveaux acces :

  Identifiant : {user.username}
  Mot de passe : {password}

Connectez-vous sur : {site_url}/mon-agence/

A bientot sur Social Immo !

--
L'equipe Social Immo
"""
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        messages.success(request, f"Nouveaux acces envoyes a {user.email} pour '{agence.nom}'.")
    except Exception as e:
        messages.warning(request, f"Erreur d'envoi du mail : {e}. Identifiants: {user.username} / {password}")

    return redirect('listings:gestion_agences')


@login_required
@require_POST
def toggle_inspiration(request):
    """Toggle le statut inspiration d'une annonce (AJAX, pour agences)"""
    try:
        data = json.loads(request.body)
        annonce_id = data.get('annonce_id')
        categorie = data.get('categorie', '')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    annonce = get_object_or_404(Annonce, id=annonce_id)

    # Verifier que l'utilisateur est responsable de l'agence qui possede ce bien
    try:
        agence = Agence.objects.get(responsable=request.user)
        if annonce.client_reference != agence.reference:
            return JsonResponse({'error': 'Non autorise'}, status=403)
    except Agence.DoesNotExist:
        if not request.user.is_staff:
            return JsonResponse({'error': 'Non autorise'}, status=403)

    # Si on envoie une categorie, on active l'inspiration avec cette categorie
    if categorie:
        annonce.is_inspiration = True
        annonce.inspiration_categorie = categorie
        annonce.save(update_fields=['is_inspiration', 'inspiration_categorie'])
    else:
        annonce.is_inspiration = not annonce.is_inspiration
        if not annonce.is_inspiration:
            annonce.inspiration_categorie = ''
        annonce.save(update_fields=['is_inspiration', 'inspiration_categorie'])

    return JsonResponse({
        'is_inspiration': annonce.is_inspiration,
        'categorie': annonce.inspiration_categorie,
    })


# ============================================================
# ESPACE PRO (decorateurs, artisans, etc.)
# ============================================================

def pro_inscription(request):
    """Inscription pro : cree un compte + profil en une etape"""
    if request.user.is_authenticated:
        try:
            request.user.pro_profile
            return redirect('listings:pro_dashboard')
        except ProProfile.DoesNotExist:
            pass

    if request.method == 'POST':
        form = ProInscriptionForm(request.POST)
        if form.is_valid():
            from django.contrib.auth.models import User

            user = User.objects.create_user(
                username=form.cleaned_data['email'].split('@')[0],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
            )

            ProProfile.objects.create(
                user=user,
                nom_entreprise=form.cleaned_data['nom_entreprise'],
                metier=form.cleaned_data['metier'],
                description=form.cleaned_data.get('description', ''),
                telephone=form.cleaned_data.get('telephone', ''),
                ville=form.cleaned_data.get('ville', ''),
                site_web=form.cleaned_data.get('site_web', ''),
                email=form.cleaned_data['email'],
            )

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('listings:pro_dashboard')
    else:
        form = ProInscriptionForm()

    return render(request, 'listings/pro_inscription.html', {'form': form})


@login_required
def pro_dashboard(request):
    """Dashboard pro : realisations, avis, demandes de contact"""
    try:
        pro = request.user.pro_profile
    except ProProfile.DoesNotExist:
        return redirect('listings:pro_inscription')

    realisations = pro.realisations.filter(is_active=True).prefetch_related('photos')
    avis = pro.avis.select_related('auteur').all()
    demandes = pro.demandes_contact.select_related('expediteur').all()

    demandes_non_lues = demandes.filter(is_read=False).count()

    # Stats
    from django.db.models import Avg, Count
    total_realisations = realisations.count()
    total_photos = ProRealisationPhoto.objects.filter(
        realisation__pro=pro, realisation__is_active=True
    ).count()
    note_moyenne = pro.note_moyenne
    total_avis = pro.nb_avis
    total_favoris = PhotoFavori.objects.filter(
        photo_pro__realisation__pro=pro
    ).count()

    context = {
        'pro': pro,
        'realisations': realisations,
        'avis': avis,
        'demandes': demandes,
        'demandes_non_lues': demandes_non_lues,
        'total_realisations': total_realisations,
        'total_photos': total_photos,
        'note_moyenne': note_moyenne,
        'total_avis': total_avis,
        'total_favoris': total_favoris,
        'inspiration_choices': Annonce.INSPIRATION_CHOICES,
    }
    return render(request, 'listings/pro_dashboard.html', context)


@login_required
def pro_ajouter_realisation(request):
    """Ajout d'une realisation par un pro"""
    try:
        pro = request.user.pro_profile
    except ProProfile.DoesNotExist:
        return redirect('listings:pro_inscription')

    if request.method == 'POST':
        form = ProRealisationForm(request.POST)
        if form.is_valid():
            realisation = ProRealisation.objects.create(
                pro=pro,
                titre=form.cleaned_data['titre'],
                description=form.cleaned_data.get('description', ''),
                categorie=form.cleaned_data.get('categorie', ''),
            )
            # Parser les URLs de photos (une par ligne)
            urls_raw = form.cleaned_data['photo_urls']
            for i, line in enumerate(urls_raw.strip().split('\n'), 1):
                url = line.strip()
                if url and url.startswith('http'):
                    ProRealisationPhoto.objects.create(
                        realisation=realisation,
                        url=url,
                        ordre=i
                    )
            messages.success(request, f'Realisation "{realisation.titre}" ajoutee !')
            return redirect('listings:pro_dashboard')
    else:
        form = ProRealisationForm()

    return render(request, 'listings/pro_ajouter_realisation.html', {'form': form})


@login_required
@require_POST
def pro_supprimer_realisation(request, realisation_id):
    """Supprime une realisation (soft delete)"""
    try:
        pro = request.user.pro_profile
    except ProProfile.DoesNotExist:
        return JsonResponse({'error': 'Non autorise'}, status=403)

    realisation = get_object_or_404(ProRealisation, id=realisation_id, pro=pro)
    realisation.is_active = False
    realisation.save(update_fields=['is_active'])
    messages.success(request, f'Realisation "{realisation.titre}" supprimee.')
    return redirect('listings:pro_dashboard')


def pro_profil(request, pro_id):
    """Page publique d'un professionnel"""
    pro = get_object_or_404(ProProfile, id=pro_id, is_active=True)
    realisations = pro.realisations.filter(is_active=True).prefetch_related('photos')
    avis = pro.avis.select_related('auteur').all()

    # Verifier si l'utilisateur a deja laisse un avis
    user_avis = None
    if request.user.is_authenticated:
        user_avis = ProAvis.objects.filter(pro=pro, auteur=request.user).first()

    context = {
        'pro': pro,
        'realisations': realisations,
        'avis': avis,
        'user_avis': user_avis,
    }
    return render(request, 'listings/pro_profil.html', context)


# ============================================================
# APIS SOCIALES (AJAX)
# ============================================================

@login_required
@require_POST
def toggle_photo_favori(request):
    """Toggle favori sur une photo (annonce ou pro)"""
    try:
        data = json.loads(request.body)
        photo_id = data.get('photo_id')
        photo_type = data.get('type', 'annonce')  # 'annonce' ou 'pro'
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    if photo_type == 'pro':
        photo = get_object_or_404(ProRealisationPhoto, id=photo_id)
        fav, created = PhotoFavori.objects.get_or_create(
            user=request.user, photo_pro=photo
        )
    else:
        photo = get_object_or_404(Photo, id=photo_id)
        fav, created = PhotoFavori.objects.get_or_create(
            user=request.user, photo=photo
        )

    if not created:
        fav.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({'liked': liked})


@login_required
@require_POST
def rate_photo(request):
    """Note une photo 1-5 etoiles"""
    try:
        data = json.loads(request.body)
        photo_id = data.get('photo_id')
        note = int(data.get('note', 0))
        photo_type = data.get('type', 'annonce')
    except (json.JSONDecodeError, KeyError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    if note < 1 or note > 5:
        return JsonResponse({'error': 'Note must be 1-5'}, status=400)

    if photo_type == 'pro':
        photo = get_object_or_404(ProRealisationPhoto, id=photo_id)
        obj, created = PhotoNote.objects.update_or_create(
            user=request.user, photo_pro=photo,
            defaults={'note': note}
        )
        avg = PhotoNote.objects.filter(photo_pro=photo).aggregate(
            avg=models.Avg('note'), count=models.Count('id')
        )
    else:
        photo = get_object_or_404(Photo, id=photo_id)
        obj, created = PhotoNote.objects.update_or_create(
            user=request.user, photo=photo,
            defaults={'note': note}
        )
        avg = PhotoNote.objects.filter(photo=photo).aggregate(
            avg=models.Avg('note'), count=models.Count('id')
        )

    return JsonResponse({
        'note': note,
        'average': round(avg['avg'], 1) if avg['avg'] else note,
        'count': avg['count'],
    })


@login_required
@require_POST
def envoyer_contact(request):
    """Envoie une demande de contact a un agent ou pro"""
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        telephone = data.get('telephone', '').strip()
        annonce_id = data.get('annonce_id')
        pro_id = data.get('pro_id')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    if not message_text:
        return JsonResponse({'error': 'Message requis'}, status=400)

    demande = DemandeContact(
        expediteur=request.user,
        message=message_text,
        telephone=telephone,
    )

    if annonce_id:
        demande.annonce = get_object_or_404(Annonce, id=annonce_id)
    elif pro_id:
        demande.pro = get_object_or_404(ProProfile, id=pro_id)
    else:
        return JsonResponse({'error': 'Cible requise'}, status=400)

    demande.save()
    return JsonResponse({'success': True})


@login_required
@require_POST
def submit_pro_avis(request):
    """Soumet un avis sur un pro"""
    try:
        data = json.loads(request.body)
        pro_id = data.get('pro_id')
        note = int(data.get('note', 0))
        commentaire = data.get('commentaire', '').strip()
    except (json.JSONDecodeError, KeyError, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    if note < 1 or note > 5:
        return JsonResponse({'error': 'Note must be 1-5'}, status=400)

    pro = get_object_or_404(ProProfile, id=pro_id)

    if request.user == pro.user:
        return JsonResponse({'error': 'Vous ne pouvez pas vous auto-evaluer'}, status=400)

    avis, created = ProAvis.objects.update_or_create(
        pro=pro, auteur=request.user,
        defaults={'note': note, 'commentaire': commentaire}
    )

    return JsonResponse({
        'success': True,
        'note_moyenne': pro.note_moyenne,
        'nb_avis': pro.nb_avis,
    })


@login_required
@require_POST
def mark_contact_read(request):
    """Marque une demande de contact comme lue"""
    try:
        data = json.loads(request.body)
        demande_id = data.get('demande_id')
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    demande = get_object_or_404(DemandeContact, id=demande_id)

    # Verifier que l'utilisateur est bien le destinataire
    is_owner = False
    if demande.annonce:
        try:
            agence = Agence.objects.get(responsable=request.user)
            is_owner = demande.annonce.client_reference == agence.reference
        except Agence.DoesNotExist:
            pass
    elif demande.pro:
        is_owner = demande.pro.user == request.user

    if not is_owner and not request.user.is_staff:
        return JsonResponse({'error': 'Non autorise'}, status=403)

    demande.is_read = True
    demande.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@login_required
def gestion_utilisateurs(request):
    """Liste de tous les utilisateurs avec filtre par role"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Acces reserve aux administrateurs.")

    role_filter = request.GET.get('role', '').strip()

    users = User.objects.all().prefetch_related('agence').order_by('-date_joined')

    # Pre-fetch pro profiles
    pro_user_ids = set(ProProfile.objects.values_list('user_id', flat=True))
    pro_profiles = {p.user_id: p for p in ProProfile.objects.all()}

    # Build user list with roles
    users_data = []
    for u in users:
        # Determine role
        role = 'client'
        role_label = 'Client'
        pro = pro_profiles.get(u.id)
        agence = u.agence.first() if u.agence.exists() else None

        if u.is_staff:
            role = 'admin'
            role_label = 'Admin'
        elif pro:
            role = 'pro'
            role_label = 'Pro - ' + pro.get_metier_display()
        elif agence:
            role = 'agence'
            role_label = 'Agence - ' + agence.nom

        if role_filter and role != role_filter:
            continue

        users_data.append({
            'user': u,
            'role': role,
            'role_label': role_label,
            'pro_profile': pro,
            'agence': agence,
        })

    # Stats
    total_users = User.objects.count()
    total_clients = User.objects.filter(is_staff=False).exclude(
        id__in=ProProfile.objects.values_list('user_id', flat=True)
    ).exclude(
        id__in=Agence.objects.values_list('responsable_id', flat=True)
    ).count()
    total_pros = ProProfile.objects.count()
    total_agences = Agence.objects.count()

    context = {
        'users_data': users_data,
        'current_role': role_filter,
        'total_users': total_users,
        'total_clients': total_clients,
        'total_pros': total_pros,
        'total_agences': total_agences,
    }
    return render(request, 'listings/gestion_utilisateurs.html', context)


@login_required
def export_utilisateurs_csv(request):
    """Export CSV de tous les utilisateurs"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Acces reserve aux administrateurs.")

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="utilisateurs_social_immo.csv"'
    response.write('\ufeff')  # BOM for Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Username', 'Email', 'Role', 'Detail', 'Ville', 'Telephone', 'Date inscription', 'Derniere connexion'])

    users = User.objects.all().prefetch_related('agence').order_by('-date_joined')
    pro_profiles = {p.user_id: p for p in ProProfile.objects.all()}

    for u in users:
        role = 'Client'
        detail = ''
        ville = ''
        telephone = ''
        pro = pro_profiles.get(u.id)

        if u.is_staff:
            role = 'Admin'
        elif pro:
            role = 'Pro'
            detail = pro.nom_entreprise + ' (' + pro.get_metier_display() + ')'
            ville = pro.ville
            telephone = pro.telephone
        elif u.agence.exists():
            agence = u.agence.first()
            role = 'Agence'
            detail = agence.nom
            ville = getattr(agence, 'adresse', '')
            telephone = getattr(agence, 'contact_telephone', '')

        writer.writerow([
            u.username,
            u.email,
            role,
            detail,
            ville,
            telephone,
            u.date_joined.strftime('%d/%m/%Y %H:%M'),
            u.last_login.strftime('%d/%m/%Y %H:%M') if u.last_login else 'Jamais',
        ])

    return response


def cgu(request):
    return render(request, 'listings/cgu.html')


def mentions_legales(request):
    return render(request, 'listings/mentions_legales.html')


def confidentialite(request):
    return render(request, 'listings/confidentialite.html')
