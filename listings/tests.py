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
from unittest import mock

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
        '/cgv/',
        '/guide-vendeur/',
        '/guide-acheteur/',
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


class ImportXmlDeactivationTests(TestCase):
    """Bug corrige : un bien present dans le flux mais dont le traitement
    echoue ne doit PAS etre desactive (annule/remplace robuste)."""

    def setUp(self):
        cache.clear()
        self.client_ref = 'TESTAG'
        self.a = creer_annonce('REF-A', client_reference=self.client_ref, is_active=True)
        self.b = creer_annonce('REF-B', client_reference=self.client_ref, is_active=True)
        # REF-C est actif mais ABSENT du flux -> doit etre desactive (temoin)
        self.c = creer_annonce('REF-C', client_reference=self.client_ref, is_active=True)

    def _xml(self, refs):
        annonces = ''.join(
            f'<annonce><reference>{r}</reference></annonce>' for r in refs)
        return f'<client reference="{self.client_ref}">{annonces}</client>'.encode('utf-8')

    def test_bien_en_erreur_reste_actif(self):
        from listings.management.commands.import_xml import Command
        cmd = Command()
        # Le traitement de CHAQUE annonce echoue (erreur transitoire simulee)
        with mock.patch.object(Command, '_process_ac3_annonce',
                               side_effect=Exception('erreur transitoire')), \
             mock.patch.object(Command, '_auto_set_departement'):
            cmd._import_ac3(self._xml(['REF-A', 'REF-B']), self.client_ref, dry_run=False)
        self.a.refresh_from_db(); self.b.refresh_from_db(); self.c.refresh_from_db()
        # A et B sont dans le flux -> restent actifs malgre l'erreur
        self.assertTrue(self.a.is_active, "REF-A desactive a tort")
        self.assertTrue(self.b.is_active, "REF-B desactive a tort")
        # C est absent du flux -> bien desactive
        self.assertFalse(self.c.is_active, "REF-C aurait du etre desactive")


class RedactionRobustesseTests(TestCase):
    """L'assistant de redaction ne plante jamais sur des entrees non numeriques."""

    def test_suggestions_entrees_non_numeriques(self):
        from listings.services.redaction import suggerer_titres, suggerer_description
        # surface / chambres / terrain non numeriques : aucune exception
        titres = suggerer_titres('appartement', 'Lyon', surface='abc',
                                 nb_pieces='trois', nb_chambres='deux',
                                 surface_terrain='n/a')
        self.assertTrue(len(titres) >= 1)
        desc = suggerer_description('maison', 'Lyon', surface='', nb_pieces=None,
                                    surface_terrain='xxx')
        self.assertIn('Lyon', desc)

    def test_api_suggerer_annonce_entree_malformee(self):
        u = User.objects.create_user('sugg', 'sugg@test.fr', 'motdepasse-123')
        self.client.force_login(u)
        resp = self.client.post('/api/suggerer-annonce/',
                                data=json.dumps({'type_bien': 'maison', 'ville': 'Lyon',
                                                 'surface': 'beaucoup', 'nb_chambres': 'plein'}),
                                content_type='application/json')
        self.assertNotEqual(resp.status_code, 500)  # ne plante jamais


class SitemapSegmentsTests(TestCase):
    """Le sitemap des segments n'inclut que les combinaisons non vides."""

    def setUp(self):
        cache.clear()
        creer_annonce('S-1', ville='Lyon', code_postal='69001',
                      type_transaction='V', libelle_type='Appartement T3', is_active=True)

    def test_segments_vides_exclus(self):
        from listings.sitemaps import VilleSegmentSitemap
        combos = VilleSegmentSitemap().items()
        self.assertIn(('lyon', 'appartement-a-vendre'), combos)
        # Lyon n'a ni terrain ni location -> exclus
        self.assertNotIn(('lyon', 'terrain-a-vendre'), combos)
        self.assertNotIn(('lyon', 'maison-a-louer'), combos)


