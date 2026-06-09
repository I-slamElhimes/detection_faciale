# utils/cosinus.py
import numpy as np


def similarite_cosinus(vec1, vec2):
    """
    Calcule la distance cosinus entre deux vecteurs 512D.
    Retourne une valeur entre 0.0 et 2.0.
    
    0.0  = même personne (photo identique)
    < 0.45 = même personne (photos différentes)
    > 0.45 = personnes différentes
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    cosinus  = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    distance = 1.0 - cosinus
    return float(distance)