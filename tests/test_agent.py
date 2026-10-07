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

if __name__ == '__main__':
    unittest.main()