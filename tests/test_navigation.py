""" Tests de navigation : planification BFS, replanification après un mur, et preuve qu'un résident est inaccessible """

import unittest

from outils_tests import armoire_pleine, carte_main, simuler_jusqua_fin
from agent import AgentReconfort, Plainte


class TestPlanification(unittest.TestCase):

    def test_chemin_de_longueur_connue(self):
        """Grille de l'annexe B, entièrement connue : 6 pas pour être adjacent à (1, 4)."""
        grille = ["######",
                  "#R.#P#",
                  "#.#..#",
                  "#...##",
                  "######"]
        carte = carte_main(grille, (1, 1), (0, 0), (0, 1), [("R1", (1, 4))])
        agent = AgentReconfort(carte, {"entrees": []}, armoire_pleine())
        # On donne toute la carte à l'agent pour tester le BFS seul
        for l, ligne in enumerate(grille):
            for c, symbole in enumerate(ligne):
                agent.carte_mentale[(l, c)] = "mur" if symbole == "#" else agent.carte_mentale.get((l, c), "libre")

        chemin = agent.calculer_chemin_bfs((1, 4))
        self.assertEqual(len(chemin), 6)
        self.assertEqual(chemin[-1], (2, 4))

    def test_replanification_mur_decouvert(self):
        """Un mur découvert sur le trajet prévu change le chemin."""
        carte = {"depart_robot": [2, 1], "dictionnaire": {"position": [0, 0]},
                 "armoire": {"position": [0, 1]}, "residents": [{"id": "R1", "position": [2, 6]}]}
        agent = AgentReconfort(carte, {"entrees": []}, armoire_pleine())

        chemin_initial = agent.calculer_chemin_bfs((2, 6))
        self.assertIn((2, 2), chemin_initial)  # hypothèse optimiste : tout droit vers l'est

        # Le robot perçoit un mur juste à l'est
        agent.mettre_a_jour_perceptions({"N": "libre", "S": "libre", "E": "mur", "O": "libre"})
        nouveau_chemin = agent.calculer_chemin_bfs((2, 6))

        self.assertNotIn((2, 2), nouveau_chemin)
        self.assertNotEqual(chemin_initial, nouveau_chemin)
        self.assertEqual(len(nouveau_chemin), len(chemin_initial) + 2)  # contournement


class TestResidentInaccessible(unittest.TestCase):

    def test_resident_mure_sans_prendre_objet(self):
        grille = ["######",
                  "#R.#P#",
                  "#..###",
                  "######"]
        carte = carte_main(grille, (1, 1), (0, 0), (0, 1), [("R1", (1, 4))])
        armoire = armoire_pleine()
        agent = AgentReconfort(carte, {"entrees": []}, armoire)
        plainte = Plainte({"numero": 1, "resident": "R1", "message": "test"}, (1, 4))
        plainte.dico_atteint = True
        plainte.emotion, plainte.intensite = "tristesse", "moyenne"
        agent.plainte_active = plainte

        actions = simuler_jusqua_fin(agent, carte, armoire)

        self.assertEqual(agent.livraison_en_attente["motif_echec"], "resident inaccessible")
        self.assertFalse(agent.livraison_en_attente["succes"])
        # L'échec est prouvé AVANT de passer à l'armoire : aucun objet pris
        self.assertNotIn("PRENDRE", [a["action"] for a in actions])
        self.assertNotIn("DONNER", [a["action"] for a in actions])


if __name__ == "__main__":
    unittest.main()