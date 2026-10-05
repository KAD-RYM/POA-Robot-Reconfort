import sys
from pathlib import Path
from collections import deque

import reconfort_io as rio
import validation as val

class Plainte:
    """Représente une demande de résident et l'avancement de sa résolution."""
    
    def __init__(self, demande_json: dict, pos_resident: tuple):
        self.numero = demande_json["numero"]
        self.id_resident = demande_json["resident"]
        self.message = rio.normaliser(demande_json["message"])
        self.pos_resident = pos_resident

        # Données résolues au fur et à mesure
        self.emotion = None           # e.g., "tristesse"
        self.intensite = None         # e.g., "moyenne"
        self.objet_associe = None     # e.g., "couverture"
        self.casiers_a_tester = []    # Liste ordonnée des 15 casiers candidats
        self.casier_cible = None      # Casier actuellement visé dans l'armoire
        self.objet_en_main = False
        self.repli = "aucun"          # "aucun", "intensite", "voisine_1", "voisine_2"

class AgentReconfort:
    """Agent autonome qui respecte strictement les règles de perception locale."""

    def __init__(self, carte: dict, dictionnaire: dict, armoire: dict):
        # 1. Extraction UNIQUEMENT des positions autorisées (Section 3.2)
        self.pos_actuelle = tuple(carte["depart_robot"])
        self.pos_dico = tuple(carte["dictionnaire"]["position"])
        self.pos_armoire = tuple(carte["armoire"]["position"])
        self.casier_selecteur = tuple(armoire["casier_depart"])  # [ligne, colonne]

        # Table des résidents : {"R1": (6, 11), ...}
        self.pos_residents = {
            res["id"]: tuple(res["position"]) for res in carte["residents"]
        }

        # 2. Dictionnaire : accès complet autorisé pour la recherche de mots (Section 6.1)
        self.dictionnaire_donnees = dictionnaire

        # 3. Armoire : ON NE GARDE QUE LES ÉTIQUETTES (Pas le champ "objet" !)
        self.armoire_structure = {
            "emotions": armoire["emotions"],
            "intensites": armoire["intensites"],
            # On conserve la grille d'étiquettes sans le contenu des casiers
            "casiers": [
                {
                    "ligne": c["ligne"],
                    "colonne": c["colonne"],
                    "emotion": c["emotion"],
                    "intensite": c["intensite"]
                }
                for c in armoire["casiers"]
            ]
        }

        # 4. Carte mentale initiale (seuls les éléments connus, AUCUN mur)
        self.carte_mentale = {
            self.pos_actuelle: ".",
            self.pos_dico: "D",
            self.pos_armoire: "A",
        }
        for pos in self.pos_residents.values():
            self.carte_mentale[pos] = "P"

        # 5. États internes
        self.chemin_en_cours = []
        self.sous_objectif_actuel = None
        self.plainte_active = None

    def choisir_objectif(self):
        """Détermine la cible uniquement en fonction du trajet de la plainte."""
        if not hasattr(self, 'plainte_active') or self.plainte_active is None:
            return None

        # Étape 1 : Se rendre au dictionnaire
        if not getattr(self.plainte_active, 'dico_atteint', False):
            self.sous_objectif_actuel = "GO_DICO"
            return self.pos_dico

        # Étape 2 : Se rendre à l'armoire
        elif not getattr(self.plainte_active, 'armoire_atteinte', False):
            self.sous_objectif_actuel = "GO_ARMOIRE"
            return self.pos_armoire

        # Étape 3 : Se rendre auprès du résident
        else:
            self.sous_objectif_actuel = "GO_RESIDENT"
            return self.plainte_active.pos_resident

    def interagir_avec_objectif(self):
        """
        Déclenché uniquement quand l'agent est adjacent à sa cible.
        Valide l'étape en cours et renvoie l'action.
        """
        sous_obj = self.sous_objectif_actuel

        if sous_obj == "GO_DICO":
            self.plainte_active.dico_atteint = True
            return {"action": "CONSULTER", "argument": None}

        elif sous_obj == "GO_ARMOIRE":
            self.plainte_active.armoire_atteinte = True
            return {"action": "CHERCHER", "argument": "E"}  # Mouvement de test pour l'armoire

        elif sous_obj == "GO_RESIDENT":
            # La plainte est terminée, on la réinitialise pour passer à la suivante !
            self.plainte_active = None
            self.sous_objectif_actuel = None
            return {"action": "DONNER", "argument": "objet_test"}

        return {"action": "ATTENDRE", "argument": None}

    def mettre_a_jour_perceptions(self, perceptions: dict) -> None:
        if not perceptions:
            return

        l, c = self.pos_actuelle
        offsets = {
            "N": (l - 1, c),
            "S": (l + 1, c),
            "E": (l, c + 1),
            "O": (l, c - 1)
        }

        for direction, type_case in perceptions.items():
            pos_tuple = offsets[direction]
            if pos_tuple not in self.carte_mentale or self.carte_mentale[pos_tuple] in (".", "libre"):
                self.carte_mentale[pos_tuple] = type_case

    def est_adjacent(self, pos1: tuple, pos2: tuple) -> bool:
        """Vérifie si pos1 et pos2 sont orthogonale-ment adjacentes (distance Manhattan = 1)."""
        if not pos1 or not pos2:
            return False
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1]) == 1

    def calculer_chemin_bfs(self, objectif: tuple) -> list:
        """
        Calcule le plus court chemin pour arriver sur une case ADJACENTE à l'objectif
        en utilisant un parcours en largeur (BFS) sur la carte mentale.
        """
        depart = self.pos_actuelle

        # Si on est déjà adjacent à l'objectif, aucun déplacement n'est nécessaire
        if self.est_adjacent(depart, objectif):
            return []

        # Ensemble des types de cases qu'on ne peut PAS traverser
        obstacles = {"mur", "#", "dictionnaire", "D", "armoire", "A", "resident", "P"}

        def obtenir_voisins(pos):
            l, c = pos
            # 4 directions orthogonales (ligne, colonne)[cite: 4]
            voisins_potentiels = [(l - 1, c), (l + 1, c), (l, c + 1), (l, c - 1)]
            # On exclut uniquement les cases explicitement connues comme des murs ("mur" ou "#")[cite: 3, 16]
            return [
                p for p in voisins_potentiels 
                if self.carte_mentale.get(p) not in obstacles
            ]

        # File BFS : stocke des couples (position_courante, chemin_parcouru)[cite: 15]
        file = deque([(depart, [depart])])
        visites = {depart}

        while file:
            pos_courante, chemin = file.popleft()

            for voisin in obtenir_voisins(pos_courante):
                # Condition de succès : le voisin est-il adjacent à l'objectif ?[cite: 4, 15]
                if self.est_adjacent(voisin, objectif):
                    # On retire la position de départ du chemin à retourner
                    chemin_complet = chemin + [voisin]
                    return chemin_complet[1:]

                if voisin not in visites:
                    visites.add(voisin)
                    file.append((voisin, chemin + [voisin]))

        # Aucun chemin trouvé (par exemple si le résident est inaccessible)[cite: 10, 16]
        return []

    def convertir_case_en_direction(self, depart: tuple, arrivee: tuple) -> str:
        """Convertit un saut de case (ligne, colonne) en direction cardinale."""
        dl = arrivee[0] - depart[0]  # Changement de ligne
        dc = arrivee[1] - depart[1]  # Changement de colonne

        if dl == -1: return "N"  # ligne - 1[cite: 4]
        if dl == 1:  return "S"  # ligne + 1[cite: 4]
        if dc == 1:  return "E"  # colonne + 1[cite: 4]
        if dc == -1: return "O"  # colonne - 1[cite: 4]

        return "N"

    def decider_action(self, perceptions):
        """Gère le déplacement étape par étape vers l'objectif courant."""
        # 1. Enregistre les cases perçues dans la carte mentale
        self.mettre_a_jour_perceptions(perceptions)

        # 2. Récupère la case cible
        pos_cible = self.choisir_objectif()
        if pos_cible is None:
            return {"action": "ATTENDRE", "argument": None}

        # 3. Si on est collé à la cible -> On interagit !
        if self.est_adjacent(self.pos_actuelle, pos_cible):
            self.chemin_en_cours = []
            return self.interagir_avec_objectif()

        # 4. Sinon, on recalcule ou on suit le chemin BFS
        besoin_recalcul = (
            not self.chemin_en_cours 
            or self.carte_mentale.get(self.chemin_en_cours[0]) == "mur"
        )

        if besoin_recalcul:
            self.chemin_en_cours = self.calculer_chemin_bfs(pos_cible)

        # 5. On extrait le prochain pas et on avance
        if self.chemin_en_cours:
            prochaine_case = self.chemin_en_cours.pop(0)
            
            # Sécurité si la première case est la position actuelle
            if prochaine_case == self.pos_actuelle and self.chemin_en_cours:
                prochaine_case = self.chemin_en_cours.pop(0)

            direction = self.convertir_case_en_direction(self.pos_actuelle, prochaine_case)
            return {"action": "AVANCER", "argument": direction}

        return {"action": "ATTENDRE", "argument": None}
    

