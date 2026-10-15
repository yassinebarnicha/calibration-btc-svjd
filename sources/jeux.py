# -*- coding: utf-8 -*-
"""Jeux de parametres calibres : format commun, rattachement aux jours, nom affiche.

Un jeu (format « calibration-a-la-main/jeux », version 1) :

    id            identifiant stable
    jour          date du marche (AAAA-MM-JJ) ; instantane : AAAA-MM-JJ_HHMMSS si connu
    modele        {"variance": heston | heston2 | hestonJ | const, "sauts": logn | biln | kou | cgmy | vg | nig | aucun}
    parametres    valeurs, avec les clefs de l'application (lam, muJ, sigJ pour Merton ; lam1..sigJ2 pour la bi-lognormale)
    calibration   {"origine", "moteur", "methode", "source", "nom_origine"} : d'ou vient le jeu
    donnees       echeances (dates) et filtres ; a defaut n_echeances et selection (dernieres | premieres | toutes)
    pricer        {"methode": COS | PROJ, "N", "L"}
    perte         {"mesure": px | iv | pxiv | rel | spr, "ponderation": raw | v2 | v2loc | v2eq | mateq}
    resultats     {"rmse_iv_bps", "rmse_prix_usd", "n_options"}

Dans la page, les jeux d'un jour sont classes par modele puis par RMSE IV croissante, et nommes
« moteur · methode · n ech. · perte · RMSE ».
"""
import json
from pathlib import Path

import pandas as pd

PERTES = {"px": "prix", "iv": "IV", "pxiv": "prix + IV", "rel": "prix relatif", "spr": "prix / fourchette"}
PONDERATIONS = {"raw": "brute", "v2": "1/vega²", "v2loc": "1/vega² local", "v2eq": "1/vega² égal", "mateq": "échéances égales"}
JOURS_MIN = 11          # regle de production : echeances a 11 jours ou plus
# point de depart generique de chaque jour : jeu Bates (Heston + Merton), mediane des bonnes calibrations 2024
GENERIQUE = dict(id="generique-bates-2024", nom="Région des bons jours 2024 (médiane des calibrations < 50 bps)",
                 groupe="Génériques", modele={"variance": "heston", "sauts": "logn"},
                 p=dict(kappa=3.904, theta=0.517, sigma=1.354, rho=0.282, v0=0.243, lam=0.419, muJ=-0.226, sigJ=0.511))


def charger_jeux(chemin):
    """Liste de jeux depuis calibrations.json, ou depuis un historique.csv de la chaine quotidienne."""
    chemin = Path(chemin)
    if chemin.suffix.lower() == ".json":
        return json.loads(chemin.read_text(encoding="utf-8"))["jeux"]
    jeux = []
    for i, x in pd.read_csv(chemin).iterrows():
        jeux.append(dict(
            id="{}-chaine-{}".format(x["horodatage"], x["moteur"]), jour=str(x["jour"])[:10], instantane=x["horodatage"],
            modele={"variance": "heston", "sauts": "logn"},
            parametres={k: float(x[k]) for k in ("kappa", "theta", "sigma", "rho", "v0", "lam", "muJ", "sigJ")},
            calibration=dict(origine="chaîne quotidienne", moteur={"surrogate": "v5", "cos": "COS"}.get(x["moteur"], x["moteur"]),
                             methode="DE + SLSQP", source=str(chemin)),
            donnees={}, n_echeances=int(x.get("n_echeances", 6)), selection="dernieres",
            pricer={"methode": "COS", "N": 512, "L": 24}, perte={"mesure": "px", "ponderation": "v2eq"},
            resultats=dict(rmse_iv_bps=float(x["rmse_iv_bps"]), rmse_prix_usd=float(x["rmse_prix"]), n_options=int(x["n_options"]))))
    return jeux


def jour_cible(jeu, cles):
    """Fichier de jour (clef = nom sans .js) qui recoit le jeu : l'instantane exact, sinon le jour, sinon le dernier
    instantane de cette date ; None si la page n'a pas ce jour."""
    if jeu.get("instantane") in cles:
        return jeu["instantane"]
    if jeu["jour"] in cles:
        return jeu["jour"]
    meme_date = sorted(c for c in cles if c[:10] == jeu["jour"])
    return meme_date[-1] if meme_date else None


def echeances(jeu, mats):
    """Echeances du jeu ; a defaut, les n dernieres (ou premieres, ou toutes) a JOURS_MIN jours ou plus du jour."""
    if jeu.get("donnees", {}).get("echeances"):
        return list(jeu["donnees"]["echeances"])
    ok = [m["date"] for m in mats if m["jours"] >= JOURS_MIN]
    n = jeu.get("n_echeances") or 6
    sel = jeu.get("selection", "dernieres")
    return ok if sel == "toutes" else ok[:n] if sel == "premieres" else ok[-n:]


def nom(jeu, n_ech):
    """Nom affiché : « moteur · méthode · n éch. · perte · RMSE »."""
    c, pe, r = jeu["calibration"], jeu.get("perte") or {}, jeu.get("resultats") or {}
    morceaux = [c.get("moteur", "?"), c.get("methode", "?"), "{} éch.".format(n_ech)]
    if pe:
        morceaux.append(PERTES.get(pe.get("mesure"), pe.get("mesure")) + " · " + PONDERATIONS.get(pe.get("ponderation"), pe.get("ponderation")))
    if r.get("rmse_iv_bps") is not None:
        morceaux.append("{:.1f} bps".format(r["rmse_iv_bps"]))
    return " · ".join(m for m in morceaux if m and m != "?")


def preset(jeu, mats):
    """Entree du menu « Point de depart » : le jeu, ses echeances resolues sur le jour, son nom."""
    ech = echeances(jeu, mats)
    donnees = {"options": "otm", "cible": "regle", "spread_rel_max": 0.2, "prix_min_btc": 0.005, "deux_cotes": True,
               **{k: v for k, v in jeu.get("donnees", {}).items() if k not in ("jour", "snapshot")}, "echeances": ech}
    reglage = dict(id=jeu["id"], nom=nom(jeu, len(ech)), modele=jeu["modele"], parametres=jeu["parametres"],
                   calibration=jeu["calibration"], donnees=donnees, pricer=jeu.get("pricer"), perte=jeu.get("perte"),
                   resultats=jeu.get("resultats") or {})
    return dict(id=jeu["id"], nom=reglage["nom"], groupe="Calibrations", modele=jeu["modele"], p=jeu["parametres"], reglage=reglage)
