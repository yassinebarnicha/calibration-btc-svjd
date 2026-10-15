# -*- coding: utf-8 -*-
"""Black-76 sur future : prix, vega et inversion vectorisée de la volatilité implicite."""
import numpy as np
from scipy.special import ndtr

_SQ2PI = np.sqrt(2.0 * np.pi)


def _bc(*a):
    return np.broadcast_arrays(*[np.asarray(x, dtype=float) for x in a])


def _appel(call, forme):
    c = np.asarray(call)
    if c.dtype.kind in "US":
        c = np.char.lower(c.astype(str)) == "call"
    return np.broadcast_to(c.astype(bool), forme)


def prix_black76(F, K, T, sigma, r=0.0, call=True):
    """Prix Black-76 d'une option européenne sur future (vectorisé)."""
    F, K, T, sigma, r = _bc(F, K, T, sigma, r)
    call = _appel(call, F.shape)
    df = np.exp(-r * T)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = sigma * np.sqrt(T)
        d1 = (np.log(F / K) + 0.5 * s ** 2) / s
        d2 = d1 - s
        c = df * (F * ndtr(d1) - K * ndtr(d2))
        p = df * (K * ndtr(-d2) - F * ndtr(-d1))
    intr = df * np.where(call, np.maximum(F - K, 0.0), np.maximum(K - F, 0.0))
    out = np.where(call, c, p)
    return np.where((T > 0) & (sigma > 0), out, intr)


def vega_black76(F, K, T, sigma, r=0.0):
    """Vega Black-76 : dérivée du prix par rapport à sigma, e^{-rT} F phi(d1) sqrt(T)."""
    F, K, T, sigma, r = _bc(F, K, T, sigma, r)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = sigma * np.sqrt(T)
        d1 = (np.log(F / K) + 0.5 * s ** 2) / s
        v = np.exp(-r * T) * F * np.exp(-0.5 * d1 ** 2) / _SQ2PI * np.sqrt(T)
    return np.where((T > 0) & (sigma > 0), v, 0.0)


def vol_implicite(prix, F, K, T, r=0.0, call=True, sig_min=1e-6, sig_max=5.0, tol=1e-12, max_iter=100):
    """Inversion de Black-76 par Newton sauvegardé (encadrement resserré à chaque pas).

    Renvoie NaN pour un prix hors des bornes d'arbitrage ou sans racine dans [sig_min, sig_max],
    0 pour un prix égal à la valeur intrinsèque. Tout le carnet avance d'un pas à la fois."""
    p, F, K, T, r = _bc(prix, F, K, T, r)
    call = _appel(call, p.shape)
    out = np.full(p.shape, np.nan)
    with np.errstate(all="ignore"):
        ok = (F > 0) & (K > 0) & (T > 0) & np.isfinite(p)
        df = np.exp(-r * T)
        intr = df * np.where(call, np.maximum(F - K, 0.0), np.maximum(K - F, 0.0))
        haut = df * np.where(call, F, K)
        ok &= (p >= intr - 1e-10) & (p <= haut + 1e-10)
        zero = ok & (np.abs(p - intr) < 1e-12)
        out[zero] = 0.0
        w = ok & ~zero
        if not w.any():
            return out
        pw, Fw, Kw, Tw, rw, cw = p[w], F[w], K[w], T[w], r[w], call[w]
        lo = np.full(pw.shape, sig_min)
        hi = np.full(pw.shape, sig_max)
        f_lo = prix_black76(Fw, Kw, Tw, lo, rw, cw) - pw
        f_hi = prix_black76(Fw, Kw, Tw, hi, rw, cw) - pw
        racine = (f_lo <= 0) & (f_hi >= 0)
        s = np.clip(np.sqrt(2.0 * np.pi / Tw) * pw / (np.exp(-rw * Tw) * Fw), 1e-4, 0.9 * sig_max)
        for _ in range(max_iter):
            f = prix_black76(Fw, Kw, Tw, s, rw, cw) - pw
            lo = np.where(f < 0, s, lo)
            hi = np.where(f > 0, s, hi)
            v = vega_black76(Fw, Kw, Tw, s, rw)
            n = s - f / np.where(v > 0, v, np.nan)
            n = np.where(np.isfinite(n) & (n > lo) & (n < hi), n, 0.5 * (lo + hi))
            fini = np.max(np.abs(n - s)) < tol
            s = n
            if fini:
                break
        out[w] = np.where(racine, s, np.nan)
    return out
