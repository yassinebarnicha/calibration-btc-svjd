# -*- coding: utf-8 -*-
"""Préparation d'un instantané Deribit en carnet d'options à calibrer.

Étapes (toutes paramétrables par `Regles`) :
    1. colonnes de base   : échéance, strike, type, T (ACT/365), F (future), X (indice)
                            T = temps jusqu'à l'expiration Deribit (08:00 UTC), à l'heure près
    2. dollars            : prix = prix en BTC x X ; milieu et spread relatif de la fourchette
    3. taux               : r = log(F / X) / T, coût de portage, sert seulement à l'actualisation
    4. volatilités        : inversion de Black-76 du mark et du milieu (jamais l'IV publiée)
    5. cible              : mark s'il est dans la fourchette bid-ask, sinon milieu (règle par défaut)
    6. vega Black-76      : à la volatilité de la cible
    7. filtres            : nettoyage, deux côtés cotés, spread, prix minimal, OTM, maturité minimale,
                            nombre minimal d'options par échéance, N dernières échéances

Le carnet produit a des colonnes standard, utilisées par les pricers et la calibration :
    echeance, jours, T, K, call, F, X, r, prix, iv, vega, bid_usd, ask_usd, mid_usd, iv_mid, source_cible
"""
from __future__ import annotations

import ast
from dataclasses import dataclass

import numpy as np
import pandas as pd

from pricers_fourier import vega_black76, vol_implicite

# T a l'heure pres. Les options Deribit expirent a 08:00 UTC et chaque ligne de
# l'instantane porte son horodatage a la milliseconde : T = (expiration 08:00 UTC
# - horodatage) / 365 jours. Compter en jours entiers faussait r = log(F/X)/T et
# les echeances courtes (0 a 7 jours), ou quelques heures pesent lourd.
# t_horaire=False redonne l'ancien calcul (jours calendaires entiers / 365), celui
# des calibrations faites avant le 15/10/2026.
HEURE_EXPIRATION = pd.Timedelta(hours=8)          # expiration Deribit : 08:00 UTC


@dataclass
class Regles:
    """Règles de préparation. Les valeurs par défaut sont celles de la production."""
    cible: str = "mark_dans_fourchette"   # "mark_dans_fourchette", "mark" ou "mid"
    spread_relatif_max: float = 0.20       # (ask - bid) / mid
    prix_min: float = 0.005                # prix minimal de la cible, en unité de la devise (BTC)
    otm_seulement: bool = True             # puts K < F, calls K > F
    jours_min: int = 11                    # maturité minimale (jours calendaires)
    options_min_par_echeance: int = 1
    nb_echeances: int | None = 6           # les N dernières échéances retenues (None : toutes)
    echeances: list | None = None          # liste explicite AAAA-MM-JJ (prioritaire)
    t_horaire: bool = True                 # T à l'heure près ; False : jours entiers / 365 (ancien calcul)


def lire_instantane(chemin):
    """Instantané brut (DataFrame), tel que téléchargé."""
    return pd.read_csv(chemin)


def _base(brut, t_horaire=True):
    df = brut.copy()
    p = df["instrument_name"].str.split("-", expand=True)
    df["echeance"] = pd.to_datetime(p[1], format="%d%b%y")
    df["K"] = p[2].astype(float)
    df["call"] = p[3].str.upper().eq("C")
    instant = pd.to_datetime(df["timestamp"], unit="ms")          # UTC
    df["date"] = instant.dt.normalize()
    df["jours"] = (df["echeance"] - df["date"]).dt.days          # jours calendaires (filtres, affichage)
    if t_horaire:
        df["T"] = (df["echeance"] + HEURE_EXPIRATION - instant) / pd.Timedelta(days=365)
    else:
        df["T"] = df["jours"] / 365.0
    df["F"] = df["underlying_price"].astype(float)
    df["X"] = df["index_price"].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        df["r"] = np.log(df["F"] / df["X"]) / df["T"]
    bid, ask = df["best_bid_price"].astype(float), df["best_ask_price"].astype(float)
    deux = (bid > 0) & (ask > 0)
    mid = np.where(deux, 0.5 * (bid + ask), np.nan)
    df["deux_cotes"] = deux
    df["spread_relatif"] = np.where(deux, (ask - bid) / mid, np.nan)
    df["mark_usd"] = df["mark_price"] * df["X"]
    df["mid_usd"] = mid * df["X"]
    df["bid_usd"], df["ask_usd"] = bid * df["X"], ask * df["X"]
    return df


