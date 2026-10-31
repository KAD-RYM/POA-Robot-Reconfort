import sys
import os
import unittest

# Permet d'importer agent.py depuis le dossier parent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent import AgentReconfort, Plainte, simuler_environnement, simuler_armoire

class TestRobotDictionnaire(unittest.TestCase):

    def setUp(self):
        """Initialise un robot avec un faux dictionnaire minimaliste pour les tests."""
        # Fausses données minimales obligatoires pour créer l'agent
        carte = {
            "depart_robot": [0, 0],
            "dictionnaire": {"position": [0, 1]},
            "armoire": {"position": [1, 0]},
            "residents": [{"id": "R1", "position": [1, 1]}]
        }
        armoire = {
            "casier_depart": [0, 0],
            "emotions": ["joie"],
            "intensites": ["faible"],
            "casiers": []
        }
        
        # Le dictionnaire qu'on va réellement tester
        dictionnaire = {
            "entrees": [
                {"emotion": "joie", "intensite": "moyenne", "formes": ["content"]},
                {"emotion": "confiance", "intensite": "faible", "formes": ["rassure"]},
                {"emotion": "surprise", "intensite": "forte", "formes": ["stupefait"]},
                {"emotion": "degout", "intensite": "moyenne", "formes": ["ecoeure"]},
                {"emotion": "colere", "intensite": "forte", "formes": ["furieux"]},
                {"emotion": "anticipation", "intensite": "faible", "formes": ["impatient"]},
                {"emotion": "tristesse", "intensite": "forte", "formes": ["pleure", "desespoir"]},
                {"emotion": "peur", "intensite": "faible", "formes": ["sursaute"]}
            ]
        }

        # On crée le robot
        self.agent = AgentReconfort(carte, dictionnaire, armoire)

    def test_message_un_mot_connu(self):
        """Un message par émotion (section 8, point 3) : chaque message contient un seul mot connu."""
        for entree in self.agent.dictionnaire_donnees["entrees"]:
            demande = {"numero": 1, "resident": "R1", "message": "Il est " + entree["formes"][0]}
            self.agent.plainte_active = Plainte(demande, (1, 1))

            emotion, intensite = self.agent.analyser_message()
            self.assertEqual(emotion, entree["emotion"])
            self.assertEqual(intensite, entree["intensite"])

    def test_message_aucun_mot_connu(self):
        """Test avec un message où aucun mot n'est dans le dictionnaire (valeur par défaut)."""
        demande = {"numero": 2, "resident": "R1", "message": "Bonjour comment ca va"}
        self.agent.plainte_active = Plainte(demande, (1, 1))
        
        emotion, intensite = self.agent.analyser_message()
        self.assertIsNone(emotion)
        self.assertIsNone(intensite)

    def test_message_deux_mots_connus(self):
         # 'sursaute' (peur) et 'desespoir' (tristesse) sont dans le dico
        demande = {"numero": 3, "resident": "R1", "message": "Il sursaute de desespoir"}
        self.agent.plainte_active = Plainte(demande, (1, 1))
        
        emotion, intensite = self.agent.analyser_message()
        # Le premier mot de la phrase présent dans le dico est 'sursaute'
        self.assertEqual(emotion, "peur")
        self.assertEqual(intensite, "faible")

