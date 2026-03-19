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
  models.py           # Annonce, Photo, Commentaire, Favori
  views.py            # listing_list, listing_detail, dashboard, signup, toggle_favorite
  urls.py             # Routes
  admin.py            # Interface admin
  forms.py            # CommentaireForm
  management/commands/
    import_xml.py     # Commande d'import XML (HTTP + fichier)
templates/            # Templates Django
  base.html           # Layout principal (Tailwind + Apple design)
  listings/           # listing_list, listing_detail, dashboard
  registration/       # login, signup
static/               # CSS/JS/images (vide, utilise CDN)
export.xml            # Donnees de test (3 annonces)
```

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
