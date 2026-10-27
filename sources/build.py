# -*- coding: utf-8 -*-
u"""Builds ../index.html: the page, the pricer and one day embedded.

The other days stay in ../jours/<date>.js and are loaded on demand by a plain <script> element -- not by fetch,
which would be blocked under file://. This is what lets the folder work by double-click, without a server, on an
isolated computer.

LaTeX formulas of the template (<m>, <md>, tex("...")) are rendered here with KaTeX (sources/maths.py); rendered
formulas are cached in sources/maths_cache.json, so this script needs Node.js only when a formula is new.

Usage:
    python build.py                          # the most recent day is embedded and opens first
    python build.py --jour 2026-08-26        # another day embedded
Also writes ../jeux.js: the index of all calibrated parameter sets of the days (filtered export of the page).
"""
import argparse
import io
import json
import os
from pathlib import Path

import maths

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
    u"""Date, number of options, of maturities and of calibrated sets: what the list of days needs."""
    out = []
    for p in sorted((RACINE / "jours").glob("*.js")):
        d = json.loads(jour_json(p.stem))
        out.append({"date": d["jour"], "n": len(d["cols"]["m"]),
                    "nprod": sum(1 for x in d["cols"]["prod"] if x),
                    "nmat": len(d["mats"]),
                    # number of embedded calibrated sets: ☆ in the list of days
                    "calib": sum(1 for p in d.get("presets", []) if p.get("groupe") == "Calibrations")})
    return out


def ecrire_jeux():
    u"""../jeux.js: every calibrated set embedded in the days, for the filtered export of the page
    (model, maturities, loss, period...). Loaded by a <script> element, like the days."""
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
    a.add_argument("--jour", help="day embedded in index.html, YYYY-MM-DD or YYYY-MM-DD_HHMMSS (default: the most recent)")
    a = a.parse_args(argv)
    n_jeux = ecrire_jeux()
    index = index_jours()
    assert index, "no day in jours/"
    jour0 = index[-1]["date"]          # the most recent by default
    if a.jour:
        cles = [p.stem for p in sorted((RACINE / "jours").glob("*.js")) if p.stem.startswith(a.jour)]
        if not cles:
            raise SystemExit("day missing from ../jours: " + a.jour)
        jour0 = cles[-1]
    html = (ICI / "template_full.html").read_text(encoding="utf-8")
    # formulas first, on the template only (never on the inserted pricer or data)
    html = maths.rendre_page(html, "katex/katex.min.css")
    html = html.replace("__DESIGN_CSS__", (ICI / "design.css").read_text(encoding="utf-8"))
    html = html.replace("__PRICER__", (ICI / "pricer.js").read_text(encoding="utf-8"))
    html = html.replace("__REPLICATION__", (ICI / "replication.js").read_text(encoding="utf-8"))
    html = html.replace("__FUTURES__", futures_json())
    html = html.replace("__DATA__", jour_json(jour0))
    html = html.replace("__JOURS__", json.dumps(index))

    cible = RACINE / "index.html"
    tmp = cible.with_suffix(".tmp")
    io.open(tmp, "w", encoding="utf-8").write(html)
    os.replace(tmp, cible)
    print("index.html: {} days ({} embedded), {:.1f} MB; jeux.js: {} calibrated sets".format(
        len(index), jour0, cible.stat().st_size / 1e6, n_jeux))


if __name__ == "__main__":
    main()
