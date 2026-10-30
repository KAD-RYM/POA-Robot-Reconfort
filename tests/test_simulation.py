import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from agent import AgentReconfort, Plainte, simuler_environnement, simuler_armoire
from outils_tests import RACINE

class TestIntegrationReconfort(unittest.TestCase):

    def test_scenario_complet_autonome(self):
        """Test l'enchaînement complet d'une requête, de la plainte jusqu'à la livraison."""
        
        # 1. CRÉATION D'UN MINI-MONDE (Une pièce 3x3 pour circuler)
        carte = {
            "nom": "Mini-Carte Test",
            "depart_robot": [0, 0],
            "dictionnaire": {"position": [0, 2]},
            "armoire": {"position": [2, 0]},
            "residents": [{"id": "R1", "position": [2, 2]}],
            "dimensions": {"hauteur": 3, "largeur": 3},
            "grille": [
                ["R", ".", "D"],
                [".", ".", "."],
                ["A", ".", "P"]
            ]
        }

        # 2. UN MINI-DICTIONNAIRE
        dictionnaire = {
            "entrees": [
                {"emotion": "Tristesse", "intensite": "forte", "formes": ["triste", "pleure"]}
            ]
        }

        # 3. UNE MINI-ARMOIRE (Avec l'objet parfait)
        armoire = {
            "casier_depart": [0, 0],
            "emotions": ["Tristesse"],
            "intensites": ["forte"],
            "casiers": [
                {"ligne": 0, "colonne": 0, "emotion": "Tristesse", "intensite": "forte", "objet": "Peluche Réconfortante"}
            ]
        }

        # 4. ON LANCE LE ROBOT !
        agent = AgentReconfort(carte, dictionnaire, armoire)
        
        # On lui donne sa mission
        demande = {"numero": 1, "resident": "R1", "message": "Je suis très triste aujourd'hui"}
        agent.plainte_active = Plainte(demande, (2, 2))  
        
        tour = 0
        max_tours = 20  # Sécurité pour éviter qu'il ne boucle à l'infini s'il est bête
        action_dict = {"action": "ATTENDRE", "argument": None}

        print("\n--- DÉBUT DE LA SIMULATION DU TEST D'INTÉGRATION ---")

        # 5. LA BOUCLE MOTEUR (Comme dans le main de ton collègue)
        while agent.plainte_active is not None and tour < max_tours:
            # A. L'agent regarde l'environnement et l'armoire
            agent.pos_actuelle, perceptions = simuler_environnement(carte, agent.pos_actuelle, action_dict)
            agent.casier_selecteur, contenu = simuler_armoire(armoire, agent.casier_selecteur, action_dict)
            perceptions["contenu_casier"] = contenu

            # B. L'agent réfléchit et agit
            action_dict = agent.decider_action(perceptions)
            tour += 1

        print("--- FIN DE LA SIMULATION ---")

        # 6. L'HEURE DE VÉRITÉ (Les Assertions)
        # A-t-il réussi en moins de 20 tours ?
        self.assertLess(tour, max_tours, "ÉCHEC : Le robot a tourné en boucle infinie !")
        
        # A-t-il bien supprimé la plainte (ce qui prouve qu'il a livré l'objet) ?
        self.assertIsNone(agent.plainte_active, "ÉCHEC : La plainte n'a pas été clôturée.")
        self.assertIsNone(agent.sous_objectif_actuel, "ÉCHEC : L'agent a gardé un objectif en tête.")
        
        # S'est-il bien arrêté sur la case juste à côté du résident en (2, 2) ?
        self.assertEqual(agent.pos_actuelle, (2, 1), "ÉCHEC : Le robot n'est pas au bon endroit à la fin.")

class TestProgrammeFichiersCasses(unittest.TestCase):
    """Bout en bout (section 5.6) : code non nul, message sur stderr, aucune trace écrite."""

    def lancer(self, scenario_modifie):
        with tempfile.TemporaryDirectory() as tmp:
            chemin_scenario = Path(tmp) / "scenario.json"
            chemin_scenario.write_text(json.dumps(scenario_modifie), encoding="utf-8")
            chemin_trace = Path(tmp) / "trace.json"
            resultat = subprocess.run(
                [sys.executable, str(RACINE / "agent.py"),
                 str(RACINE / "cartes" / "appartement_01.json"), str(chemin_scenario),
                 str(RACINE / "donnees"), str(chemin_trace)],
                capture_output=True, text=True, timeout=30)
            return resultat, chemin_trace.exists()

    def scenario_valide(self):
        return json.loads((RACINE / "cartes" / "scenario_01.json").read_text(encoding="utf-8"))

    def test_scenario_sans_armoire(self):
        scenario = self.scenario_valide()
        del scenario["armoire"]
        resultat, trace_ecrite = self.lancer(scenario)
        self.assertNotEqual(resultat.returncode, 0)
        self.assertIn("armoire", resultat.stderr)
        self.assertNotIn("Traceback", resultat.stderr)
        self.assertFalse(trace_ecrite)

    def test_armoire_introuvable(self):
        scenario = self.scenario_valide()
        scenario["armoire"] = "armoire_inexistante"
        resultat, trace_ecrite = self.lancer(scenario)
        self.assertNotEqual(resultat.returncode, 0)
        self.assertNotIn("Traceback", resultat.stderr)
        self.assertFalse(trace_ecrite)