def afficher_carte_mentale(agent: AgentReconfort, dimensions: dict):
    """
    Affiche la grille de la carte mentale en mode texte.
    R représente la position actuelle du robot.
    """
    hauteur = dimensions["hauteur"]
    largeur = dimensions["largeur"]

    print("\n--- Carte Mentale de l'Agent ---")
    for l in range(hauteur):
        ligne_str = ""
        for c in range(largeur):
            pos = (l, c)
            if pos == agent.pos_actuelle:
                ligne_str += "R "  # Le robot à sa position courante
            elif pos in agent.carte_mentale:
                val = agent.carte_mentale[pos]
                if val in ("mur", "#"):
                    ligne_str += "# "
                elif val in ("libre", "."):
                    ligne_str += ". "
                elif val == "D":
                    ligne_str += "D "
                elif val == "A":
                    ligne_str += "A "
                elif val == "P":
                    ligne_str += "P "
                else:
                    ligne_str += "? "
            else:
                ligne_str += "  "  # Case encore non perçue
        print(ligne_str)
    print("--------------------------------\n")

def simuler_environnement(carte_donnees: dict, pos_robot: tuple, action_dict: dict) -> tuple[tuple, dict]:
    l, c = pos_robot
    
    # Déplacement
    if action_dict["action"] == "AVANCER":
        direction = action_dict["argument"]
        if direction == "N": l -= 1
        elif direction == "S": l += 1
        elif direction == "E": c += 1
        elif direction == "O": c -= 1
        pos_robot = (l, c)

    grille_reelle = carte_donnees["grille"]
    
    # On associe la direction cardinale aux coordonnées réelles
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

