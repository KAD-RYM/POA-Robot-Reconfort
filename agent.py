import sys
import reconfort_io as rio

USAGE = ("Usage : python agent.py <carte.json> <scenario.json> "
         "<dossier_donnees> <trace_sortie.json>")


def lire_arguments(argv):
    """Renvoie les 4 chemins, ou lève ErreurFichier."""
    if len(argv) != 5:
        raise rio.ErreurFichier(f"4 arguments attendus.\n{USAGE}")
    return argv[1], argv[2], argv[3], argv[4]


def main(argv):
    try:
        f_carte, f_scenario, d_donnees, f_trace = lire_arguments(argv)
        carte = rio.charger_carte(f_carte)
        scenario = rio.charger_scenario(f_scenario)
        # puis dictionnaire, armoire, validation, simulation, écriture
    except rio.ErreurFichier as err:
        print(f"ERREUR : {err}", file=sys.stderr)
        return 1
    except OSError as err:
        print(f"ERREUR d'écriture : {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))