# -*- coding: utf-8 -*-
"""Full daily history of every Deribit future -> futures.js.

SOURCE
Deribit serves `get_tradingview_chart_data` even for expired instruments: this gives the daily close of each future
over its whole life, since its listing. The days of the page (jours/*.js) tell which maturities existed.

INCREMENTAL
Each raw answer is kept in cache_futures/. An expired maturity will not change any more: it is never downloaded
again. Only the instruments still alive are refreshed at each run.

Usage (online computer), then python build.py:
    python telecharger_futures.py                         # incremental
    python telecharger_futures.py --tout-retelecharger    # ignores the cache
    python telecharger_futures.py --cache D --pause 0.3
"""
import argparse
import io
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
CACHE = ICI / "cache_futures"
PAGES = [ICI.parent]

API = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"
UA = {"User-Agent": "calibration-bates/1.0"}
MOIS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
PRE, SUF = "window.__recevoirJour(", ");"


def fichiers_jours():
    """Fichiers jours/<cle>.js de toutes les pages, sans doublon (la premiere page l'emporte)."""
    vus = {}
    for page in PAGES:
        for p in sorted((page / "jours").glob("*.js")):
            vus.setdefault(p.name, p)
    return [vus[n] for n in sorted(vus)]


def ms(d):
    return int(d.replace(tzinfo=timezone.utc).timestamp() * 1000)


def jour(t):
    return datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")


def nom_deribit(iso):
    """2024-09-27 -> BTC-27SEP24 (jour sans zero de tete, comme Deribit)."""
    d = datetime.strptime(iso, "%Y-%m-%d")
    return "BTC-{}{}{:02d}".format(d.day, MOIS[d.month - 1], d.year % 100)


