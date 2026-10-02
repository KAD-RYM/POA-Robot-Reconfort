import sys

def erreur_et_quitte(message: str) -> None:
    """Affiche le message d'erreur sur stderr et quitte avec le code 1."""
    print(f"ERREUR : {message}", file=sys.stderr)
    sys.exit(1)

def _valider_entete(donnees: dict, format_attendu: str, version_attendue: int = 1) -> None:
    """Vérifie les champs 'format' et 'version' en tête de fichier JSON."""
    if "format" not in donnees or donnees["format"] != format_attendu:
        erreur_et_quitte(
            f"Format inattendu : attendu '{format_attendu}', "
            f"obtenu '{donnees.get('format')}'."
        )
    
    if "version" not in donnees or donnees["version"] != version_attendue:
        erreur_et_quitte(
            f"Version inattendue : attendue {version_attendue}, "
            f"obtenue {donnees.get('version')}."
        )


def valider_carte(carte: dict) -> None:
    """Valide la structure et le contenu d'un fichier carte."""

    _valider_entete(carte, "robot-reconfort/carte", 1)

    # 1. Vérification des dimensions
    if "hauteur" not in carte or "largeur" not in carte:
        erreur_et_quitte("La carte doit contenir 'hauteur' et 'largeur'.")

    hauteur = carte["hauteur"]
    largeur = carte["largeur"]

    if not isinstance(hauteur, int) or not isinstance(largeur, int):
        erreur_et_quitte("Les dimensions 'hauteur' et 'largeur' doivent etre des entiers.")
    if hauteur <= 0 or largeur <= 0:
        erreur_et_quitte(f"Dimensions invalides pour la carte : {hauteur}x{largeur}.")

    # 2. Vérification de la grille
    if "grille" not in carte or not isinstance(carte["grille"], list):
        erreur_et_quitte("La carte doit contenir une 'grille' sous forme de liste.")

    grille = carte["grille"]
    if len(grille) != hauteur:
        erreur_et_quitte(
            f"Incoherence hauteur : {len(grille)} lignes trouvees dans la grille, "
            f"{hauteur} declarees."
        )

    symboles_valides = {".", "#", "R", "A", "D", "P"}
    for idx, ligne in enumerate(grille):
        if not isinstance(ligne, str):
            erreur_et_quitte(f"La ligne {idx} de la grille doit etre une chaine de caracteres.")
        if len(ligne) != largeur:
            erreur_et_quitte(
                f"Incoherence largeur a la ligne {idx} : {len(ligne)} caracteres trouves, "
                f"{largeur} declares."
            )
        for char in ligne:
            if char not in symboles_valides:
                erreur_et_quitte(f"Symbole inconnu '{char}' dans la grille a la ligne {idx}.")

    # 3. Fonction locale pour valider une coordonnée [ligne, colonne]
    def valider_coord(coord, nom_element):
        if not isinstance(coord, list) or len(coord) != 2:
            erreur_et_quitte(f"L'element '{nom_element}' doit etre une liste de 2 entiers [ligne, col].")
        l, c = coord[0], coord[1]
        if not isinstance(l, int) or not isinstance(c, int):
            erreur_et_quitte(f"Les coordonnees de '{nom_element}' doivent etre des entiers.")
        if not (0 <= l < hauteur) or not (0 <= c < largeur):
            erreur_et_quitte(f"Position de '{nom_element}' {coord} hors des bornes de la carte.")
        return l, c

    # 4. Vérification des positions principales et des symboles associés
    if "depart_robot" not in carte:
        erreur_et_quitte("Champ 'depart_robot' manquant dans la carte.")
    l_r, c_r = valider_coord(carte["depart_robot"], "depart_robot")
    if grille[l_r][c_r] != "R":
        erreur_et_quitte(f"Le symbole a la position depart_robot {carte['depart_robot']} doit etre 'R'.")


    if "armoire" not in carte or not isinstance(carte["armoire"], dict):
        erreur_et_quitte("Champ 'armoire' manquant ou invalide dans la carte.")
    if "position" not in carte["armoire"]:
        erreur_et_quitte("Champ 'position' manquant dans l'armoire.")
    l_a, c_a = valider_coord(carte["armoire"]["position"], "armoire")
    if grille[l_a][c_a] != "A":
        erreur_et_quitte(f"Le symbole a la position armoire {carte['armoire']['position']} doit etre 'A'.")


    if "dictionnaire" not in carte or not isinstance(carte["dictionnaire"], dict):
        erreur_et_quitte("Champ 'dictionnaire' manquant ou invalide dans la carte.")
    if "position" not in carte["dictionnaire"]:
        erreur_et_quitte("Champ 'position' manquant dans le dictionnaire.")
    l_d, c_d = valider_coord(carte["dictionnaire"]["position"], "dictionnaire")
    if grille[l_d][c_d] != "D":
        erreur_et_quitte(f"Le symbole a la position dictionnaire {carte['dictionnaire']['position']} doit etre 'D'.")


    # 5. Vérification des résidents
    if "residents" not in carte or not isinstance(carte["residents"], list):
        erreur_et_quitte("La carte doit contenir une liste 'residents'.")

    ids_residents = set()
    for resident in carte["residents"]:
        if not isinstance(resident, dict):
            erreur_et_quitte("Chaque resident doit etre un objet JSON (dictionnaire).")
        if "id" not in resident or "position" not in resident:
            erreur_et_quitte("Chaque resident doit avoir un 'id' et une 'position'.")

        res_id = resident["id"]
        if res_id in ids_residents:
            erreur_et_quitte(f"Identifiant de resident en double : '{res_id}'.")
        ids_residents.add(res_id)

        l_p, c_p = valider_coord(resident["position"], f"resident {res_id}")
        if grille[l_p][c_p] != "P":
            erreur_et_quitte(f"Le symbole a la position du resident '{res_id}' {resident['position']} doit etre 'P'.")


