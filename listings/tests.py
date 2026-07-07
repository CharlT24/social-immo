"""
Suite de tests Social Immo.

Regle d'or : AUCUN appel reseau. Les chemins qui touchent des APIs externes
(DVF, geocodage, Stripe, flux XML) sont soit evites (type_bien='terrain',
avec_dvf=False), soit simules (signature webhook calculee localement).
"""
import hashlib
import hmac
import json
import time

from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import (
    Abonnement, Agence, AgenceOptions, Annonce, DemandeAgence, DemandeContact,
    Photo, ProProfile, RechercheSauvegardee, StatJour, TicketSupport,
)
from .services.estimation import estimer_bien


def creer_annonce(reference, **kwargs):
    """Fabrique une annonce minimale valide."""
    defaults = {
        'titre': f'Annonce {reference}',
        'type_transaction': 'V',
        'prix': 150000,
        'ville': 'Caen',
        'code_postal': '14000',
        'is_active': True,
    }
    defaults.update(kwargs)
    return Annonce.objects.create(reference=reference, **defaults)


class PagesPubliquesTests(TestCase):
    """Les pages publiques repondent 200 sans authentification."""

    URLS = [
        '/',
        '/recherche/',
        '/inspirations/',
        '/estimer/',
        '/pros/',
        '/devis/',
        '/barometre/',
        '/tarifs/',
        '/aide/',
        '/agence/inscription/',
        '/cgu/',
        '/sitemap.xml',
    ]

    def setUp(self):
        cache.clear()

    def test_pages_publiques_200(self):
        for url in self.URLS:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, f'{url} -> {response.status_code}')


