import sys
from pathlib import Path
from collections import deque
from typing import Optional
from simulateur import simuler_environnement, simuler_armoire

import reconfort_io as rio
import validation as val

EQUIPE = ["HARAUT Kevin", "KADDOUR Reyam"]

class Plainte:
    """Une demande d'un résident + où on en est (émotion trouvée, casier visé, objet en main...)
      On en recrée une à chaque demande"""
    def __init__(self, demande_json: dict, pos_resident: tuple):
        self.numero = demande_json["numero"]
        self.id_resident = demande_json["resident"]
        self.message = rio.normaliser(demande_json["message"])
        self.pos_resident = pos_resident
        self.emotion = None        
        self.intensite = None        
        self.casiers_a_tester = []  
        self.casier_cible = None     
        self.objet_associe = None    
        self.objet_en_main = False
        self.casier_trouve = None
        self.repli = "aucun"
        self.dico_atteint = False          

class AgentReconfort:
    def __init__(self, carte: dict, dictionnaire: dict, armoire: dict):
        self.pos_actuelle = tuple(carte["depart_robot"])
        self.pos_dico = tuple(carte["dictionnaire"]["position"])
        self.pos_armoire = tuple(carte["armoire"]["position"])
        self.casier_selecteur = tuple(armoire["casier_depart"])
        self.emotions_roue = tuple(armoire["emotions"])
        self.casiers_vides_memoire = set()

        dimensions = carte.get("dimensions")
        self.hauteur = dimensions["hauteur"] if dimensions else None
        self.largeur = dimensions["largeur"] if dimensions else None

        self.pos_residents = {
            res["id"]: tuple(res["position"]) for res in carte["residents"]
        }

        self.dictionnaire_donnees = dictionnaire

        self.armoire_structure = {
            "emotions": armoire["emotions"],
            "intensites": armoire["intensites"],
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

        self.casiers_par_etiquette = {
            (c["emotion"], c["intensite"]): (c["ligne"], c["colonne"])
            for c in armoire["casiers"]
        }

        self.carte_mentale = {
            self.pos_actuelle: ".",
            self.pos_dico: "D",
            self.pos_armoire: "A",
        }
        for pos in self.pos_residents.values():
            self.carte_mentale[pos] = "P"

        self.chemin_en_cours = []
        self.sous_objectif_actuel = None
        self.plainte_active = None
        self.livraison_en_attente = None
        self.residents_atteints = set()


    def abandonner_plainte(self, motif: str, action: Optional[dict] = None) -> dict:
        """Termine la demande en échec avec son motif (résident inaccessible, armoire vide,
        émotion indéterminée) et prépare la livraison ratée pour la trace"""
        plainte = self.plainte_active
        self.livraison_en_attente = {
            "demande": plainte.numero,
            "resident": plainte.id_resident,
            "emotion": plainte.emotion,
            "intensite": plainte.intensite,
            "casier_choisi": None,
            "repli": "aucun",
            "objet": None,
            "succes": False,
            "motif_echec": motif,
        }

        print(f"ABANDON de la demande {plainte.numero} ({motif})")

        self.plainte_active = None
        self.sous_objectif_actuel = None

        return action or {"action": "ATTENDRE", "argument": None}

    def choisir_objectif(self):
        """Dans l'ordre : dico -> vérifier le résident -> armoire -> résident. La vérif du résident ne se fait qu'une fois par résident"""
        if self.plainte_active is None:
            return None

        if not self.plainte_active.dico_atteint:
            self.sous_objectif_actuel = "GO_DICO"
            return self.pos_dico
        
        elif (not self.plainte_active.objet_en_main and self.plainte_active.id_resident not in self.residents_atteints):
            self.sous_objectif_actuel = "VERIF_RESIDENT"
            return self.plainte_active.pos_resident
        
        elif not self.plainte_active.objet_en_main:
            self.sous_objectif_actuel = "GO_ARMOIRE"
            return self.pos_armoire

        else:
            self.sous_objectif_actuel = "GO_RESIDENT"
            return self.plainte_active.pos_resident

    def consulter_dictionnaire(self) -> dict:
        self.plainte_active.dico_atteint = True
                    
        self.plainte_active.emotion, self.plainte_active.intensite = self.analyser_message()
        
        print("\n" + "=" * 100)
        print("ACTION : CONSULTER le dictionnaire")
        print(f" Requête normalisée : \"{self.plainte_active.message}\"")
        print(f" Émotion conclue    : {self.plainte_active.emotion}")
        print(f" Intensité conclue   : {self.plainte_active.intensite}")
        print("=" * 100 + "\n")

        consulter = {"action": "CONSULTER", "argument": None}
        if self.plainte_active.emotion is None:
            return self.abandonner_plainte("emotion indeterminee", consulter)
        return consulter

    def fouiller_armoire(self, perceptions_locales: dict) -> dict:
        plainte = self.plainte_active

        if not plainte.casiers_a_tester:
            candidats = self.generer_candidats_plutchik(plainte.emotion, plainte.intensite)
            
            plainte.casiers_a_tester = [
                cand for cand in candidats 
                if cand[0] not in self.casiers_vides_memoire
            ]

            print("\n" + "=" * 100)
            print("ACTION : FOUILLER l'armoire")
            print(f" Émotion cible : {plainte.emotion}")
            print(f" Intensité cible : {plainte.intensite}")
            print(f" Liste brute Plutchik (15 candidats) :")
            for pos, em, idx in candidats:
                print(f"   • Casier {pos} -> {em} | {idx}")
            print(f" Casiers vides en mémoire : {list(self.casiers_vides_memoire)}")
            print(f" Candidats restants à tester ({len(plainte.casiers_a_tester)}) :")
            for pos, em, idx in plainte.casiers_a_tester:
                print(f"   -> Casier {pos}")
            print("=" * 100 + "\n")

            if not plainte.casiers_a_tester:
                print("Tous les casiers candidats sont vides ! (Échec armoire vide)")
                return self.abandonner_plainte("armoire vide")

            plainte.casier_cible = plainte.casiers_a_tester[0][0]
            print(f" Première cible sélectionnée : {plainte.casier_cible}")

        contenu = perceptions_locales.get("contenu_casier")

        if self.casier_selecteur == plainte.casier_cible:
            if contenu:

                print("\n" + "-" * 100)
                print(f"OBJET TROUVE : '{contenu}'")
                print(f"CASIER CIBLE ATTEINT : {self.casier_selecteur}")
                print(f"CIBLE INITIALE : {plainte.casier_cible}")
                print("-" * 100 + "\n")

                plainte.objet_associe = contenu
                plainte.casier_trouve = self.casier_selecteur
                plainte.objet_en_main = True
                emotion_casier = plainte.casiers_a_tester[0][1]
                plainte.repli = self.calculer_repli(plainte, emotion_casier)
                self.sous_objectif_actuel = "GO_RESIDENT"
                
                return {"action": "PRENDRE", "argument": contenu}
            else:
                print(f"Casier {self.casier_selecteur} vide. Mémorisation et passage au candidat suivant.")
                self.casiers_vides_memoire.add(self.casier_selecteur)
                plainte.casiers_a_tester.pop(0)

                if not plainte.casiers_a_tester:
                    print("Tous les casiers candidats de la liste ont été testés sans succès.")
                    return self.abandonner_plainte("armoire vide")

                plainte.casier_cible = plainte.casiers_a_tester[0][0]
                print(f"Nouvelle cible sélectionnée : {plainte.casier_cible}")

        direction = self.calculer_direction_selecteur(self.casier_selecteur, plainte.casier_cible)
        
        return {"action": "CHERCHER", "argument": direction}

    def livrer_resident(self) -> dict:
        plainte = self.plainte_active
        self.livraison_en_attente = {
            "demande": plainte.numero,
            "resident": plainte.id_resident,
            "emotion": plainte.emotion,
            "intensite": plainte.intensite,
            "casier_choisi": plainte.casier_trouve,
            "repli": plainte.repli,
            "objet": plainte.objet_associe,
            "succes": True,
        }

        print("\n" + "=" * 50)
        print(f"LIVRAISON RÉUSSIE | Demande #{plainte.numero}")
        print(f"Objet '{plainte.objet_associe}' pris en {plainte.casier_trouve} livré avec succès au résident {plainte.id_resident}.")
        print("=" * 50 + "\n")

        self.plainte_active = None
        self.sous_objectif_actuel = None
        
        return {"action": "DONNER", "argument": plainte.objet_associe}

    def interagir_avec_objectif(self, perceptions_locales: dict) -> dict:
        sous_obj = self.sous_objectif_actuel

        if sous_obj == "GO_DICO":
            return self.consulter_dictionnaire()
        elif sous_obj == "GO_ARMOIRE":
            return self.fouiller_armoire(perceptions_locales)
        elif sous_obj == "GO_RESIDENT":
            return self.livrer_resident()
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
            if direction in offsets:
                pos_tuple = offsets[direction]
                if pos_tuple not in self.carte_mentale or self.carte_mentale[pos_tuple] in (".", "libre"):
                    self.carte_mentale[pos_tuple] = type_case

    def est_adjacent(self, pos1: tuple, pos2: tuple) -> bool:
        if not pos1 or not pos2:
            return False
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1]) == 1

    def calculer_chemin_bfs(self, objectif: tuple) -> list:
        depart = self.pos_actuelle

        if self.est_adjacent(depart, objectif):
            return []

        obstacles = {"mur", "#", "dictionnaire", "D", "armoire", "A", "resident", "P"}

        def dans_la_grille(pos):

            if self.hauteur is None:
                return True
            return 0 <= pos[0] < self.hauteur and 0 <= pos[1] < self.largeur

        def obtenir_voisins(pos):
            l, c = pos
            voisins_potentiels = [(l - 1, c), (l + 1, c), (l, c + 1), (l, c - 1)]
            return [
                p for p in voisins_potentiels
                if dans_la_grille(p) and self.carte_mentale.get(p) not in obstacles
            ]

        file = deque([(depart, [depart])])
        visites = {depart}

        while file:
            pos_courante, chemin = file.popleft()

            for voisin in obtenir_voisins(pos_courante):
                if self.est_adjacent(voisin, objectif):
                    chemin_complet = chemin + [voisin]
                    return chemin_complet[1:]

                if voisin not in visites:
                    visites.add(voisin)
                    file.append((voisin, chemin + [voisin]))
        return []

    def convertir_case_en_direction(self, depart: tuple, arrivee: tuple) -> str:
        """Convertit un saut de case (ligne, colonne) en direction cardinale."""
        dl = arrivee[0] - depart[0]  
        dc = arrivee[1] - depart[1]

        if dl == -1: return "N"  
        if dl == 1:  return "S"  
        if dc == 1:  return "E"
        if dc == -1: return "O"  

        return "N"

    def decider_action(self, perceptions):
        """Gère le déplacement étape par étape vers l'objectif courant."""
        self.mettre_a_jour_perceptions(perceptions)

        pos_cible = self.choisir_objectif()
        if pos_cible is None:
            return {"action": "ATTENDRE", "argument": None}

        if self.sous_objectif_actuel == "VERIF_RESIDENT" and self.est_adjacent(self.pos_actuelle, pos_cible):
            self.residents_atteints.add(self.plainte_active.id_resident)
            self.chemin_en_cours = []
            pos_cible = self.choisir_objectif()

        if self.est_adjacent(self.pos_actuelle, pos_cible):
            self.chemin_en_cours = []
            return self.interagir_avec_objectif(perceptions)

        besoin_recalcul = (
            not self.chemin_en_cours 
            or self.carte_mentale.get(self.chemin_en_cours[0]) == "mur"
        )

        if besoin_recalcul:
            self.chemin_en_cours = self.calculer_chemin_bfs(pos_cible)

        if self.chemin_en_cours:
            prochaine_case = self.chemin_en_cours.pop(0)
            direction = self.convertir_case_en_direction(self.pos_actuelle, prochaine_case)
            return {"action": "AVANCER", "argument": direction}

        else:
            print("Impossible de trouver un chemin vers la cible ! (Résident inaccessible)")
            return self.abandonner_plainte("resident inaccessible")

    def analyser_message(self) -> tuple[str, str]:
        index_dico = {}
        for entree in self.dictionnaire_donnees.get("entrees", []):
            emotion = entree["emotion"]
            intensite = entree["intensite"]
            for forme in entree.get("formes", []):
                index_dico[forme.strip().lower()] = (emotion, intensite)

        mots_message = self.plainte_active.message

        for mot in mots_message:
            mot_clean = mot.strip().lower()
            if mot_clean in index_dico:
                return index_dico[mot_clean]

        return None, None

    def calculer_repli(self, plainte: Plainte, emotion_casier: str) -> str:
        casier_exact = self.casiers_par_etiquette.get((plainte.emotion, plainte.intensite))
        if plainte.casier_trouve == casier_exact:
            return "aucun"

        distance = self.calculer_distance_emotion(plainte.emotion, emotion_casier)
        if distance == 0:
            return "intensite"
        return f"voisine_{distance}"

    def calculer_distance_emotion(self, e1: str, e2: str) -> int:
        e1_clean = e1.lower()
        e2_clean = e2.lower()
        roue_clean = [e.lower() for e in self.emotions_roue]

        if e1_clean not in roue_clean or e2_clean not in roue_clean:
            return 4

        idx1: int = roue_clean.index(e1_clean)
        idx2: int = roue_clean.index(e2_clean)
        diff: int = abs(idx1 - idx2)
        taille: int = len(self.emotions_roue)
        return min(diff, taille - diff)

    def determiner_sens_rotation(self, emotion_cible: str, emotion_cand: str) -> int:
        if emotion_cible == emotion_cand:
            return 0  

        idx_cible: int = self.emotions_roue.index(emotion_cible)
        idx_cand: int = self.emotions_roue.index(emotion_cand)
        taille: int = len(self.emotions_roue)  

        if (idx_cible + 1) % taille == idx_cand or (idx_cible + 2) % taille == idx_cand:
            return 0 
        
        return 1 

    def generer_candidats_plutchik(self, emotion_cible: str, intensite_cible: int) -> list[tuple[tuple[int, int], str, int]]:
        candidats = []
        CONV_INTENSITE = {
            "faible": 1, "1": 1, 1: 1,
            "moyenne": 2, "2": 2, 2: 2,
            "forte": 3, "3": 3, 3: 3
        }
        val_i_cible = CONV_INTENSITE.get(str(intensite_cible).lower(), 2)

        for (emotion, intensite), coords in self.casiers_par_etiquette.items():
            dist: int = self.calculer_distance_emotion(emotion_cible, emotion)

            if dist > 2:
                continue

            val_i_cand = CONV_INTENSITE.get(str(intensite).lower(), 2)

            ecart_intensite: int = abs(val_i_cible - val_i_cand)
            rotation: int = self.determiner_sens_rotation(emotion_cible, emotion)

            cle_tri = (dist, ecart_intensite, val_i_cand, rotation)

            candidats.append((cle_tri, coords, emotion, intensite))

        candidats.sort(key=lambda item: item[0])

        return [(item[1], item[2], item[3]) for item in candidats]

    def calculer_direction_selecteur(self, depart: tuple[int, int], cible: tuple[int, int]) -> str:

        l_dep, c_dep = depart
        l_cib, c_cib = cible

        if l_dep < l_cib:
            return "S"
        elif l_dep > l_cib:
            return "N"

        if c_dep != c_cib:
            a = (c_cib - c_dep) % 8
            if a <= 4:
                return "E"   
            else:
                return "O"   

        return ""
    
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
    
