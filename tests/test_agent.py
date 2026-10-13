import sys
import os
import unittest

# Permet d'importer agent.py depuis le dossier parent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent import AgentReconfort, Plainte

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
                {"emotion": "tristesse", "intensite": "forte", "formes": ["pleure", "desespoir"]},
                {"emotion": "peur", "intensite": "faible", "formes": ["sursaute"]}
            ]
        }

        # On crée le robot
        self.agent = AgentReconfort(carte, dictionnaire, armoire)

    def test_message_un_mot_connu(self):
        """Test avec exactement un mot présent dans le dictionnaire."""
        demande = {"numero": 1, "resident": "R1", "message": "Il pleure beaucoup"}
        self.agent.plainte_active = Plainte(demande, (1, 1))
        
        emotion, intensite = self.agent.analyser_message()
        self.assertEqual(emotion, "tristesse")
        self.assertEqual(intensite, "forte")

    def test_message_aucun_mot_connu(self):
        """Test avec un message où aucun mot n'est dans le dictionnaire (valeur par défaut)."""
        demande = {"numero": 2, "resident": "R1", "message": "Bonjour comment ca va"}
        self.agent.plainte_active = Plainte(demande, (1, 1))
        
        emotion, intensite = self.agent.analyser_message()
        self.assertEqual(emotion, "neutre")
        self.assertEqual(intensite, "moyenne")

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

        # 2. On simule qu'il a atteint le dictionnaire
        self.agent.plainte_active.dico_atteint = True
        cible = self.agent.choisir_objectif()
        self.assertEqual(cible, (2, 2))  # Position armoire
        self.assertEqual(self.agent.sous_objectif_actuel, "GO_ARMOIRE")

        # 3. On simule qu'il a atteint l'armoire
        self.agent.plainte_active.armoire_atteinte = True
        cible = self.agent.choisir_objectif()
        self.assertEqual(cible, (3, 3))  # Position résident
        self.assertEqual(self.agent.sous_objectif_actuel, "GO_RESIDENT")

if __name__ == '__main__':
    unittest.main()