class RolesAccesTests(TestCase):
    """Controle d'acces : gestion (staff) et mon-compte (login)."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('membre', 'membre@test.fr', 'motdepasse-123')
        self.staff = User.objects.create_user(
            'admin', 'admin@test.fr', 'motdepasse-123', is_staff=True
        )

    def test_gestion_anonyme_redirige_vers_login(self):
        response = self.client.get('/gestion/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_gestion_non_staff_403(self):
        self.client.force_login(self.user)
        response = self.client.get('/gestion/')
        self.assertEqual(response.status_code, 403)

    def test_gestion_staff_200(self):
        self.client.force_login(self.staff)
        response = self.client.get('/gestion/')
        self.assertEqual(response.status_code, 200)

    def test_mon_compte_necessite_login(self):
        response = self.client.get('/mon-compte/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_mon_compte_connecte_200(self):
        self.client.force_login(self.user)
        response = self.client.get('/mon-compte/')
        self.assertEqual(response.status_code, 200)


class ApiEstimerTests(TestCase):
    """API d'estimation instantanee (type 'terrain' : jamais d'appel DVF)."""

    def setUp(self):
        cache.clear()

    def _estimer(self, **payload):
        return self.client.post(
            '/api/estimer/', data=json.dumps(payload),
            content_type='application/json',
        )

    def test_estimation_terrain_ok(self):
        response = self._estimer(
            type_bien='terrain', ville='Caen', code_postal='14000', surface=500,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for cle in ('prix_estime', 'prix_min', 'prix_max'):
            self.assertIn(cle, data)
        self.assertLess(data['prix_min'], data['prix_estime'])
        self.assertLess(data['prix_estime'], data['prix_max'])

    def test_estimation_sans_surface_400(self):
        response = self._estimer(type_bien='terrain', ville='Caen', code_postal='14000')
        self.assertEqual(response.status_code, 400)

    def test_rate_limit_apres_20_appels(self):
        payload = dict(type_bien='terrain', ville='Caen', code_postal='14000', surface=500)
        for i in range(20):
            response = self._estimer(**payload)
            self.assertEqual(response.status_code, 200, f'appel {i + 1} bloque trop tot')
        response = self._estimer(**payload)
        self.assertEqual(response.status_code, 429)


class DepotAnnonceParticulierTests(TestCase):
    """Depot d'annonce particulier : activation conditionnee a l'email verifie."""

    DONNEES = {
        'titre': 'Maison familiale avec jardin',
        'texte': 'Belle maison lumineuse.',
        'libelle_type': 'Maison',
        'type_transaction': 'V',
        'prix': '250000',
        'ville': 'Caen',
        'code_postal': '14000',
    }

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('vendeur', 'vendeur@test.fr', 'motdepasse-123')
        self.client.force_login(self.user)

    def test_depot_sans_email_verifie_annonce_inactive(self):
        response = self.client.post('/mon-compte/deposer/', self.DONNEES)
        annonce = Annonce.objects.get(user=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'/mon-compte/annonce/{annonce.id}/publiee/', response['Location'])
        self.assertFalse(annonce.is_active)
        self.assertEqual(annonce.source, 'particulier')
        self.assertEqual(annonce.contact_email, 'vendeur@test.fr')

    def test_depot_avec_email_verifie_annonce_active(self):
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True, primary=True,
        )
        response = self.client.post('/mon-compte/deposer/', self.DONNEES)
        self.assertEqual(response.status_code, 302)
        annonce = Annonce.objects.get(user=self.user)
        self.assertTrue(annonce.is_active)


class SignalEmailConfirmeTests(TestCase):
    """Le signal email_confirmed active les annonces recentes en attente."""

    def test_confirmation_active_les_annonces_recentes(self):
        user = User.objects.create_user('confirme', 'confirme@test.fr', 'motdepasse-123')
        annonce = creer_annonce(
            'PART-TEST-1', user=user, source='particulier', is_active=False,
        )
        annonce_agence = creer_annonce('AGENCE-TEST-1', is_active=False)
        email = EmailAddress.objects.create(
            user=user, email=user.email, verified=True, primary=True,
        )
        email_confirmed.send(sender=EmailAddress, request=None, email_address=email)
        annonce.refresh_from_db()
        annonce_agence.refresh_from_db()
        self.assertTrue(annonce.is_active)
        self.assertFalse(annonce_agence.is_active)  # pas concernee


class AlertesRechercheTests(TestCase):
    """Alertes email : creation via la vue + logique de matching."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('acheteur', 'acheteur@test.fr', 'motdepasse-123')

    def test_creation_alerte_necessite_login(self):
        response = self.client.post('/alertes/creer/', {'ville': 'Caen', 'type': 'V'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])
        self.assertEqual(RechercheSauvegardee.objects.count(), 0)

    def test_creation_alerte(self):
        self.client.force_login(self.user)
        response = self.client.post('/alertes/creer/', {
            'ville': 'Caen', 'type': 'V', 'prix_max': '200000',
        })
        self.assertEqual(response.status_code, 302)
        alerte = RechercheSauvegardee.objects.get(user=self.user)
        self.assertEqual(alerte.ville, 'Caen')
        self.assertEqual(alerte.type_transaction, 'V')
        self.assertEqual(alerte.prix_max, 200000)
        self.assertTrue(alerte.is_active)

    def test_correspond_a(self):
        alerte = RechercheSauvegardee.objects.create(
            user=self.user, ville='Caen', type_transaction='V', prix_max=200000,
        )
        ok = creer_annonce('MATCH-1', ville='Caen', prix=150000)
        trop_cher = creer_annonce('MATCH-2', ville='Caen', prix=250000)
        ailleurs = creer_annonce('MATCH-3', ville='Paris', prix=150000)
        location = creer_annonce('MATCH-4', ville='Caen', prix=650, type_transaction='L')
        self.assertTrue(alerte.correspond_a(ok))
        self.assertFalse(alerte.correspond_a(trop_cher))
        self.assertFalse(alerte.correspond_a(ailleurs))
        self.assertFalse(alerte.correspond_a(location))

    def test_acheteurs_pour(self):
        vendeur = User.objects.create_user('proprio', 'proprio@test.fr', 'motdepasse-123')
        annonce = creer_annonce('VENTE-1', user=vendeur, ville='Caen', prix=180000)
        autre = User.objects.create_user('acheteur2', 'a2@test.fr', 'motdepasse-123')
        RechercheSauvegardee.objects.create(
            user=self.user, ville='Caen', type_transaction='V', prix_max=200000,
        )
        RechercheSauvegardee.objects.create(user=autre, ville='Caen')
        # Alerte du vendeur lui-meme : exclue du comptage
        RechercheSauvegardee.objects.create(user=vendeur, ville='Caen')
        # Alerte qui ne matche pas
        RechercheSauvegardee.objects.create(
            user=autre, ville='Paris', type_transaction='V',
        )
        self.assertEqual(RechercheSauvegardee.acheteurs_pour(annonce), 2)

    def test_annonces_correspondantes(self):
        alerte = RechercheSauvegardee.objects.create(
            user=self.user, ville='Caen', type_transaction='V',
            prix_max=200000, surface_min=50,
        )
        ok = creer_annonce('CORR-1', ville='Caen', prix=150000, surface=80)
        creer_annonce('CORR-2', ville='Caen', prix=150000, surface=30)   # trop petit
        creer_annonce('CORR-3', ville='Lisieux', prix=150000, surface=80)  # autre ville
        creer_annonce('CORR-4', ville='Caen', prix=150000, surface=80,
                      is_active=False)  # inactive
        resultats = list(alerte.annonces_correspondantes())
        self.assertEqual(resultats, [ok])


