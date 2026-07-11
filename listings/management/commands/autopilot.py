"""
AUTOPILOT — la commande unique qui fait vivre le site sans intervention.

A configurer en CRON quotidien sur o2switch (ex. 6h du matin) :
    python manage.py autopilot

Elle enchaine, avec tolerance aux pannes (une etape qui echoue n'arrete
pas les autres) :
  1. Import des flux XML de toutes les agences actives
  2. Geocodage des nouvelles villes (carte)
  3. Envoi des alertes email acheteurs
  4. Generation des miniatures manquantes
  5. Expiration des annonces particuliers anciennes (+ email de relance)
  6. Expiration des boosts Pack Vendeur arrives a terme
  7. Le lundi : rapport hebdomadaire aux vendeurs
  8. Sauvegarde de la base (7 jours de retention)
  9. Rapport complet a l'admin par email
"""
import gzip
import io
import traceback
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

ANNONCE_DUREE_JOURS = 60
BACKUPS_RETENTION = 7


class Command(BaseCommand):
    help = "Pilote automatique quotidien : imports, alertes, entretien, sauvegarde, rapport"

    def add_arguments(self, parser):
        parser.add_argument('--site-url', default='https://social-immo.com')
        parser.add_argument('--sans-import', action='store_true',
                            help="Saute l'import XML (tests)")

    def handle(self, *args, **options):
        site = options['site_url'].rstrip('/')
        rapport = []
        erreurs = []

        def etape(nom, fonction):
            try:
                resultat = fonction()
                rapport.append(f"[OK] {nom}" + (f" — {resultat}" if resultat else ""))
            except Exception as e:
                erreurs.append(f"[ERREUR] {nom} : {e}\n{traceback.format_exc(limit=3)}")
                rapport.append(f"[ERREUR] {nom} : {e}")

        # 1. Imports XML
        if not options['sans_import']:
            etape('Import flux agences', lambda: self._capture(
                call_command, 'import_xml', '--all-agences'))

        # 2. Geocodage
        etape('Geocodage villes', lambda: self._capture(call_command, 'geocoder_villes'))

        # 3. Alertes acheteurs
        etape('Alertes email', lambda: self._capture(
            call_command, 'envoyer_alertes', '--site-url', site))

        # 3b. Alertes baisse de prix sur les favoris
        etape('Alertes favoris (baisse de prix)', lambda: self._capture(
            call_command, 'alertes_favoris', '--site-url', site))

        # 4. Miniatures
        etape('Miniatures', lambda: self._capture(call_command, 'generer_miniatures'))

        # 4b. Pre-chauffage DVF (communes demandees + communes des annonces)
        etape('Pre-chauffage DVF', self._prechauffer_dvf)

        # 4c. Re-verification des SIRET pros (badges Verifie a jour)
        etape('Verification SIRET pros', lambda: self._capture(
            call_command, 'reverifier_siret'))

        # 5. Expiration des annonces particuliers
        etape('Expiration annonces particuliers', lambda: self._expirer_annonces(site))

        # 6. Expiration des boosts
        etape('Expiration boosts Pack Vendeur', self._expirer_boosts)

        # 7. Rapport hebdo vendeurs (le lundi)
        if date.today().weekday() == 0:
            etape('Rapport hebdo vendeurs', lambda: self._capture(
                call_command, 'rapport_vendeurs', '--site-url', site))

        # 7a. Rapport mensuel de performance aux partenaires (le 1er du mois) :
        # retention agences & artisans -> ils restent et recommandent.
        if date.today().day == 1:
            etape('Rapport mensuel partenaires', lambda: self._rapport_partenaires(site))

        # 6b. Machine a leads : relance des estimations sans suite
        etape('Relance estimations', lambda: self._relancer_estimations(site))

        # 6c. Resume des leads pour l'admin (24h)
        etape('Leads (24h)', self._resume_leads)

        # 7b. Purge des vieilles pages vues (analytics : retention 90 j)
        etape('Purge analytics (90j)', self._purger_pagevues)

        # 8. Sauvegarde
        etape('Sauvegarde base', self._sauvegarde)

        # 9. Rapport admin
        corps = (f"Autopilot Social Immo — {timezone.now():%d/%m/%Y %H:%M}\n\n"
                 + "\n".join(rapport))
        if erreurs:
            corps += "\n\n===== DETAILS DES ERREURS =====\n\n" + "\n\n".join(erreurs)
        self.stdout.write(corps)

        admins = getattr(settings, 'ADMINS', [])
        if admins:
            try:
                send_mail(
                    subject=f"[Autopilot] {'⚠ ' + str(len(erreurs)) + ' erreur(s)' if erreurs else 'OK'} — Social Immo {timezone.now():%d/%m}",
                    message=corps,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admins[0][1]],
                    fail_silently=True,
                )
            except Exception:
                pass

    # ===== Etapes internes =====

    def _capture(self, fn, *args, **kwargs):
        """Execute une commande en capturant sa sortie (derniere ligne)."""
        out = io.StringIO()
        fn(*args, stdout=out, stderr=out, **kwargs)
        lignes = [l for l in out.getvalue().strip().splitlines() if l.strip()]
        return lignes[-1] if lignes else ''

    def _expirer_annonces(self, site):
        """Desactive les annonces particuliers de plus de 60 jours et
        envoie un email de relance avec la marche a suivre pour republier."""
        from listings.models import Annonce
        seuil = timezone.now() - timedelta(days=ANNONCE_DUREE_JOURS)
        anciennes = Annonce.objects.filter(
            source='particulier', is_active=True,
            updated_at__lt=seuil, user__isnull=False,
        ).select_related('user')
        n = 0
        for annonce in anciennes:
            annonce.is_active = False
            annonce.save(update_fields=['is_active'])
            n += 1
            if annonce.user.email:
                try:
                    send_mail(
                        subject='[Social Immo] Votre annonce est en pause — toujours en vente ?',
                        message=(
                            f'Bonjour {annonce.user.first_name or annonce.user.username},\n\n'
                            f'Votre annonce "{annonce.titre[:60]}" a plus de {ANNONCE_DUREE_JOURS} jours : '
                            f'nous l\'avons mise en pause pour garder le site a jour.\n\n'
                            f'Toujours en vente ? Republiez-la en 1 clic depuis votre compte :\n'
                            f'{site}/mon-compte/\n\n'
                            f'Bien vendu ? Felicitations ! Vous n\'avez rien a faire.\n\n'
                            f"L'equipe Social Immo"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[annonce.user.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
        return f'{n} annonce(s) mise(s) en pause'

    def _prechauffer_dvf(self):
        """Telecharge les ventes DVF des communes les plus utiles pour que
        l'estimation web soit instantanee (elle ne sert que le cache)."""
        from django.core.cache import cache
        from listings.models import Annonce
        from listings.services.dvf import rafraichir_commune

        # 1. Assurer l'existence de la table de cache (idempotent)
        try:
            call_command('createcachetable', verbosity=0)
        except Exception:
            pass

        communes = []
        # Communes explicitement demandees par des visiteurs (non cachees)
        try:
            for cle in cache.get('dvf:a_rechauffer', []):
                ville, _, cp = cle.partition('|')
                if ville:
                    communes.append((ville, cp))
            cache.delete('dvf:a_rechauffer')
        except Exception:
            pass
        # + communes des annonces actives (vente, maison/appart)
        for ville, cp in (Annonce.objects.filter(is_active=True, type_transaction='V')
                          .exclude(ville='').values_list('ville', 'code_postal').distinct()[:200]):
            if (ville, cp or '') not in communes:
                communes.append((ville, cp or ''))

        n = 0
        for ville, cp in communes[:250]:
            try:
                if rafraichir_commune(ville, cp, autoriser_telechargement=True):
                    n += 1
            except Exception:
                continue
        return f'{n} commune(s) rafraichie(s)'

    def _expirer_boosts(self):
        """Retire la mise en avant des Pack Vendeur arrives a terme."""
        from listings.models import Abonnement, Annonce
        finis = Abonnement.objects.filter(
            type_abonnement__in=['pack_vendeur', 'vendeur_alaune_7', 'vendeur_alaune_30'],
            statut='actif', date_fin__isnull=False, date_fin__lt=timezone.now(),
        )
        n = 0
        for abo in finis:
            if abo.annonce_id:
                Annonce.objects.filter(id=abo.annonce_id).update(mise_en_avant=False)
            abo.statut = 'resilie'
            abo.save(update_fields=['statut'])
            n += 1
        return f'{n} boost(s) expire(s)'

    def _relancer_estimations(self, site):
        """Relance UNE fois les prospects d'estimation sans suite (3-14 jours),
        avec consentement recueilli au formulaire. Email utile, non intrusif."""
        from listings.models import Estimation
        debut = timezone.now() - timedelta(days=14)
        fin = timezone.now() - timedelta(days=3)
        prospects = Estimation.objects.filter(
            is_treated=False, relance_envoyee=False,
            created_at__gte=debut, created_at__lte=fin,
        ).exclude(email='')
        from listings.services.emails import envoyer_email_prospection
        n = 0
        for e in prospects:
            corps = (
                f"Bonjour {e.nom or ''},\n\n"
                f"Il y a quelques jours, vous avez estime votre bien a {e.ville}. "
                f"Ou en etes-vous dans votre projet ?\n\n"
                f"Pour vendre au meilleur prix, un professionnel de votre secteur "
                f"peut vous accompagner gratuitement (visite, prix de marche, diffusion). "
                f"Il vous suffit de repondre a cet email et nous vous mettons en relation.\n\n"
                f"Vous pouvez aussi affiner votre estimation ici :\n{site}/estimer/\n\n"
                f"L'equipe Social Immo\n\n"
                f"— Vous recevez cet email car vous avez demande une estimation.")
            envoye = envoyer_email_prospection(
                '[Social Immo] Votre projet immobilier avance ?', corps, e.email, site)
            # On marque comme traitee dans tous les cas (desabonne inclus) pour
            # ne pas reessayer chaque jour.
            e.relance_envoyee = True
            e.save(update_fields=['relance_envoyee'])
            if envoye:
                n += 1
        return f'{n} relance(s) envoyee(s)'

    def _rapport_partenaires(self, site):
        """Rapport mensuel de performance aux pros et agences (retention).
        On n'envoie que s'il y a quelque chose a dire (jamais un email vide)."""
        from listings.models import (ProProfile, Agence, DemandeContact,
                                     PhotoFavori, Annonce)
        from listings.services.emails import envoyer_email_prospection
        depuis = timezone.now() - timedelta(days=30)
        n = 0

        # Artisans / pros
        for pro in ProProfile.objects.filter(is_active=True).select_related('user'):
            email = pro.email or (pro.user.email if pro.user_id else '')
            if not email:
                continue
            nb_real = pro.realisations.filter(is_active=True).count()
            favoris = PhotoFavori.objects.filter(
                photo_pro__realisation__pro=pro, created_at__gte=depuis).count()
            contacts = pro.demandes_contact.filter(created_at__gte=depuis).count()
            if nb_real == 0 and favoris == 0 and contacts == 0:
                continue
            corps = (
                f"Bonjour {pro.nom_entreprise},\n\n"
                f"Votre activite sur Social Immo ces 30 derniers jours :\n"
                f"  - Realisations en ligne : {nb_real}\n"
                f"  - Photos mises en favori : {favoris}\n"
                f"  - Demandes de contact recues : {contacts}\n\n"
                f"Ajoutez des realisations pour gagner en visibilite :\n{site}/pro/dashboard/\n\n"
                f"L'equipe Social Immo")
            if envoyer_email_prospection('[Social Immo] Votre bilan du mois', corps, email, site):
                n += 1

        # Agences
        for agence in Agence.objects.filter(is_active=True).select_related('responsable'):
            email = (agence.responsable.email if agence.responsable_id else '') or agence.contact_email
            if not email:
                continue
            nb_annonces = Annonce.objects.filter(agence=agence, is_active=True).count()
            contacts = DemandeContact.objects.filter(
                annonce__agence=agence, created_at__gte=depuis).count()
            if nb_annonces == 0 and contacts == 0:
                continue
            corps = (
                f"Bonjour {agence.nom},\n\n"
                f"Votre activite sur Social Immo ces 30 derniers jours :\n"
                f"  - Annonces en ligne : {nb_annonces}\n"
                f"  - Demandes de contact recues : {contacts}\n\n"
                f"Gerez vos annonces et votre vitrine :\n{site}/mon-agence/\n\n"
                f"L'equipe Social Immo")
            if envoyer_email_prospection('[Social Immo] Le bilan mensuel de votre agence', corps, email, site):
                n += 1

        return f'{n} rapport(s) partenaire envoye(s)'

    def _resume_leads(self):
        """Compte les leads des dernieres 24h (visible dans le rapport admin)."""
        from listings.models import Estimation, DemandeContact, DemandeAgence
        depuis = timezone.now() - timedelta(hours=24)
        est = Estimation.objects.filter(created_at__gte=depuis).count()
        contacts = DemandeContact.objects.filter(created_at__gte=depuis).count()
        agences = DemandeAgence.objects.filter(created_at__gte=depuis).count()
        total = est + contacts + agences
        return f'{total} lead(s) : {est} estimation(s), {contacts} contact(s), {agences} agence(s)'

    def _purger_pagevues(self):
        """Supprime les pages vues de plus de 90 jours (le cockpit ne montre
        que 30 j ; on garde 90 j de marge). Evite que la table gonfle."""
        from listings.models import PageVue
        seuil = timezone.now() - timedelta(days=90)
        n, _ = PageVue.objects.filter(created_at__lt=seuil).delete()
        return f'{n} page(s) vue(s) purgee(s)'

    def _sauvegarde(self):
        """Dump JSON gzip de la base (retention 7 fichiers). Ecrit en FLUX
        direct dans le gzip (pas de gros StringIO en memoire) et exclut les
        tables 'cache' volumineuses et re-telechargeables (DVF, analytics)."""
        dossier = Path(settings.BASE_DIR) / 'backups'
        dossier.mkdir(exist_ok=True)
        fichier = dossier / f'backup-{timezone.now():%Y%m%d-%H%M}.json.gz'
        with gzip.open(fichier, 'wt', encoding='utf-8') as f:
            call_command('dumpdata', '--natural-foreign', '--natural-primary',
                         '-e', 'contenttypes', '-e', 'auth.permission',
                         '-e', 'sessions', '-e', 'admin.logentry',
                         '-e', 'listings.pagevue',      # analytics (re-genere)
                         '-e', 'listings.ventedvf',     # cache DVF volumineux (re-telecharge)
                         '-e', 'listings.communedvf',   # cache DVF (re-telecharge)
                         stdout=f)
        # Rotation
        sauvegardes = sorted(dossier.glob('backup-*.json.gz'))
        for ancien in sauvegardes[:-BACKUPS_RETENTION]:
            ancien.unlink()
        taille = fichier.stat().st_size // 1024
        return f'{fichier.name} ({taille} Ko), {min(len(sauvegardes), BACKUPS_RETENTION)} conservee(s)'
