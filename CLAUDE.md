# Social Immo - Contexte Projet

## Description
Site immobilier social (type LeBonCoin) avec import automatique depuis un CRM via flux XML.

## Stack technique
- **Framework** : Django 5.2 / Python 3.11
- **BDD** : SQLite (dev) / MySQL o2switch (prod)
- **CSS** : Tailwind CDN, design Apple-inspired
- **Dependances cles** : lxml (XML), requests (HTTP), mysqlclient (MySQL)

## Structure du projet
```
social_immo/          # Config Django (settings, urls, wsgi)
listings/             # App principale
  models.py           # 20 modeles : Annonce, Photo, Agence, ProProfile,
                      # ProRealisation, Estimation, DemandeContact, etc.
  views.py            # ~3000 lignes : public, particulier, pro, agence,
                      # conseiller, admin + APIs AJAX
  services/           # "IA maison" (100% Python, compatible o2switch)
    estimation.py     # Estimation par comparables (mediane prix/m2 ville
                      # -> departement -> bareme national x coef dept)
    photos.py         # Amelioration auto photos (Pillow : contraste,
                      # luminosite, nettete, resize 1920px)
    redaction.py      # Suggestions titre + description d'annonce
  urls.py             # Routes (dont /api/estimer/, /api/suggerer-annonce/)
  management/commands/
    import_xml.py     # Commande d'import XML (HTTP + fichier + FTP)
templates/            # Templates Django — TOUS heritent de base.html
  base.html           # Design system : Tailwind CDN + config apple-*,
                      # scroll-reveal, toasts, helpers JS globaux
                      # (getCookie, showToast, toggleFav, hideCard)
  listings/includes/  # Composants : carte_annonce.html, inspi_items.html
  listings/           # Pages (homepage, search, inspirations, dashboards...)
  account/            # Templates allauth (actifs)
  registration/       # Legacy Django auth (a nettoyer)
static/               # CSS/JS/images (vide, utilise CDN)
export.xml            # Donnees de test (3 annonces)
ROADMAP.md            # Suivi des travaux v3 (mis a jour a chaque phase)
```

## Fonctionnalites v3 (2026-07)
- **Estimation instantanee** `/estimer/` : moteur par comparables + fourchette + fiabilite, puis lead pro
- **Feed Inspirations** : agences + pros melanges, scroll infini (`?partial=1&page=N`)
- **Pre-visite immersive** : bouton "Pre-visiter" sur les annonces (Ken Burns plein ecran, style story)
- **Assistant depot particulier** : suggestions titre/description + optimisation photos (checkbox)
- **Annuaire pros** : filtre par metier (`?metier=peintre`), pros a la une sur la carte
- **Rollback** : tag `v2-stable` / branche `backup-avant-v3` sur GitHub

## Fonctionnalites v3.1 (2026-07)
- **Alertes email** : RechercheSauvegardee + CRON `envoyer_alertes` ;
  bouton "Creer une alerte" sur la recherche, gestion dans /mon-compte/?tab=acquereur
- **Pages SEO villes** `/immobilier/<slug>/` : prix m2 median, biens, pros du dept, sitemap 'villes'
- **Partage inspirations** : /inspirations/photo/<type>/<id>/ avec og:image de la photo
- **Pros du secteur** sur chaque annonce (meme departement) + stats vendeur
  (vues, favoris, conseil prix vs estimation) dans le dashboard particulier
- **Tailwind COMPILE** (plus de CDN !) : static/css/app.css commite.
  IMPORTANT : toute NOUVELLE classe Tailwind exige un rebuild :
  `npx tailwindcss@3.4.17 -c tailwind.config.js -i static/src/input.css -o static/css/app.css --minify`
- **Miniatures** : Photo.image_thumb / ProRealisationPhoto.image_thumb (auto a l'upload,
  `src_thumb` dans les grilles, CRON `generer_miniatures` pour rattrapage)
- **Carte des resultats** : Leaflet a la demande, VilleGeo rempli par CRON `geocoder_villes`
- **FK Annonce.agence** : vraie relation (remplie a l'import) ; `client_reference`
  reste uniquement la cle texte du flux XML
- **SECRET_KEY obligatoire** en prod (DEBUG=False) — definir dans .env

## Modeles
### Annonce
- `reference` (unique, cle d'import) - ex: "CT-00123"
- `client_reference` - reference agence (ex: "OI123")
- `titre`, `texte`, `code_type`, `libelle_type`
- `contact_nom`, `contact_email`, `contact_telephone`
- `code_postal`, `ville`
- `nb_pieces`, `nb_chambres`, `surface`, `surface_sejour`, `surface_terrain`, `annee_construction`
- DPE : `dpe_etiquette_conso/ges`, `dpe_valeur_conso/ges`, `dpe_date_realisation`, `montant_depenses_energies_min/max`
- Transaction : `type_transaction` (V/L/S/F/B/W/G), `prix`, `frais_agence`, `honoraires_payeurs`
- Location : `loyer_mensuel`, `charges_locatives`, `depot_garantie`, `honoraires_location`
- Meta : `created_at`, `updated_at`, `is_active`

### Photo
- `annonce` (FK), `url`, `ordre`

### Commentaire
- `annonce` (FK), `auteur` (FK User), `texte`, `created_at`

### Favori
- `user` (FK), `annonce` (FK) - unique ensemble

## Import XML (commande `import_xml`)
### Source du flux
```
GET https://logiciel-immo-clean.vercel.app/api/export/socialimmo/[agenceId]
```
- Retourne XML, pas d'auth requise
- Appel 1-2x/jour (CRON recommande)

### Usage
```bash
python manage.py import_xml --agence-id OI123          # Via HTTP
python manage.py import_xml --url https://...           # URL complete
python manage.py import_xml --file export.xml           # Fichier local
python manage.py import_xml --agence-id OI123 --dry-run # Test sans ecriture
```

### Logique "annule et remplace"
1. Fetch XML → parser chaque `<annonce>`
2. Cle unique = `<reference>`
3. Upsert : create ou update par reference
4. Apres import : biens actifs absents du flux → `is_active=False`
5. Si un bien revient dans le flux → reactive (`is_active=True`)

## Variables d'environnement
```
SECRET_KEY=...
DEBUG=True/False
ALLOWED_HOSTS=domaine.com
SOCIALIMMO_AGENCE_ID=OI123
SOCIALIMMO_FEED_URL=https://logiciel-immo-clean.vercel.app/api/export/socialimmo/

# MySQL o2switch
MYSQL_HOST=localhost
MYSQL_DATABASE=...
MYSQL_USER=...
MYSQL_PASSWORD=...

# Ou DATABASE_URL (PostgreSQL/MySQL)
DATABASE_URL=mysql://user:pass@host:3306/dbname
```

## Auth
- Django auth standard (login, signup, logout)
- Dashboard : `@login_required` + `is_staff`
- Commentaires/Favoris : `@login_required`
- Annonces : lecture publique

## Migrations
- 0001 : Annonce + Photo
- 0002 : Commentaire
- 0003 : Favori
- 0004 : Champs XML enrichis (DPE complet, surfaces, frais, location)