def _volatilites(df):
    args = (df["F"].to_numpy(), df["K"].to_numpy(), df["T"].to_numpy(), df["r"].to_numpy(), df["call"].to_numpy())
    df["iv_mark"] = vol_implicite(df["mark_usd"].to_numpy(), *args)
    mid = df["mid_usd"].to_numpy()
    iv = vol_implicite(np.where(np.isfinite(mid), mid, 0.0), *args)
    df["iv_mid"] = np.where(np.isfinite(mid) & (mid > 0), iv, np.nan)
    return df


def _cible(df, regle):
    df["prix"], df["iv"], df["source_cible"] = df["mark_usd"], df["iv_mark"], "mark"
    mid_ok = df["iv_mid"].notna() & (df["iv_mid"] > 0)
    if regle == "mid":
        m = mid_ok
    elif regle == "mark_dans_fourchette":
        bid, ask, mark = df["best_bid_price"], df["best_ask_price"], df["mark_price"]
        hors = df["deux_cotes"] & (ask >= bid) & ((mark < bid - 1e-12) | (mark > ask + 1e-12))
        m = hors & mid_ok
        df.loc[hors & ~mid_ok, "source_cible"] = "mark_hors_fourchette"
    elif regle == "mark":
        m = pd.Series(False, index=df.index)
    else:
        raise ValueError("règle de cible inconnue : " + regle)
    df.loc[m, "prix"], df.loc[m, "iv"], df.loc[m, "source_cible"] = df.loc[m, "mid_usd"], df.loc[m, "iv_mid"], "mid"
    df["prix_devise"] = df["prix"] / df["X"]
    return df


def _complet(brut, regle, t_horaire=True):
    df = _cible(_volatilites(_base(brut, t_horaire)), regle)
    df["vega"] = vega_black76(df["F"], df["K"], df["T"], df["iv"], df["r"])
    return df


def _nettoyer(df):
    return df[(df["T"] > 0) & np.isfinite(df["iv"]) & (df["iv"] > 0) & (df["prix"] > 0) & (df["vega"] > 1e-8)]


def preparer_base(brut, cible="mark_dans_fourchette", t_horaire=True):
    """Chaîne complète nettoyée (toutes échéances, calls et puts, toutes colonnes) : étapes 1 à 6 et
    élimination des lignes sans prix ou sans volatilité exploitable. t_horaire : T à l'heure près
    (False : jours entiers / 365, l'ancien calcul)."""
    return _nettoyer(_complet(brut, cible, t_horaire)).reset_index(drop=True)


def preparer_carnet(brut, regles: Regles | None = None, detail=False):
    """Instantané brut -> carnet filtré (DataFrame trié par échéance, type, strike).
    detail=True renvoie aussi le nombre d'options par échéance à chaque étape."""
    R = regles or Regles()
    df = _complet(brut, R.cible, R.t_horaire)
    etapes = {"brut": df}
    df = _nettoyer(df)
    etapes["nettoye"] = df
    df = df[df["deux_cotes"] & (df["spread_relatif"] < R.spread_relatif_max) & (df["prix_devise"] > R.prix_min)]
    etapes["fourchette"] = df
    if R.otm_seulement:
        df = df[(~df["call"] & (df["K"] < df["F"])) | (df["call"] & (df["K"] > df["F"]))]
    etapes["otm"] = df
    df = df[df["jours"] >= R.jours_min]
    n = df.groupby("echeance").size()
    df = df[df["echeance"].isin(n[n >= R.options_min_par_echeance].index)]
    etapes["maturite"] = df
    if R.echeances:
        df = df[df["echeance"].isin(pd.to_datetime(R.echeances))]
    elif R.nb_echeances:
        df = df[df["echeance"].isin(sorted(df["echeance"].unique())[-R.nb_echeances:])]
    etapes["retenu"] = df
    colonnes = ["echeance", "jours", "T", "K", "call", "F", "X", "r", "prix", "iv", "vega", "bid_usd", "ask_usd",
                "mid_usd", "iv_mid", "iv_mark", "spread_relatif", "source_cible", "instrument_name"]
    carnet = df[colonnes].sort_values(["echeance", "call", "K"]).reset_index(drop=True)
    if not detail:
        return carnet
    compte = pd.DataFrame({k: v.groupby("echeance").size() for k, v in etapes.items()}).fillna(0).astype(int)
    compte.insert(0, "jours", etapes["brut"].groupby("echeance")["jours"].first())
    return carnet, compte


def charger_carnet(chemin, regles: Regles | None = None, detail=False):
    """Raccourci : lire_instantane puis preparer_carnet."""
    return preparer_carnet(lire_instantane(chemin), regles, detail)


def vega_deribit(brut):
    """Vega publiée par Deribit (colonne greeks), pour comparaison."""
    return brut["greeks"].apply(lambda g: ast.literal_eval(g).get("vega") if isinstance(g, str) else np.nan)