class UrlsSlugSeoTests(TestCase):
    """Les URLs riches (slug SEO) fonctionnent ET les anciennes URLs restent valides."""

    def setUp(self):
        cache.clear()
        self.a = creer_annonce('CT-777', libelle_type='Appartement', ville='Perigueux',
                               code_postal='24000', is_active=True)

    def test_get_absolute_url_riche(self):
        self.assertEqual(self.a.get_absolute_url(),
                         '/annonce/CT-777/appartement-perigueux/')

    def test_ancienne_url_toujours_valide(self):
        resp = self.client.get('/annonce/CT-777/')
        self.assertEqual(resp.status_code, 200)

    def test_nouvelle_url_slug_valide(self):
        resp = self.client.get('/annonce/CT-777/appartement-perigueux/')
        self.assertEqual(resp.status_code, 200)

    def test_slug_errone_resout_quand_meme(self):
        # Le slug est purement decoratif : n'importe quel slug resout par reference
        resp = self.client.get('/annonce/CT-777/nimporte-quoi/')
        self.assertEqual(resp.status_code, 200)


class EncadrementLoyersTests(TestCase):
    """La mention d'encadrement des loyers s'affiche dans les zones concernees."""

    def setUp(self):
        cache.clear()

    def test_paris_location_encadree(self):
        a = creer_annonce('LOC-PARIS', type_transaction='L', ville='Paris',
                          code_postal='75011', loyer_mensuel=1200, prix=0, is_active=True)
        self.assertTrue(a.est_zone_encadree_loyers)
        resp = self.client.get(a.get_absolute_url())
        self.assertContains(resp, "encadrement des loyers")

    def test_vente_hors_zone_pas_de_mention(self):
        a = creer_annonce('V-CAEN', type_transaction='V', ville='Caen',
                          code_postal='14000', is_active=True)
        self.assertFalse(a.est_zone_encadree_loyers)


