#!/bin/bash
# Deploiement Social Immo sur o2switch — partie automatisable.
# A lancer DEPUIS le dossier du site, APRES avoir active le virtualenv
# de l'app Python (cPanel affiche la commande "source .../activate")
# et APRES avoir cree le fichier .env (voir DEPLOIEMENT.md).
set -e

echo "==> 1/5 Installation des dependances"
pip install -r requirements.txt

echo "==> 2/5 Migrations de la base"
python manage.py migrate --noinput

echo "==> 3/5 Table de cache (rate-limiting, verrous)"
python manage.py createcachetable

echo "==> 4/5 Fichiers statiques"
python manage.py collectstatic --noinput

echo "==> 5/5 Verification"
python manage.py check --deploy || true

echo ""
echo "OK. Reste a faire une fois :"
echo "  - python manage.py createsuperuser   (ton compte admin)"
echo "  - redemarrer l'app Python dans cPanel"
echo "  - ajouter le CRON quotidien (voir DEPLOIEMENT.md section 4)"
