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
| 1 | **Design system global** : animations fluides, scroll-reveal, composants réutilisables (carte annonce unique), skeletons, footer enrichi | 🔄 En cours |
| 2 | **Feed Inspirations** façon Pinterest : masonry, scroll infini, lightbox immersive, tags, liens vers les pros | ⏳ À venir |
| 3 | **Espace Pros du bâtiment** : portfolios de réalisations, annuaire par métier/ville, fiches attractives | ⏳ À venir |
| 4 | **IA maison** (compatible o2switch) : estimation par comparables, amélioration auto des photos, assistant de rédaction d'annonce | ⏳ À venir |
| 5 | **Pré-visite immersive** : diaporama plein écran pièce par pièce, support photos 360°, bases pour la 3D | ⏳ À venir |
| 6 | **QA + docs** : vérification de toutes les pages, mise à jour CLAUDE.md, push final | ⏳ À venir |

## 🔮 Plus tard (nécessite plus que o2switch)

- Vraie reconstruction 3D depuis photos (type Matterport) — demande du GPU, à faire via un service externe (Vercel + API, Replicate, etc.)
- IA générative pour home-staging virtuel des photos
- Application mobile

## 📓 Journal

- **2026-07-02** : Démarrage v3. Rollback sécurisé, scan complet du code lancé, roadmap créée.
