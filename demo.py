#!/usr/bin/env python3
"""
Demonstration de la base fournie -- projet "Robot de reconfort".

Ce script ne resout rien. Il montre seulement :
  - le contrat d'appel attendu (quatre arguments) ;
  - comment charger les quatre fichiers d'entree ;
  - comment gerer proprement un fichier absent ou mal forme ;
  - comment produire un fichier de trace conforme.

Le robot de cette demo n'avance pas, ne consulte rien, et echoue sur
toutes les demandes. C'est a vous d'ecrire celui qui reussit.

    python3 demo.py cartes/appartement_01.json cartes/scenario_01.json \
        donnees sorties/trace_01.json
"""

import sys
from pathlib import Path

import reconfort_io as rio


def main(argv):
    if len(argv) != 5:
        print(__doc__.strip())
        return 2

    chemin_carte, chemin_scenario = Path(argv[1]), Path(argv[2])
    dossier_donnees, chemin_sortie = Path(argv[3]), Path(argv[4])

    try:
        carte = rio.charger_carte(chemin_carte)
        scenario = rio.charger_scenario(chemin_scenario)
        dictionnaire = rio.charger_dictionnaire(
            dossier_donnees / "dictionnaire.json")
        armoire = rio.charger_armoire(
            dossier_donnees / f"{scenario['armoire']}.json")
    except rio.ErreurFichier as err:
        print(f"erreur de chargement : {err}", file=sys.stderr)
        return 1

    print(f"carte        : {carte['nom']} "
          f"{carte['dimensions']['hauteur']}x{carte['dimensions']['largeur']}, "
          f"{len(carte['residents'])} residents")
    print(f"scenario     : {scenario['nom']}, "
          f"{len(scenario['demandes'])} demandes")
    print(f"dictionnaire : {len(dictionnaire['entrees'])} entrees")
    print(f"armoire      : {armoire['nom']}, "
          f"{len(armoire['casiers'])} casiers")
    print()

    # Ce que voit le robot au depart : sa position, celle de l'armoire, celle
    # du dictionnaire, et celles des residents. Les murs, eux, ne sont PAS
    # connus a priori, et le contenu des casiers non plus (enonce 3.2 et 3.3).
    # Ne lisez ni carte["grille"], ni le champ "objet" des casiers : votre
    # agent n'y a pas droit.
    print(f"depart robot   : {carte['depart_robot']}")
    print(f"armoire        : {carte['armoire']['position']}")
    print(f"dictionnaire   : {carte['dictionnaire']['position']}")
    print(f"casier depart  : {armoire['casier_depart']}")

    trace = rio.Trace(
        nom_carte=carte["nom"],
        nom_scenario=scenario["nom"],
        equipe=["A completer", "A completer"],
    )

    for demande in scenario["demandes"]:
        numero = demande["numero"]
        print(f"\ndemande {numero} ({demande['resident']}) : "
              f"{demande['message']}")
        print(f"  mots normalises : {rio.normaliser(demande['message'])}")

        trace.ajouter_pas(
            demande=numero,
            position=carte["depart_robot"],
            casier=armoire["casier_depart"],
            action="ATTENDRE",
            commentaire="robot de demonstration : ne fait rien",
        )
        trace.ajouter_livraison(
            demande=numero,
            resident=demande["resident"],
            emotion=None,
            intensite=None,
            casier_choisi=None,
            repli="aucun",
            objet=None,
            succes=False,
            motif_echec="agent non implemente",
        )

    trace.ecrire(chemin_sortie)
    print(f"\ntrace ecrite : {chemin_sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