class DemandeDevisTests(TestCase):
    """Devis travaux : 3 pros max, departement respecte, honeypot."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('client', 'client@test.fr', 'motdepasse-123')
        self.client.force_login(self.user)
        # 4 plombiers dans le 14, 1 dans le 75
        for i in range(4):
            u = User.objects.create_user(f'plombier14-{i}', f'p14-{i}@test.fr', 'x-123456')
            ProProfile.objects.create(
                user=u, nom_entreprise=f'Plomberie 14 n{i}', metier='plombier',
                departement='14', email=u.email, is_active=True,
            )
        u75 = User.objects.create_user('plombier75', 'p75@test.fr', 'x-123456')
        ProProfile.objects.create(
            user=u75, nom_entreprise='Plomberie Paris', metier='plombier',
            departement='75', email=u75.email, is_active=True,
        )

    DONNEES = {
        'metier': 'plombier',
        'ville': 'Caen',
        'code_postal': '14000',
        'description': 'Remplacement du chauffe-eau.',
        'telephone': '0601020304',
    }

    def test_devis_cree_3_demandes_dans_le_departement(self):
        response = self.client.post('/devis/', self.DONNEES)
        self.assertEqual(response.status_code, 302)
        demandes = DemandeContact.objects.filter(expediteur=self.user)
        self.assertEqual(demandes.count(), 3)
        for demande in demandes:
            self.assertEqual(demande.pro.departement, '14')

    def test_devis_honeypot_ne_cree_rien(self):
        donnees = dict(self.DONNEES, site_web_hp='http://spam.example.com')
        response = self.client.post('/devis/', donnees)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DemandeContact.objects.count(), 0)


@override_settings(ADMINS=[])
class SupportTests(TestCase):
    """Centre d'aide : ticket + accuse de reception, honeypot."""

    def setUp(self):
        cache.clear()

    DONNEES = {
        'nom': 'Jean Dupont',
        'email': 'jean@test.fr',
        'sujet': 'technique',
        'message': 'Je ne parviens pas a modifier mon annonce.',
    }

    def test_ticket_cree_avec_accuse_de_reception(self):
        response = self.client.post('/aide/', self.DONNEES)
        self.assertEqual(response.status_code, 302)
        ticket = TicketSupport.objects.get()
        self.assertEqual(ticket.email, 'jean@test.fr')
        self.assertEqual(ticket.sujet, 'technique')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('jean@test.fr', mail.outbox[0].to)
        self.assertIn(str(ticket.id), mail.outbox[0].subject)

    def test_honeypot_ne_cree_pas_de_ticket(self):
        donnees = dict(self.DONNEES, site_web_hp='http://spam.example.com')
        response = self.client.post('/aide/', donnees)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TicketSupport.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)


