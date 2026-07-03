# 📱 Publier Social Immo sur Google Play et l'App Store

> Le site est maintenant une **PWA** (application web installable) : manifest,
> service worker, icônes, mode hors-ligne. L'app mobile a **exactement les
> mêmes fonctionnalités que le site** — c'est le même code, emballé.
> Toute amélioration future du site est automatiquement dans l'app,
> sans re-soumission aux stores.

## ⚠️ Prérequis commun

1. Le site doit être **en ligne en HTTPS** (DEPLOIEMENT.md) — les stores
   empaquettent l'URL de production.
2. Vérifie la PWA : ouvre https://social-immo.com sur ton téléphone →
   Chrome propose "Ajouter à l'écran d'accueil" → l'app s'installe déjà,
   sans store ! (Tu peux t'arrêter là pour commencer.)

## 🤖 Google Play (~1 h + 25 $ une seule fois)

1. Va sur **https://www.pwabuilder.com** → entre `https://social-immo.com`
   → il analyse la PWA (tout est déjà vert : manifest, service worker, icônes).
2. Clique **Package for stores → Android** → télécharge le `.aab`
   + le fichier `signing.keystore` (garde-le précieusement) + note
   l'empreinte **SHA-256** affichée.
3. Dans le `.env` du serveur, ajoute :
   ```env
   ANDROID_PACKAGE=com.socialimmo.app
   ANDROID_CERT_SHA256=AA:BB:CC:...   # l'empreinte de l'etape 2
   ```
   puis redémarre l'app. Vérifie que
   `https://social-immo.com/.well-known/assetlinks.json` répond — c'est ce
   qui fait ouvrir l'app en plein écran (déjà codé, il ne manque que l'empreinte).
4. Crée ton compte développeur sur **play.google.com/console** (25 $ à vie),
   crée l'application → téléverse le `.aab` → remplis la fiche
   (description : reprends celle du manifest ; captures : ton téléphone).
5. Soumets. Validation : 1-3 jours.

## 🍎 App Store (~2-3 h + 99 €/an + un Mac)

1. Compte développeur sur **developer.apple.com** (99 €/an).
2. Sur **https://www.pwabuilder.com** → Package for stores → **iOS** →
   télécharge le projet Xcode.
3. Ouvre le projet dans Xcode (ton Mac) → signe avec ton compte →
   Product → Archive → Distribute to App Store.
4. Fiche App Store Connect + captures → soumets. Validation : 1-3 jours.
   (Apple est plus exigeant : mets en avant l'estimation, la pré-visite
   immersive et les devis artisans comme fonctionnalités "app".)

## 📲 Ce que l'app offre déjà (identique au site)

- Icône sur l'écran d'accueil, plein écran sans barre de navigateur
- Raccourcis longs-press : Estimer, Rechercher, Inspirations
- Page hors-ligne élégante si pas de réseau
- Toutes les fonctionnalités : estimation DVF, dépôt 4 étapes, alertes,
  inspirations, devis, pré-visite immersive, paiements Stripe...

## 🔮 Plus tard (si besoin)

- **Notifications push** : possibles en PWA (Android + iOS 16.4+) — à coder
  côté site quand tu voudras relancer les visiteurs.
- App 100 % native (Swift/Kotlin) : uniquement si un besoin très spécifique
  apparaît (caméra avancée, AR) — sinon la TWA/PWA suffit largement,
  c'est ce que font beaucoup d'acteurs (Twitter Lite, Starbucks...).
