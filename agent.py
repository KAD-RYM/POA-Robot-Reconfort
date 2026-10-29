import sys
from pathlib import Path
from collections import deque
from typing import Optional
#from interface import SimulationPygame

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
        self.casiers_a_tester = []    # Liste ordonnée des 15 casiers candidats
        self.casier_cible = None      # Casier actuellement visé dans l'armoire
        self.objet_associe = None     # e.g., "couverture"
        self.objet_en_main = False
        self.casier_trouve = None
        self.repli = "aucun"          # "aucun", "intensite", "voisine_1", "voisine_2"

class AgentReconfort:
    """Agent autonome qui respecte strictement les règles de perception locale."""

    def __init__(self, carte: dict, dictionnaire: dict, armoire: dict):
        # 1. Extraction UNIQUEMENT des positions autorisées (Section 3.2)
        self.pos_actuelle = tuple(carte["depart_robot"])
        self.pos_dico = tuple(carte["dictionnaire"]["position"])
        self.pos_armoire = tuple(carte["armoire"]["position"])
        self.casier_selecteur = tuple(armoire["casier_depart"])
        self.emotions_roue = tuple(armoire["emotions"])
        self.casiers_vides_memoire = set()

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

        # Table de correspondance rapide : (emotion, intensite) -> (ligne, colonne)
        self.casiers_par_etiquette = {
            (c["emotion"], c["intensite"]): (c["ligne"], c["colonne"])
            for c in armoire["casiers"]
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
        # Livraison terminée (réussie ou non) que main() doit écrire dans la trace
        self.livraison_en_attente = None
        # Résidents déjà atteints au moins une fois : un chemin vers eux est prouvé
        self.residents_atteints = set()


    def abandonner_plainte(self, motif: str, action: Optional[dict] = None) -> dict:
        """
        Clôture la plainte en cours sur un échec.
        motif : "resident inaccessible", "armoire vide" ou "emotion indeterminee".
        action : l'action jouée ce tour-ci (ATTENDRE par défaut).
        """
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

        print(f"❌ ABANDON de la demande {plainte.numero} ({motif})")

        # On réinitialise le cerveau du robot
        self.plainte_active = None
        self.sous_objectif_actuel = None

        return action or {"action": "ATTENDRE", "argument": None}

    def choisir_objectif(self):
        """Détermine la cible uniquement en fonction du trajet de la plainte."""
        if not hasattr(self, 'plainte_active') or self.plainte_active is None:
            return None

        # Étape 1 : Se rendre au dictionnaire (jusqu'à consultation)
        if not getattr(self.plainte_active, 'dico_atteint', False):
            self.sous_objectif_actuel = "GO_DICO"
            return self.pos_dico

        # Étape 1 bis : si ce résident n'a jamais été atteint, prouver qu'il est
        # accessible AVANT de prendre l'objet (sinon le robot resterait chargé)
        elif (not getattr(self.plainte_active, 'objet_en_main', False) and self.plainte_active.id_resident not in self.residents_atteints):
            self.sous_objectif_actuel = "VERIF_RESIDENT"
            return self.plainte_active.pos_resident

        # Étape 2 : Se rendre à l'armoire (jusqu'à avoir pris l'objet !)
        elif not getattr(self.plainte_active, 'objet_en_main', False):
            self.sous_objectif_actuel = "GO_ARMOIRE"
            return self.pos_armoire

        # Étape 3 : Se rendre auprès du résident
        else:
            self.sous_objectif_actuel = "GO_RESIDENT"
            return self.plainte_active.pos_resident

    def interagir_avec_objectif(self, perceptions_locales: dict) -> dict:
        """
        Déclenché uniquement quand l'agent est adjacent à sa cible.
        Valide l'étape en cours et renvoie l'action.
        """
        sous_obj = self.sous_objectif_actuel

        if sous_obj == "GO_DICO":
            self.plainte_active.dico_atteint = True
            
            # 1. Analyse et stockage direct DANS la plainte active :
            self.plainte_active.emotion, self.plainte_active.intensite = self.analyser_message()
            
            # (Optionnel) Tu peux aussi garder tes variables sur l'agent si tu en as besoin ailleurs :
            self.emotion_courante = self.plainte_active.emotion
            self.intensite_courante = self.plainte_active.intensite

            print("\n" + "=" * 50)
            print("📖 ACTION : CONSULTER le dictionnaire")
            print(f"💬 Requête normalisée : \"{self.plainte_active.message}\"")
            print(f"🎯 Émotion conclue    : {self.plainte_active.emotion}")
            print(f"⚡ Intensité conclue   : {self.plainte_active.intensite}")
            print("=" * 50 + "\n")

            consulter = {"action": "CONSULTER", "argument": None}
            if self.plainte_active.emotion is None:
                return self.abandonner_plainte("emotion indeterminee", consulter)
            return consulter

        elif sous_obj == "GO_ARMOIRE":
            plainte = self.plainte_active
            plainte.armoire_atteinte = True

            # 1. Initialisation de la liste des candidats Plutchik si pas encore fait
            if not plainte.casiers_a_tester:
                candidats = self.generer_candidats_plutchik(plainte.emotion, plainte.intensite)
                
                # Filtrage en retirant les casiers connus comme vides
                plainte.casiers_a_tester = [
                    cand for cand in candidats 
                    if cand[0] not in self.casiers_vides_memoire
                ]

                # --- AFFICHAGE DES ÉLÉMENTS UTILES ---
                print("\n" + "=" * 50)
                print(f"🎯 Émotion / Intensité cibles : {plainte.emotion} ({plainte.intensite})")
                print(f"📋 Liste brute Plutchik (15 candidats) :")
                for pos, em, idx in candidats:
                    print(f"   • Casier {pos} -> {em} (dist: {idx})")
                print(f"🚫 Casiers vides en mémoire : {list(self.casiers_vides_memoire)}")
                print(f"🔍 Candidats restants à tester ({len(plainte.casiers_a_tester)}) :")
                for pos, em, idx in plainte.casiers_a_tester:
                    print(f"   -> Casier {pos}")
                print("=" * 50 + "\n")

                if not plainte.casiers_a_tester:
                    print("⚠️ Tous les casiers candidats sont vides ! (Échec armoire vide)")
                    return self.abandonner_plainte("armoire vide")

                plainte.casier_cible = plainte.casiers_a_tester[0][0]
                print(f"🎯 Première cible sélectionnée : {plainte.casier_cible}")

            # 2. Traitement du contenu du casier courant UNIQUEMENT s'il correspond au casier cible visé
            contenu = perceptions_locales.get("contenu_casier")

            if self.casier_selecteur == plainte.casier_cible:
                if contenu:
                    # OBJET TROUVÉ DANS LE CASIER CIBLE !
                    print("\n" + "🎉 " * 10)
                    print(f"📦 OBJET PRIS        : '{contenu}'")
                    print(f"📍 CASIER CIBLE ATTEINT : {self.casier_selecteur}")
                    print(f"🎯 CIBLE INITIALE    : {plainte.casier_cible}")
                    print("🎉 " * 10 + "\n")

                    plainte.objet_associe = contenu
                    plainte.casier_trouve = self.casier_selecteur
                    plainte.objet_en_main = True
                    emotion_casier = plainte.casiers_a_tester[0][1]
                    plainte.repli = self.calculer_repli(plainte, emotion_casier)
                    
                    # Passage à l'étape suivante : livrer le résident
                    self.sous_objectif_actuel = "GO_RESIDENT"
                    plainte.sous_objectif_actuel = "GO_RESIDENT"
                    
                    return {"action": "PRENDRE", "argument": contenu}
                else:
                    # Le casier cible était vide : on l'enregistre en mémoire et on passe au suivant
                    print(f"❌ Casier {self.casier_selecteur} vide. Mémorisation et passage au candidat suivant.")
                    self.casiers_vides_memoire.add(self.casier_selecteur)
                    plainte.casiers_a_tester.pop(0)

                    if not plainte.casiers_a_tester:
                        print("⚠️ Tous les casiers candidats de la liste ont été testés sans succès.")
                        return self.abandonner_plainte("armoire vide")

                    plainte.casier_cible = plainte.casiers_a_tester[0][0]
                    print(f"🎯 Nouvelle cible sélectionnée : {plainte.casier_cible}")

            # 3. Calcul de la direction du sélecteur vers le casier cible courant
            direction = self.calculer_direction_selecteur(self.casier_selecteur, plainte.casier_cible)
            print(f"🕹️ DEPLACEMENT SELECTEUR : Pos Actuelle {self.casier_selecteur} ➔ Cible {plainte.casier_cible} | Action : CHERCHER {direction}")
            
            return {"action": "CHERCHER", "argument": direction}
        
        # --- 3. RÉSIDENT (LIVRAISON) ---
        elif sous_obj == "GO_RESIDENT":
            plainte = self.plainte_active

            # 1. Préparation de la livraison (main l'écrit après le pas DONNER)
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
            print(f"🎁 LIVRAISON RÉUSSIE | Demande #{plainte.numero} | Résident : {plainte.id_resident}")
            print(f"📦 Objet '{plainte.objet_associe}' livré (pris en {plainte.casier_trouve})")
            print("=" * 50 + "\n")

            # 2. On clôture la plainte
            self.plainte_active = None
            self.sous_objectif_actuel = None
            
            return {"action": "DONNER", "argument": plainte.objet_associe}

        # --- SÉCURITÉ ---
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
            # Ignorer contenu_casier et toute clé qui n'est pas une direction cardinale
            if direction in offsets:
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
        self.mettre_a_jour_perceptions(perceptions)

        pos_cible = self.choisir_objectif()
        if pos_cible is None:
            return {"action": "ATTENDRE", "argument": None}

        # Résident atteint pendant la vérification : on passe directement à l'armoire
        if self.sous_objectif_actuel == "VERIF_RESIDENT" and self.est_adjacent(self.pos_actuelle, pos_cible):
            self.residents_atteints.add(self.plainte_active.id_resident)
            self.chemin_en_cours = []
            pos_cible = self.choisir_objectif()

        # 3. Si on est collé à la cible -> On interagit !
        # (Pour l'armoire, cela va renvoyer CHERCHER E, puis CHERCHER E..., jusqu'à PRENDRE)
        if self.est_adjacent(self.pos_actuelle, pos_cible):
            self.chemin_en_cours = []
            return self.interagir_avec_objectif(perceptions)

        # 4. Sinon, on se déplace sur la carte mentale (BFS)
        besoin_recalcul = (
            not self.chemin_en_cours 
            or self.carte_mentale.get(self.chemin_en_cours[0]) == "mur"
        )

        if besoin_recalcul:
            self.chemin_en_cours = self.calculer_chemin_bfs(pos_cible)

        if self.chemin_en_cours:
            prochaine_case = self.chemin_en_cours.pop(0)
            if prochaine_case == self.pos_actuelle and self.chemin_en_cours:
                prochaine_case = self.chemin_en_cours.pop(0)

            direction = self.convertir_case_en_direction(self.pos_actuelle, prochaine_case)
            return {"action": "AVANCER", "argument": direction}

        else:
            # Si on n'a pas de chemin, c'est qu'on est coincé ! On abandonne proprement.
            print("⚠️ Impossible de trouver un chemin vers la cible ! (Résident inaccessible)")
            return self.abandonner_plainte("resident inaccessible")

    def analyser_message(self) -> tuple[str, str]:
        """
        Analyse self.message mot par mot dans l'ordre de la phrase.
        Retourne (emotion, intensite) pour le premier mot-clé trouvé dans le dictionnaire.
        """
        # 1. Construction de la table d'indexation du dictionnaire : {forme: (emotion, intensite)}
        index_dico = {}
        for entree in self.dictionnaire_donnees.get("entrees", []):
            emotion = entree["emotion"]
            intensite = entree["intensite"]
            for forme in entree.get("formes", []):
                index_dico[forme.strip().lower()] = (emotion, intensite)

        # 2. Découpage du message normalisé en liste ordonnée de mots
        mots_message = self.plainte_active.message

        # 3. Parcours mot par mot de la phrase
        for mot in mots_message:
            mot_clean = mot.strip().lower()
            # Si le mot appartient aux mots-clés du dictionnaire
            if mot_clean in index_dico:
                return index_dico[mot_clean]

        # Aucun mot reconnu : émotion indéterminée 
        return None, None

    def calculer_repli(self, plainte: Plainte, emotion_casier: str) -> str:
        """
        Étiquette 'repli' de la trace (section 6.2) pour le casier pris :
        "aucun" si c'est le casier exact, "intensite" si même émotion,
        sinon "voisine_1" ou "voisine_2" selon la distance sur la roue.
        """
        casier_exact = self.casiers_par_etiquette.get((plainte.emotion, plainte.intensite))
        if plainte.casier_trouve == casier_exact:
            return "aucun"

        distance = self.calculer_distance_emotion(plainte.emotion, emotion_casier)
        if distance == 0:
            return "intensite"
        return f"voisine_{distance}"

    def calculer_distance_emotion(self, e1: str, e2: str) -> int:
        """
        Calcule la distance circulaire minimale entre deux émotions (0 à 4).
        """
        # Normalisation en minuscules pour éviter les erreurs de casse
        e1_clean = e1.lower()
        e2_clean = e2.lower()
        roue_clean = [e.lower() for e in self.emotions_roue]

        if e1_clean not in roue_clean or e2_clean not in roue_clean:
            # Sécurité si l'émotion recherchée n'est pas trouvée
            return 4

        idx1: int = roue_clean.index(e1_clean)
        idx2: int = roue_clean.index(e2_clean)
        diff: int = abs(idx1 - idx2)
        taille: int = len(self.emotions_roue)
        return min(diff, taille - diff)

    def determiner_sens_rotation(self, emotion_cible: str, emotion_cand: str) -> int:
        """
        Détermine si une émotion candidate est dans le sens horaire par rapport à l'émotion cible.

        Args:
            emotion_cible: L'émotion d'origine demandée.
            emotion_cand: L'émotion du casier candidat évalué.

        Returns:
            int: 0 si horaire (ou identique), 1 si antihoraire.
                 (Rendre 0 pour horaire permet à Python de la trier en premier).
        """
        if emotion_cible == emotion_cand:
            return 0  # Même émotion -> pas de rotation nécessaire

        idx_cible: int = self.emotions_roue.index(emotion_cible)
        idx_cand: int = self.emotions_roue.index(emotion_cand)
        taille: int = len(self.emotions_roue)  # 8

        # Sens horaire à distance 1 ou 2 sur un cycle modulo 8 :
        if (idx_cible + 1) % taille == idx_cand or (idx_cible + 2) % taille == idx_cand:
            return 0  # Horaire
        
        return 1  # Antihoraire

    def generer_candidats_plutchik(self, emotion_cible: str, intensite_cible: int) -> list[tuple[tuple[int, int], str, int]]:
        """
        Génère et trie les 15 candidats Plutchik en gérant les intensités texte ou numériques.
        """
        candidats = []

        # Table de correspondance pour convertir "faible", "moyenne", "forte" en chiffres 1, 2, 3
        CONV_INTENSITE = {
            "faible": 1, "1": 1, 1: 1,
            "moyenne": 2, "2": 2, 2: 2,
            "forte": 3, "3": 3, 3: 3
        }

        # Conversion de l'intensité cible en nombre (par défaut 2 si non trouvée)
        val_i_cible = CONV_INTENSITE.get(str(intensite_cible).lower(), 2)

        for (emotion, intensite), coords in self.casiers_par_etiquette.items():
            dist: int = self.calculer_distance_emotion(emotion_cible, emotion)

            # On rejette les distances 3 et 4 (Section 3.3)
            if dist > 2:
                continue

            # Conversion de l'intensité du casier candidat en nombre
            val_i_cand = CONV_INTENSITE.get(str(intensite).lower(), 2)

            # Calculs mathématiques sécurisés entre entiers
            ecart_intensite: int = abs(val_i_cible - val_i_cand)
            rotation: int = self.determiner_sens_rotation(emotion_cible, emotion)

            # Clé de tri à 4 critères
            cle_tri = (dist, ecart_intensite, val_i_cand, rotation)

            # On conserve les données originales du casier pour le retour
            candidats.append((cle_tri, coords, emotion, intensite))

        # Tri selon les 4 critères
        candidats.sort(key=lambda item: item[0])

        # Renvoie la liste ordonnée : [((ligne, colonne), emotion, intensite), ...]
        return [(item[1], item[2], item[3]) for item in candidats]

    def calculer_direction_selecteur(self, depart: tuple[int, int], cible: tuple[int, int]) -> str:
        """
        Calcule la direction ("N", "S", "E", "O") pour faire 1 pas du sélecteur
        depuis 'depart' vers 'cible' (avec bouclage des colonnes 0 <-> 7).
        """
        l_dep, c_dep = depart
        l_cib, c_cib = cible

        # 1. Mouvement vertical prioritaire (si pas sur la même ligne)
        if l_dep < l_cib:
            return "S"
        elif l_dep > l_cib:
            return "N"

        # 2. Mouvement horizontal (avec bouclage circulaire des 8 colonnes)
        if c_dep != c_cib:
            a = (c_cib - c_dep) % 8
            if a <= 4:
                return "E"   # Aller vers l'Est (plus court)
            else:
                return "O"   # Aller vers l'Ouest (via le bouclage)

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

def simuler_armoire(armoire_donnees: dict, casier_selecteur: tuple, action_dict: dict) -> tuple[tuple, Optional[str]]:
    """
    Gère uniquement le sous-univers de l'armoire (déplacement du sélecteur et contenu du casier).
    """
    lig, col = casier_selecteur
    action = action_dict.get("action")
    arg = action_dict.get("argument")

    # 1. Mise à jour de la position du sélecteur en cas de CHERCHER
    if action == "CHERCHER":
        if arg == "N" and lig > 0: lig -= 1
        elif arg == "S" and lig < 2: lig += 1
        elif arg == "E": col = (col + 1) % 8  # Bouclage circulaire
        elif arg == "O": col = (col - 1) % 8  # Bouclage circulaire
    
    nouveau_selecteur = (lig, col)

    # 2. Consultation du contenu du casier courant sous le sélecteur
    contenu_casier = None
    for casier in armoire_donnees.get("casiers", []):
        if casier["ligne"] == lig and casier["colonne"] == col:
            contenu_casier = casier.get("objet")  # None si vide, str si garni
            break

    return nouveau_selecteur, contenu_casier

def main(argv):
    
    avec_interface = len(argv) == 6 and argv[5] == "--gui"
    if len(argv) != 5 and not avec_interface:
        print("Usage: python agent.py <carte> <scenario> <dossier_donnees> <trace_sortie> [--gui]", file=sys.stderr)
        return 2

    chemin_carte = Path(argv[1])
    chemin_scenario = Path(argv[2])
    dossier_donnees = Path(argv[3])
    chemin_sortie = Path(argv[4])

    # 1. Chargement des fichiers d'entrée
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
        # Filet de sécurité : jamais de traceback pour un fichier mal formé 
        print(f"ERREUR : fichier d'entrée mal formé ({type(err).__name__} : {err})", file=sys.stderr)
        return 1

    # 3. Instanciation de l'agent, de la trace et de l'interface graphique
    agent = AgentReconfort(carte, dictionnaire, armoire)
    trace = rio.Trace(carte["nom"], scenario["nom"], equipe=["HARAUT Kevin", "KADDOUR Reyam"])


    # Initialisation de la GUI Tkinter
    interface = None
    if avec_interface:
        from interface import SimulationPygame
        interface = SimulationPygame(dimensions=carte["dimensions"], cell_size=40)

    # 4. Boucle sur chaque demande du scénario
    for demande in scenario["demandes"]:
        id_resident = demande["resident"]
        pos_res = agent.pos_residents[id_resident]
        
        # Injection de la plainte en cours (doublon nettoyé)
        agent.plainte_active = Plainte(demande, pos_res)
        
        print(f"\n==========================================")
        print(f" DÉBUT DEMANDE {demande['numero']} POUR {id_resident}")
        print(f"==========================================")

        tour = 0
        perceptions_locales = {}
        action_dict = {"action": "ATTENDRE", "argument": None}

        # Boucle tour par tour jusqu'à la livraison complète au résident
        while agent.plainte_active is not None:
            # A. L'environnement simule la perception
            agent.pos_actuelle, perceptions_locales = simuler_environnement(
                carte, agent.pos_actuelle, action_dict
            )

            agent.casier_selecteur, contenu = simuler_armoire(
                armoire, agent.casier_selecteur, action_dict
            )

            # Le robot ne voit le casier que s'il est devant l'armoire (section 5.5)
            devant_armoire = agent.est_adjacent(agent.pos_actuelle, agent.pos_armoire)
            contenu_visible = contenu if devant_armoire else None
            perception_cases = dict(perceptions_locales)   # N, S, E, O uniquement

            # Injection de la vision du casier
            perceptions_locales["contenu_casier"] = contenu_visible

            # B. L'agent décide de son action
            action_dict = agent.decider_action(perceptions_locales)

            # C. Affichage visuel dans la console
            print(f"Tour {tour} | Action: {action_dict['action']} {action_dict.get('argument') or ''} | Pos: {agent.pos_actuelle}")
            
            # D. 📌 Mise à jour graphique en temps réel (si --gui)
            if interface is not None:
                interface.rafraichir(agent, fps=6)

            # E. Enregistrement dans la trace
            trace.ajouter_pas(
                demande=demande["numero"],
                position=agent.pos_actuelle,
                casier=agent.casier_selecteur,
                action=action_dict["action"],
                argument=action_dict.get("argument"),
                perception=perception_cases,
                contenu_casier=contenu_visible
            )

            # F. Livraison écrite APRÈS son dernier pas (pas_utilises exact)
            if agent.livraison_en_attente is not None:
                trace.ajouter_livraison(**agent.livraison_en_attente)
                agent.livraison_en_attente = None

            tour += 1

    # 5. Écriture du fichier de trace
    trace.ecrire(chemin_sortie)
    print(f"\nSimulation terminée avec succès. Trace écrite dans {chemin_sortie}")

    # 5. 📌 Garder l'interface ouverte à la fin (seulement en mode --gui)
    if interface is not None:
        interface.attendre_fermeture()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))