# 💰 Plan 1 M€ — Monétisation & game changers Social Immo

> Principe de lucidité : 1 M€ de chiffre d'affaires annuel ne vient pas d'une
> "feature magique" mais d'un **empilement de sources de revenus** sur un
> trafic qui grossit. La bonne nouvelle : le site a déjà les fondations de
> chacune (options agences, annuaire pros, estimation DVF, alertes).

## 🧮 Le calcul — à quoi ressemble 1 M€/an

| Source | Hypothèse à maturité | CA annuel |
|---|---|---|
| **Abonnements agences** (options premium : badge, remontée, stats, leads prioritaires) | 250 agences × 150 €/mois | 450 000 € |
| **Leads vendeurs vendus aux agences** (issus de l'estimation DVF) | 300 leads/mois × 80 € | 288 000 € |
| **Abonnements artisans/pros** (fiche + mise en avant + devis) | 400 pros × 29 €/mois | 139 000 € |
| **Pack "Vendeur Pro" particuliers** (boost + diffusion + panneau QR) | 200/mois × 39 € | 94 000 € |
| **Apport d'affaires crédit** (courtier partenaire, ~300 €/dossier financé) | 15 dossiers/mois | 54 000 € |
| **Total** | | **~1 025 000 €** |

Chaque ligne est un produit à construire + un volume à atteindre. Le volume
vient du trafic (SEO villes, réseaux, alertes) — la machine est en place,
c'est la distribution qui fait le reste.

**Étapes intermédiaires réalistes** : 30 k€/an (10 agences + 30 pros payants)
→ 150 k€/an → 1 M€. Le premier euro encaissé est l'étape la plus importante.

## 🚀 Les game changers, classés par (impact × faisabilité)

### 1. Le tunnel vendeur — l'or du site 🥇
L'estimation DVF est ton **aimant à vendeurs** (la donnée que SeLoger fait payer).
Après l'estimation, 3 portes :
- **"Vendre avec un pro"** → le lead est vendu/attribué à une agence abonnée
  (l'attribution admin existe déjà — il manque la facturation et l'espace
  agence "mes leads").
- **"Vendre moi-même"** → dépôt gratuit (déjà excellent) + **Pack Vendeur Pro
  39 €** : annonce boostée 30 jours, rediffusion réseaux, panneau "À VENDRE"
  PDF avec QR code (généré par le site, imprimable), rapport de marché PDF de
  sa ville.
- **"Je veux juste suivre le marché"** → alerte prix de sa ville (nurturing,
  il reviendra).

### 2. Devis travaux : le Doctolib des artisans 🥈
Le visiteur voit une inspiration ou un bien → bouton **"Obtenir des devis"**
→ 3 artisans du département reçoivent la demande. L'artisan paie l'accès aux
demandes (abonnement 29 €/mois) ou au devis (10-15 €/lead). Toutes les briques
existent (annuaire par métier/département, DemandeContact, quotas d'options).
C'est LE pont entre le côté Pinterest et le côté business.

### 3. Observatoire des prix — autorité + backlinks 🥉
Tu as les ventes DVF en base. Publier chaque mois **"Le baromètre Social Immo"**
par ville/département (page publique + PDF) : prix médian, évolution, délais.
- Gratuit = SEO massif + presse locale + posts LinkedIn tout faits.
- Version Pro (agences/notaires) payante dans l'abonnement.

### 4. Home staging virtuel IA — le wow qui fait parler
"Votre salon vide → meublé en 3 styles" à partir d'une photo. Impossible sur
o2switch seul, mais trivial via une API externe (Replicate/Stability,
~0,10 €/image) revendue 5 €/image ou incluse dans le Pack Vendeur Pro.
Effet démo/viral énorme — c'est le genre de feature qui fait un post LinkedIn
à 100 k vues.

### 5. Financement intégré
Le simulateur de mensualités existe sur chaque annonce. Le brancher sur un
courtier partenaire (affiliation type Pretto/Meilleurtaux : ~150-300 € par
dossier financé) = revenu passif sur chaque annonce consultée.

### 6. Parrainage & effet réseau
"Invitez un artisan → 1 mois de mise en avant offert pour vous deux."
Les pros recrutent les pros, coût d'acquisition ≈ 0.

## 🧱 Prérequis avant d'encaisser le premier euro

1. **Stripe** (abonnements + paiements one-shot) — s'intègre à Django en une
   phase de travail ; o2switch suffit (webhooks HTTPS).
2. **CGV + statut juridique** (auto-entrepreneur suffit pour démarrer,
   attention TVA sur les abonnements).
3. **Bannière cookies RGPD** dès qu'on ajoute pixel/analytics.
4. Éthique leads : le vendeur doit cocher "j'accepte d'être contacté par une
   agence partenaire" — c'est aussi ce qui rend le lead qualifié donc cher.

## 📅 Ordre de construction recommandé (je peux tout coder)

| # | Chantier | Revenu visé |
|---|---|---|
| 1 | Stripe + espace facturation | prérequis |
| 2 | Abonnement agence en self-service (les options existent, elles deviennent achetables) | 450 k€ potentiel |
| 3 | Tunnel vendeur 3 portes + vente de leads | 288 k€ |
| 4 | Abonnement pro + demandes de devis | 139 k€ |
| 5 | Pack Vendeur Pro particulier (panneau QR PDF déjà à moitié fait) | 94 k€ |
| 6 | Baromètre des prix mensuel (DVF déjà en base) | trafic/autorité |
| 7 | Home staging IA (API externe) + affiliation courtier | bonus |

> ⚠️ Le vrai goulot n'est pas le code : c'est le **volume** (annonces, agences,
> visiteurs). La stratégie réseaux (STRATEGIE-RESEAUX.md) et le SEO villes
> sont ce qui transforme ce plan en chiffre d'affaires réel.
