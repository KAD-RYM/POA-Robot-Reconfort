import sys
import os

def afficher_erreur_et_quitte(message):
    """Affiche le message d'erreur sur stderr et quitte avec un code 1."""
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)

def valider_arguments():
    """
    1. Vérifie le nombre d'arguments en ligne de commande.
    2. Vérifie l'existence des fichiers carte et scénario.
    3. Vérifie l'existence du dossier de données.
    """
    # 1. Vérification du nombre d'arguments (sys.argv contient script + 4 arguments = 5 éléments)
    if len(sys.argv) < 5:
        afficher_erreur_et_quitte(
            "Nombre d'arguments insuffisant.\n"
            "Usage : python agent.py <carte.json> <scenario.json> <dossier_donnees/> <trace_sortie.json>"
        )
    
    f_carte = sys.argv[1]
    f_scenario = sys.argv[2]
    d_donnees = sys.argv[3]
    f_trace = sys.argv[4]
    
    # 2. Vérification de l'existence de la carte
    if not os.path.exists(f_carte):
        afficher_erreur_et_quitte(f"Fichier de carte introuvable : '{f_carte}'")
    if not os.path.isfile(f_carte):
        afficher_erreur_et_quitte(f"Le chemin de carte spécifié n'est pas un fichier : '{f_carte}'")
        
    # 3. Vérification de l'existence du scénario
    if not os.path.exists(f_scenario):
        afficher_erreur_et_quitte(f"Fichier de scenario introuvable : '{f_scenario}'")
    if not os.path.isfile(f_scenario):
        afficher_erreur_et_quitte(f"Le chemin de scenario spécifié n'est pas un fichier : '{f_scenario}'")

    # 4. Vérification de l'existence du dossier de données
    if not os.path.exists(d_donnees):
        afficher_erreur_et_quitte(f"Dossier de donnees introuvable : '{d_donnees}'")
    if not os.path.isdir(d_donnees):
        afficher_erreur_et_quitte(f"Le chemin de donnees spécifié n'est pas un dossier : '{d_donnees}'")
        
    return f_carte, f_scenario, d_donnees, f_trace

def main():
    # C'est ICI qu'on appelle réellement la fonction !
    f_carte, f_scenario, d_donnees, f_trace = valider_arguments()
    print("[OK] Bloc A valide : Tous les arguments et fichiers de base sont présents.")

if __name__ == "__main__":
    main()