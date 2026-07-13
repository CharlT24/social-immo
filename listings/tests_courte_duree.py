"""
Tests de la v4 : location courte durée (type Airbnb), réservations,
affichage des prix, paiements (Stripe mocké) et navigation.
Lancer : python manage.py test listings.tests_courte_duree
"""
import json
from datetime import date, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Annonce, Reservation, PeriodeIndisponible, Abonnement
from .services import paiements


def _jour(n):
    return (date.today() + timedelta(days=n)).isoformat()


class CourteDureeModeleTests(TestCase):
    def test_prix_principal_et_suffixe_par_type(self):
        v = Annonce.objects.create(reference='M-V', titre='Maison', type_transaction='V', prix=250000)
        loc = Annonce.objects.create(reference='M-L', titre='Appart', type_transaction='L', loyer_mensuel=750)
        cd = Annonce.objects.create(reference='M-S', titre='Studio', type_transaction='S', prix_nuit=95)
        self.assertEqual(v.prix_principal, '250 000 €')
        self.assertEqual(v.prix_suffixe, '')
        self.assertEqual(loc.prix_principal, '750 €')
        self.assertEqual(loc.prix_suffixe, '/ mois')
        self.assertEqual(cd.prix_principal, '95 €')
        self.assertEqual(cd.prix_suffixe, '/ nuit')
        self.assertTrue(cd.est_courte_duree)
        self.assertFalse(v.est_courte_duree)

    def test_equipements_list(self):
        a = Annonce.objects.create(reference='EQ', titre='X', type_transaction='S', prix_nuit=80,
                                   equip_wifi=True, equip_cuisine=True, equip_piscine=True)
        labels = [lbl for lbl, emo in a.equipements_list]
        self.assertIn('Wifi', labels)
        self.assertIn('Cuisine équipée', labels)
        self.assertIn('Piscine', labels)
        self.assertNotIn('Climatisation', labels)

    def test_plages_indisponibles(self):
        a = Annonce.objects.create(reference='PL', titre='X', type_transaction='S', prix_nuit=80)
        Reservation.objects.create(annonce=a, date_arrivee=date.today() + timedelta(days=5),
                                   date_depart=date.today() + timedelta(days=8), statut='acceptee')
        Reservation.objects.create(annonce=a, date_arrivee=date.today() + timedelta(days=20),
                                   date_depart=date.today() + timedelta(days=22), statut='en_attente')
        PeriodeIndisponible.objects.create(annonce=a, date_debut=date.today() + timedelta(days=30),
                                           date_fin=date.today() + timedelta(days=35))
        plages = a.plages_indisponibles()
        # 1 réservation acceptée + 1 période bloquée (la réservation en_attente ne bloque PAS)
        self.assertEqual(len(plages), 2)


class FormulaireDepotTests(TestCase):
    def _data(self, **over):
        d = {
            'titre': 'Joli studio', 'texte': 'Description', 'libelle_type': 'Studio',
            'type_transaction': 'S', 'ville': 'Biarritz', 'code_postal': '64200',
            'prix_nuit': '95', 'nb_voyageurs': '2', 'nuits_min': '2',
        }
        d.update(over)
        return d

    def test_courte_duree_exige_prix_nuit(self):
        from .forms import ParticulierAnnonceForm
        f = ParticulierAnnonceForm(data=self._data(prix_nuit=''))
        self.assertFalse(f.is_valid())
        self.assertIn('prix_nuit', f.errors)

    def test_courte_duree_valide_avec_prix_nuit(self):
        from .forms import ParticulierAnnonceForm
        f = ParticulierAnnonceForm(data=self._data())
        self.assertTrue(f.is_valid(), f.errors)

    def test_choix_type_contient_courte_duree(self):
        from .forms import ParticulierAnnonceForm
        choix = dict(ParticulierAnnonceForm().fields['type_transaction'].choices)
        self.assertIn('S', choix)

    def test_location_valide_sans_prix_vente(self):
        # Regression : le prix de vente ne doit PAS etre exige pour une location
        from .forms import ParticulierAnnonceForm
        f = ParticulierAnnonceForm(data=self._data(
            type_transaction='L', prix_nuit='', loyer_mensuel='700'))
        self.assertTrue(f.is_valid(), f.errors)


class ReservationFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user('hote', 'hote@example.com', 'x')
        self.annonce = Annonce.objects.create(
            reference='CD-1', source='particulier', user=self.owner, titre='Villa mer',
            type_transaction='S', prix_nuit=100, frais_menage=50, nuits_min=2,
            nb_voyageurs=4, ville='Anglet', code_postal='64600', is_active=True)
        self.d1, self.d2 = _jour(10), _jour(14)  # 4 nuits

    def _post_resa(self, **over):
        payload = {'annonce_id': self.annonce.id, 'date_arrivee': self.d1, 'date_depart': self.d2,
                   'nb_voyageurs': 2, 'nom': 'Jean', 'email': 'jean@x.fr', 'telephone': '0600000000'}
        payload.update(over)
        return self.client.post('/api/reservation/', data=json.dumps(payload),
                                content_type='application/json')

    def test_demande_valide_cree_reservation_et_email(self):
        r = self._post_resa()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['success'])
        resa = Reservation.objects.get(annonce=self.annonce)
        self.assertEqual(resa.statut, 'en_attente')
        self.assertEqual(float(resa.prix_total), 450.0)  # 100*4 + 50
        self.assertEqual(resa.nb_nuits, 4)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('hote@example.com', mail.outbox[0].to)

    def test_anonyme_sans_coordonnees_400(self):
        r = self._post_resa(nom='', email='', telephone='')
        self.assertEqual(r.status_code, 400)

    def test_sejour_trop_court_400(self):
        r = self._post_resa(date_arrivee=_jour(10), date_depart=_jour(11))  # 1 nuit < 2
        self.assertEqual(r.status_code, 400)

    def test_capacite_depassee_400(self):
        r = self._post_resa(nb_voyageurs=10)  # > 4
        self.assertEqual(r.status_code, 400)

    def test_date_passee_400(self):
        r = self._post_resa(date_arrivee=_jour(-3), date_depart=_jour(2))
        self.assertEqual(r.status_code, 400)

    def test_chevauchement_409(self):
        Reservation.objects.create(annonce=self.annonce, date_arrivee=date.today() + timedelta(days=10),
                                   date_depart=date.today() + timedelta(days=14), statut='acceptee')
        r = self._post_resa()
        self.assertEqual(r.status_code, 409)

    def test_proprietaire_accepte(self):
        self._post_resa()
        resa = Reservation.objects.get(annonce=self.annonce)
        mail.outbox.clear()
        self.client.force_login(self.owner)
        r = self.client.post(f'/reservation/{resa.id}/repondre/', {'action': 'accepter'})
        self.assertEqual(r.status_code, 302)
        resa.refresh_from_db()
        self.assertEqual(resa.statut, 'acceptee')
        self.assertEqual(len(mail.outbox), 1)  # email au voyageur

    def test_proprietaire_refuse(self):
        self._post_resa()
        resa = Reservation.objects.get(annonce=self.annonce)
        self.client.force_login(self.owner)
        self.client.post(f'/reservation/{resa.id}/repondre/', {'action': 'refuser'})
        resa.refresh_from_db()
        self.assertEqual(resa.statut, 'refusee')

    def test_repondre_non_proprietaire_404(self):
        self._post_resa()
        resa = Reservation.objects.get(annonce=self.annonce)
        intrus = User.objects.create_user('intrus', 'i@x.fr', 'x')
        self.client.force_login(intrus)
        r = self.client.post(f'/reservation/{resa.id}/repondre/', {'action': 'accepter'})
        self.assertEqual(r.status_code, 404)
        resa.refresh_from_db()
        self.assertEqual(resa.statut, 'en_attente')

    def test_bloquer_et_debloquer_periode(self):
        self.client.force_login(self.owner)
        r = self.client.post('/disponibilites/bloquer/', {
            'annonce_id': self.annonce.id, 'date_debut': _jour(40), 'date_fin': _jour(45)})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(PeriodeIndisponible.objects.filter(annonce=self.annonce).count(), 1)
        p = PeriodeIndisponible.objects.get(annonce=self.annonce)
        self.client.post(f'/disponibilites/{p.id}/debloquer/')
        self.assertEqual(PeriodeIndisponible.objects.filter(annonce=self.annonce).count(), 0)

    def test_widget_present_sur_fiche_S_absent_sur_V(self):
        r = self.client.get(self.annonce.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'booking-widget')
        vente = Annonce.objects.create(reference='V-1', titre='Maison', type_transaction='V',
                                       prix=200000, ville='Anglet', code_postal='64600', is_active=True)
        r2 = self.client.get(vente.get_absolute_url())
        self.assertNotContains(r2, 'booking-widget')

    def test_dashboard_onglet_reservations(self):
        self._post_resa()
        self.client.force_login(self.owner)
        r = self.client.get('/mon-compte/?tab=reservations')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Jean')


