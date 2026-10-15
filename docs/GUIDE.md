# Guide détaillé — calibration d'options Bitcoin

Retour au [README](../README.md).

## Utilisation

1. **Jour** : liste de tous les jours disponibles. Chaque ligne donne la date, puis en toutes lettres ce qui existe pour ce jour :
   « 3 calibrations » (jeux calibrés embarqués), « 2 réglages » (tes réglages enregistrés, « dont un final »
   le cas échéant) et « téléchargé » pour un jour récupéré par *Aujourd'hui*.
   **Instantané du jour, écrit directement dans `jours/`** :

   ```
   python sources/aujourdhui.py
   ```

   télécharge la chaîne Deribit du moment (API publique, sans clé), l'écrit dans
   `jours/<date>.js` (chemin relatif au dossier, rien à choisir), garde le CSV brut dans
   `instantanes/` et reconstruit la page. Un jour déjà présent à la même date est remplacé
   par l'instantané plus récent.
   Le bouton **↻ Aujourd'hui** de la page fait le même téléchargement sans Python : le jour est gardé dans le
   navigateur (il revient au lancement suivant, marqué « téléchargé »), mais un navigateur n'a pas le droit
   d'écrire seul dans un dossier : il n'écrit `jours/<date>.js` que si le dossier du site a été
   désigné une fois dans *Réglages*.
2. **Modèle** (onglet *Modèle*) : un bloc de variance (Black-Scholes, Heston, double Heston, Heston à sauts de
   variance) et une loi de sauts (aucune, Merton, bi-log-normale, Kou, CGMY, Variance Gamma, NIG). Le bouton
   **ⓘ Dynamique** affiche au survol (et fige au clic) la dynamique complète du modèle actif : équations du
   future et de la variance, loi des sauts, compensateur, fonction caractéristique, contraintes et rôle de chaque
   paramètre. Survoler une option des listes en donne la dynamique en une ligne.
   **Appliquer** passe au modèle choisi ; sans changement, **Réappliquer** repart du départ du modèle.
