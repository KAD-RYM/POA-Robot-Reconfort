import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from agent import simuler_environnement, simuler_armoire

EMOTIONS = ["joie", "confiance", "peur", "surprise",
            "tristesse", "degout", "colere", "anticipation"]
INTENSITES = ["faible", "moyenne", "forte"]


def armoire_pleine(vides=()):
    """Armoire 3 x 8 dont chaque casier contient 'objet_l_c', sauf ceux de `vides`."""
    return {
        "casier_depart": [1, 0],
        "emotions": EMOTIONS,
        "intensites": INTENSITES,
        "casiers": [
            {"ligne": l, "colonne": c, "emotion": EMOTIONS[c], "intensite": INTENSITES[l],
             "objet": None if (l, c) in vides else f"objet_{l}_{c}"}
            for l in range(3) for c in range(8)
        ],
    }


def carte_main(grille, depart, armoire, dico, residents):
    """Petite carte écrite à la main (le champ grille sert au simulateur seulement)."""
    return {
        "dimensions": {"hauteur": len(grille), "largeur": len(grille[0])},
        "grille": grille,
        "depart_robot": list(depart),
        "armoire": {"position": list(armoire)},
        "dictionnaire": {"position": list(dico)},
        "residents": [{"id": rid, "nom": rid, "position": list(pos)} for rid, pos in residents],
    }


def simuler_jusqua_fin(agent, carte, armoire, max_tours=500):
    """Fait tourner la boucle perception -> décision jusqu'à la fin de la plainte."""
    action = {"action": "ATTENDRE", "argument": None}
    actions = []
    for _ in range(max_tours):
        agent.pos_actuelle, perceptions = simuler_environnement(carte, agent.pos_actuelle, action)
        agent.casier_selecteur, contenu = simuler_armoire(armoire, agent.casier_selecteur, action)
        perceptions["contenu_casier"] = contenu
        action = agent.decider_action(perceptions)
        actions.append(action)
        if agent.plainte_active is None:
            return actions
    raise AssertionError("la plainte ne se termine pas (boucle infinie ?)")