def valider_scenario(scenario: dict, carte: dict) -> None:
    """Valide la structure du fichier scenario et sa coherence avec la carte."""

    _valider_entete(scenario, "robot-reconfort/scenario", 1)

    # 1. Vérification du nom de la carte associée
    if "carte" not in scenario or not isinstance(scenario["carte"], str):
        erreur_et_quitte("Le scenario doit contenir un champ 'carte' valide (chaine de caracteres).")
    
    nom_carte_attendue = carte.get("nom")
    if nom_carte_attendue and scenario["carte"] != nom_carte_attendue:
        erreur_et_quitte(
            f"Incoherence scenario/carte : le scenario attend la carte '{scenario['carte']}', "
            f"mais la carte chargee s'appelle '{nom_carte_attendue}'."
        )

    # 2. Vérification du champ 'armoire'
    if "armoire" not in scenario or not isinstance(scenario["armoire"], str):
        erreur_et_quitte("Le scenario doit specifier un nom d'armoire valide (chaine de caracteres).")

    # 3. Vérification de la liste 'demandes'
    if "demandes" not in scenario or not isinstance(scenario["demandes"], list):
        erreur_et_quitte("Le scenario doit contenir une liste 'demandes'.")

    # Extraction des IDs des résidents présents sur la carte pour vérification
    ids_residents_carte = {res["id"] for res in carte.get("residents", [])}

    ids_demandes = set()
    for idx, d in enumerate(scenario["demandes"]):
        if not isinstance(d, dict):
            erreur_et_quitte(f"La demande a l'index {idx} doit etre un dictionnaire.")

        # Vérification de l'identifiant de la demande
        if "numero" not in d:
            erreur_et_quitte(f"Champ 'numero' (ID) manquant dans la demande index {idx}.")
        
        id_d = d["numero"]
        if not isinstance(id_d, int) or id_d <= 0:
            erreur_et_quitte(f"L'identifiant de demande {id_d} doit etre un entier strictement positif.")
        
        if id_d in ids_demandes:
            erreur_et_quitte(f"Identifiant de demande en double dans le scenario : {id_d}.")
        ids_demandes.add(id_d)

        # Vérification du résident cible
        if "resident" not in d:
            erreur_et_quitte(f"Champ 'resident' manquant dans la demande {id_d}.")
        
        res_target = d["resident"]
        if res_target not in ids_residents_carte:
            erreur_et_quitte(
                f"La demande {id_d} s'adresse au resident '{res_target}', "
                f"mais celui-ci n'existe pas sur la carte."
            )

        # 3. Vérification du message
        if "message" not in d:
            erreur_et_quitte(f"La demande {id_d} doit contenir un 'message'.")
        
        if not isinstance(d["message"], str) or not d["message"].strip():
            erreur_et_quitte(f"Le message de la demande {id_d} doit etre une chaine de caracteres non vide.")


