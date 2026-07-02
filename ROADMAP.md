# 🗺️ Roadmap Social Immo v3 — "Passer un cap"

> **Suivi en direct** : ce fichier est mis à jour et poussé sur GitHub à chaque étape.
> Consulte-le depuis ton téléphone : https://github.com/CharlT24/social-immo/blob/main/ROADMAP.md

## 🔙 Rollback (en cas de problème)

L'état stable avant les travaux est sauvegardé :
- **Tag** : `v2-stable`
- **Branche** : `backup-avant-v3`

Pour tout annuler : `git checkout main && git reset --hard v2-stable && git push --force origin main`

## 🎯 Vision

Un site immobilier d'avenir mêlant **SeLoger + Pinterest + Instagram** :
- Les **agences** publient via flux XML (existant)
- Les **pros du bâtiment** montrent leurs réalisations et se font trouver
- Les **particuliers** déposent leurs biens, aidés par une **IA maison** (estimation, photos, rédaction)
- Les **inspirations** créent le trafic et l'envie (parcourir → contacter les pros → vendre)
- **Pré-visite immersive** des biens depuis les photos

## 📋 Avancement

| Phase | Contenu | Statut |
|-------|---------|--------|
| 0 | Sauvegarde rollback (tag `v2-stable` + branche backup) | ✅ Terminé |
| 1 | **Design system global** : animations fluides, scroll-reveal, toasts, carte annonce unifiée, footer enrichi, **5 dashboards unifiés sur base.html** | ✅ Terminé |
| 2 | **Feed Inspirations** façon Pinterest : feed unifié agences+pros, scroll infini, pagination serveur | ✅ Terminé |
| 3 | **Espace Pros du bâtiment** : recherche par métier, pros à la une sur la carte, annuaire enrichi | ✅ Terminé |
| 4 | **IA maison** (compatible o2switch) : ✨ estimation instantanée par comparables sur `/estimer/`, amélioration auto des photos (Pillow), assistant de rédaction au dépôt d'annonce | ✅ Terminé |
| 5 | **Pré-visite immersive** : diaporama plein écran façon story (Ken Burns, barres de progression, swipe) sur chaque annonce | ✅ Terminé |
| 6 | **QA + docs** : 34 pages testées (tous rôles), documentation à jour | ✅ Terminé |

## 📋 Avancement v3.1 — "Mieux que parfait" (2026-07-02)

| Phase | Contenu | Statut |
|-------|---------|--------|
| 7 | **Prêt pour la prod** : SECRET_KEY obligatoire hors DEBUG, image Open Graph générée | ✅ Terminé |
| 8 | **Moteur de trafic** : alertes email (CRON `envoyer_alertes`), pages SEO `/immobilier/<ville>/` avec prix au m², partage des inspirations avec OG dédié | ✅ Terminé |
| 9 | **Boucle particulier ↔ pro** : pros du secteur sur chaque annonce, stats vendeur (vues, favoris, conseil prix vs estimation) | ✅ Terminé |
| 10 | **Performance** : Tailwind compilé (fin du CDN, 71 Ko de CSS statique), miniatures 480px auto, carte Leaflet des résultats (CRON `geocoder_villes`) | ✅ Terminé |
| 11 | **Dette technique** : vraie FK Annonce→Agence (migrations 0028/0029), legacy supprimé (Decoration/Partenaire/registration login), décorateur staff sur 22 vues admin | ✅ Terminé |

## ⚙️ CRON à configurer sur o2switch (après déploiement)

```bash
# Import des flux XML (déjà prévu)
python manage.py import_xml --all-agences
# Puis dans l'ordre, à la suite :
python manage.py geocoder_villes      # géocode les nouvelles villes (carte)
python manage.py envoyer_alertes      # emails des recherches sauvegardées
python manage.py generer_miniatures   # miniatures des images uploadées
```

## 🎨 Rebuild du CSS (si de nouvelles classes Tailwind sont ajoutées)

```bash
npx tailwindcss@3.4.17 -c tailwind.config.js -i static/src/input.css -o static/css/app.css --minify
```

## 📋 Avancement v4 — "Le vendeur particulier devient un pro" (2026-07-02)

| Phase | Contenu | Statut |
|-------|---------|--------|
| 12 | **Ventes réelles DVF** : estimation ancrée sur les ventes notariées (Etalab), exemples de biens comparables vendus (même ville, même type, taille proche) affichés sur /estimer/ | ✅ Terminé |
| 13 | **Assistant de dépôt 4 étapes** : Bien → Photos → Prix → Annonce ; prix suggéré en direct avec ventes réelles, photos réordonnables, score de qualité, aperçu exact côté acheteur | ✅ Terminé |
| 14 | **Célébration + diffusion** : page "Votre bien est en ligne 🎉", partage WhatsApp/Facebook/lien, QR code à imprimer, compteur d'acheteurs en alerte ; rapport hebdo vendeur (CRON `rapport_vendeurs`) | ✅ Terminé |

