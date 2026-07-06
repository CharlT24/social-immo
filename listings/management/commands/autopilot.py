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
            type_abonnement='pack_vendeur', statut='actif',
            date_fin__isnull=False, date_fin__lt=timezone.now(),
        )
        n = 0
        for abo in finis:
            if abo.annonce_id:
                Annonce.objects.filter(id=abo.annonce_id).update(mise_en_avant=False)
            abo.statut = 'resilie'
            abo.save(update_fields=['statut'])
            n += 1
        return f'{n} boost(s) expire(s)'

    def _sauvegarde(self):
        """Dump JSON gzip de la base, retention de 7 fichiers."""
        dossier = Path(settings.BASE_DIR) / 'backups'
        dossier.mkdir(exist_ok=True)
        fichier = dossier / f'backup-{timezone.now():%Y%m%d-%H%M}.json.gz'
        out = io.StringIO()
        call_command('dumpdata', '--natural-foreign', '--natural-primary',
                     '-e', 'contenttypes', '-e', 'auth.permission',
                     '-e', 'sessions', '-e', 'admin.logentry',
                     stdout=out)
        with gzip.open(fichier, 'wt', encoding='utf-8') as f:
            f.write(out.getvalue())
        # Rotation
        sauvegardes = sorted(dossier.glob('backup-*.json.gz'))
        for ancien in sauvegardes[:-BACKUPS_RETENTION]:
            ancien.unlink()
        taille = fichier.stat().st_size // 1024
        return f'{fichier.name} ({taille} Ko), {min(len(sauvegardes), BACKUPS_RETENTION)} conservee(s)'
