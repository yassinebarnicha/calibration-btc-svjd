# -*- coding: utf-8 -*-
"""Adds days to the page: ../jours/<date>.js from Deribit snapshots, then python build.py.

A day = the full cleaned chain (donnees_deribit.preparer_base), the bid/ask IVs (pricers_fourier), the rows of the
production book flagged (donnees_deribit.preparer_carnet, production rules) and the starting points: the parameter
sets calibrated on that day (format of jeux.py) and the generic start.

Usage:
    python ajouter_jours.py <snapshot folder>                        # days missing from the page
    python ajouter_jours.py <snapshot folder> 2026-10-07 2026-10-08  # chosen days (replaced if they exist)
    python ajouter_jours.py <folder> --jeux historique.csv           # another source of sets (default: calibrations.json)
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from donnees_deribit import Regles, horodatage, instantanes, lire_instantane, preparer_base, preparer_carnet
from jeux import GENERIQUE, charger_jeux, jour_cible, preset
from pricers_fourier import vol_implicite

ICI = Path(__file__).resolve().parent
JOURS = ICI.parent / "jours"



def r_(v, s=10):
    return None if v is None or not np.isfinite(v) else float("{:.{}g}".format(v, s))


def iv(prix, F, K, T, r, call):
    out = np.full(len(prix), np.nan)
    ok = prix > 0
    out[ok] = vol_implicite(prix[ok], F[ok], K[ok], T[ok], r[ok], call[ok])
    return out


def exporter(fichier, jeux):
    stamp = horodatage(fichier)
    brut = lire_instantane(fichier)
    df = preparer_base(brut)
    df = df.assign(_put=~df["call"]).sort_values(["echeance", "K", "_put"]).reset_index(drop=True)
    prod = preparer_carnet(brut, Regles())
    F, X, K, T, call = (df[c].to_numpy() for c in ("F", "X", "K", "T", "call"))
    r = np.log(F / X) / T
    bid = pd.to_numeric(df["best_bid_price"], errors="coerce").fillna(0).to_numpy(float)
    ask = pd.to_numeric(df["best_ask_price"], errors="coerce").fillna(0).to_numpy(float)
    mats = sorted(df["echeance"].unique())
    ids = set(prod["instrument_name"])
    cols = dict(m=[mats.index(m) for m in df["echeance"]], T=[r_(v) for v in T], F=[r_(v) for v in F],
                X=[r_(v) for v in X], K=[float(v) for v in K], r=[r_(v) for v in r], c=[int(v) for v in call],
                mark=[r_(v, 8) for v in df["mark_price"]], bid=[r_(v, 8) for v in bid], ask=[r_(v, 8) for v in ask],
                iv_mark=[r_(v) for v in df["iv_mark"]], iv_mid=[r_(v) for v in df["iv_mid"]],
                iv_bid=[r_(v) for v in iv(bid * X, F, K, T, r, call)], iv_ask=[r_(v) for v in iv(ask * X, F, K, T, r, call)],
                prod=[int(n in ids) for n in df["instrument_name"]],
                # open interest (BTC) : sert a l'onglet GEX
                oi=[r_(v) for v in pd.to_numeric(df.get("open_interest", pd.Series(index=df.index, dtype=float)), errors="coerce")])
    jour = stamp[:10]
    mats_j = [dict(date=str(m)[:10], jours=int(df.loc[df["echeance"] == m, "jours"].iloc[0])) for m in mats]
    presets = [preset(j, mats_j) for j in jeux if jour_cible(j, {jour}) == jour] + [GENERIQUE]
    data = dict(jour=jour, date=jour, heure="{}:{}:{}".format(stamp[11:13], stamp[13:15], stamp[15:17]),
                index=float(X[0]), fichier=Path(fichier).name, mats=mats_j, presets=presets, cols=cols)
    (JOURS / (jour + ".js")).write_text("window.__recevoirJour(" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ");",
                                        encoding="utf-8")
    return jour, len(df), len(presets) - 1


def main(dossier, dates, source_jeux=None):
    source = Path(source_jeux) if source_jeux else ICI / "calibrations.json"
    jeux = charger_jeux(source) if source.exists() else []
    presents = {p.stem[:10] for p in JOURS.glob("*.js")}
    par_jour = {}
    for f in instantanes(dossier):
        par_jour[horodatage(f)[:10]] = f            # dernier instantane de chaque jour
    for jour, f in sorted(par_jour.items()):
        if (dates and jour in dates) or (not dates and jour not in presents):
            print("  {}: {} options, {} parameter set(s)".format(*exporter(f, jeux)))


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("dossier", help="folder of the btc_options_snapshot_*.csv snapshots")
    a.add_argument("dates", nargs="*", help="YYYY-MM-DD (default: the days missing from the page)")
    a.add_argument("--jeux", help="calibrations.json or historique.csv of the daily chain (default: calibrations.json)")
    a = a.parse_args()
    main(a.dossier, set(a.dates), a.jeux)