> CRON à ajouter : `python manage.py rapport_vendeurs` (1×/semaine, lundi matin).

## 📋 Avancement v5 — "Remplacer SeLoger/LeBonCoin/Zefir" (2026-07-02)

| Phase | Contenu | Statut |
|-------|---------|--------|
| 15 | **Tunnel vendeur 3 portes** après l'estimation : Vendre avec un pro (lead + consentement RGPD), Vendre moi-même (wizard), Suivre le marché (alerte 1 clic) | ✅ Terminé |
| 16 | **Devis travaux** `/devis/` : 3 artisans du département rappellent (emails + dashboard pro) ; boutons sur annonce, page ville, annuaire | ✅ Terminé |
| 17 | **Baromètre public des prix** `/barometre/` : médianes des ventes réelles par commune + évolution, s'enrichit à chaque estimation | ✅ Terminé |
| 18 | **Panneau "À VENDRE" A4** imprimable avec QR code (celebration + dashboard) + section homepage "Vendez comme un pro. Gratuitement." + kit copier-coller | ✅ Terminé |

- 📋 Kit de prospection prêt à copier-coller : [LEADS-COPIER-COLLER.md](LEADS-COPIER-COLLER.md)
- 💰 Plan 1 M€ : [MONETISATION.md](MONETISATION.md) — prochaine brique payante : **Stripe** (il me faudra tes clés API, guide au moment venu)

## 📌 Prochaine étape : v4

- Backlog UX complet : [AMELIORATIONS-UX.md](AMELIORATIONS-UX.md) — priorité 1 = le dépôt d'annonce "comme un pro" (assistant 4 étapes, prix suggéré en direct, aperçu, kit de diffusion, rapport hebdo vendeur)
- Stratégie réseaux sociaux : [STRATEGIE-RESEAUX.md](STRATEGIE-RESEAUX.md) — LinkedIn (agences + artisans) et Facebook (particuliers, groupes locaux)

## 🔮 Plus tard (nécessite plus que o2switch)

- Vraie reconstruction 3D depuis photos (type Matterport) — demande du GPU, à faire via un service externe (Vercel + API, Replicate, etc.)
- IA générative pour home-staging virtuel des photos
- Application mobile

## 📓 Journal

- **2026-07-02** : Démarrage v3. Rollback sécurisé, scan complet du code lancé, roadmap créée.
- **2026-07-02** : Phase 1 terminée — design system global (scroll-reveal, transitions de page, toasts, shimmer images), carte annonce unifiée (3 duplications supprimées), les 5 dashboards héritent enfin de base.html (nav commune partout).
- **2026-07-02** : Phase 4 terminée — l'estimation est maintenant **réelle et instantanée** (comparables de la base → médiane €/m², repli barème national × coefficient départemental), fourchette + fiabilité affichées, puis mise en relation pro. Assistant de rédaction (titres + description) et optimisation automatique des photos (Pillow) au dépôt d'annonce particulier. 19 pages smoke-testées en 200.
- **2026-07-02** : Phase 2 terminée — feed Inspirations unifié (agences + pros mélangés, "à la une" en tête) avec pagination serveur et scroll infini.
- **2026-07-02** : Phase 3 terminée — annuaire pros : recherche par corps de métier (chips + select), pros à la une sous la carte de France.
- **2026-07-02** : Phase 5 terminée — bouton "Pré-visiter" sur chaque annonce : visite immersive plein écran façon story Instagram (effet Ken Burns, lecture auto, swipe mobile, clavier).
- **2026-07-02** : Phase 6 terminée — **v3 livrée**. 34 pages testées sur les 6 rôles (public, particulier, pro, agence, conseiller, admin), toutes en 200. Pipeline photo validé (4000px → 1920px, luminosité corrigée).
- **2026-07-02 (v3.1)** : Phases 7 à 11 livrées dans la foulée — sécurisation prod (SECRET_KEY), image Open Graph, **alertes email** sur recherches sauvegardées, **pages SEO par ville** avec prix au m², partage d'inspirations, pros du secteur sur chaque annonce, stats vendeur avec conseil prix, **Tailwind compilé** (fin du CDN), miniatures automatiques, **carte Leaflet** des résultats, vraie FK Annonce→Agence, suppression du legacy et décorateur staff. QA finale : 38 vérifications sur les 6 rôles, zéro échec.

## ✅ Reprendre le travail sur un autre PC

```bash
git clone https://github.com/CharlT24/social-immo.git
cd social-immo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