def get(url, essais=4):
    for k in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            # 400 = instrument inconnu de Deribit : une absence, pas une panne.
            # Le corps porte le detail, et le reessayer ne changerait rien.
            if e.code == 400:
                return {"error": json.loads(e.read() or b"{}").get("error", {})}
            if e.code not in (429, 500, 502, 503, 504) or k == essais - 1:
                raise
            time.sleep(2.0 * (k + 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if k == essais - 1:
                raise
            time.sleep(1.5 * (k + 1))          # l'API limite le debit : on cede


def serie(instrument, debut, fin):
    """Clotures quotidiennes, ou None si Deribit ne connait pas l'instrument."""
    u = "{}?instrument_name={}&start_timestamp={}&end_timestamp={}&resolution=1D".format(
        API, instrument, ms(debut), ms(fin))
    r = get(u).get("result", {})
    if r.get("status") != "ok" or not r.get("ticks"):
        return None
    return [[jour(t), round(float(c), 2)] for t, c in zip(r["ticks"], r["close"])]


def instantanes():
    """Echeances vues dans nos instantanes, et leur forward implicite.

    Deribit ne cote de future que pour une partie des expirations du chainier
    -- les hebdomadaires, mensuelles et trimestrielles. Les expirations
    QUOTIDIENNES n'ont aucun instrument : leur prix a terme n'existe que
    comme forward implicite, tire de la parite call-put, et c'est nous qui
    l'avons releve. Pour celles-la, nos instantanes restent la seule source,
    aussi trouee soit-elle.
    """
    implicite = {}
    for p in fichiers_jours():
        brut = io.open(p, encoding="utf-8").read()
        d = json.loads(brut[len(PRE):-len(SUF)])
        cols, vus = d["cols"], set()
        for i, m in enumerate(cols["m"]):
            if m in vus:
                continue
            vus.add(m)
            implicite.setdefault(d["mats"][m]["date"], []).append(
                [d["jour"], round(float(cols["F"][i]), 2)])
    return implicite


def cachee(nom, vivant, charge):
    """Lit le cache ; ne retelecharge que les instruments encore vivants."""
    f = CACHE / (nom + ".json")
    if f.exists() and not vivant:
        return json.loads(f.read_text(encoding="utf-8"))
    v = charge()
    f.write_text(json.dumps(v), encoding="utf-8")
    return v


def main():
    global CACHE
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--cache", default=str(CACHE), help="cache folder of the raw answers (default: %(default)s)")
    a.add_argument("--tout-retelecharger", action="store_true", help="also downloads again the expired maturities already cached")
    a.add_argument("--pause", type=float, default=0.12, help="seconds between two requests (default: %(default)s)")
    a = a.parse_args()
    CACHE = Path(a.cache)
    CACHE.mkdir(parents=True, exist_ok=True)
    implicite = instantanes()
    liste = sorted(implicite)
    aujourdhui = datetime.now(timezone.utc).replace(tzinfo=None)
    print("{} maturities to cover".format(len(liste)))

    brut, absentes, neuves = {}, [], 0
    for i, iso in enumerate(liste, 1):
        exp = datetime.strptime(iso, "%Y-%m-%d")
        nom = nom_deribit(iso)
        vivant = exp >= aujourdhui - timedelta(days=1) or a.tout_retelecharger
        neuf = not (CACHE / (nom + ".json")).exists() or vivant
        # 540 jours avant l'expiration : large de quoi couvrir meme les
        # echeances annuelles, cotees pres d'un an et demi avant leur terme
        s = cachee(nom, vivant,
                   lambda: serie(nom, exp - timedelta(days=540), exp + timedelta(days=2)))
        neuves += neuf
        if s:
            brut[iso] = s
        else:
            absentes.append(iso)
        if neuf:
            time.sleep(a.pause)                 # on reste poli avec l'API
        if i % 40 == 0:
            print("   {}/{}...".format(i, len(liste)))

    # PAS DE REPERE COMPTANT. Mesure faite : perpetuel contre spot Coinbase,
    # 54 bps d'ecart median quel que soit le decalage teste ; future le jour de
    # son expiration contre perpetuel, 116 bps. Les futures Deribit expirent a
    # 08:00 UTC et leur derniere bougie quotidienne ne couvre que huit heures,
    # la ou celle du perpetuel en couvre vingt-quatre. Or la base qu'on veut
    # lire vaut 5 a 60 bps sur les echeances courtes : diviser par un proxy
    # quotidien noierait le signal sous le bruit d'alignement.
    #
    # La base n'est donc calculee QUE la ou F et l'indice viennent du meme
    # instantane, au meme instant -- exactement le r = log(F/X)/T du reste du
    # projet. Trouee, mais juste ; le graphe la dessine en points.
    base = {}
    for p in fichiers_jours():
        d = json.loads(io.open(p, encoding="utf-8").read()[len(PRE):-len(SUF)])
        cols, X, vus = d["cols"], float(d["index"]), set()
        for i, m in enumerate(cols["m"]):
            if m in vus:
                continue
            vus.add(m)
            base.setdefault(d["mats"][m]["date"], []).append(
                [d["jour"], round((float(cols["F"][i]) / X - 1) * 1e4, 1)])

    # ce que Deribit ne cote pas, nos instantanes le portent quand meme
    retombee = {iso: s for iso, s in implicite.items() if iso not in brut and len(s) > 1}

    # ---- format compact : un axe de dates commun, une tranche par echeance ----
    axe = sorted({j for s in brut.values() for j, _ in s}
                 | {j for s in retombee.values() for j, _ in s}
                 | {j for s in base.values() for j, _ in s})
    rang = {j: i for i, j in enumerate(axe)}
    futures = {}
    # src : 0 = future cote chez Deribit, depuis son emission
    #       1 = forward implicite releve dans nos instantanes (troue)
    for source, lot in ((0, brut), (1, retombee)):
        for iso, s in lot.items():
            i0 = rang[s[0][0]]
            vals = [None] * (rang[s[-1][0]] - i0 + 1)
            for j, c in s:
                vals[rang[j] - i0] = c
            futures[iso] = [i0, vals, source]
    # la base ne vit que sur nos jours d'instantane : on la garde en paires
    # (rang du jour, bps) plutot qu'en tableau plein, qui serait vide a 84 %
    bases = {iso: [[rang[j], b] for j, b in s]
             for iso, s in base.items() if iso in futures}

    sortie = {"jours": axe, "futures": futures, "base": bases}
    txt = "window.__recevoirFutures(" + json.dumps(sortie, separators=(",", ":")) + ");"
    for dossier in PAGES:
        cible = dossier / "futures.js"
        tmp = cible.with_suffix(".tmp")
        io.open(tmp, "w", encoding="utf-8").write(txt)
        os.replace(tmp, cible)

    pts = sum(sum(v is not None for v in s[1]) for s in futures.values())
    print("\n{} maturities: {} listed futures (Deribit, since listing)"
          " + {} implied forwards (our snapshots)".format(
              len(futures), len(brut), len(retombee)))
    print("{} points, {} axis days, {:.0f} KB · {} downloaded this run".format(
        pts, len(axe), len(txt) / 1024, neuves))
    perdues = [a for a in absentes if a not in retombee]
    if perdues:
        print("{} maturity(ies) without any source: {}".format(
            len(perdues), ", ".join(perdues[:6])))
    long = max(futures.items(), key=lambda kv: len(kv[1][1]))
    print("the longest: {} over {} days, from {}".format(
        long[0], len(long[1][1]), axe[long[1][0]]))


if __name__ == "__main__":
    main()
