
# Champ obligatoire absent ou du mauvais type

def _exiger(objet, cle, type_, chemin):
    """Renvoie objet[cle] après avoir vérifié sa présence et son type."""
    if not isinstance(objet, dict):
        raise ErreurFichier(f"{chemin} doit être un objet JSON")
    if cle not in objet:
        raise ErreurFichier(f"{chemin} : champ obligatoire {cle!r} absent")
    valeur = objet[cle]
    # bool est un sous-type de int en Python : on l'exclut explicitement
    ok = type(valeur) is int if type_ is int else isinstance(valeur, type_)
    if not ok:
        raise ErreurFichier(
            f"{chemin}.{cle} : type {type_.__name__} attendu, "
            f"trouvé {type(valeur).__name__}"
        )
    return valeur


def _liste_de(objet, cle, type_, chemin):
    """Comme _exiger pour une liste dont tous les éléments ont un type."""
    liste = _exiger(objet, cle, list, chemin)
    for i, element in enumerate(liste):
        ok = type(element) is int if type_ is int else isinstance(element, type_)
        if not ok:
            raise ErreurFichier(
                f"{chemin}.{cle}[{i}] : type {type_.__name__} attendu"
            )
    return liste


def _position(valeur, chemin):
    if not (isinstance(valeur, list) and len(valeur) == 2
            and all(type(v) is int for v in valeur)):
        raise ErreurFichier(f"{chemin} doit être [ligne, colonne] (2 entiers)")


def valider_structure_carte(carte):
    _exiger(carte, "nom", str, "carte")
    dim = _exiger(carte, "dimensions", dict, "carte")
    _exiger(dim, "hauteur", int, "carte.dimensions")
    _exiger(dim, "largeur", int, "carte.dimensions")
    _liste_de(carte, "grille", str, "carte")
    _position(_exiger(carte, "depart_robot", list, "carte"),
              "carte.depart_robot")
    for cle in ("armoire", "dictionnaire"):
        sous = _exiger(carte, cle, dict, "carte")
        _position(_exiger(sous, "position", list, f"carte.{cle}"),
                  f"carte.{cle}.position")
    for i, r in enumerate(_exiger(carte, "residents", list, "carte")):
        chemin = f"carte.residents[{i}]"
        _exiger(r, "id", str, chemin)
        _exiger(r, "nom", str, chemin)
        _position(_exiger(r, "position", list, chemin), f"{chemin}.position")


def valider_structure_scenario(scenario):
    _exiger(scenario, "nom", str, "scénario")
    _exiger(scenario, "carte", str, "scénario")
    _exiger(scenario, "armoire", str, "scénario")
    for i, d in enumerate(_exiger(scenario, "demandes", list, "scénario")):
        chemin = f"scénario.demandes[{i}]"
        _exiger(d, "numero", int, chemin)
        _exiger(d, "resident", str, chemin)
        _exiger(d, "message", str, chemin)


def valider_structure_armoire(armoire):
    _exiger(armoire, "nom", str, "armoire")
    _liste_de(armoire, "emotions", str, "armoire")
    _liste_de(armoire, "intensites", str, "armoire")
    _position(_exiger(armoire, "casier_depart", list, "armoire"),
              "armoire.casier_depart")
    for i, c in enumerate(_exiger(armoire, "casiers", list, "armoire")):
        chemin = f"armoire.casiers[{i}]"
        _exiger(c, "ligne", int, chemin)
        _exiger(c, "colonne", int, chemin)
        _exiger(c, "emotion", str, chemin)
        _exiger(c, "intensite", str, chemin)


def valider_structure_dictionnaire(dico):
    _exiger(dico, "nom", str, "dictionnaire")
    _liste_de(dico, "emotions", str, "dictionnaire")
    _liste_de(dico, "intensites", str, "dictionnaire")
    for i, e in enumerate(_exiger(dico, "entrees", list, "dictionnaire")):
        chemin = f"dictionnaire.entrees[{i}]"
        _liste_de(e, "formes", str, chemin)
        _exiger(e, "emotion", str, chemin)
        _exiger(e, "intensite", str, chemin)


#------------------------------------

#Verification position et symboles


def _positions_de_la_carte(carte):
    """Renvoie (description, position, symbole attendu) pour chaque élément."""
    yield "départ du robot", carte["depart_robot"], "R"
    yield "armoire", carte["armoire"]["position"], "A"
    yield "dictionnaire", carte["dictionnaire"]["position"], "D"
    for r in carte["residents"]:
        yield f"résident {r['id']}", r["position"], "P"



def verifier_positions_et_symboles(carte):
    hauteur = carte["dimensions"]["hauteur"]
    largeur = carte["dimensions"]["largeur"]
    
    for nom, (ligne, colonne), attendu in _positions_de_la_carte(carte):
        
        # 1. D'abord, on vérifie que la position est dans la grille
        if not (0 <= ligne < hauteur and 0 <= colonne < largeur):
            raise ErreurFichier(
                f"carte : {nom} en [{ligne}, {colonne}], hors de la grille "
                f"{hauteur}x{largeur}"
            )
        
        # 2. Si on arrive ici, la position est valide, on peut donc lire le symbole sans faire planter Python
        trouve = carte["grille"][ligne][colonne]
        if trouve != attendu:
            raise ErreurFichier(
                f"carte : {nom} en [{ligne}, {colonne}] : symbole "
                f"{attendu!r} attendu dans la grille, trouvé {trouve!r}"
            )