def main(argv):
    if len(argv) != 5:
        print("Usage: python agent.py <carte> <scenario> <dossier_donnees> <trace_sortie>", file=sys.stderr)
        return 2

    chemin_carte = Path(argv[1])
    chemin_scenario = Path(argv[2])
    dossier_donnees = Path(argv[3])
    chemin_sortie = Path(argv[4])

    # 1. Chargement des fichiers d'entrée
    try:
        carte = rio.charger_carte(chemin_carte)
        scenario = rio.charger_scenario(chemin_scenario)
        dictionnaire = rio.charger_dictionnaire(dossier_donnees / "dictionnaire.json")
        armoire = rio.charger_armoire(dossier_donnees / f"{scenario['armoire']}.json")
    except rio.ErreurFichier as err:
        print(f"Erreur de chargement : {err}", file=sys.stderr)
        return 1

    # 2. Validation de la structure (quitte avec sys.exit(1) si invalide)
    val.valider_carte(carte)
    val.valider_scenario(scenario, carte)
    val.valider_armoire(armoire)
    val.valider_dictionnaire(dictionnaire)

    # 2. Instanciation de l'agent et de la trace
    agent = AgentReconfort(carte, dictionnaire, armoire)
    trace = rio.Trace(carte["nom"], scenario["nom"], equipe=["Test", "Agent"])

    # 3. Boucle sur chaque demande du scénario
    for demande in scenario["demandes"]:
        id_resident = demande["resident"]
        pos_res = agent.pos_residents[id_resident]
        
        # Injection de la plainte en cours
        agent.plainte_active = Plainte(demande, pos_res)
        
        print(f"\n==========================================")
        print(f" DÉBUT DEMANDE {demande['numero']} POUR {id_resident}")
        print(f"==========================================")

        tour = 0
        perceptions_locales = {}

        # Boucle tour par tour jusqu'à la livraison complète au résident
        while agent.plainte_active is not None:
            # A. L'environnement simule la perception autour de la position physique
            agent.pos_actuelle, perceptions_locales = simuler_environnement(
                carte, agent.pos_actuelle, {"action": "ATTENDRE", "argument": None}
            )

            # B. L'agent décide de son action
            action_dict = agent.decider_action(perceptions_locales)

            # C. Affichage visuel dans la console
            print(f"Tour {tour} | Action: {action_dict['action']} {action_dict.get('argument') or ''} | Pos: {agent.pos_actuelle}")
            afficher_carte_mentale(agent, carte["dimensions"])

            # D. Application de l'action dans le monde réel
            agent.pos_actuelle, _ = simuler_environnement(
                carte, agent.pos_actuelle, action_dict
            )

            # E. Enregistrement dans la trace
            trace.ajouter_pas(
                demande=demande["numero"],
                position=agent.pos_actuelle,
                casier=agent.casier_selecteur,
                action=action_dict["action"],
                argument=action_dict.get("argument"),
                perception=perceptions_locales
            )

            tour += 1

        # Clôture fictive de la livraison pour ce test de déplacement
        trace.ajouter_livraison(
            demande=demande["numero"],
            resident=id_resident,
            emotion="tristesse",
            intensite="moyenne",
            casier_choisi=(1, 4),
            repli="aucun",
            objet="objet_test",
            succes=True
        )

    # 4. Écriture du fichier de trace
    trace.ecrire(chemin_sortie)
    print(f"\nSimulation terminée avec succès. Trace écrite dans {chemin_sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))