class TestPerceptionsAgent(unittest.TestCase):

    def setUp(self):
        """Initialise un agent avec une carte vide."""
        carte = {
            "depart_robot": [0, 0],
            "dictionnaire": {"position": [2, 2]},
            "armoire": {"position": [0, 3]},
            "residents": []
        }
        self.agent = AgentReconfort(carte, {"entrees": []}, {"casier_depart": [0,0], "casiers": [], "emotions": [], "intensites": []})

    def test_mise_a_jour_carte_mentale(self):
        """Vérifie que l'agent mémorise bien ce qu'il voit autour de lui."""
        # Le robot est en (0,0). On lui dit qu'il voit un mur au Sud et libre à l'Est.
        perceptions = {
            "N": "mur",   # Hors carte
            "S": "mur",   # Un mur en (1, 0)
            "E": "libre", # Libre en (0, 1)
            "O": "mur"    # Hors carte
        }
        
        self.agent.mettre_a_jour_perceptions(perceptions)
        
        # On vérifie que sa carte mentale a bien été mise à jour
        self.assertEqual(self.agent.carte_mentale.get((1, 0)), "mur")
        self.assertEqual(self.agent.carte_mentale.get((0, 1)), "libre")

    def test_memoire_apres_deplacement(self):
        """Vérifie que le robot retient les anciens obstacles après avoir bougé."""
        # Le robot est en (0,0) et voit un mur au Sud en (1,0)
        self.agent.pos_actuelle = (0, 0)
        perceptions_tour_1 = {
            "N": "mur", 
            "S": "mur",   # Mur en (1,0)
            "E": "libre", 
            "O": "mur"
        }
        self.agent.mettre_a_jour_perceptions(perceptions_tour_1)
        
        self.agent.pos_actuelle = (0, 1)
        
        perceptions_tour_2 = {
            "N": "mur", 
            "S": "libre", 
            "E": "mur",   # Mur en (0,2)
            "O": "libre"
        }
        self.agent.mettre_a_jour_perceptions(perceptions_tour_2)
        
        self.assertEqual(self.agent.carte_mentale.get((1, 0)), "mur")
        self.assertEqual(self.agent.carte_mentale.get((0, 2)), "mur")

class TestChoixObjectif(unittest.TestCase):

    def setUp(self):
        """Initialise un agent avec une plainte pour tester ses priorités."""
        carte = {
            "depart_robot": [0, 0],
            "dictionnaire": {"position": [1, 1]},
            "armoire": {"position": [2, 2]},
            "residents": [{"id": "R1", "position": [3, 3]}]
        }
        self.agent = AgentReconfort(carte, {"entrees": []}, {"casier_depart": [0,0], "casiers": [], "emotions": [], "intensites": []})
        
        # On crée une fausse demande
        demande = {"numero": 1, "resident": "R1", "message": "test"}
        self.agent.plainte_active = Plainte(demande, (3, 3))

    def test_ordre_objectifs(self):
        """Vérifie que l'agent va d'abord au dico, puis armoire, puis résident."""
        
        # 1. Au début, il doit viser le dictionnaire (1, 1)
        cible = self.agent.choisir_objectif()
        self.assertEqual(cible, (1, 1))
        self.assertEqual(self.agent.sous_objectif_actuel, "GO_DICO")

        # 2. On simule qu'il a atteint le dictionnaire : résident jamais vu -> vérification
        self.agent.plainte_active.dico_atteint = True
        cible = self.agent.choisir_objectif()
        self.assertEqual(cible, (3, 3))  # Position résident
        self.assertEqual(self.agent.sous_objectif_actuel, "VERIF_RESIDENT")

        # 2 bis. Résident atteint une fois : direction l'armoire
        self.agent.residents_atteints.add("R1")
        cible = self.agent.choisir_objectif()
        self.assertEqual(cible, (2, 2))  # Position armoire
        self.assertEqual(self.agent.sous_objectif_actuel, "GO_ARMOIRE")

        # 3. On simule qu'il a atteint l'armoire
        self.agent.plainte_active.objet_en_main = True
        cible = self.agent.choisir_objectif()
        self.assertEqual(cible, (3, 3))  # Position résident
        self.assertEqual(self.agent.sous_objectif_actuel, "GO_RESIDENT")

    def test_enchainement_plaintes(self):
        "Vérifie que l'agent peut traiter une deuxième demande après avoir fini la première."
        
        # On simule que le robot a déjà fait Dico et Armoire pour la plainte 1
        self.agent.plainte_active.dico_atteint = True
        self.agent.plainte_active.objet_en_main = True
        
        # Il vise le résident 
        self.agent.choisir_objectif() 
        self.assertEqual(self.agent.sous_objectif_actuel, "GO_RESIDENT")
        
        # Il interagit (donne l'objet). Cela doit réinitialiser l'état du robot !
        action = self.agent.interagir_avec_objectif({})
        self.assertEqual(action["action"], "DONNER")
        self.assertIsNone(self.agent.plainte_active, "Le robot n'a pas supprimé l'ancienne plainte")
        self.assertIsNone(self.agent.sous_objectif_actuel, "Le robot n'a pas réinitialisé son objectif")
        
        # Deuxieme plainte
        self.agent.pos_residents["R2"] = (8, 8)  # Ajout du resident sur la carte
        demande_2 = {"numero": 2, "resident": "R2", "message": "je suis triste"}
        self.agent.plainte_active = Plainte(demande_2, (8, 8))
        
        # On vérifie que le cycle recommence bien à zéro (vers le Dictionnaire)
        cible = self.agent.choisir_objectif()
        self.assertEqual(cible, (1, 1))  # Position du dico définie dans setUp
        self.assertEqual(self.agent.sous_objectif_actuel, "GO_DICO")
        
        # Et qu'il passe bien à l'armoire ensuite (R2 déjà atteint une fois)
        self.agent.residents_atteints.add("R2")
        self.agent.plainte_active.dico_atteint = True
        cible = self.agent.choisir_objectif()
        self.assertEqual(cible, (2, 2))  # Position de l'armoire
        self.assertEqual(self.agent.sous_objectif_actuel, "GO_ARMOIRE")

