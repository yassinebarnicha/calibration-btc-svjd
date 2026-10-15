# -*- coding: utf-8 -*-
"""donnees_deribit — instantanés d'options Deribit et préparation du carnet à calibrer.

    from donnees_deribit import telecharger_instantane, charger_carnet, Regles
    chemin = telecharger_instantane("donnees/snapshots", devise="BTC")
    carnet, compte = charger_carnet(chemin, Regles(nb_echeances=6), detail=True)
"""
from .preparation import Regles, charger_carnet, lire_instantane, preparer_base, preparer_carnet
from .telechargement import (horodatage, instantanes, lister_options, telecharger_instantane,
                             telecharger_si_absent)

__all__ = ["Regles", "charger_carnet", "lire_instantane", "preparer_base", "preparer_carnet", "horodatage", "instantanes",
           "lister_options", "telecharger_instantane", "telecharger_si_absent"]
__version__ = "1.0.0"
