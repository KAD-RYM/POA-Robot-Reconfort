import unittest
from agent import AgentReconfort, Plainte, simuler_environnement, simuler_armoire

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

        # Repli (cas « casier exact garni ») : livraison réussie avec l'étiquette "aucun"
        self.assertTrue(agent.livraison_en_attente["succes"])
        self.assertEqual(agent.livraison_en_attente["repli"], "aucun")
    
    def test_resident_mure(self):
        """Cas inaccessible (section 8, point 7) : résident muré sur une grille minuscule."""

        # 1. UNE MINI-CARTE OÙ LE RÉSIDENT P EST ENTOURÉ DE MURS
        carte = {
            "nom": "Mini-Carte Muree",
            "depart_robot": [1, 1],
            "dictionnaire": {"position": [2, 1]},
            "armoire": {"position": [2, 2]},
            "residents": [{"id": "R1", "position": [1, 4]}],
            "dimensions": {"hauteur": 4, "largeur": 6},
            "grille": [
                ["#", "#", "#", "#", "#", "#"],
                ["#", "R", ".", "#", "P", "#"],
                ["#", "D", "A", "#", "#", "#"],
                ["#", "#", "#", "#", "#", "#"]
            ]
        }
        dictionnaire = {
            "entrees": [
                {"emotion": "Tristesse", "intensite": "forte", "formes": ["triste"]}
            ]
        }
        armoire = {
            "casier_depart": [0, 0],
            "emotions": ["Tristesse"],
            "intensites": ["forte"],
            "casiers": [
                {"ligne": 0, "colonne": 0, "emotion": "Tristesse", "intensite": "forte", "objet": "Peluche Réconfortante"}
            ]
        }

        # 2. ON LANCE LE ROBOT SUR LA DEMANDE
        agent = AgentReconfort(carte, dictionnaire, armoire)
        agent.plainte_active = Plainte({"numero": 1, "resident": "R1", "message": "Je suis triste"}, (1, 4))

        tour = 0
        max_tours = 50
        action_dict = {"action": "ATTENDRE", "argument": None}
        actions_jouees = []

        while agent.plainte_active is not None and tour < max_tours:
            agent.pos_actuelle, perceptions = simuler_environnement(carte, agent.pos_actuelle, action_dict)
            agent.casier_selecteur, contenu = simuler_armoire(armoire, agent.casier_selecteur, action_dict)
            perceptions["contenu_casier"] = contenu

            action_dict = agent.decider_action(perceptions)
            actions_jouees.append(action_dict["action"])
            tour += 1

        # 3. VÉRIFICATIONS
        # Il a fini par abandonner, sans tourner en rond
        self.assertLess(tour, max_tours, "ÉCHEC : Le robot n'a jamais prouvé que le résident était inaccessible.")
        self.assertIsNone(agent.plainte_active)

        # L'échec est bien noté avec le bon motif
        self.assertFalse(agent.livraison_en_attente["succes"])
        self.assertEqual(agent.livraison_en_attente["motif_echec"], "resident inaccessible")

        # Il n'a jamais pris d'objet (impossible de le reposer ensuite)
        self.assertNotIn("PRENDRE", actions_jouees)
        self.assertNotIn("DONNER", actions_jouees)