class TestMoteurEnvironnement(unittest.TestCase):

    def test_perception_grille_reelle(self):
        """Vérifie que simuler_environnement traduit bien la grille en perceptions."""

        carte_donnees = {
            "grille": [
                ["#", ".", "#"],
                ["#", "R", "D"],
                [".", "A", "#"]
            ]
        }
        
        pos_robot = (1, 1)
        
        action = {"action": "ATTENDRE", "argument": None}
        
        # On fait tourner le moteur de jeu
        nouvelle_pos, perceptions = simuler_environnement(carte_donnees, pos_robot, action)
        
        # Le robot n'a pas bougé
        self.assertEqual(nouvelle_pos, (1, 1))
        
        self.assertEqual(perceptions["N"], "libre")        
        self.assertEqual(perceptions["S"], "armoire")     
        self.assertEqual(perceptions["E"], "dictionnaire") 
        self.assertEqual(perceptions["O"], "mur")          

    def test_perception_bord_de_carte(self):
        """Vérifie que regarder en dehors de la grille renvoie bien un 'mur'."""
        carte_donnees = {
            "grille": [
                ["R", "."]
            ]
        }
        # Le robot est tout en haut à gauche (0, 0)
        pos_robot = (0, 0)
        action = {"action": "ATTENDRE", "argument": None}
        
        _, perceptions = simuler_environnement(carte_donnees, pos_robot, action)
        
        # Au Nord et à l'Ouest, il n'y a plus de carte. Le moteur doit sécuriser ça en renvoyant "mur".
        self.assertEqual(perceptions["N"], "mur")
        self.assertEqual(perceptions["O"], "mur")
        self.assertEqual(perceptions["E"], "libre")
        self.assertEqual(perceptions["S"], "mur")

