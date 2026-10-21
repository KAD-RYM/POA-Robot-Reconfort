import pygame
import sys

class SimulationPygame:
    def __init__(self, dimensions: dict, cell_size=40):
        pygame.init()
        self.hauteur = dimensions["hauteur"]
        self.largeur = dimensions["largeur"]
        self.cell_size = cell_size

        self.fenetre = pygame.display.set_mode((
            self.largeur * cell_size, 
            self.hauteur * cell_size
        ))
        pygame.display.set_caption("Carte Mentale & Déplacement du Robot")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16, bold=True)

        # Palette de couleurs (RGB)
        self.couleurs = {
            "inconnu": (26, 26, 26),
            "libre": (255, 255, 255),
            "mur": (51, 51, 51),
            "D": (52, 152, 219),
            "A": (243, 156, 18),
            "P": (46, 204, 113),
            "robot": (231, 76, 60)
        }

    def rafraichir(self, agent, fps=15):  # 👈 On gère en FPS (ex: 15 actions par seconde)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                import sys
                sys.exit()

        self.fenetre.fill((17, 17, 17))

        for l in range(self.hauteur):
            for c in range(self.largeur):
                pos = (l, c)
                rect = (c * self.cell_size, l * self.cell_size, self.cell_size, self.cell_size)

                couleur = self.couleurs["inconnu"]
                texte = ""

                if pos in agent.carte_mentale:
                    val = agent.carte_mentale[pos]
                    if val in ("mur", "#"):
                        couleur = self.couleurs["mur"]
                        texte = "#"
                    elif val in ("libre", "."):
                        couleur = self.couleurs["libre"]
                    elif val == "D":
                        couleur = self.couleurs["D"]
                        texte = "D"
                    elif val == "A":
                        couleur = self.couleurs["A"]
                        texte = "A"
                    elif val == "P":
                        couleur = self.couleurs["P"]
                        texte = "P"

                if pos == agent.pos_actuelle:
                    couleur = self.couleurs["robot"]
                    texte = "R"

                pygame.draw.rect(self.fenetre, couleur, rect)
                pygame.draw.rect(self.fenetre, (68, 68, 68), rect, 1)

                if texte:
                    surface_texte = self.font.render(texte, True, (255, 255, 255))
                    text_rect = surface_texte.get_rect(
                        center=(c * self.cell_size + self.cell_size // 2, 
                                l * self.cell_size + self.cell_size // 2)
                    )
                    self.fenetre.blit(surface_texte, text_rect)

        pygame.display.flip()
        self.clock.tick(fps)  # 👈 Régule la vitesse proprement (15 images/sec)

    def attendre_fermeture(self):
        """Bloque le script à la fin de la simulation pour garder la fenêtre ouverte."""
        print("\n🏁 Simulation terminée ! Fermez la fenêtre pour quitter.")
        
        attente = True
        while attente:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    attente = False
            self.clock.tick(10)  # Limite l'utilisation du processeur
            
        pygame.quit()