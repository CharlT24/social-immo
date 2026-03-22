from django.shortcuts import render, get_object_or_404, redirect
from django.db import models
from django.db.models import Prefetch, Avg, Sum, Count, F, Value, FloatField
from django.db.models.functions import Cast
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.core.management import call_command
from django.views.decorators.http import require_POST
from datetime import timedelta
import json

from .models import Annonce, Photo, Commentaire, Favori, Agence, Decoration, DecoCommentaire, Partenaire
from .forms import CommentaireForm, AgenceCreateForm


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
    nouveaux_commentaires = Commentaire.objects.filter(
        created_at__gte=hier
    ).count()

    context = {
        'total_annonces': total_annonces,
        'prix_moyen': stats['prix_moyen'] or 0,
        'valeur_totale': stats['valeur_totale'] or 0,
        'derniers_commentaires': derniers_commentaires,
        'annonces_aujourdhui': annonces_aujourdhui,
        'dernieres_annonces': dernieres_annonces,
        'nouveaux_commentaires': nouveaux_commentaires,
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
    """Vue inspirations : biens selectionnes par les agences"""
    inspirations = Annonce.objects.filter(
        is_active=True, is_inspiration=True
    ).prefetch_related(
        Prefetch('photos', queryset=Photo.objects.order_by('ordre'))
    ).select_related().order_by('-updated_at')

    # Filtrer par categorie
    current_categorie = request.GET.get('categorie', '').strip()
    if current_categorie:
        inspirations = inspirations.filter(inspiration_categorie=current_categorie)

    # Categories disponibles (avec au moins 1 bien)
    categories_dispo = Annonce.objects.filter(
        is_active=True, is_inspiration=True
    ).exclude(inspiration_categorie='').values_list(
        'inspiration_categorie', flat=True
    ).distinct()
    # Convertir en liste de tuples (code, label)
    cat_choices = dict(Annonce.INSPIRATION_CHOICES)
    categories = [(c, cat_choices.get(c, c)) for c in categories_dispo]

    return render(request, 'listings/decoration_list.html', {
        'inspirations': inspirations,
        'categories': categories,
        'current_categorie': current_categorie,
    })


def partenaire_list(request):
    """Vue liste des partenaires pro"""
    partenaires = Partenaire.objects.filter(is_active=True)
    metiers = Partenaire.objects.filter(is_active=True).values_list('metier', flat=True).distinct().order_by('metier')

    current_metier = request.GET.get('metier', '').strip()
    if current_metier:
        partenaires = partenaires.filter(metier=current_metier)

    context = {
        'partenaires': partenaires,
        'metiers': metiers,
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