def valider_armoire(armoire: dict) -> None:
    """Valide la structure du fichier armoire"""

    _valider_entete(armoire, "robot-reconfort/armoire", 1)

    # 1. Validation des listes de référence (emotions, intensites)
    if "emotions" not in armoire or not isinstance(armoire["emotions"], list):
        erreur_et_quitte("L'armoire doit contenir une liste 'emotions'.")
    emotions_valides = set(armoire["emotions"])

    if "intensites" not in armoire or not isinstance(armoire["intensites"], list):
        erreur_et_quitte("L'armoire doit contenir une liste 'intensites'.")
    intensites_valides = set(armoire["intensites"])

    # 2. Validation du casier de départ
    if "casier_depart" not in armoire or not isinstance(armoire["casier_depart"], list):
        erreur_et_quitte("L'armoire doit contenir un champ 'casier_depart' sous forme de liste.")

    hauteur_max = len(armoire["intensites"])
    largeur_max = len(armoire["emotions"]) 
    
    cd = armoire.get("casier_depart")
    if not isinstance(cd, list) or len(cd) != 2:
        erreur_et_quitte("Le 'casier_depart' doit etre une liste de 2 entiers [ligne, colonne].")

    l_dep, c_dep = cd[0], cd[1]

    if (not isinstance(l_dep, int) or not isinstance(c_dep, int) 
            or not (0 <= l_dep < hauteur_max) or not (0 <= c_dep < largeur_max)):
        erreur_et_quitte(
            f"Le 'casier_depart' ({l_dep}, {c_dep}) est hors de l'armoire "
            f"(lignes 0 à {hauteur_max - 1}, colonnes 0 à {largeur_max - 1})."
        )

    # 3. Validation de la liste des casiers
    if "casiers" not in armoire or not isinstance(armoire["casiers"], list):
        erreur_et_quitte("L'armoire doit contenir une liste 'casiers'.")

    coords_casiers = set()
    # 1. Calcul des bornes de l'armoire depuis les en-têtes

    for idx, casier in enumerate(armoire["casiers"]):
        if not isinstance(casier, dict):
            erreur_et_quitte(f"Le casier a l'index {idx} doit etre un dictionnaire.")

        # Vérification des coordonnées
        if "ligne" not in casier or "colonne" not in casier:
            erreur_et_quitte(f"Champs 'ligne' et 'colonne' requis dans le casier index {idx}.")
        
        lig, col = casier["ligne"], casier["colonne"]
        if (not isinstance(lig, int) or not isinstance(col, int) 
                or not (0 <= lig < hauteur_max) or not (0 <= col < largeur_max)):
            erreur_et_quitte(
                f"Les coordonnees ({lig}, {col}) du casier index {idx} sont hors de l'armoire "
                f"(lignes 0..{hauteur_max - 1}, colonnes 0..{largeur_max - 1})."
            )

        # Détection de doublons de casier
        coord_key = (lig, col)
        if coord_key in coords_casiers:
            erreur_et_quitte(f"Casier en double aux coordonnees : {coord_key}.")
        coords_casiers.add(coord_key)

        # Vérification de l'émotion associée
        if "emotion" not in casier or casier["emotion"] not in emotions_valides:
            erreur_et_quitte(f"Emotion invalide ou manquante '{casier.get('emotion')}' dans le casier {coord_key}.")

        emotion_attendue = armoire["emotions"][col]
        if casier.get("emotion") != emotion_attendue:
            erreur_et_quitte(
                f"Emotion incorrecte au casier ({lig}, {col}) : "
                f"attendu '{emotion_attendue}', obtenu '{casier.get('emotion')}'."
            )

        # Vérification de l'intensité
        if "intensite" not in casier or casier["intensite"] not in intensites_valides:
            erreur_et_quitte(f"Intensite invalide ou manquante '{casier.get('intensite')}' dans le casier {coord_key}.")

        intensite_attendue = armoire["intensites"][lig]
        if casier.get("intensite") != intensite_attendue:
            erreur_et_quitte(
                f"Intensite incorrecte au casier ({lig}, {col}) : "
                f"attendue '{intensite_attendue}', obtenue '{casier.get('intensite')}'."
            )

        # Vérification de l'objet (chaine ou None)
        if "objet" not in casier:
            erreur_et_quitte(f"Champ 'objet' manquant dans le casier {coord_key}.")
        
        obj = casier["objet"]
        if obj is not None and (not isinstance(obj, str) or not obj.strip()):
            erreur_et_quitte(f"L'objet du casier {coord_key} doit etre une chaine non vide ou null.")


