# 🚀 Lancement sur o2switch — le guide complet (une seule fois, puis autonomie totale)

> Après ce guide, le site s'auto-gère : inscriptions, imports, alertes,
> facturation, SAV, entretien, sauvegardes. Tu n'interviens qu'en cas de crash
> (et tu recevras un email s'il y en a un).

## 1. Installer le site (~30 min, une fois)

Dans cPanel o2switch → **Setup Python App** : crée une application Python 3.11,
racine `social-immo`, puis dans le terminal de l'app :

```bash
git clone https://github.com/CharlT24/social-immo.git .
pip install -r requirements.txt
```

## 2. Le fichier `.env` (copie-colle et remplis)

Crée `~/social-immo/.env` :

```env
# — Obligatoire —
SECRET_KEY=REMPLACE_MOI            # genere avec : python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=False
ALLOWED_HOSTS=social-immo.com,www.social-immo.com
CSRF_TRUSTED_ORIGINS=https://social-immo.com,https://www.social-immo.com

# — Base MySQL (cPanel > Bases de donnees MySQL) —
MYSQL_HOST=localhost
MYSQL_DATABASE=xxxx_socialimmo
MYSQL_USER=xxxx_immo
MYSQL_PASSWORD=REMPLACE_MOI

# — Email (cPanel > Comptes de messagerie : cree noreply@social-immo.com) —
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mail.social-immo.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
EMAIL_HOST_USER=noreply@social-immo.com
EMAIL_HOST_PASSWORD=REMPLACE_MOI
DEFAULT_FROM_EMAIL=noreply@social-immo.com

# — Toi (rapports autopilot + alertes erreurs 500 + tickets support) —
ADMIN_EMAIL=charles.tudela@gmail.com

# — Stripe (voir section 5, a remplir quand tu veux encaisser) —
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_AGENCE=
STRIPE_PRICE_PRO=
STRIPE_PRICE_PACK=
```

## 3. Initialiser

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Puis dans cPanel, redémarre l'application Python. Le site est en ligne. ✅

## 4. Le CRON unique (cPanel → Tâches Cron)

**Une seule ligne à ajouter**, tous les jours à 6h :

```
0 6 * * * cd ~/social-immo && source ~/virtualenv/social-immo/3.11/bin/activate && python manage.py autopilot >> ~/autopilot.log 2>&1
```

L'autopilot fait TOUT, chaque jour :
- importe les flux XML de toutes les agences inscrites
- géocode les nouvelles villes (carte)
- envoie les alertes email aux acheteurs
- génère les miniatures manquantes
- met en pause les annonces particuliers de +60 jours (email de relance
  automatique, bouton "Republier" dans leur compte)
- expire les boosts Pack Vendeur terminés
- envoie le rapport hebdo aux vendeurs (le lundi)
- sauvegarde la base (7 jours conservés dans `~/social-immo/backups/`)
- **t'envoie le rapport par email** — objet "OK" ou "⚠ N erreur(s)"

## 5. Activer les paiements Stripe (~20 min, quand tu veux)

1. Crée ton compte sur **stripe.com** (SIRET + IBAN demandés).
2. **Catalogue → Produits** : crée 3 produits :
   - "Premium Agence" → tarif récurrent mensuel (ex. 149 €/mois) → copie le `price_...`
   - "Artisan Pro" → tarif récurrent mensuel (ex. 29 €/mois) → copie le `price_...`
   - "Pack Vendeur" → tarif unique (ex. 39 €) → copie le `price_...`
3. **Développeurs → Clés API** : copie la clé secrète `sk_live_...`
4. **Développeurs → Webhooks → Ajouter un endpoint** :
   - URL : `https://social-immo.com/stripe/webhook/`
   - Événements : `checkout.session.completed`, `customer.subscription.deleted`,
     `invoice.payment_failed`
   - Copie le secret `whsec_...`
5. Colle les 5 valeurs dans le `.env`, redémarre l'app. **C'est tout** :
   la page /tarifs/ passe en mode paiement, les avantages s'activent et se
   retirent automatiquement, les factures partent par email (Stripe),
   la résiliation est self-service (portail Stripe).

## 6. Surveillance externe (5 min, gratuit)

Crée un compte **uptimerobot.com** (gratuit) → "Add Monitor" →
`https://social-immo.com/` toutes les 5 min → alerte sur ton email/téléphone
si le site tombe. C'est le seul cas où tu interviens.

## 7. En cas de crash — le plan de secours

```bash
# Voir ce qui se passe
tail -50 ~/social-immo/django_errors.log
tail -50 ~/autopilot.log

# Revenir a la derniere version qui marchait
cd ~/social-immo && git log --oneline -5     # repere le commit
git reset --hard <commit>                     # ou : git reset --hard v2-stable

# Restaurer la base depuis une sauvegarde
python manage.py flush --noinput
zcat backups/backup-XXXX.json.gz | python manage.py loaddata --format=json -
```

## ✅ Récap : ce qui tourne tout seul

| Quoi | Comment |
|---|---|
| Inscriptions particuliers / pros / agences | Self-service, emails de bienvenue auto |
| Annonces agences | Flux XML importés chaque jour (autopilot) |
| Annonces particuliers | Dépôt guidé, expiration + relance auto à 60 j |
| Alertes acheteurs | Email quotidien automatique |
| Paiements, factures, résiliations | Stripe Checkout + portail + webhook |
| SAV niveau 1 | FAQ /aide/ + tickets avec accusé de réception |
| Erreurs 500 | Email automatique à ADMIN_EMAIL |
| Sauvegardes | Quotidiennes, rotation 7 jours |
| Toi | Tu lis un email de rapport par jour. C'est tout. |