class ProInscriptionUtilisateurConnecteTests(TestCase):
    """Un utilisateur DEJA connecte (sans profil pro) peut devenir pro sans
    recreer de compte, puis ajouter des realisations. (Bug corrige.)"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('villageacb', 'contact@village-acb.fr', 'motdepasse-123')
        self.client.force_login(self.user)

    def _donnees(self, **extra):
        d = {
            'nom_entreprise': 'Village ACB',
            'metier': 'tous_corps_etat',
            'autres_metiers': 'Plomberie, Electricite, Peinture',
            'ville': 'Perigueux', 'code_postal': '24000',
            'site_web_hp': '',  # honeypot vide
        }
        d.update(extra)
        return d

    def test_utilisateur_connecte_devient_pro(self):
        from listings.models import ProProfile
        n_users_avant = User.objects.count()
        resp = self.client.post('/pro/inscription/', self._donnees())
        self.assertEqual(resp.status_code, 302)
        # AUCUN nouveau compte cree
        self.assertEqual(User.objects.count(), n_users_avant)
        # Le profil pro est rattache a l'utilisateur connecte
        pro = ProProfile.objects.get(user=self.user)
        self.assertEqual(pro.nom_entreprise, 'Village ACB')
        self.assertEqual(pro.metier, 'tous_corps_etat')
        self.assertEqual(pro.autres_metiers, 'Plomberie, Electricite, Peinture')

    def test_apres_inscription_peut_ajouter_realisation(self):
        from listings.models import ProRealisation
        self.client.post('/pro/inscription/', self._donnees())
        # La page d'ajout de realisation est desormais accessible (plus de boucle)
        resp = self.client.get('/pro/realisation/ajouter/')
        self.assertEqual(resp.status_code, 200)
        # Et l'ajout fonctionne
        self.client.post('/pro/realisation/ajouter/', {
            'titre': 'Renovation complete maison', 'categorie': '', 'description': 'Test',
        })
        self.assertTrue(ProRealisation.objects.filter(titre='Renovation complete maison').exists())


class PhotoHeicTests(TestCase):
    """Les photos iPhone (HEIC) sont bien lues et re-encodees en JPEG."""

    def test_heic_reencode_en_jpeg(self):
        import io
        from PIL import Image
        from listings.services.photos import valider_et_reencoder
        b = io.BytesIO()
        Image.new('RGB', (320, 240), (10, 20, 30)).save(b, format='HEIF')
        b.seek(0)
        out = valider_et_reencoder(b)
        im = Image.open(out)
        self.assertEqual(im.format, 'JPEG')


class RealisationPhotosFeedbackTests(TestCase):
    """L'ajout de realisation : photo valide OK, et feedback honnete si echec."""

    def setUp(self):
        cache.clear()
        from listings.models import ProProfile
        self.user = User.objects.create_user('pro_feed', 'pro@feed.fr', 'motdepasse-123')
        ProProfile.objects.create(user=self.user, nom_entreprise='Feed Pro',
                                  metier='tous_corps_etat', is_active=True)
        self.client.force_login(self.user)

    def _jpeg(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        b = io.BytesIO(); Image.new('RGB', (400, 300), (80, 80, 80)).save(b, 'JPEG'); b.seek(0)
        return SimpleUploadedFile('c.jpg', b.read(), content_type='image/jpeg')

    def test_realisation_avec_photo_valide(self):
        from listings.models import ProRealisation
        self.client.post('/pro/realisation/ajouter/', {
            'titre': 'Chantier OK', 'categorie': '', 'description': 'x', 'photos': self._jpeg()})
        r = ProRealisation.objects.get(titre='Chantier OK')
        self.assertEqual(r.photos.count(), 1)

    def test_heic_via_formulaire(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from listings.models import ProRealisation
        b = io.BytesIO(); Image.new('RGB', (400, 300), (60, 60, 60)).save(b, 'HEIF'); b.seek(0)
        heic = SimpleUploadedFile('photo.heic', b.read(), content_type='image/heic')
        self.client.post('/pro/realisation/ajouter/', {
            'titre': 'Chantier iPhone', 'categorie': '', 'description': 'x', 'photos': heic})
        r = ProRealisation.objects.get(titre='Chantier iPhone')
        self.assertEqual(r.photos.count(), 1)  # HEIC accepte et converti


class InteractionsSocialesTests(TestCase):
    """Feed Pinterest : favoris (mettre de cote), etoiles, commentaires.
    Tout est ouvert du moment qu'on a un compte ; lecture des commentaires publique."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('social', 'social@test.fr', 'motdepasse-123')
        self.annonce = creer_annonce('SOC-1', is_active=True)
        self.photo = Photo.objects.create(annonce=self.annonce, url='http://x/p.jpg', ordre=1,
                                          is_inspiration=True, inspiration_categorie='cuisine')

    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type='application/json')

    # --- Favoris (mettre de cote) ---
    def test_favori_necessite_compte(self):
        resp = self._post('/api/photo-favori/', {'photo_id': self.photo.id, 'type': 'annonce'})
        self.assertEqual(resp.status_code, 302)  # redirige vers login

    def test_favori_toggle_avec_compte(self):
        from listings.models import PhotoFavori
        self.client.force_login(self.user)
        r1 = self._post('/api/photo-favori/', {'photo_id': self.photo.id, 'type': 'annonce'})
        self.assertTrue(r1.json()['liked'])
        self.assertEqual(PhotoFavori.objects.filter(user=self.user, photo=self.photo).count(), 1)
        r2 = self._post('/api/photo-favori/', {'photo_id': self.photo.id, 'type': 'annonce'})
        self.assertFalse(r2.json()['liked'])  # retire des favoris
        self.assertEqual(PhotoFavori.objects.filter(user=self.user, photo=self.photo).count(), 0)

    # --- Etoiles (notation) ---
    def test_note_etoiles(self):
        self.client.force_login(self.user)
        r = self._post('/api/photo-note/', {'photo_id': self.photo.id, 'note': 4, 'type': 'annonce'})
        data = r.json()
        self.assertEqual(data['note'], 4)
        self.assertEqual(data['average'], 4.0)
        self.assertEqual(data['count'], 1)
        # re-noter met a jour (pas de doublon)
        r2 = self._post('/api/photo-note/', {'photo_id': self.photo.id, 'note': 2, 'type': 'annonce'})
        self.assertEqual(r2.json()['count'], 1)
        self.assertEqual(r2.json()['average'], 2.0)

    def test_note_invalide_rejetee(self):
        self.client.force_login(self.user)
        r = self._post('/api/photo-note/', {'photo_id': self.photo.id, 'note': 9, 'type': 'annonce'})
        self.assertEqual(r.status_code, 400)

    def test_note_necessite_compte(self):
        r = self._post('/api/photo-note/', {'photo_id': self.photo.id, 'note': 4, 'type': 'annonce'})
        self.assertEqual(r.status_code, 302)

    # --- Commentaires ---
    def test_commentaire_avec_compte(self):
        from listings.models import PhotoCommentaire
        self.client.force_login(self.user)
        r = self._post('/api/photo-comment/', {'photo_id': self.photo.id, 'type': 'annonce',
                                               'texte': 'Superbe cuisine !'})
        self.assertEqual(r.json()['texte'], 'Superbe cuisine !')
        self.assertEqual(PhotoCommentaire.objects.filter(photo=self.photo).count(), 1)

    def test_commentaire_trop_long_rejete(self):
        self.client.force_login(self.user)
        r = self._post('/api/photo-comment/', {'photo_id': self.photo.id, 'type': 'annonce',
                                               'texte': 'x' * 501})
        self.assertEqual(r.status_code, 400)

    def test_commentaire_necessite_compte(self):
        r = self._post('/api/photo-comment/', {'photo_id': self.photo.id, 'type': 'annonce',
                                               'texte': 'coucou'})
        self.assertEqual(r.status_code, 302)

    def test_lecture_commentaires_publique(self):
        from listings.models import PhotoCommentaire
        PhotoCommentaire.objects.create(auteur=self.user, photo=self.photo, texte='Joli')
        resp = self.client.get(f'/api/photo-comments/?photo_id={self.photo.id}&type=annonce')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['comments'][0]['texte'], 'Joli')

    def test_suppression_commentaire_admin_uniquement(self):
        from listings.models import PhotoCommentaire
        c = PhotoCommentaire.objects.create(auteur=self.user, photo=self.photo, texte='a virer')
        # utilisateur normal : interdit
        self.client.force_login(self.user)
        r = self._post('/api/photo-comment/delete/', {'comment_id': c.id})
        self.assertEqual(r.status_code, 403)
        # admin : OK
        staff = User.objects.create_user('modo', 'modo@test.fr', 'x', is_staff=True)
        self.client.force_login(staff)
        r2 = self._post('/api/photo-comment/delete/', {'comment_id': c.id})
        self.assertEqual(r2.status_code, 200)
        self.assertFalse(PhotoCommentaire.objects.filter(id=c.id).exists())


class CockpitAnalyticsTests(TestCase):
    """Analytics maison : le middleware enregistre les pages vues (sans cookie),
    ignore staff/bots, et le cockpit admin agrege tout."""

    def setUp(self):
        cache.clear()
        from listings.models import PageVue
        PageVue.objects.all().delete()

    def test_middleware_enregistre_visite_publique(self):
        from listings.models import PageVue, StatJour
        creer_annonce('COCK-1', is_active=True)
        self.client.get('/')
        self.assertGreaterEqual(PageVue.objects.filter(section='home').count(), 1)
        # StatJour.visites incremente aussi
        self.assertGreaterEqual(StatJour.objects.get(date=timezone.localdate()).visites, 1)

    def test_middleware_ignore_staff(self):
        from listings.models import PageVue
        staff = User.objects.create_user('cockadmin', 'c@a.fr', 'x', is_staff=True)
        self.client.force_login(staff)
        self.client.get('/')
        self.assertEqual(PageVue.objects.count(), 0)  # on ne compte pas nos visites

    def test_middleware_ignore_bot(self):
        from listings.models import PageVue
        self.client.get('/', HTTP_USER_AGENT='Googlebot/2.1')
        self.assertEqual(PageVue.objects.count(), 0)

    def test_visiteur_hash_anonyme_et_stable_par_jour(self):
        from listings.models import PageVue
        self.client.get('/', HTTP_USER_AGENT='Mozilla/5.0', REMOTE_ADDR='1.2.3.4')
        self.client.get('/recherche/', HTTP_USER_AGENT='Mozilla/5.0', REMOTE_ADDR='1.2.3.4')
        hashes = set(PageVue.objects.values_list('visiteur_hash', flat=True))
        self.assertEqual(len(hashes), 1)  # meme visiteur = 1 seul hash
        # le hash ne contient aucune donnee perso en clair
        h = hashes.pop()
        self.assertNotIn('1.2.3.4', h)
        self.assertEqual(len(h), 64)

    def test_cockpit_accessible_staff_seulement(self):
        # anonyme -> redirige
        self.assertEqual(self.client.get('/gestion/cockpit/').status_code, 302)
        # non-staff -> 403
        u = User.objects.create_user('cockuser', 'cu@a.fr', 'x')
        self.client.force_login(u)
        self.assertEqual(self.client.get('/gestion/cockpit/').status_code, 403)
        # staff -> 200
        staff = User.objects.create_user('cockstaff', 'cs@a.fr', 'x', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get('/gestion/cockpit/').status_code, 200)


class MachineALeadsTests(TestCase):
    """Relance automatique des estimations sans suite (levier machine a leads)."""

    def setUp(self):
        cache.clear()

    def _estimation(self, jours, **extra):
        from listings.models import Estimation
        from datetime import timedelta
        e = Estimation.objects.create(type_bien='maison', ville='Caen', code_postal='14000',
                                      nom='Client', email='client@test.fr', **extra)
        # backdate created_at
        Estimation.objects.filter(pk=e.pk).update(
            created_at=timezone.now() - timedelta(days=jours))
        return Estimation.objects.get(pk=e.pk)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_relance_estimation_sans_suite(self):
        from listings.management.commands.autopilot import Command
        e = self._estimation(jours=5)  # dans la fenetre 3-14 j
        Command()._relancer_estimations('https://social-immo.com')
        e.refresh_from_db()
        self.assertTrue(e.relance_envoyee)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_pas_de_relance_si_recente_ou_traitee(self):
        from listings.management.commands.autopilot import Command
        recente = self._estimation(jours=1)         # trop recente
        traitee = self._estimation(jours=5, is_treated=True)  # deja traitee
        Command()._relancer_estimations('https://social-immo.com')
        recente.refresh_from_db(); traitee.refresh_from_db()
        self.assertFalse(recente.relance_envoyee)
        self.assertFalse(traitee.relance_envoyee)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_relance_une_seule_fois(self):
        from listings.management.commands.autopilot import Command
        self._estimation(jours=5)
        Command()._relancer_estimations('https://social-immo.com')
        Command()._relancer_estimations('https://social-immo.com')  # 2e passage
        self.assertEqual(len(mail.outbox), 1)  # pas de doublon


class RapportPartenairesTests(TestCase):
    """Rapport mensuel de performance aux pros et agences (retention)."""

    def setUp(self):
        cache.clear()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_rapport_pro_avec_activite(self):
        from listings.models import ProProfile, ProRealisation, DemandeContact
        from listings.management.commands.autopilot import Command
        u = User.objects.create_user('proR', 'pror@test.fr', 'x')
        pro = ProProfile.objects.create(user=u, nom_entreprise='ACB', metier='tous_corps_etat',
                                        is_active=True, email='pror@test.fr')
        ProRealisation.objects.create(pro=pro, titre='Chantier', is_active=True)
        DemandeContact.objects.create(pro=pro, message='Bonjour', nom='X', email='x@y.fr')
        Command()._rapport_partenaires('https://social-immo.com')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('bilan', mail.outbox[0].subject.lower())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_pas_de_rapport_si_aucune_activite(self):
        from listings.models import ProProfile
        from listings.management.commands.autopilot import Command
        u = User.objects.create_user('proV', 'prov@test.fr', 'x')
        ProProfile.objects.create(user=u, nom_entreprise='Vide', metier='peintre',
                                  is_active=True, email='prov@test.fr')
        Command()._rapport_partenaires('https://social-immo.com')
        self.assertEqual(len(mail.outbox), 0)  # rien a dire -> pas d'email


class ConfianceDifferenciationTests(TestCase):
    """Levier confiance : etoiles avis pro (rich snippet) + preuve sociale homepage."""

    def setUp(self):
        cache.clear()

    def test_pro_avis_aggregate_rating(self):
        from listings.models import ProProfile, ProAvis
        u = User.objects.create_user('proC', 'proc@test.fr', 'x')
        pro = ProProfile.objects.create(user=u, nom_entreprise='ACB Renov',
                                        metier='tous_corps_etat', ville='Perigueux', is_active=True)
        client = User.objects.create_user('clientavis', 'ca@test.fr', 'x')
        ProAvis.objects.create(pro=pro, auteur=client, note=5, commentaire='Excellent travail')
        resp = self.client.get(pro.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'AggregateRating')
        self.assertContains(resp, '"ratingValue": "5')

    def test_homepage_bande_reassurance(self):
        cache.delete('home:stats')
        resp = self.client.get('/')
        self.assertContains(resp, 'ventes reelles notariees')
        self.assertContains(resp, 'Agences partenaires')


class RechercheCodePostalTests(TestCase):
    """La recherche fonctionne par nom de ville ET par code postal."""

    def setUp(self):
        cache.clear()
        creer_annonce('CP-1', ville='Perigueux', code_postal='24000',
                      prix=221000, type_transaction='V', is_active=True)

    def test_recherche_par_code_postal(self):
        resp = self.client.get('/recherche/?ville=24000')
        self.assertContains(resp, 'CP-1')

    def test_recherche_par_nom_ville(self):
        resp = self.client.get('/recherche/?ville=Perigueux')
        self.assertContains(resp, 'CP-1')


class NettoyerDoublonsTests(TestCase):
    """La commande de nettoyage garde la plus ancienne annonce et desactive les doublons."""

    def test_desactive_doublons_garde_le_plus_ancien(self):
        from django.core.management import call_command
        import io
        u = User.objects.create_user('vdup', 'vdup@test.fr', 'x')
        refs = []
        for i in range(4):  # 4 fois la meme annonce (double-clic)
            a = creer_annonce(f'DUP-{i}', user=u, source='particulier',
                              titre='Maison Perigueux', ville='Perigueux',
                              prix=221000, is_active=True)
            refs.append(a)
        call_command('nettoyer_doublons', stdout=io.StringIO())
        actives = Annonce.objects.filter(titre='Maison Perigueux', is_active=True)
        self.assertEqual(actives.count(), 1)  # une seule reste
        self.assertEqual(actives.first().reference, 'DUP-0')  # la plus ancienne


class GuideVendeurTests(TestCase):
    """Le guide vendeur est public et porte bien la mention de non-responsabilite."""

    def setUp(self):
        cache.clear()

    def test_guide_public_avec_disclaimer(self):
        resp = self.client.get('/guide-vendeur/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'titre purement informatif')
        self.assertContains(resp, 'ne saurait etre tenu responsable')
        # contenu cle present
        self.assertContains(resp, 'DPE')
        self.assertContains(resp, 'diagnostics')


class GuideAcheteurTests(TestCase):
    """Le guide acheteur est public, avec disclaimer + incitation a l'inscription (non bloquante)."""

    def setUp(self):
        cache.clear()

    def test_guide_public_avec_disclaimer_et_cta(self):
        resp = self.client.get('/guide-acheteur/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'titre purement informatif')
        self.assertContains(resp, 'ne saurait etre tenu responsable')
        # incitation a creer un compte (visiteur anonyme), sans bloquer le contenu
        self.assertContains(resp, 'espace acquereur')
        self.assertContains(resp, '/accounts/signup/')
        # le contenu reste accessible sans compte
        self.assertContains(resp, 'Constituer son dossier')

    def test_guide_connecte_montre_lien_espace(self):
        u = User.objects.create_user('acq', 'acq@test.fr', 'x')
        self.client.force_login(u)
        resp = self.client.get('/guide-acheteur/')
        self.assertContains(resp, 'Mon espace acquereur')
