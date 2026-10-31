"""
Simulateur de l'environnement : Permet de lire la grille réelle de la carte
et le contenu des casiers. L'agent (agent.py) n'y a jamais accès : il ne reçoit
que les perceptions renvoyées par ces fonctions.
"""
from typing import Optional

def simuler_environnement(carte_donnees: dict, pos_robot: tuple, action_dict: dict) -> tuple[tuple, dict]:
    l, c = pos_robot
    
    if action_dict["action"] == "AVANCER":
        direction = action_dict["argument"]
        if direction == "N": l -= 1
        elif direction == "S": l += 1
        elif direction == "E": c += 1
        elif direction == "O": c -= 1
        pos_robot = (l, c)

    grille_reelle = carte_donnees["grille"]
    
    voisins_directions = {
        "N": (l - 1, c),
        "S": (l + 1, c),
        "E": (l, c + 1),
        "O": (l, c - 1)
    }
    
    symboles_map = {
        "#": "mur",
        ".": "libre",
        "R": "libre",
        "D": "dictionnaire",
        "A": "armoire",
        "P": "resident"
    }

    perceptions = {}
    for d, (vl, vc) in voisins_directions.items():
        if 0 <= vl < len(grille_reelle) and 0 <= vc < len(grille_reelle[0]):
            symbole = grille_reelle[vl][vc]
            perceptions[d] = symboles_map.get(symbole, "libre")
        else:
            perceptions[d] = "mur"

    return pos_robot, perceptions

def simuler_armoire(armoire_donnees: dict, casier_selecteur: tuple, action_dict: dict) -> tuple[tuple, Optional[str]]:
    lig, col = casier_selecteur
    action = action_dict.get("action")
    arg = action_dict.get("argument")
    if action == "CHERCHER":
        if arg == "N" and lig > 0: lig -= 1
        elif arg == "S" and lig < 2: lig += 1
        elif arg == "E": col = (col + 1) % 8 
        elif arg == "O": col = (col - 1) % 8
    
    nouveau_selecteur = (lig, col)
    contenu_casier = None
    for casier in armoire_donnees.get("casiers", []):
        if casier["ligne"] == lig and casier["colonne"] == col:
            contenu_casier = casier.get("objet")  # None si vide, str si garni
            break

    return nouveau_selecteur, contenu_casier