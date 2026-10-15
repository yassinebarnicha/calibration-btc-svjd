# -*- coding: utf-8 -*-
"""pricers_fourier (réduit à Black-76) — prix, vega et volatilité implicite de Black-76.

    from pricers_fourier import prix_black76, vol_implicite
"""
from .black76 import prix_black76, vega_black76, vol_implicite

__all__ = ["prix_black76", "vega_black76", "vol_implicite"]
__version__ = "1.0.0"