class SuppressionCompteTests(TestCase):
    """Droit a l'effacement : suppression de compte self-service."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('partant', 'partant@test.fr', 'motdepasse-123')
        self.annonce = creer_annonce(
            'PART-DEL-1', user=self.user, source='particulier',
            contact_email='partant@test.fr', is_active=True,
        )
        self.client.force_login(self.user)

    def test_mauvais_mot_de_passe_conserve_le_compte(self):
        response = self.client.post('/mon-compte/supprimer/', {'password': 'mauvais'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.annonce.refresh_from_db()
        self.assertTrue(self.annonce.is_active)

    def test_bon_mot_de_passe_supprime_et_purge(self):
        response = self.client.post('/mon-compte/supprimer/', {'password': 'motdepasse-123'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.annonce.refresh_from_db()
        self.assertFalse(self.annonce.is_active)
        self.assertEqual(self.annonce.contact_email, '')
        self.assertEqual(self.annonce.contact_telephone, '')


@override_settings(STRIPE_WEBHOOK_SECRET='whsec_test_secret')
class StripeWebhookTests(TestCase):
    """Webhook Stripe : signature HMAC + activation/desactivation des avantages."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('agent', 'agent@test.fr', 'motdepasse-123')
        self.agence = Agence.objects.create(
            nom='Agence Test', reference='AGTEST', responsable=self.user,
        )

    def _signer(self, payload, secret='whsec_test_secret'):
        t = int(time.time())
        signature = hmac.new(
            secret.encode(), f'{t}.'.encode() + payload, hashlib.sha256,
        ).hexdigest()
        return f't={t},v1={signature}'

    def _poster(self, event, signature=None):
        payload = json.dumps(event).encode()
        extra = {}
        if signature is not False:
            extra['HTTP_STRIPE_SIGNATURE'] = signature or self._signer(payload)
        return self.client.post(
            '/stripe/webhook/', data=payload,
            content_type='application/json', **extra,
        )

    def _event_checkout(self):
        return {
            'type': 'checkout.session.completed',
            'data': {'object': {
                'id': 'cs_test_123',  # Stripe envoie toujours l'id de session
                'metadata': {'type_abonnement': 'agence', 'user_id': str(self.user.id)},
                'subscription': 'sub_test_123',
                'customer': 'cus_test_123',
            }},
        }

    def test_sans_signature_400(self):
        response = self._poster(self._event_checkout(), signature=False)
        self.assertEqual(response.status_code, 400)

    def test_signature_invalide_400(self):
        response = self._poster(
            self._event_checkout(), signature=f't={int(time.time())},v1=deadbeef',
        )
        self.assertEqual(response.status_code, 400)

    def test_checkout_complete_active_abonnement_et_badge(self):
        response = self._poster(self._event_checkout())
        self.assertEqual(response.status_code, 200)
        abo = Abonnement.objects.get(user=self.user)
        self.assertEqual(abo.statut, 'actif')
        self.assertEqual(abo.type_abonnement, 'agence')
        self.assertEqual(abo.stripe_subscription_id, 'sub_test_123')
        options = AgenceOptions.objects.get(agence=self.agence)
        self.assertTrue(options.badge_premium)

    def test_checkout_idempotent_pas_de_doublon(self):
        # Rejouer le meme event (Stripe reessaie) ne cree pas de 2e abonnement
        self._poster(self._event_checkout())
        self._poster(self._event_checkout())
        self.assertEqual(Abonnement.objects.filter(user=self.user).count(), 1)

    def test_subscription_deleted_resilie_et_retire_le_badge(self):
        self._poster(self._event_checkout())
        response = self._poster({
            'type': 'customer.subscription.deleted',
            'data': {'object': {'id': 'sub_test_123'}},
        })
        self.assertEqual(response.status_code, 200)
        abo = Abonnement.objects.get(user=self.user)
        self.assertEqual(abo.statut, 'resilie')
        options = AgenceOptions.objects.get(agence=self.agence)
        self.assertFalse(options.badge_premium)


class EstimationServiceTests(TestCase):
    """Moteur d'estimation local (avec_dvf=False : aucun appel reseau)."""

    def test_estimer_maison_ville_inconnue(self):
        resultat = estimer_bien(
            'maison', 'VilleInconnue', '14000', 100, avec_dvf=False,
        )
        self.assertIsNotNone(resultat)
        self.assertIn(resultat['zone'], ('ville', 'departement', 'bareme'))
        self.assertLess(resultat['prix_min'], resultat['prix_estime'])
        self.assertLess(resultat['prix_estime'], resultat['prix_max'])
        self.assertGreater(resultat['prix_m2'], 0)

    def test_estimer_sans_surface_retourne_none(self):
        self.assertIsNone(estimer_bien('maison', 'Caen', '14000', None, avec_dvf=False))
        self.assertIsNone(estimer_bien('maison', 'Caen', '14000', 0, avec_dvf=False))

    def test_estimer_avec_comparables_ville(self):
        for i in range(10):
            creer_annonce(
                f'COMP-{i}', libelle_type='Maison', ville='Caen',
                prix=200000 + i * 5000, surface=100,
            )
        resultat = estimer_bien('maison', 'Caen', '14000', 100, avec_dvf=False)
        self.assertEqual(resultat['zone'], 'ville')
        self.assertEqual(resultat['nb_comparables'], 10)


