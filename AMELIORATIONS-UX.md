# 🚀 Backlog v4 — Expérience utilisateur extraordinaire

> Objectif central : **quand un particulier dépose son bien, il doit se sentir
> comme un professionnel de l'immobilier**. Facile, valorisant, et son bien
> est diffusé immédiatement.
> Suivi : chaque bloc peut devenir une phase (même méthode que v3/v3.1).

## 🏆 Priorité 1 — Le dépôt d'annonce "comme un pro"

| # | Amélioration | Effet ressenti |
|---|--------------|----------------|
| 1 | **Assistant en 4 étapes** (Bien → Photos → Prix → Aperçu) avec barre de progression, au lieu du long formulaire actuel | "Je suis guidé comme par un agent" |
| 2 | **Prix suggéré en direct** à l'étape Prix : le moteur d'estimation (déjà en place) affiche "Les biens similaires du secteur : 285 000 € (fourchette 256-313k)" et pré-remplit | "Je fixe mon prix comme un pro, avec des données" |
| 3 | **Aperçu réel avant publication** : rendu exact de la carte annonce + de la page détail ("Voici ce que verront les acheteurs") | "C'est du niveau SeLoger" |
| 4 | **Score de qualité d'annonce** : "Annonce complète à 70 % — ajoutez 2 photos et le DPE pour être mieux classé" (jauge + conseils) | Gamification, annonces plus complètes |
| 5 | **Photos niveau pro** : glisser-déposer, réordonnancement, choix de la photo principale, aperçu avant/après de l'optimisation automatique (le moteur Pillow existe déjà — montrer le résultat vend la feature) | "Mes photos ont l'air pro" |
| 6 | **Écran de célébration post-publication** : "🎉 Votre bien est en ligne !" + **kit de diffusion** : boutons WhatsApp/Facebook/copier le lien, QR code à imprimer, et surtout : **"Votre bien vient d'être envoyé à X acheteurs qui ont une alerte correspondante"** (les alertes existent — ce chiffre est calculable et c'est un effet wow énorme) | "Mon bien est déjà diffusé" |
| 7 | **Rapport hebdo vendeur par email** (CRON) : vues, favoris, conseil prix, comparaison avec les biens du secteur | "J'ai un agent qui me rend des comptes" |
| 8 | **Messagerie interne** acheteur↔vendeur (les DemandeContact existent, il manque le fil de réponse côté site) + badge "Répond vite" | Confiance, réactivité |
| 9 | **Aide DPE intégrée** : explication simple + lien direct vers les diagnostiqueurs du site (boucle pro, le métier existe dans l'annuaire) | Le site accompagne, et nourrit les pros |

## 🥈 Priorité 2 — Expérience visiteur

- **Recherche par rayon** ("dans un rayon de 20 km") — VilleGeo a déjà les coordonnées, il manque le calcul de distance.
- **Comparateur de favoris** : tableau côte à côte de 2-3 biens favoris (prix/m², DPE, mensualité — les propriétés existent sur le modèle).
- **PWA** : manifest + service worker → le site s'installe comme une app sur le téléphone (gratuit, gros effet).
- **Préchargement au survol** des liens (style instant.page, 3 lignes de JS) → navigation perçue instantanée.
- **Historique de prix** sur une annonce ("prix baissé de 10 000 € le 12/06") — tracer les changements à l'import.
- **Onboarding 1ère visite** : mini-bandeau "Acheteur ? Vendeur ? Curieux ?" qui personnalise la homepage.

## 🥉 Priorité 3 — Confiance & conformité (avant d'investir en pub)

- **Bannière cookies RGPD** : indispensable AVANT d'installer le pixel Meta ou Google Analytics (aucun tracker aujourd'hui, donc pas urgent, mais bloquant pour la stratégie pub).
- **Page "Qui sommes-nous"** avec photo et histoire — la confiance est le nerf de l'immobilier entre particuliers.
- **Avis vendeurs** ("j'ai vendu en 3 semaines") en homepage.
- **Vérification email obligatoire** au dépôt d'annonce (aujourd'hui optionnelle) → moins de spam, plus de sérieux.

## 📈 Mesure (sinon on améliore à l'aveugle)

- Compteur simple côté serveur (modèle StatJour : visites, dépôts, alertes créées, contacts) affiché dans le dashboard admin — pas besoin de Google Analytics pour commencer, et zéro cookie.