3. **Point de départ** (onglet *Paramètres et optimiseur*) : la liste ne contient que les jeux **du modèle actif** ;
   changer de modèle change la liste. Ordre :
   - *Mes réglages enregistrés* ;
   - *Calibrations du jour*, de la meilleure RMSE IV à la moins bonne, nommées
     « moteur · méthode · n éch. · perte · RMSE » (par exemple « COS · DE + local · 6 éch. · prix · 1/vega² égal ·
     38,6 bps ») ;
   - *Départ générique* (s'il est de ce modèle) ; *Départ du modèle* (toujours présent).
   **Charger ce point de départ** charge l'entrée affichée, même si c'est la seule ; avec la case cochée, ses
   échéances, filtres, pricer, perte et bornes sont rétablis aussi.
4. **Paramètres** : curseurs et saisie, verrou par paramètre (gelé pendant l'optimisation), bornes. Une intensité de
   sauts mise à 0 met sa taille (μJ, σJ) à 0 et la fige ; elle revient à sa valeur précédente quand λ redevient
   positif.
5. **Perte, pricer, jours empilés** (plusieurs jours calibrés ensemble, certains paramètres libres par jour).
6. **Grecques** (onglet *Grecques*, dans la zone centrale) : pour chaque option retenue d'une échéance, IV et prix
   marché / modèle, puis Δ, Γ 1 % (variation du Δ pour +1 % de F), Vega (par point de vol) et Θ (par jour), deux
   fois : **Black-76** (formules fermées, à l'IV de marché ou à l'IV du modèle) et **modèle actif** (différences
   finies centrées sur son pricer COS ou PROJ : F ±0,1 %, vol instantanée σ₀
   ±0,1 %, échéance ±1 jour). Bates n'a pas de formule fermée de ses grecques, pas plus que de son prix : elles
   passent par la fonction caractéristique. Contrôle : en modèle Black-Scholes, les différences finies retrouvent
   Black-76 aux décimales affichées (Θ à moins de 0,1 %). Un graphique par grecque (Δ, Γ, Vega, Θ par strike, modèle contre Black-76) et
   export CSV. L'écart Δ modèle − Δ Black-76 est l'effet du smile sur la couverture.
7. **Surface de vol** (onglet *Surface de vol*, calculé seulement à son ouverture) : la surface de volatilité
   implicite du modèle actif en 3D (log-moneyness k = ln(K/F), échéance, vol), pricée sur une grille de 25, 41 ou
   61 strikes par échéance puis inversée en Black-76, et les IV de marché par-dessus. Deux modes :
   - **Calibré seulement** : les échéances retenues, les options calibrées (●) et la surface sur leur plage ;
   - **Tous les points du jour + extrapolation du modèle** : toutes les options du jour sur toutes les échéances
     (○ celles qui ne servent pas à la calibration, IV du mark) et la surface étendue à toute cette zone ; le
     survol d'un point donne l'IV du modèle exactement en ce point (extrapolée hors des données calibrées).
   La surface est toujours pricée en PROJ : sa grille suit les strikes demandés, alors que l'intervalle de
   troncature de COS se resserre avec l'échéance (à 4 h d'échéance et dans les ailes larges, COS s'écartait de
   PROJ jusqu'à 2,6·10⁵ $) ; là où le prix du modèle est quasi nul, la vol n'est pas définie et la surface a un
   trou. Glisser pour tourner, molette pour zoomer, double-clic pour la vue par défaut. Pendant une
   optimisation, la surface n'est recalculée qu'une fois par seconde. Dessinée sans bibliothèque externe.
8. **Pricer tes propres options** (onglet *Pricer*) : avec le modèle actif et ses paramètres actuels, en PROJ
   (juste aussi sur les échéances très courtes et les strikes éloignés).
   - *À la main* : type, K, F, échéance (jours), r et, si on veut, un prix de marché → prix et IV du modèle, IV de
     marché et écart, Δ, Γ, Vega, Θ du modèle et de Black-76.
   - *Fichier CSV* : une ligne par option, colonnes obligatoires `type` (call/put, C/P), `K`, `F` et l'échéance par
     `T` (années) **ou** `jours` **ou** `echeance` (AAAA-MM-JJ, expiration 08:00 UTC, comptée depuis `valorisation`
     si la colonne existe, sinon depuis l'instantané du jour) ; facultatives `r`, `prix_marche` ; toute autre
     colonne est recopiée. Séparateur `,` ou `;` (virgule décimale acceptée avec `;`). Le fichier revient
     (`<nom>_price.csv`) avec `iv_marche, prix_modele, iv_modele, ecart_iv_bps, ecart_prix, delta/gamma/vega/theta`
     du modèle et de Black-76, `vol_b76, modele, pricer, erreur` ; une ligne invalide garde ses données et reçoit
     son message dans `erreur`. Bouton *CSV modèle* : un fichier exemple à remplir.
9. **Options exotiques par Monte-Carlo** (onglet *Pricer*, calcul seulement au clic, arrêtable) :
   - *Paramètres* : les actuels (curseurs, résultat de l'optimisation) ou n'importe quel réglage enregistré ou
     calibration du jour du modèle actif ;
   - *Produits* : asiatique, barrière, digitale, américaine (Longstaff-Schwartz), lookback, européenne ; ou
     **composé** : valeur observée (F final, moyenne, max, min) × payoff (call, put, digitale) × jusqu'à deux
     barrières (up/down, in/out) × exercice (européen, américain) ; ou **formule libre** (variables `FT, MOY, MAX,
     MIN, F0, K, B, B2, Q, T`, fonctions `max, min, abs, exp, log, sqrt`, comparaisons valant 1 ou 0) ;
   - *Simulation* : facteurs CIR par QE (Andersen 2008), sauts Merton, bi-log-normaux, Kou, Variance Gamma, NIG
     (CGMY n'a pas de simulation exacte simple : non proposé) ; surveillance discrète à chaque pas ;
   - *Américaine* : régression sur 1, x, x², x³ et la valeur européenne Black-76 de l'option restante, qui sert
     aussi de plancher à la continuation (sans elle, le bruit de la régression faisait exercer à tort) ; contrôlé :
     prime ≈ 0 pour r = 0, positive pour r > 0 ;
   - *Contrôle* : l'européenne de strike K est simulée sur les mêmes trajectoires et comparée à son prix de
     Fourier (écart en nombre d'erreurs standard ; |écart| > 3 σ signale un biais de discrétisation) ; elle sert
     aussi de variable de contrôle. Vérifié sur Black-Scholes, Heston + Merton, double Heston + bi-log-normal,
     Heston à sauts de variance + Kou, Heston + VG, Heston + NIG (écarts de −1,1 à +1,9 σ).
10. **GEX — gamma exposure** (onglet *GEX*, calculé à son ouverture) : par option, signe × open interest (BTC) × Γ ×
    F² × 1 % = le delta en dollars à racheter ou vendre pour un mouvement de +1 % du future. Échéances retenues ou
    toutes ; gamma de Black-76 à l'IV du mark ou du modèle ; convention « teneurs de marché » (+ calls, − puts) ou
    gamma brut. Tuiles : GEX total, niveau de bascule (zero gamma), call wall, put wall, calls/puts et open
    interest ; graphiques : GEX net par strike et GEX total selon le niveau du future (−20 % à +20 %). L'open
    interest vient des instantanés Deribit (colonne `oi` des jours ; absent des deux jours reconstruits).
11. **Optimiseur** (Feller imposée ou non, dans les bornes des curseurs, paramètres verrouillés fixes) :

   | Méthode | Nature | Quand la choisir |
   |---|---|---|
   | Nelder–Mead classique (défaut) | local, coefficients 1, 2, ½, ½ | affiner depuis un bon point de départ |
   | Nelder–Mead adaptatif (Gao & Han 2012) | local, coefficients fonction de la dimension n | beaucoup de paramètres libres : descend en général plus bas, s'arrête plus tard |
   | Évolution différentielle (Storn & Price 1997) | global, population en hypercube latin | pas de bon point de départ ; graine fixe → résultat reproductible |
   | DE puis Nelder–Mead (classique ou adaptatif) | global puis local | la chaîne de calibration Python (Nelder–Mead à la place de SLSQP) ; l'étape locale peut changer de pricer |

   Réglages : tolérance, évaluations max., pas initial (Nelder–Mead) ; stratégie best1bin/rand1bin, popsize,
   générations, mutation, recombinaison, tol, atol, graine, injection du point actuel (DE), avec deux préréglages
   « Défauts scipy » et « Réglages de production » (ceux de la chaîne de calibration Python d'origine). Ils sont enregistrés avec le réglage.

## Vitesse et fluidité

- **Réglages par défaut les plus rapides** : pricer COS (N = 512, L = 24) et modèle de Bates (Heston + sauts
  lognormaux, 8 paramètres). PROJ et les autres modèles restent au choix ; un réglage choisi est retenu par le
  navigateur.
- **Pricer** : tout ce qui ne dépend pas de la fréquence (compensateurs des sauts, Γ(−Y) de CGMY, k_J) est calculé
  une fois par échéance, la fonction caractéristique ne crée aucun tableau intermédiaire, COS ne calcule que la
  partie réelle utile, et la FFT de PROJ lit ses facteurs de rotation dans une table. Prix inchangés (écart
  maximal 6·10⁻¹¹ $ sur 17 192 prix, 28 compositions de modèle, COS et PROJ).
- **Optimiseur** : calcul par tranches de 12 ms (la page garde ses 60 images par seconde) ; l'affichage est
  rafraîchi environ toutes les 100 ms et reprend l'évaluation que l'optimiseur vient de faire au lieu de la
  refaire ; les smiles sont dessinés avant les autres écritures de la page ; l'onglet Grecques n'est recalculé
  qu'une fois par seconde pendant une optimisation (et à la fin).
- **Ordre de grandeur** (Bates, 6 échéances, ~300 options, COS) : une évaluation ≈ 3 ms, soit environ 300
  évaluations par seconde ; un rafraîchissement complet de l'écran ≈ 5 à 9 ms. PROJ (N = 2048) coûte environ
  3 fois plus ; un modèle à deux composantes de sauts (11 paramètres) demande aussi plus d'itérations.

## Enregistrer et exporter

- **Enregistrer ce réglage** : le réglage (modèle, paramètres, jour, échéances, filtres, pricer, perte, bornes,
  résultats) va dans le navigateur **et sur le disque**. Au premier enregistrement, choisir le dossier
  du site (le navigateur s'en souvient) :

  ```
  resultats/<jour>/<variance>-<sauts>/NN_<nom>/   reglage.json, params.json, results.csv, df_used.csv, smile_grid.csv, smiles.png
  resultats/<jour>/final/                          le réglage marqué « final » du jour
  resultats/jeux_enregistres.json                  tous tes réglages, au format commun des jeux
  ```
- **Exporter des jeux de paramètres (JSON)** : tous les jeux d'un modèle, sur tous les jours, filtrés par origine
  (calibrations historiques, mes réglages), nombre d'échéances (de … à …), perte, période, RMSE IV maximale, et « tous »
  ou « le meilleur par jour ». Le compte des jeux retenus s'affiche avant l'export.

**Format commun des jeux** (« calibration-a-la-main/jeux », version 1), partagé avec les scripts de calibration :
`id, jour, instantane, modele {variance, sauts}, parametres, calibration {origine, moteur, methode, source},
donnees {echeances, filtres}, pricer, perte {mesure, ponderation}, resultats {rmse_iv_bps, rmse_prix_usd, n_options}`.
Clés des modèles : variance `const`, `heston`, `heston2`, `hestonJ` ; sauts `aucun`, `logn`, `biln`, `kou`, `cgmy`,
`vg`, `nig`.

## Contenu

```
├── README.md, METHODOLOGIE_app_web_yassine.pdf, requirements.txt, .nojekyll
├── .github/workflows/maj_quotidienne.yml   instantané Deribit chaque matin (GitHub Actions)
└── (racine du site)
    ├── index.html                la page (assemblée par sources/build.py)
    ├── futures.js                286 échéances de futures (cotées et forwards implicites)
    ├── jeux.js                   index de tous les jeux calibrés embarqués (pour l'export)
    ├── jours/<date>.js           un fichier par jour : chaîne complète, carnet par défaut marqué, jeux calibrés du jour
    │                             (T à l'heure près jusqu'à l'expiration de 08:00 UTC, r = log(F/X)/T)
    └── sources/
        ├── template_full.html    la page (modèles, dynamiques, menus, enregistrement, export)
        ├── pricer.js             fonctions caractéristiques, COS, PROJ, Black-76
        ├── calibrations.json     les 529 jeux calibrés embarqués, au format commun
        ├── jeux.py               format commun : rattachement aux jours, nom affiché
        ├── ajouter_jours.py      ajoute des jours depuis des instantanés Deribit
        ├── ajouter_calibrations.py  range des jeux calibrés dans les jours
        ├── aujourdhui.py         instantané Deribit du moment -> ../jours/<date>.js, puis build
        ├── build.py              assemble index.html et jeux.js
        ├── telecharger_futures.py  historique des futures Deribit -> futures.js
        ├── donnees_deribit/      préparation des instantanés
        └── pricers_fourier/      Black-76 et volatilité implicite
```

## Mettre à jour les données

Python 3.10 ou plus récent, numpy, scipy, pandas, requests. Depuis `sources/` :

| Je veux… | Commande |
|---|---|
| ajouter les jours absents d'un dossier d'instantanés | `python ajouter_jours.py <dossier>` puis `python build.py` |
| ajouter ou remplacer des jours précis | `python ajouter_jours.py <dossier> 2026-10-13 2026-10-14` |
| ranger des jeux calibrés (JSON au format commun) | `python ajouter_calibrations.py jeux.json --ajouter` puis `python build.py` |
| tout reconstruire depuis calibrations.json | `python ajouter_calibrations.py` puis `python build.py` |
| mettre à jour les futures | `python telecharger_futures.py` puis `python build.py` |
| ajouter l'instantané du moment dans jours/ | `python aujourdhui.py` (reconstruit la page) |
| ouvrir la page sur un autre jour | `python build.py --jour 2026-08-26` |

Un nouveau modèle s'ajoute dans `sources/pricer.js` (exposant de la fonction caractéristique), puis dans le gabarit
(`VARIANCES` ou `SAUTS`, et sa fiche dans `DYNAMIQUES`) ; `python build.py` reconstruit la page.

## Scripts

<!-- debut:scripts -->
### `ajouter_jours.py`

Ajoute des jours a la page : ../jours/<date>.js depuis des instantanes Deribit, puis python build.py.

*Argument positionnel*

| Argument | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `dossier` | texte | — | dossier des instantanes btc_options_snapshot_*.csv |
| `dates` | texte … | — | AAAA-MM-JJ (defaut : les jours absents de la page) |

*Arguments*

| Argument | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `--jeux` | texte | — | fichier de jeux calibres (defaut : calibrations.json) |

### `ajouter_calibrations.py`

Range des jeux de parametres calibres dans les jours de la page (../jours/<jour>.js), puis python build.py.

*Argument positionnel*

| Argument | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `fichier` | texte | `calibrations.json` | fichier de jeux calibrés (calibrations.json par défaut) |

*Arguments*

| Argument | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `--jours` | texte … | — | AAAA-MM-JJ ou AAAA-MM-JJ_HHMMSS (defaut : tous les jours de la page) |
| `--ajouter` | drapeau | — | garder les calibrations deja presentes dans les jours |

### `aujourdhui.py`

Telecharge l'instantane Deribit du moment et l'ecrit directement dans ../jours/<date>.js, puis reconstruit la page.

*Arguments*

| Argument | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `--devise` | texte | `BTC` | devise des options Deribit |
| `--instantanes` | texte | `../instantanes` | dossier ou garder le CSV brut de l'instantane |
| `--jeux` | texte | — | fichier de jeux calibres pour les points de depart du jour (defaut : calibrations.json) |
| `--sans-build` | drapeau | — | ne pas reconstruire index.html (python build.py le fera) |

### `build.py`

Construit ../index.html : la page, le pricer et un jour integres.

*Arguments*

| Argument | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `--jour` | texte | — | jour integre a index.html, AAAA-MM-JJ ou AAAA-MM-JJ_HHMMSS (defaut : le plus recent) |

### `telecharger_futures.py`

Historique quotidien complet de chaque future Deribit -> futures.js.

*Arguments*

| Argument | Valeurs | Défaut | Rôle |
|---|---|---|---|
| `--cache` | texte | `cache_futures` | dossier du cache des reponses brutes (defaut : sources/cache_futures) |
| `--tout-retelecharger` | drapeau | — | retelecharge aussi les echeances expirees deja en cache |
| `--pause` | réel | `0.12` | secondes entre deux requetes (defaut : 0.12) |
<!-- fin:scripts -->

## Publier (GitHub Pages)

1. Créer sur GitHub un dépôt **public** (par exemple `app-web-yassine`).
2. Depuis ce dossier (ou avec GitHub Desktop : *Add local repository → create a repository → Publish repository*, en décochant *Keep this code private*) :

   ```
   git init
   git add .
   git commit -m "Calibration d'options Bitcoin"
   git branch -M main
   git remote add origin https://github.com/yassinebarnicha/yassinebarnicha.github.io.git
   git push -u origin main
   ```
3. Sur GitHub : **Settings → Pages → Build and deployment → Deploy from a branch → `main` / `(root)`**.
   Le site est en ligne quelques minutes plus tard à `https://yassinebarnicha.github.io/`, servi par
   un réseau mondial (rapide depuis tous les continents). Rien à payer, aucun serveur à gérer : la page et ses
   données sont des fichiers statiques, tout le calcul se fait dans le navigateur du visiteur.

Le fichier `.nojekyll` demande à GitHub de servir les fichiers tels quels.

## Mise à jour automatique des données

`.github/workflows/maj_quotidienne.yml` lance chaque jour à 08:20 UTC (juste après l'expiration Deribit) :
`pip install -r requirements.txt`, puis `python sources/aujourdhui.py` (instantané de la chaîne Deribit → nouveau
`jours/<date>.js`, `index.html` et `jeux.js` reconstruits), puis un commit ; GitHub Pages republie la page
automatiquement. On peut aussi la lancer à la main : onglet **Actions → Mise à jour quotidienne → Run workflow**.
Le CSV brut de l'instantané n'est pas versionné (`.gitignore`) : le dépôt grossit d'environ 120 Ko par jour.
Si Deribit refusait un jour les requêtes des machines de GitHub, la tâche échouerait (visible dans l'onglet
Actions) sans rien casser : le site garde les jours déjà publiés.