def valider_dictionnaire(dico: dict) -> None:
    """Valide la structure du fichier dictionnaire"""

    _valider_entete(dico, "robot-reconfort/dictionnaire", 1)

    # 1. Validation de la liste des emotions
    if "emotions" not in dico or not isinstance(dico["emotions"], list):
        erreur_et_quitte("Le dictionnaire doit contenir une liste 'emotions'.")
    emotions_valides = set(dico["emotions"])

    # 2. Validation de la liste des intensites
    if "intensites" not in dico or not isinstance(dico["intensites"], list):
        erreur_et_quitte("Le dictionnaire doit contenir une liste 'intensites'.")
    intensites_valides = set(dico["intensites"])

    # 3. Validation de la liste des entrees
    if "entrees" not in dico or not isinstance(dico["entrees"], list):
        erreur_et_quitte("Le dictionnaire doit contenir une liste 'entrees'.")

    formes_visitees = set()

    for idx, entree in enumerate(dico["entrees"]):
        if not isinstance(entree, dict):
            erreur_et_quitte(f"L'entree a l'index {idx} doit etre un dictionnaire.")

        # Validation de l'emotion
        if "emotion" not in entree or entree["emotion"] not in emotions_valides:
            erreur_et_quitte(f"Emotion invalide ou manquante '{entree.get('emotion')}' a l'index {idx}.")

        # Validation de l'intensite
        if "intensite" not in entree or entree["intensite"] not in intensites_valides:
            erreur_et_quitte(f"Intensite invalide ou manquante '{entree.get('intensite')}' a l'index {idx}.")

        # Validation des formes (liste de mots)
        if "formes" not in entree or not isinstance(entree["formes"], list) or not entree["formes"]:
            erreur_et_quitte(f"L'entree a l'index {idx} doit contenir une liste 'formes' non vide.")

        for mot in entree["formes"]:
            if not isinstance(mot, str) or not mot.strip():
                erreur_et_quitte(f"Chaque forme dans l'entree {idx} doit etre une chaine non vide.")
            
            mot_clean = mot.strip().lower()
            if mot_clean in formes_visitees:
                erreur_et_quitte(f"Forme/mot en double dans le dictionnaire : '{mot_clean}'.")
            formes_visitees.add(mot_clean)