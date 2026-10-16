# -*- coding: utf-8 -*-
"""Downloads the current Deribit snapshot, writes it directly to ../jours/<date>.js, then rebuilds the page.

Same result as the "Today" button of the page, but written to disk without asking anything: paths are relative to the
application folder (a browser is not allowed to write to a folder it has not been given). Public Deribit API, no key.

Usage:
    python aujourdhui.py                  # current snapshot -> ../jours/<date>.js, CSV in ../instantanes/, page rebuilt
    python aujourdhui.py --sans-build     # without rebuilding index.html
A day of the same date already in ../jours/ is replaced by the more recent snapshot.
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
    a.add_argument("--devise", default="BTC", help="currency of the Deribit options (default: %(default)s)")
    a.add_argument("--instantanes", default=str(ICI.parent / "instantanes"),
                   help="folder where the raw CSV of the snapshot is kept (default: ../instantanes)")
    a.add_argument("--jeux", help="calibrations.json or historique.csv for the starting points of the day (default: calibrations.json)")
    a.add_argument("--sans-build", action="store_true", help="do not rebuild index.html (python build.py will)")
    a = a.parse_args(argv)
    csv = telecharger_instantane(a.instantanes, a.devise)
    source = Path(a.jeux) if a.jeux else ICI / "calibrations.json"
    jeux = charger_jeux(source) if source.exists() else []
    jour, n, k = ajouter_jours.exporter(csv, jeux)
    print("day {}: {} options, {} parameter set(s) -> {}".format(jour, n, k, ajouter_jours.JOURS / (jour + ".js")))
    if not a.sans_build:
        build.main([])


if __name__ == "__main__":
    main()