class ModelesTests(TestCase):
    """Petites logiques de modeles : formats, fallbacks, compteurs."""

    def test_prix_format(self):
        annonce = creer_annonce('FMT-1', prix=500000)
        self.assertEqual(annonce.prix_format, '500 000 €')

    def test_photo_src_thumb_fallback_url(self):
        annonce = creer_annonce('PHOTO-1')
        photo = Photo.objects.create(
            annonce=annonce, url='https://exemple.fr/photo.jpg', ordre=1,
        )
        self.assertEqual(photo.src_thumb, 'https://exemple.fr/photo.jpg')
        self.assertEqual(photo.src, 'https://exemple.fr/photo.jpg')

    def test_statjour_incrementer(self):
        StatJour.incrementer('estimations')
        StatJour.incrementer('estimations')
        StatJour.incrementer('visites')
        stat = StatJour.objects.get(date=timezone.localdate())
        self.assertEqual(stat.estimations, 2)
        self.assertEqual(stat.visites, 1)


class RayonRgpdTests(TestCase):
    """Recherche par rayon geographique + export/suppression RGPD."""

    def setUp(self):
        cache.clear()
        from .models import VilleGeo
        VilleGeo.objects.create(ville='Caen', code_postal='14000', latitude=49.1829, longitude=-0.3707)
        VilleGeo.objects.create(ville='Herouville', code_postal='14200', latitude=49.2050, longitude=-0.3280)
        VilleGeo.objects.create(ville='Bayeux', code_postal='14400', latitude=49.2764, longitude=-0.7024)

    def test_villes_dans_rayon(self):
        from .models import VilleGeo
        proches = VilleGeo.villes_dans_rayon('Caen', 10)
        self.assertIn('Caen', proches)
        self.assertIn('Herouville', proches)
        self.assertNotIn('Bayeux', proches)  # ~27 km
        self.assertIn('Bayeux', VilleGeo.villes_dans_rayon('Caen', 30))
        self.assertIsNone(VilleGeo.villes_dans_rayon('VilleInconnue', 10))

    def test_recherche_rayon_elargit(self):
        creer_annonce('R-CAEN', ville='Caen', code_postal='14000')
        creer_annonce('R-HERO', ville='Herouville', code_postal='14200')
        creer_annonce('R-BAY', ville='Bayeux', code_postal='14400')
        resp = self.client.get('/recherche/?ville=Caen&rayon=10')
        self.assertContains(resp, 'Annonce R-CAEN')
        self.assertContains(resp, 'Annonce R-HERO')
        self.assertNotContains(resp, 'Annonce R-BAY')

    def test_export_donnees_json(self):
        u = User.objects.create_user('exp', 'exp@t.fr', 'x', first_name='Jean')
        creer_annonce('EXP-A', user=u, source='particulier')
        RechercheSauvegardee.objects.create(user=u, ville='Caen', type_transaction='V')
        self.client.force_login(u)
        resp = self.client.get('/mon-compte/exporter/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('attachment', resp['Content-Disposition'])
        data = json.loads(b''.join(resp.streaming_content) if hasattr(resp, 'streaming_content') else resp.content)
        self.assertEqual(data['compte']['email'], 'exp@t.fr')
        self.assertEqual(len(data['mes_annonces']), 1)
        self.assertEqual(len(data['mes_alertes']), 1)

    def test_health_endpoint(self):
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')


class VerificationProTests(TestCase):
    """Verification SIRET anti-escroquerie (API mockee, zero reseau)."""

    def setUp(self):
        cache.clear()

    def test_siret_valide_badge_verifie(self):
        from unittest.mock import patch
        faux_resultat = {'valide': True, 'actif': True, 'nom': 'PEINTURE SARL',
                         'activite': '43.34Z', 'ville': 'CAEN', 'siret': '12345678900011'}
        with patch('listings.services.verification.verifier_siret', return_value=faux_resultat):
            resp = self.client.post('/pro/inscription/', {
                'email': 'v@t.fr', 'password1': 'motdepasse123', 'password2': 'motdepasse123',
                'nom_entreprise': 'Peinture', 'metier': 'peintre', 'code_postal': '14000',
                'siret': '12345678900011',
            }, follow=True)
        pro = ProProfile.objects.get(user__email='v@t.fr')
        self.assertTrue(pro.siret_verifie)
        self.assertEqual(pro.nom_officiel, 'PEINTURE SARL')

    def test_siret_introuvable_pas_de_badge(self):
        from unittest.mock import patch
        faux_resultat = {'valide': False, 'actif': False, 'raison': 'introuvable'}
        with patch('listings.services.verification.verifier_siret', return_value=faux_resultat):
            self.client.post('/pro/inscription/', {
                'email': 'f@t.fr', 'password1': 'motdepasse123', 'password2': 'motdepasse123',
                'nom_entreprise': 'Faux', 'metier': 'plombier', 'code_postal': '75001',
                'siret': '00000000000000',
            }, follow=True)
        pro = ProProfile.objects.get(user__email='f@t.fr')
        self.assertTrue(pro.is_active)      # le profil reste actif
        self.assertFalse(pro.siret_verifie)  # mais sans badge

    def test_nettoyer_siret(self):
        from .services.verification import nettoyer_siret
        self.assertEqual(nettoyer_siret('356 000 000'), '356000000')
        self.assertEqual(nettoyer_siret('123-456/789'), '123456789')


class SecuriteTests(TestCase):
    """Durcissements de securite (upload, SIRET, anti-bot)."""

    def setUp(self):
        cache.clear()

    def test_upload_rejette_non_image(self):
        from listings.services.photos import valider_et_reencoder, ImageInvalide
        import io
        faux = io.BytesIO(b'<html><script>alert(1)</script></html>')
        with self.assertRaises(ImageInvalide):
            valider_et_reencoder(faux)

    def test_upload_reencode_en_jpeg(self):
        from listings.services.photos import valider_et_reencoder
        from PIL import Image
        import io
        img = Image.new('RGB', (2400, 1800), (100, 120, 140))
        b = io.BytesIO(); img.save(b, format='PNG'); b.seek(0)
        result = Image.open(valider_et_reencoder(b))
        self.assertEqual(result.format, 'JPEG')
        self.assertLessEqual(max(result.size), 1920)

    def test_siret_badge_refuse_si_nom_different(self):
        from unittest.mock import patch
        # SIRET valide/actif mais nom officiel != nom declare (usurpation)
        faux = {'valide': True, 'actif': True, 'nom': 'FONCIA', 'siret': '12345678900011'}
        with patch('listings.services.verification.verifier_siret', return_value=faux):
            self.client.post('/pro/inscription/', {
                'email': 'escroc@t.fr', 'password1': 'motdepasse123', 'password2': 'motdepasse123',
                'nom_entreprise': 'Depann Express', 'metier': 'plombier', 'code_postal': '75001',
                'siret': '12345678900011',
            }, follow=True)
        pro = ProProfile.objects.get(user__email='escroc@t.fr')
        self.assertFalse(pro.siret_verifie)  # pas de badge : noms differents

    def test_pro_inscription_username_unique(self):
        # Deux emails avec la meme partie locale ne provoquent pas de 500
        from unittest.mock import patch
        with patch('listings.services.verification.verifier_siret', return_value=None):
            r1 = self.client.post('/pro/inscription/', {
                'email': 'contact@a.fr', 'password1': 'motdepasse123', 'password2': 'motdepasse123',
                'nom_entreprise': 'Pro A', 'metier': 'peintre', 'code_postal': '14000',
            }, follow=True)
            cache.clear()
            self.client.logout()
            r2 = self.client.post('/pro/inscription/', {
                'email': 'contact@b.fr', 'password1': 'motdepasse123', 'password2': 'motdepasse123',
                'nom_entreprise': 'Pro B', 'metier': 'macon', 'code_postal': '69001',
            }, follow=True)
        self.assertEqual(ProProfile.objects.filter(nom_entreprise__in=['Pro A', 'Pro B']).count(), 2)

    def test_honeypot_bloque_inscription_pro(self):
        self.client.post('/pro/inscription/', {
            'email': 'bot@t.fr', 'password1': 'motdepasse123', 'password2': 'motdepasse123',
            'nom_entreprise': 'Bot', 'metier': 'peintre', 'code_postal': '14000',
            'site_web_hp': 'http://spam.com',
        }, follow=True)
        self.assertFalse(ProProfile.objects.filter(user__email='bot@t.fr').exists())

    def test_import_sanitize_champs_trop_longs(self):
        from listings.management.commands.import_xml import Command
        data = Command()._sanitize({
            'titre': 'X' * 400, 'dpe_etiquette_conso': 'N/A',
            'code_postal': '14000 CEDEX 9',
        })
        self.assertEqual(len(data['titre']), 255)
        self.assertEqual(data['dpe_etiquette_conso'], '')
        self.assertLessEqual(len(data['code_postal']), 10)


class DepotAntiDoublonTests(TestCase):
    """Un double-clic ne cree pas plusieurs fois la meme annonce."""

    def setUp(self):
        cache.clear()
        from allauth.account.models import EmailAddress
        self.u = User.objects.create_user('dep', 'dep@t.fr', 'x')
        EmailAddress.objects.create(user=self.u, email='dep@t.fr', verified=True, primary=True)
        self.client.force_login(self.u)

    def test_double_clic_pas_de_doublon(self):
        data = {'titre': 'Maison unique', 'texte': 'x', 'libelle_type': 'Maison',
                'type_transaction': 'V', 'prix': '250000', 'ville': 'Caen', 'code_postal': '14000',
                'surface': '90', 'dpe_etiquette_conso': 'D', 'dpe_etiquette_ges': 'E'}
        for _ in range(4):
            self.client.post('/mon-compte/deposer/', data, follow=True)
        self.assertEqual(Annonce.objects.filter(titre='Maison unique', user=self.u).count(), 1)

    def test_ges_enregistre_et_affiche(self):
        data = {'titre': 'Maison GES', 'texte': 'x', 'libelle_type': 'Maison',
                'type_transaction': 'V', 'prix': '250000', 'ville': 'Caen', 'code_postal': '14000',
                'surface': '90', 'dpe_etiquette_conso': 'D', 'dpe_valeur_conso': '180',
                'dpe_etiquette_ges': 'E', 'dpe_valeur_ges': '35'}
        self.client.post('/mon-compte/deposer/', data, follow=True)
        a = Annonce.objects.get(titre='Maison GES', user=self.u)
        self.assertEqual(a.dpe_etiquette_ges, 'E')
        self.assertEqual(a.dpe_valeur_ges, 35)
        resp = self.client.get(f'/annonce/{a.reference}/')
        self.assertContains(resp, 'gaz à effet de serre')


class DemandeAgenceTests(TestCase):
    """La demande d'une agence (page vitrine) est toujours enregistree en base,
    meme si l'email admin echoue — aucun lead perdu."""

    def setUp(self):
        cache.clear()

    def _post(self):
        return self.client.post('/agence-immobiliere/', {
            'nom_agence': 'Agence Test Diffusion', 'ville': 'Bordeaux',
            'email': 'contact@agence-test.fr', 'telephone': '0611223344',
            'nb_biens': '25', 'message': 'On veut diffuser nos biens.',
        })

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_demande_persistee_et_email_envoye(self):
        resp = self._post()
        self.assertEqual(resp.status_code, 200)
        d = DemandeAgence.objects.get(nom_agence='Agence Test Diffusion')
        self.assertEqual(d.email, 'contact@agence-test.fr')
        self.assertTrue(d.email_envoye)
        self.assertEqual(len(mail.outbox), 1)

    def test_demande_persistee_meme_si_email_echoue(self):
        # Backend qui plante a l'envoi : la demande doit quand meme etre en base.
        with override_settings(EMAIL_BACKEND='listings.tests.BrokenEmailBackend'):
            resp = self._post()
        self.assertEqual(resp.status_code, 200)
        d = DemandeAgence.objects.get(nom_agence='Agence Test Diffusion')
        self.assertFalse(d.email_envoye)


from django.core.mail.backends.base import BaseEmailBackend


class BrokenEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise OSError('SMTP indisponible (test)')
