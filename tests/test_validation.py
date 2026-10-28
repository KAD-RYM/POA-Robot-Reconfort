
import os
import sys
import unittest
import io
import validation as val
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestValidationFichiers(unittest.TestCase):

    def setUp(self):
        # Bloque l'affichage des "ERREUR : ..." dans le terminal pendant les tests
        self.held_stderr = sys.stderr
        sys.stderr = io.StringIO()

    def tearDown(self):
        # Restaure l'affichage normal
        sys.stderr = self.held_stderr

    # --- 1. TESTS DE LA CARTE ---

    def test_champ_manquant_ou_mauvais_type(self):
        """Teste l'absence d'un champ obligatoire (Section 5.6)."""
        carte = {
            "format": "robot-reconfort/carte",
            "version": 1,
            "nom": "test",
            "dimensions": {"hauteur": 2, "largeur": 2},
            "grille": ["R.", "A."],
            # "depart_robot" manque
            "armoire": {"position": [1, 0]},
            "dictionnaire": {"position": [0, 1]},
            "residents": []
        }
        with self.assertRaises(SystemExit):
            val.valider_carte(carte)

    def test_grille_non_rectangulaire(self):
        """Teste une grille avec des lignes de tailles différentes (Section 5.6)."""
        carte = {
            "format": "robot-reconfort/carte",
            "version": 1,
            "nom": "test",
            "dimensions": {"hauteur": 2, "largeur": 3},
            "grille": ["R.A", "D."], # La 2ème ligne n'a que 2 caractères
            "depart_robot": [0, 0],
            "armoire": {"position": [0, 2]},
            "dictionnaire": {"position": [1, 0]},
            "residents": []
        }
        with self.assertRaises(SystemExit):
            val.valider_carte(carte)

    def test_position_hors_grille(self):
        """Teste un élément placé en dehors des limites (Section 5.6)."""
        carte = {
            "format": "robot-reconfort/carte",
            "version": 1,
            "nom": "test",
            "dimensions": {"hauteur": 2, "largeur": 2},
            "grille": ["R.", "A."],
            "depart_robot": [0, 0],
            "armoire": {"position": [99, 99]}, # Hors grille
            "dictionnaire": {"position": [0, 1]},
            "residents": []
        }
        with self.assertRaises(SystemExit):
            val.valider_carte(carte)

    def test_symbole_attendu_incorrect(self):
        """Teste si le symbole sur la grille ne correspond pas à la position annoncée (Section 5.6)."""
        carte = {
            "format": "robot-reconfort/carte",
            "version": 1,
            "nom": "test",
            "dimensions": {"hauteur": 2, "largeur": 2},
            "grille": ["#.", "A."], # '#' au lieu de 'R'
            "depart_robot": [0, 0],
            "armoire": {"position": [1, 0]},
            "dictionnaire": {"position": [0, 1]},
            "residents": []
        }
        with self.assertRaises(SystemExit):
            val.valider_carte(carte)

    def test_deux_residents_meme_identifiant(self):
        """Teste la présence de deux résidents avec le même ID (Section 5.6)."""
        carte = {
            "format": "robot-reconfort/carte",
            "version": 1,
            "nom": "test",
            "dimensions": {"hauteur": 2, "largeur": 2},
            "grille": ["R.", "PP"],
            "depart_robot": [0, 0],
            "armoire": {"position": [0, 1]},
            "dictionnaire": {"position": [0, 1]},
            "residents": [
                {"id": "R1", "nom": "Bob", "position": [1, 0]},
                {"id": "R1", "nom": "Alice", "position": [1, 1]} # Doublon
            ]
        }
        with self.assertRaises(SystemExit):
            val.valider_carte(carte)

    # --- 2. TESTS DU SCENARIO ---

    def test_scenario_autre_carte(self):
        """Teste un scénario prévu pour une autre carte (Section 5.6)."""
        carte = {"nom": "carte_A", "residents": []}
        scenario = {
            "format": "robot-reconfort/scenario",
            "version": 1,
            "nom": "scen",
            "carte": "carte_B", # Ne correspond pas
            "armoire": "standard",
            "demandes": []
        }
        with self.assertRaises(SystemExit):
            val.valider_scenario(scenario, carte)

    # --- 3. TESTS DE L'ARMOIRE ---

    def test_casier_hors_dimensions(self):
        """Teste un casier placé en dehors des dimensions de l'armoire (Section 5.6)."""
        armoire = {
            "format": "robot-reconfort/armoire",
            "version": 1,
            "nom": "arm",
            "emotions": ["joie"],
            "intensites": ["faible"],
            "casier_depart": [0, 0],
            "casiers": [
                {"ligne": 5, "colonne": 5, "emotion": "joie", "intensite": "faible", "objet": "rien"}
            ]
        }
        with self.assertRaises(SystemExit):
            val.valider_armoire(armoire)

    # --- 4. TESTS DU DICTIONNAIRE ---

    def test_dictionnaire_mot_en_double(self):
        """Teste la présence d'un même mot dans deux entrées différentes (Section 5.6)."""
        dico = {
            "format": "robot-reconfort/dictionnaire",
            "version": 1,
            "nom": "dic",
            "emotions": ["joie", "peur"],
            "intensites": ["faible"],
            "entrees": [
                {"emotion": "joie", "intensite": "faible", "formes": ["cri"]},
                {"emotion": "peur", "intensite": "faible", "formes": ["cri"]} # Doublon
            ]
        }
        with self.assertRaises(SystemExit):
            val.valider_dictionnaire(dico)

if __name__ == '__main__':
    unittest.main()