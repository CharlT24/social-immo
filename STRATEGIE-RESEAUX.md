# 📣 Stratégie LinkedIn + Facebook — Social Immo

> Objectif : faire connaître le site, attirer des **agences et artisans** (LinkedIn)
> et des **particuliers vendeurs/acheteurs** (Facebook), avec ~30 min/jour.

## 🧭 Les deux réseaux n'ont pas le même rôle

| | LinkedIn | Facebook |
|---|---|---|
| Cible | Agences immo, artisans, décorateurs, diagnostiqueurs | Particuliers vendeurs/acheteurs, trafic local |
| Objectif | Qu'ils créent leur profil pro / branchent leur flux XML | Qu'ils déposent un bien, créent une alerte, parcourent les inspirations |
| Ton | Fondateur qui construit ("build in public") | Utile, local, visuel |

## 💼 LinkedIn — plan sur 90 jours

### Semaine 0 : les fondations (1 soirée)
1. **Profil personnel optimisé** : titre "Je construis Social Immo — l'immobilier qui inspire (biens + déco + artisans)" ; bannière aux couleurs du site ; section "Sélection" avec le lien du site.
2. **Page entreprise Social Immo** : logo, description, lien, 3 premiers posts.
3. Abonne-toi à 50 comptes : agents immo de ta région, artisans, médias immo (MySweetImmo, Immomatin...).

### Rythme : 3 posts/semaine (lun-mer-ven)
- **Lundi — Chiffres du marché** : recycle tes pages SEO villes ! "Prix médian à Caen ce mois-ci : 2 400 €/m² (calculé sur X biens). Détail par ville → [lien /immobilier/caen/]". Contenu infini, autorité locale, trafic SEO.
- **Mercredi — Coulisses produit** ("build in public") : "Cette semaine j'ai ajouté l'estimation instantanée / la pré-visite immersive... voilà pourquoi". Ces posts attirent les pros curieux ET créent de la sympathie.
- **Vendredi — Artisan à l'honneur** : avant/après d'une réalisation d'un pro inscrit (avec son accord), en le **taguant** → il partage → sa communauté te découvre. C'est le post à plus forte portée.

### Prospection douce (15 min/jour)
- Commente 3 posts d'agents/artisans de ta région (utile, pas vendeur).
- 5 invitations/jour à des artisans avec ce message :
  > "Bonjour [prénom], je développe Social Immo, un site immobilier local qui met en avant les réalisations des artisans (photos avant/après, fiche pro, mise en relation avec les vendeurs). L'inscription est gratuite — est-ce que je peux vous créer un profil d'exemple avec 2-3 photos de vos réalisations ?"
- Offre de lancement : "les 50 premiers artisans inscrits ont la mise en avant gratuite" (l'option existe déjà dans le back-office).

### 10 idées de posts prêtes à l'emploi
1. "Pourquoi j'ai construit un site immobilier qui ressemble à Pinterest" (histoire fondateur)
2. Prix au m² de 3 villes de ta région (carrousel)
3. Avant/après d'une rénovation d'un artisan inscrit
4. "Un particulier peut-il vendre comme un pro ? Voici les 5 outils que je lui donne" (estimation, photos optimisées, alertes...)
5. Démo vidéo 30 s de la pré-visite immersive
6. "Ce que 90 % des annonces de particuliers ratent (et comment on le corrige automatiquement)" (photos sombres → Pillow)
7. Les coulisses : "j'héberge une IA d'estimation sur un simple hébergement mutualisé, voilà comment"
8. Appel : "Vous êtes agent immobilier ? Votre flux XML se branche en 5 minutes"
9. Témoignage du 1er vendeur / 1er artisan
10. Bilan mensuel en chiffres (biens, inspirations, alertes créées) — transparence

## 📘 Facebook — plan local

### Semaine 0
1. **Page Facebook Social Immo** (logo, bannière, bouton "En savoir plus" → site).
2. Rejoins 10-15 **groupes locaux** : "Immobilier [ta région]", "Vivre à [ville]", "Bons plans [ville]", groupes de quartier. Lis les règles de chaque groupe (beaucoup interdisent la pub directe → y aller en apportant de la valeur).

### Rythme : 1 post/jour sur la page (10 min, contenu recyclé du site)
- **Inspiration du jour** : une photo du feed avec le lien de partage (l'URL `/inspirations/photo/...` a déjà la photo en aperçu Open Graph — c'est fait pour ça).
- **Bien coup de cœur de la semaine** (avec accord du vendeur/de l'agence).
- **Le chiffre de la semaine** : prix m² d'une ville → lien page SEO.
- **Conseil vendeur** : "3 réglages photo qui changent une annonce" etc.

### Dans les groupes (2-3 interventions/semaine, pas plus)
- Réponds aux posts "je cherche un plombier/peintre" → lien vers l'annuaire pros du département.
- Réponds aux posts "je cherche un T3 sur [ville]" → lien vers la recherche filtrée + "créez une alerte, vous recevrez les nouveaux biens".
- Poste le "prix au m² du mois" de la ville du groupe (valeur pure, pas de pub) avec le lien.

### Publicité (quand il y aura ~50 biens actifs)
- Budget test : 5-10 €/jour sur 2 semaines.
- Campagne 1 : "Estimez votre bien gratuitement en 30 secondes" → page /estimer/ (c'est l'aimant à vendeurs).
- Campagne 2 : carrousel d'inspirations → feed.
- ⚠️ **Prérequis technique** : installer le pixel Meta exige une **bannière cookies RGPD** sur le site (voir AMELIORATIONS-UX.md, priorité 3). Sans pub, pas besoin.

## 📅 Ta semaine type (~3 h au total)
- Lun/Mer/Ven : 1 post LinkedIn (20 min) + 1 post Facebook (5 min)
- Mar/Jeu : posts Facebook seulement + commentaires LinkedIn
- Chaque jour : 5 invitations artisans + réponses aux groupes (15 min)
- Dimanche : programmer la semaine (Meta Business Suite permet de programmer les posts Facebook gratuitement)

## 🤖 Ce que je peux automatiser côté site (à la demande)
- Une commande `generer_post_semaine` : compose automatiquement le texte + les liens du "chiffre de la semaine" et du "top 3 inspirations" — tu n'as plus qu'à copier-coller.
- Des pages de destination dédiées par campagne (ex. /estimer/ est déjà parfaite).
- Des images de partage par ville (prix m² sur fond aux couleurs du site, générées avec Pillow comme l'OG).
