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
| 7 | **Prêt pour la prod** : SECRET_KEY/DEBUG sécurisés, nettoyage du repo (.gitignore, db/logs), image Open Graph | 🔄 En cours |
| 8 | **Moteur de trafic** : alertes email sur recherche sauvegardée (+ CRON), pages SEO par ville avec prix au m², partage des inspirations | ⏳ À venir |
| 9 | **Boucle particulier ↔ pro** : pros du secteur sur chaque annonce, stats vendeur (vues, favoris, conseil prix vs estimation) | ⏳ À venir |
| 10 | **Performance** : Tailwind compilé (fin du CDN), miniatures d'images uploadées, carte des résultats (Leaflet) | ⏳ À venir |
| 11 | **Dette technique** : vraie FK Annonce→Agence, suppression du legacy (Decoration/Partenaire/registration), décorateur staff | ⏳ À venir |

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

## ✅ Reprendre le travail sur un autre PC

```bash
git clone https://github.com/CharlT24/social-immo.git
cd social-immo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