class RechercheTypeSTests(TestCase):
    def test_filtre_courte_duree(self):
        cd = Annonce.objects.create(reference='S-SEARCH', titre='Studio bord de mer',
                                    type_transaction='S', prix_nuit=90, ville='Biarritz',
                                    code_postal='64200', is_active=True)
        v = Annonce.objects.create(reference='V-SEARCH', titre='Maison a vendre',
                                   type_transaction='V', prix=300000, ville='Biarritz',
                                   code_postal='64200', is_active=True)
        r = self.client.get('/recherche/?type=S')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Studio bord de mer')
        self.assertNotContains(r, 'Maison a vendre')


class PaiementsTests(TestCase):
    def test_types_valides_complets(self):
        for t in ['agence', 'agence_illimite', 'pro', 'pro_priorite_secteur',
                  'pack_vendeur', 'vendeur_photos', 'vendeur_alaune_7', 'vendeur_alaune_30']:
            self.assertIn(t, paiements.TYPES_VALIDES)

    @override_settings(STRIPE_SECRET_KEY='sk_test_xxx', STRIPE_PRICE_VENDEUR_ALAUNE_7='price_abc')
    def test_creer_session_checkout_mode_payment(self):
        u = User.objects.create_user('acheteur', 'a@x.fr', 'x')
        with mock.patch.object(paiements, '_post', return_value={'url': 'https://stripe/session'}) as m:
            url = paiements.creer_session_checkout('vendeur_alaune_7', u,
                                                   'http://s/ok', 'http://s/ko', annonce_id=1)
        self.assertEqual(url, 'https://stripe/session')
        # vendeur_alaune_7 est un paiement UNIQUE -> mode 'payment'
        self.assertEqual(m.call_args[0][1]['mode'], 'payment')

    def test_activer_avantages_vendeur_met_a_la_une(self):
        u = User.objects.create_user('vendeur', 'v@x.fr', 'x')
        a = Annonce.objects.create(reference='ABO-1', user=u, titre='Bien', type_transaction='V',
                                   prix=100000, mise_en_avant=False)
        abo = Abonnement.objects.create(user=u, type_abonnement='vendeur_alaune_7', annonce=a)
        paiements.activer_avantages(abo)
        a.refresh_from_db()
        self.assertTrue(a.mise_en_avant)
        abo.refresh_from_db()
        self.assertIsNotNone(abo.date_fin)

    @override_settings(STRIPE_SECRET_KEY='')
    def test_souscrire_inactif_redirige(self):
        u = User.objects.create_user('u2', 'u2@x.fr', 'x')
        a = Annonce.objects.create(reference='ABO-2', user=u, titre='B', type_transaction='S', prix_nuit=90)
        self.client.force_login(u)
        r = self.client.get(f"/abonnement/souscrire/vendeur_alaune_7/?annonce={a.id}")
        self.assertEqual(r.status_code, 302)  # redirige vers tarifs (paiements inactifs)


class NavigationTests(TestCase):
    def test_header_et_homepage_exposent_les_parcours(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Acheter')
        self.assertContains(r, 'Courte')          # "Courte durée" dans la nav + homepage
        self.assertContains(r, 'Deposer une annonce')
