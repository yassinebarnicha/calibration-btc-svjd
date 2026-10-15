# App web Yassine — calibration d'options Bitcoin dans le navigateur

**Pricer, calibrer et analyser les options BTC de Deribit avec onze modèles à sauts et volatilité stochastique,
entièrement dans le navigateur : aucun serveur de calcul, aucune installation.**

▶ **Démo en ligne : https://yassinebarnicha.github.io/**

![Calibration du modèle de Bates sur les smiles Deribit du 26/08/2026](docs/apercu_calibration.png)

## Ce que fait l'application

- **Calibration interactive** : chaque curseur repricé en direct sur toute la chaîne d'options du jour ; cinq
  optimiseurs (Nelder–Mead classique et adaptatif, évolution différentielle, DE puis Nelder–Mead), contrainte de
  Feller, paramètres verrouillables, bornes, plusieurs jours calibrés ensemble.
- **Modèles composables** : un bloc de variance × une loi de sauts, chacun avec sa dynamique affichée en clair.
- **Grecques** : Δ, Γ, Vega, Θ du modèle (différences finies sur son propre pricer) contre Black-76, par strike.
- **Surface de volatilité 3D** : surface du modèle et points de marché, calibrés seulement ou tous, avec
  l'extrapolation du modèle là où il n'a rien vu.
- **Pricer à la demande** : une option saisie à la main, ou un fichier CSV entier rendu avec prix, IV et grecques.
- **Exotiques par Monte-Carlo** : asiatiques, barrières, digitales, lookbacks, américaines (Longstaff-Schwartz),
  payoffs composés ou formule libre, avec contrôle automatique contre le prix exact de Fourier.
- **GEX (gamma exposure)** : exposition gamma des teneurs de marché par strike, niveau de bascule, call / put walls.
- **Données** : 270+ jours de chaînes d'options Deribit depuis janvier 2024, l'historique des futures, 529 jeux de
  paramètres calibrés, et un jour de plus chaque matin.

## Modèles

| Variance \ sauts | aucun | Merton | bi-log-normal | Kou | CGMY | Variance Gamma | NIG |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Black-Scholes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Heston | ✓ | ✓ (Bates) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Double Heston | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Heston + sauts de variance | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Les 28 compositions sont pricées par leur fonction caractéristique, avec **COS** (Fang–Oosterlee 2008) ou
**PROJ** (Kirkby 2015), écrits en JavaScript.

## Comment ça marche

- **Un site 100 % statique** : `index.html` (la page, ses pricers et un jour intégrés), un fichier par jour dans
  `jours/`, chargé à la demande. Tout le calcul tourne dans le navigateur du visiteur, qui garde ses réglages chez
  lui (navigateur, ou dossier de son disque avec Chrome et Edge) : aucune base de données, aucun compte.
- **Des données qui se mettent à jour seules** : une GitHub Action télécharge chaque matin la chaîne d'options
  Deribit (API publique, sans clé), l'ajoute et republie la page. Le bouton *↻ Aujourd'hui* fait la même chose
  depuis le navigateur, à tout moment.
- **Fluide** : le pricer ne recalcule rien d'inutile (une évaluation complète ≈ 3 ms en COS, soit environ 300 par
  seconde) ; l'optimisation tourne par tranches de 12 ms, l'écran garde ses 60 images par seconde.

## Validation

- Parité call–put et martingalité : C(K = F) − P(K = F) = 0,0000 bp sur les 28 compositions ; Black-Scholes retrouvé
  à moins de 0,005 bp ; pricer JavaScript égal au pricer Python de référence à 6·10⁻⁶ $ près.
- Grecques par différences finies égales aux formules fermées de Black-76 (modèle Black-Scholes) aux décimales
  affichées.
- Monte-Carlo : l'européenne simulée tombe à moins de 2 erreurs standard du prix de Fourier sur six familles de
  modèles ; prime d'exercice anticipé nulle pour r = 0, positive pour r > 0.
- Temps à l'échéance compté à l'heure près jusqu'à l'expiration de 08:00 UTC, ce qui compte pour les échéances de
  quelques jours.

## Aperçus

| Surface de volatilité 3D | GEX |
|---|---|
| ![Surface de volatilité implicite en 3D, modèle et marché](docs/apercu_surface.png) | ![Gamma exposure par strike et profil](docs/apercu_gex.png) |

![Grecques du modèle contre Black-76, par strike](docs/apercu_grecques.png)

## Démarrer

- **En ligne** : ouvrir la démo. Un onglet s'ouvre directement par l'adresse, par exemple `…/#GEX` ou
  `…/#Surface%20de%20vol`.
- **En local** : télécharger le dépôt et double-cliquer sur `index.html` (garder `jours/`, `futures.js` et
  `jeux.js` à côté).

## Pour aller plus loin

- [docs/GUIDE.md](docs/GUIDE.md) : mode d'emploi complet (chaque onglet, format CSV, scripts, mise à jour des
  données, publication).
- [METHODOLOGIE_app_web_yassine.pdf](METHODOLOGIE_app_web_yassine.pdf) : théorie et algorithmes (composition des
  modèles, pricers de Fourier, perte, optimiseurs, validation).
- Développement : la page se construit depuis `sources/` (`template_full.html`, `pricer.js`) avec
  `python sources/build.py` ; un nouveau modèle s'ajoute par son exposant dans `pricer.js` et sa fiche dans le
  gabarit.

## Auteur et licence

Mohammed-Yassine Barnicha — code sous licence [MIT](LICENSE). Données de marché : API publique de Deribit.
