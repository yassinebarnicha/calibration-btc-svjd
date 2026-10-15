# -*- coding: utf-8 -*-
"""Telecharge l'instantane Deribit du moment et l'ecrit directement dans ../jours/<date>.js, puis reconstruit la page.

Meme resultat que le bouton « Aujourd'hui » de la page, mais ecrit sur le disque sans rien demander : les chemins
sont relatifs au dossier calibration_a_la_main (un navigateur, lui, n'a pas le droit d'ecrire dans un dossier
qu'on ne lui a pas designe). API publique de Deribit, sans cle.

Usage :
    python aujourdhui.py                         # instantane du moment -> ../jours/<date>.js, CSV dans ../instantanes/, page reconstruite
    python aujourdhui.py --sans-build            # sans reconstruire index.html
Le jour du meme date deja present dans ../jours/ est remplace par l'instantane plus recent.
"""
import argparse
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

import ajouter_jours  # noqa: E402
import build  # noqa: E402
from donnees_deribit import telecharger_instantane  # noqa: E402
from jeux import charger_jeux  # noqa: E402


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--devise", default="BTC", help="devise des options Deribit (defaut : %(default)s)")
    a.add_argument("--instantanes", default=str(ICI.parent / "instantanes"),
                   help="dossier ou garder le CSV brut de l'instantane (defaut : ../instantanes)")
    a.add_argument("--jeux", help="calibrations.json ou historique.csv pour les points de depart du jour (defaut : calibrations.json)")
    a.add_argument("--sans-build", action="store_true", help="ne pas reconstruire index.html (python build.py le fera)")
    a = a.parse_args(argv)
    csv = telecharger_instantane(a.instantanes, a.devise)
    source = Path(a.jeux) if a.jeux else ICI / "calibrations.json"
    jeux = charger_jeux(source) if source.exists() else []
    jour, n, k = ajouter_jours.exporter(csv, jeux)
    print("jour {} : {} options, {} jeu(x) de parametres -> {}".format(jour, n, k, ajouter_jours.JOURS / (jour + ".js")))
    if not a.sans_build:
        build.main([])


if __name__ == "__main__":
    main()
