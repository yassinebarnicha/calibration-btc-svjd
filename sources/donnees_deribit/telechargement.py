# -*- coding: utf-8 -*-
"""Téléchargement d'instantanés d'options Deribit (API REST publique v2, sans clé).

    GET /public/get_instruments?currency=<DEVISE>&kind=option&expired=false
    GET /public/ticker?instrument_name=<nom>          (requêtes parallèles)

Un instantané = un CSV, une ligne par option listée :
    <devise>_options_snapshot_<AAAA-MM-JJ>_<HHMMSS>utc.csv
Le téléchargement est relancé si moins de 98 % des instruments ont répondu (limite de débit).
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://www.deribit.com/api/v2"
DELAI_S = 10
REQUETES_PARALLELES = 15      # 25 dépassent la limite de débit publique
ESSAIS_PAR_TICKER = 6
COMPLETUDE_MIN = 0.98
ESSAIS_COMPLETS = 3

_session = requests.Session()


def lister_options(devise="BTC"):
    """Noms des options actives de la devise (BTC, ETH, ...)."""
    r = _session.get(URL + "/public/get_instruments",
                     params={"currency": devise, "kind": "option", "expired": "false"}, timeout=DELAI_S)
    r.raise_for_status()
    return [x["instrument_name"] for x in r.json()["result"]]


def _ticker(nom):
    for k in range(ESSAIS_PAR_TICKER):
        r = _session.get(URL + "/public/ticker", params={"instrument_name": nom}, timeout=DELAI_S)
        if r.status_code == 429:
            time.sleep(0.5 * 2 ** k)
            continue
        r.raise_for_status()
        t = r.json()["result"]
        for c in ("greeks", "stats"):
            if isinstance(t.get(c), dict):
                t[c] = repr(t[c])
        return t
    r.raise_for_status()


def _une_passe(noms, bavard):
    lignes, echecs = [], 0
    with ThreadPoolExecutor(max_workers=REQUETES_PARALLELES) as pool:
        futurs = {pool.submit(_ticker, n): n for n in noms}
        for i, f in enumerate(as_completed(futurs), 1):
            try:
                lignes.append(f.result())
            except Exception:
                echecs += 1
            if bavard and (i % 200 == 0 or i == len(noms)):
                print("  {}/{} options".format(i, len(noms)))
    return pd.DataFrame(lignes), echecs


def telecharger_instantane(dossier, devise="BTC", bavard=True):
    """Télécharge la chaîne complète d'options de `devise` et l'écrit dans `dossier`.
    Renvoie le chemin du CSV."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    noms = lister_options(devise)
    meilleur = None
    for essai in range(1, ESSAIS_COMPLETS + 1):
        df, _ = _une_passe(noms, bavard)
        if meilleur is None or len(df) > len(meilleur):
            meilleur = df
        if len(df) >= COMPLETUDE_MIN * len(noms):
            break
        time.sleep(2.0)
    t = datetime.now(timezone.utc)
    chemin = dossier / "{}_options_snapshot_{}_{}utc.csv".format(devise.lower(), t.strftime("%Y-%m-%d"), t.strftime("%H%M%S"))
    meilleur.to_csv(chemin, index=False)
    if bavard:
        print("{} options -> {}".format(len(meilleur), chemin))
    return chemin


def instantanes(dossier, devise="BTC", jour=None):
    """Instantanés présents dans `dossier` (triés), éventuellement d'un jour AAAA-MM-JJ."""
    motif = "{}_options_snapshot_{}*utc.csv".format(devise.lower(), (jour + "_") if jour else "")
    return sorted(Path(dossier).glob(motif))


def horodatage(chemin):
    """'2026-08-26_090232' pour btc_options_snapshot_2026-08-26_090232utc.csv"""
    n = Path(chemin).name
    return n[n.index("snapshot_") + 9:-len("utc.csv")]


def telecharger_si_absent(dossier, devise="BTC", lignes_min=200, bavard=True):
    """Télécharge l'instantané du jour (date UTC) seulement s'il n'existe pas déjà un fichier
    complet (au moins `lignes_min` lignes). Renvoie le chemin de l'instantané du jour."""
    jour = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for f in reversed(instantanes(dossier, devise, jour)):
        with open(f, encoding="utf-8", errors="ignore") as h:
            if sum(1 for _ in h) - 1 >= lignes_min:
                if bavard:
                    print("instantané du jour déjà présent :", f.name)
                return f
    return telecharger_instantane(dossier, devise, bavard)