class TestPlanificationChemin(unittest.TestCase):

    def setUp(self):
        """Petite grille écrite à la main (celle de l'annexe B), entièrement connue du robot."""
        self.grille = [
            "######",
            "#R.#P#",
            "#.#..#",
            "#...##",
            "######"
        ]
        carte = {
            "depart_robot": [1, 1],
            "dictionnaire": {"position": [0, 0]},
            "armoire": {"position": [0, 1]},
            "residents": [{"id": "R1", "position": [1, 4]}]
        }
        self.agent = AgentReconfort(carte, {"entrees": []}, {"casier_depart": [0,0], "casiers": [], "emotions": [], "intensites": []})

    def test_chemin_longueur_connue(self):
        """Planification (section 8, point 1) : on connaît la longueur du plus court chemin."""
        # On donne toute la grille au robot pour tester le BFS seul
        for l, ligne in enumerate(self.grille):
            for c, symbole in enumerate(ligne):
                if symbole == "#":
                    self.agent.carte_mentale[(l, c)] = "mur"

        chemin = self.agent.calculer_chemin_bfs((1, 4))

        # (1,1) -> (2,1) -> (3,1) -> (3,2) -> (3,3) -> (2,3) -> (2,4) : 6 pas
        self.assertEqual(len(chemin), 6)
        # Il s'arrête sur une case voisine du résident, pas sur le résident
        self.assertEqual(chemin[-1], (2, 4))

    def test_replanification_mur_decouvert(self):
        """Replanification (section 8, point 2) : un mur découvert en route change le trajet."""
        # Le robot ne connaît rien : il imagine aller tout droit vers l'Est
        chemin_avant = self.agent.calculer_chemin_bfs((1, 4))
        self.assertEqual(chemin_avant[0], (1, 2))

        # Il découvre un mur juste à l'Est, en (1, 2)
        self.agent.mettre_a_jour_perceptions({"N": "mur", "S": "libre", "E": "mur", "O": "mur"})
        chemin_apres = self.agent.calculer_chemin_bfs((1, 4))

        # Le nouveau chemin évite le mur et passe par le Sud, donc il est plus long
        self.assertNotIn((1, 2), chemin_apres)
        self.assertEqual(chemin_apres[0], (2, 1))
        self.assertGreater(len(chemin_apres), len(chemin_avant))

class TestArmoirePlutchik(unittest.TestCase):

    def setUp(self):
        """Prépare une roue des émotions et des casiers pour tester le tri de l'agent."""
        carte = {"depart_robot": [0,0], "dictionnaire": {"position": [1,1]}, "armoire": {"position": [2,2]}, "residents": []}
        armoire = {
            "casier_depart": [0,0],
            # La roue officielle de Plutchik dans l'ordre :
            "emotions": ["Joie", "Confiance", "Peur", "Surprise", "Tristesse", "Degout", "Colere", "Anticipation"],
            "intensites": ["faible", "moyenne", "forte"],
            "casiers": [
                # Casier 1 : Correspondance exacte (Distance 0, Intensité 3) -> DOIT ÊTRE 1er
                {"ligne": 0, "colonne": 0, "emotion": "Joie", "intensite": "forte"},
                
                # Casier 2 : Bonne émotion mais intensité faible (Distance 0, Intensité 1) -> DOIT ÊTRE 2ème
                {"ligne": 0, "colonne": 1, "emotion": "Joie", "intensite": "faible"},
                
                # Casier 3 : Émotion voisine Horaire (Distance 1, Intensité 3) -> DOIT ÊTRE 3ème
                {"ligne": 0, "colonne": 2, "emotion": "Confiance", "intensite": "forte"},
                
                # Casier 4 : Émotion voisine Antihoraire (Distance 1, Intensité 3) -> DOIT ÊTRE 4ème
                {"ligne": 0, "colonne": 3, "emotion": "Anticipation", "intensite": "forte"},
                
                # Casier 5 : Émotion opposée (Distance 4) -> DOIT ÊTRE EXCLU PAR L'ALGO
                {"ligne": 0, "colonne": 4, "emotion": "Tristesse", "intensite": "forte"}
            ]
        }
        self.agent = AgentReconfort(carte, {"entrees": []}, armoire)

    def test_ordre_tri_plutchik(self):
        """Vérifie que la génération des candidats respecte strictement les priorités."""
        # On demande "Joie" et "forte" (Intensité forte = 3)
        candidats = self.agent.generer_candidats_plutchik("Joie", "forte")
        
        # 1. Le casier 5 (Tristesse, distance 4) doit avoir été viré. Il ne doit rester que 4 casiers.
        self.assertEqual(len(candidats), 4)
        
        # 2. Vérification de l'ordre exact : l'algorithme renvoie [(ligne, colonne), emotion, intensite]
        self.assertEqual(candidats[0][0], (0, 0)) # 1er : L'exact
        self.assertEqual(candidats[1][0], (0, 1)) # 2ème : La même émotion, mauvaise intensité
        self.assertEqual(candidats[2][0], (0, 2)) # 3ème : Le voisin Horaire
        self.assertEqual(candidats[3][0], (0, 3)) # 4ème : Le voisin Antihoraire