def main(argv):
    
    avec_interface = len(argv) == 6 and argv[5] == "--gui"
    if len(argv) != 5 and not avec_interface:
        print("Usage: python agent.py <carte> <scenario> <dossier_donnees> <trace_sortie> [--gui]", file=sys.stderr)
        return 2

    chemin_carte = Path(argv[1])
    chemin_scenario = Path(argv[2])
    dossier_donnees = Path(argv[3])
    chemin_sortie = Path(argv[4])

    try:
        carte = rio.charger_carte(chemin_carte)
        val.valider_carte(carte)
        scenario = rio.charger_scenario(chemin_scenario)
        val.valider_scenario(scenario, carte)
        dictionnaire = rio.charger_dictionnaire(dossier_donnees / "dictionnaire.json")
        val.valider_dictionnaire(dictionnaire)
        armoire = rio.charger_armoire(dossier_donnees / f"{scenario['armoire']}.json")
        val.valider_armoire(armoire)
        val.valider_coherence_dictionnaire_armoire(dictionnaire, armoire)
    except rio.ErreurFichier as err:
        print(f"Erreur de chargement : {err}", file=sys.stderr)
        return 1
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as err:
        print(f"ERREUR : fichier d'entrée mal formé ({type(err).__name__} : {err})", file=sys.stderr)
        return 1

    carte_robot = {cle: valeur for cle, valeur in carte.items() if cle != "grille"}
    agent = AgentReconfort(carte_robot, dictionnaire, armoire)
    trace = rio.Trace(carte["nom"], scenario["nom"], equipe=EQUIPE)

    interface = None
    if avec_interface:
        from interface import SimulationPygame
        interface = SimulationPygame(dimensions=carte["dimensions"], cell_size=40)

    for demande in scenario["demandes"]:
        id_resident = demande["resident"]
        pos_res = agent.pos_residents[id_resident]
        agent.plainte_active = Plainte(demande, pos_res)
        
        print(f"\n"+"="*30)
        print(f" DÉBUT DEMANDE {demande['numero']} POUR {id_resident}")
        print(f"="*30 + "\n")
        tour = 0
        perceptions_locales = {}
        action_dict = {"action": "ATTENDRE", "argument": None}

        while agent.plainte_active is not None:
            agent.pos_actuelle, perceptions_locales = simuler_environnement(
                carte, agent.pos_actuelle, action_dict
            )

            agent.casier_selecteur, contenu = simuler_armoire(
                armoire, agent.casier_selecteur, action_dict
            )

            devant_armoire = agent.est_adjacent(agent.pos_actuelle, agent.pos_armoire)
            contenu_visible = contenu if devant_armoire else None
            perception_cases = dict(perceptions_locales) 

            perceptions_locales["contenu_casier"] = contenu_visible

            afficher_carte_mentale(agent, carte["dimensions"])

            action_dict = agent.decider_action(perceptions_locales)

            act_nom = action_dict['action']
            act_arg = action_dict.get('argument') or ''

            if act_nom == "CHERCHER":
                cible = agent.plainte_active.casier_cible if agent.plainte_active else "?"
                print(f"Tour {tour:<2} | Action: DEPLACER SELECTEUR ARMOIRE {act_arg} : Pos Actuelle {agent.casier_selecteur} vers Cible {cible}")
            elif act_nom == "PRENDRE":
                print(f"Tour {tour:<2} | Action: PRENDRE {act_arg} | Casier: {agent.casier_selecteur}")
            else:
                print(f"Tour {tour:<2} | Action: {act_nom} {act_arg} | Pos: {agent.pos_actuelle}")
            
            if interface is not None:
                interface.rafraichir(agent, fps=6)

            trace.ajouter_pas(
                demande=demande["numero"],
                position=agent.pos_actuelle,
                casier=agent.casier_selecteur,
                action=action_dict["action"],
                argument=action_dict.get("argument"),
                perception=perception_cases,
                contenu_casier=contenu_visible
            )

            if agent.livraison_en_attente is not None:
                trace.ajouter_livraison(**agent.livraison_en_attente)
                agent.livraison_en_attente = None

            tour += 1

    trace.ecrire(chemin_sortie)
    print(f"\nSimulation terminée avec succès. Trace écrite dans {chemin_sortie}")

    if interface is not None:
        interface.attendre_fermeture()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))