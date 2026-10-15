# -*- coding: utf-8 -*-
"""Range des jeux de parametres calibres dans les jours de la page (../jours/<jour>.js), puis python build.py.

Chaque jeu va dans le jour de son instantane (ou de sa date). Les calibrations deja presentes dans un jour
sont remplacees par celles du fichier ; le point de depart generique est garde.

Usage :
    python ajouter_calibrations.py                              # calibrations.json (a cote de ce script)
    python ajouter_calibrations.py historique.csv               # historique de la chaine quotidienne
    python ajouter_calibrations.py calibrations.json --jours 2026-10-07 2026-10-08
    python ajouter_calibrations.py --ajouter                    # ajoute aux calibrations existantes au lieu de les remplacer
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from jeux import GENERIQUE, charger_jeux, jour_cible, preset

ICI = Path(__file__).resolve().parent
JOURS = ICI.parent / "jours"
PRE, SUF = "window.__recevoirJour(", ");"


def lire_jour(f):
    s = f.read_text(encoding="utf-8")
    return json.loads(s[len(PRE):-len(SUF)])


def ecrire_jour(f, d):
    f.write_text(PRE + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + SUF, encoding="utf-8")


def ranger(jeux, jours=None, ajouter=False):
    """Ecrit les jeux dans les fichiers de jour ; renvoie {clef de jour: nombre de jeux}."""
    fichiers = {f.stem: f for f in JOURS.glob("*.js")}
    par_jour = defaultdict(list)
    for j in jeux:
        c = jour_cible(j, fichiers)
        if c and (not jours or c[:10] in jours or c in jours):
            par_jour[c].append(j)
    compte = {}
    for c, f in sorted(fichiers.items()):
        if jours and c[:10] not in jours and c not in jours:
            continue
        d = lire_jour(f)
        # le generique est toujours remis a jour ; les calibrations remplacees, sauf avec --ajouter
        gardes = [p for p in d.get("presets", []) if p.get("groupe") not in ("Calibrations", "Génériques")
                  or (ajouter and p.get("groupe") == "Calibrations")]
        deja = {p.get("id") for p in gardes}
        nouveaux = [preset(j, d["mats"]) for j in par_jour.get(c, []) if j["id"] not in deja]
        d["presets"] = nouveaux + gardes + [GENERIQUE]
        ecrire_jour(f, d)
        compte[c] = len(nouveaux)
    return compte


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("fichier", nargs="?", default=str(ICI / "calibrations.json"), help="calibrations.json ou historique.csv de la chaîne quotidienne (défaut : %(default)s)")
    a.add_argument("--jours", nargs="*", help="AAAA-MM-JJ ou AAAA-MM-JJ_HHMMSS (defaut : tous les jours de la page)")
    a.add_argument("--ajouter", action="store_true", help="garder les calibrations deja presentes dans les jours")
    a = a.parse_args()
    compte = ranger(charger_jeux(a.fichier), set(a.jours or []), a.ajouter)
    print("{} jeux ranges dans {} jours".format(sum(compte.values()), sum(1 for n in compte.values() if n)))


if __name__ == "__main__":
    main()