class TestArmoirePhysique(unittest.TestCase):

    def test_bouclage_circulaire_colonnes(self):
        """Vérifie que le sélecteur traverse bien les murs latéraux de l'armoire (bouclage modulo 8)."""
        armoire = {"casiers": []} # Armoire vide, on teste juste le déplacement
        
        # --- TEST 1 : Dépasser par la droite (Est) ---
        # Le sélecteur est tout au bout à droite (colonne 7)
        selecteur_initial = (1, 7)
        action_est = {"action": "CHERCHER", "argument": "E"}
        
        nouveau_selecteur, _ = simuler_armoire(armoire, selecteur_initial, action_est)
        # Il doit réapparaître colonne 0 !
        self.assertEqual(nouveau_selecteur, (1, 0))
        
        # --- TEST 2 : Dépasser par la gauche (Ouest) ---
        # Le sélecteur est tout au bout à gauche (colonne 0)
        selecteur_initial = (2, 0)
        action_ouest = {"action": "CHERCHER", "argument": "O"}
        
        nouveau_selecteur, _ = simuler_armoire(armoire, selecteur_initial, action_ouest)
        # Il doit réapparaître colonne 7 !
        self.assertEqual(nouveau_selecteur, (2, 7))

    def test_blocage_vertical(self):
        """Vérifie qu'on ne peut pas traverser le plafond ou le sol (Ligne 0 à 2)."""
        armoire = {"casiers": []}
        
        # On essaie de monter (N) depuis la ligne tout en haut (Ligne 0)
        selecteur, _ = simuler_armoire(armoire, (0, 4), {"action": "CHERCHER", "argument": "N"})
        # Le sélecteur doit rester bloqué en ligne 0
        self.assertEqual(selecteur, (0, 4))

class TestArmoireMemoire(unittest.TestCase):

    def test_memorisation_casier_vide(self):
        """Vérifie que l'agent mémorise un casier vide et passe au candidat suivant."""
        # On prépare un faux agent sur sa plainte
        carte = {"depart_robot": [0,0], "dictionnaire": {"position": [1,1]}, "armoire": {"position": [2,2]}, "residents": []}
        armoire = {
            "casier_depart": [0,0], "emotions": ["Joie"], "intensites": ["forte"],
            "casiers": [{"ligne": 0, "colonne": 0, "emotion": "Joie", "intensite": "forte"}]
        }
        agent = AgentReconfort(carte, {"entrees": []}, armoire)
        
        # On simule qu'il est déjà devant l'armoire, prêt à fouiller
        agent.plainte_active = Plainte({"numero": 1, "resident": "R1", "message": "test"}, (3, 3))
        agent.plainte_active.emotion = "Joie"
        agent.plainte_active.intensite = "forte"
        agent.sous_objectif_actuel = "GO_ARMOIRE"
        
        # Le robot et son sélecteur sont pile sur le casier cible
        agent.casier_selecteur = (0, 0)
        agent.plainte_active.casier_cible = (0, 0)
        agent.plainte_active.casiers_a_tester = [((0, 0), "Joie", "forte")]
        
        # L'environnement lui dit "Désolé, il n'y a pas d'objet dedans (None)"
        perceptions = {"contenu_casier": None}
        
        # Le robot agit
        action = agent.interagir_avec_objectif(perceptions)
        
        # 1. Il doit avoir ajouté (0,0) à sa liste noire des casiers vides
        self.assertIn((0, 0), agent.casiers_vides_memoire)
        
        # 2. Comme la liste est vide, il abandonne la plainte (elle devient None)
        self.assertIsNone(agent.plainte_active)
        
        # 3. L'action renvoyée lors d'un abandon est ATTENDRE
        self.assertEqual(action["action"], "ATTENDRE")

        # 4. L'échec est noté avec le motif "armoire vide" (repli, cas « aucun casier garni »)
        self.assertEqual(agent.livraison_en_attente["motif_echec"], "armoire vide")

if __name__ == '__main__':
    unittest.main()