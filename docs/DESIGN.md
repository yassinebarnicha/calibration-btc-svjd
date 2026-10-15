# Barnicha / Volatility Lab

## Direction

Un atelier de recherche quantitatif : navigation latérale numérotée, surfaces
neutres, typographie sans empattement, contrôles compacts et graphiques prioritaires.
L'identité repose sur le travail de calibration et les données du projet.

Référence principale : Carbon, système open source conçu par IBM et sa communauté.
Le dépôt Carbon est sous licence Apache-2.0. Cette refonte est une adaptation
originale de ses principes, pas une intégration de ses composants. Aucun logo IBM
ni code de composant Carbon n'a été repris.

- https://github.com/carbon-design-system/carbon
- https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid/overview
- https://www.carbondesignsystem.com/building-blocks/foundations/color/overview

## Règles à conserver

- Grille et espacements par multiples de 8 px, avec ajustements pour les contrôles.
- Fond gris #f4f4f4, panneaux blancs, encre #161616.
- Bleu #0f62fe pour les actions et la sélection ; pétrole #005d5d pour le modèle.
- Titres et contrôles : Instrument Sans ; nombres : JetBrains Mono, déjà embarquées.
- Angles droits, filets nets. Pas de dégradé décoratif, verre flouté ou ombre de carte.
- La rampe de couleurs de la surface conserve sa fonction scientifique.
- Navigation verticale au bureau ; sur mobile, deux menus « ☰ » (onglets, panneau de l'onglet sous les smiles) et smiles 2 à 3 par rang.
- Sous 1180 px, les réglages passent avant les graphiques et leur hauteur est bornée.
- Thème clair explicite pour maintenir un contraste stable dans l'ensemble des vues.
- Les textes explicatifs scientifiques et les données existantes sont conservés.

## Maintenance

La direction visuelle se modifie dans `sources/design.css`.
`python sources/build.py` l'intègre à `index.html`, sans requête réseau pour le CSS.
Les règles structurelles historiques restent dans `sources/template_full.html` ;
les anciennes passes de palette et de décoration superposées ont été retirées.
Le moteur de pricing, les optimiseurs et les fichiers de données sont conservés.

## Vérification

La construction, la syntaxe des scripts et du CSS, les identifiants HTML et
l'intégrité des fichiers de données ont été contrôlés. Aucun test visuel dans un
navigateur ni test de bout en bout des interactions n'a été effectué dans cette
session. Les appels externes (instantané Deribit, chargement de modèles externes)
restent soumis aux conditions d'accès réseau existantes du projet.
