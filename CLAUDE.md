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

## Fonctionnalites v4 (2026-07) — vendeur particulier "pro"
- **DVF** : listings/services/dvf.py — ventes reelles notariees (Etalab, gratuit,
  sans cle), cache 90j en base (CommuneDVF/VenteDVF, migration 0031).
  L'estimation privilegie les ventes reelles (zone='dvf') et retourne des
  'exemples' (ventes comparables meme ville/type/surface ±30%)
- **Depot particulier = wizard 4 etapes** (particulier_creer_annonce.html) :
  Bien -> Photos (reordonnables) -> Prix (estimation live + ecart marche) ->
  Annonce (assistant, score qualite, apercu carte)
- **Post-publication** : /mon-compte/annonce/<id>/publiee/ — partage
  WhatsApp/Facebook/lien, QR code (qrcodejs CDN), compteur
  RechercheSauvegardee.acheteurs_pour(annonce)
- **CRON rapport_vendeurs** (hebdo) : vues, favoris, conseil prix par email

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
- CRON prod : toutes les 30 min (voir section "Prod o2switch" pour la forme obligatoire)

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

## Prod o2switch (deploye — compte tuch9508, serveur plouf)
- App : `~/social-immo`, virtualenv cPanel `~/virtualenv/social-immo/3.11/`
  (son `bin/python` est un script bash wrapper cPanel, pas un binaire)
- Redemarrer Passenger : `touch ~/social-immo/tmp/restart.txt`

### REGLE CRON (incident 2026-07-14 : saturation limite de processus)
Toute tache CRON DOIT etre de la forme :
```
flock -n ~/locks/<nom>.lock timeout <duree> bash -c 'cd ~/social-immo && ~/virtualenv/social-immo/3.11/bin/python manage.py <commande> >> <log> 2>&1'
```
- `bash -c '...'` englobe TOUTE la commande. JAMAIS `flock ... cd dir && python ...` :
  le `&&` couperait la commande, flock ne verrouillerait que le `cd` et python
  tournerait hors verrou et hors repertoire (c'est ce qui a cause l'incident).
- `flock -n` (fichier distinct par tache dans `~/locks/`) = une seule instance a la fois
- `timeout` = tue un job bloque (25m pour import_xml qui tourne toutes les 30 min,
  4h pour autopilot quotidien a 6h)

### Crontab en place (2026-07-14)
- `import_xml` : toutes les 30 min, log `~/social-immo/cron_import.log`
- `autopilot` : 6h00, log `~/autopilot.log` (enchaine import --all-agences,
  geocodage, alertes, miniatures, siret, rapports via call_command, 1 seul processus)

### Si le serveur re-sature (`fork: Resource temporarily unavailable` en SSH)
1. Taper A LA MAIN `kill -9 -1` (builtin bash, marche sans fork ; tue aussi la
   session SSH — deconnexion brutale = succes, se reconnecter ensuite)
2. `ps -u $USER -o pid,etime,cmd` pour identifier ce qui s'empilait
3. Verifier `crontab -l` respecte la regle ci-dessus ; sinon suspecter Passenger

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
