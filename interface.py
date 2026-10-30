import pygame
import sys
import os

class SimulationPygame:
    def __init__(self, dimensions: dict, cell_size=40):
        pygame.init()
        self.hauteur = dimensions["hauteur"]
        self.largeur = dimensions["largeur"]
        self.cell_size = cell_size
        self.running = True

        self.fenetre = pygame.display.set_mode((
            self.largeur * cell_size, 
            self.hauteur * cell_size
        ))
        pygame.display.set_caption("Simulation Robot Réconfort 🐈")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 14, bold=True)

        # Palette de couleurs de base (murs, meubles, brouillard)
        self.couleurs = {
            "inconnu": (20, 20, 20),
            "libre": (240, 240, 240),
            "mur": (60, 60, 60),
            "D": (52, 152, 219),
            "A": (243, 156, 18),
            "P": (46, 204, 113),
            "robot": (231, 76, 60)
        }

        # Animation du chat (Spritesheet 8 frames)
        self.frames_chat = []
        self.frame_index = 0
        self.charger_anim_chat(cell_size)

    def charger_anim_chat(self, cell_size):
        # Image fixe du chat (une seule frame), chemin relatif à ce fichier
        chemin_chat = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cat.png")
        if os.path.exists(chemin_chat):
            try:
                image = pygame.image.load(chemin_chat).convert_alpha()
                self.frames_chat.append(pygame.transform.smoothscale(image, (cell_size, cell_size)))
            except Exception as e:
                print(f"⚠️ Erreur chargement image chat : {e}")

    def rafraichir(self, agent, fps=8):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                pygame.quit()
                sys.exit()

        self.fenetre.fill((10, 10, 10))

        # Avancement de la frame d'animation à chaque tour de boucle
        if self.frames_chat:
            self.frame_index = (self.frame_index + 1) % len(self.frames_chat)

        for l in range(self.hauteur):
            for c in range(self.largeur):
                pos = (l, c)
                x = c * self.cell_size
                y = l * self.cell_size
                rect = (x, y, self.cell_size, self.cell_size)

                # 1. Brouillard de guerre (inconnu)
                if pos not in agent.carte_mentale:
                    pygame.draw.rect(self.fenetre, self.couleurs["inconnu"], rect)
                    pygame.draw.rect(self.fenetre, (30, 30, 30), rect, 1)
                    continue

                val = agent.carte_mentale[pos]
                cle_element = "libre"
                texte = ""

                if val in ("mur", "#"):
                    cle_element = "mur"
                elif val == "D":
                    cle_element = "D"
                    texte = "D"
                elif val == "A":
                    cle_element = "A"
                    texte = "A"
                elif val == "P":
                    cle_element = "P"
                    texte = "P"

                # 2. Rendu des cases de base (Couleurs + Lettres)
                pygame.draw.rect(self.fenetre, self.couleurs[cle_element], rect)
                if texte:
                    txt_surface = self.font.render(texte, True, (255, 255, 255))
                    self.fenetre.blit(txt_surface, (x + 12, y + 10))

                # 3. Rendu du Robot / Chat animé
                if pos == agent.pos_actuelle:
                    if self.frames_chat:
                        img = self.frames_chat[self.frame_index]
                        self.fenetre.blit(img, (x, y))
                    else:
                        pygame.draw.rect(self.fenetre, self.couleurs["robot"], rect)
                        txt_surface = self.font.render("R", True, (255, 255, 255))
                        self.fenetre.blit(txt_surface, (x + 15, y + 10))

                # Quadrillage
                pygame.draw.rect(self.fenetre, (50, 50, 50), rect, 1)

        pygame.display.flip()
        self.clock.tick(fps)

    def attendre_fermeture(self):
        print("\n🏁 Simulation terminée ! Fermez la fenêtre graphique pour quitter.")
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            self.clock.tick(10)
        pygame.quit()