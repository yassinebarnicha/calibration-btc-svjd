# -*- coding: utf-8 -*-
u"""Construit ../index.html : la page, le pricer et un jour integres.

Les autres jours restent dans ../jours/<date>.js et sont charges a la demande
par une balise <script> classique -- pas par fetch, qui serait bloque en
file://. C'est ce qui permet au dossier de marcher par double-clic, sans
serveur, sur un poste isole.

Usage :
    python build.py                          # le jour le plus recent est integre et s'ouvre en premier
    python build.py --jour 2026-08-26        # autre jour integre
Ecrit aussi ../jeux.js : l'index de tous les jeux calibres des jours (export filtre de la page).
"""
import argparse
import io
import json
import os
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
PRE, SUF = "window.__recevoirJour(", ");"
PRE_FUT, SUF_FUT = "window.__recevoirFutures(", ");"


def jour_json(date):
    brut = (RACINE / "jours" / "{}.js".format(date)).read_text(encoding="utf-8")
    assert brut.startswith(PRE) and brut.endswith(SUF), date
    return brut[len(PRE):-len(SUF)]


def futures_json():
    p = RACINE / "futures.js"
    if not p.exists():
        return "null"
    brut = p.read_text(encoding="utf-8")
    assert brut.startswith(PRE_FUT) and brut.endswith(SUF_FUT), "futures.js"
    return brut[len(PRE_FUT):-len(SUF_FUT)]


def index_jours():
    u"""date, nombre d'options, d'echeances et de jeux calibres : de quoi peupler la liste."""
    out = []
    for p in sorted((RACINE / "jours").glob("*.js")):
        d = json.loads(jour_json(p.stem))
        out.append({"date": d["jour"], "n": len(d["cols"]["m"]),
                    "nprod": sum(1 for x in d["cols"]["prod"] if x),
                    "nmat": len(d["mats"]),
                    # nombre de jeux calibres embarques : ☆ dans la liste des jours
                    "calib": sum(1 for p in d.get("presets", []) if p.get("groupe") == "Calibrations")})
    return out


def ecrire_jeux():
    u"""../jeux.js : tous les jeux calibres embarques dans les jours, pour l'export filtre de la page
    (modele, echeances, perte, periode...). Charge par une balise <script>, comme les jours."""
    jeux = []
    for p in sorted((RACINE / "jours").glob("*.js")):
        d = json.loads(jour_json(p.stem))
        for x in d.get("presets", []):
            r = x.get("reglage")
            if x.get("groupe") == "Calibrations" and r:
                jeux.append(dict(r, jour=d["jour"][:10], instantane=p.stem if "_" in p.stem else None))
    (RACINE / "jeux.js").write_text("window.__JEUX = " + json.dumps(jeux, ensure_ascii=False, separators=(",", ":")) + ";",
                                    encoding="utf-8")
    return len(jeux)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--jour", help="jour integre a index.html, AAAA-MM-JJ ou AAAA-MM-JJ_HHMMSS (defaut : le plus recent)")
    a = a.parse_args(argv)
    n_jeux = ecrire_jeux()
    index = index_jours()
    assert index, "aucun jour dans jours/"
    jour0 = index[-1]["date"]          # le plus recent par defaut
    if a.jour:
        cles = [p.stem for p in sorted((RACINE / "jours").glob("*.js")) if p.stem.startswith(a.jour)]
        if not cles:
            raise SystemExit("jour absent de ../jours : " + a.jour)
        jour0 = cles[-1]
    html = (ICI / "template_full.html").read_text(encoding="utf-8")
    html = html.replace("__DESIGN_CSS__", (ICI / "design.css").read_text(encoding="utf-8"))
    html = html.replace("__PRICER__", (ICI / "pricer.js").read_text(encoding="utf-8"))
    html = html.replace("__FUTURES__", futures_json())
    html = html.replace("__DATA__", jour_json(jour0))
    html = html.replace("__JOURS__", json.dumps(index))

    cible = RACINE / "index.html"
    tmp = cible.with_suffix(".tmp")
    io.open(tmp, "w", encoding="utf-8").write(html)
    os.replace(tmp, cible)
    print("index.html : {} jours ({} integre), {:.1f} Mo ; jeux.js : {} jeux calibres".format(
        len(index), jour0, cible.stat().st_size / 1e6, n_jeux))


if __name__ == "__main__":
    main()
