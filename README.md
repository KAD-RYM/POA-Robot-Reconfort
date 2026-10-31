# Robot de réconfort — HARAUT Kevin & KADDOUR Reyam

Projet de semestre, Master Informatique. Un robot qui a qu'une perception 
locale des quatres cases autour de lui (Nord, Sud, Ouest et Est), il 
reçoit un message d'un résident lui indiquant son état actuel.
Consulte un dictionnaire pour analyser le message reçu et en conclure 
une émotion et une intensité, puis fouille une armoire pour y récupérer 
l'objet adéquat parmi ceux disponibles, et le rapporte au résident.

- **Langage :**  Python — Version : 3.10 ou plus
- **Dépendances :**  aucune pour le programme. 
`pygame` seulement pour l'affichage graphique qui facultatif, s'intalle avec `pip install pygame`, puis ajouter `--gui` en 5e argument de lancement.

## Lancer

Depuis la racine du projet :

SANS INTERFACE :

```
python3 agent.py <carte.json> <scenario.json> <dossier_donnees> <trace_sortie.json>
```

Exemple sans interface :

```
python3 agent.py cartes/appartement_01.json cartes/scenario_01.json donnees sortie.json
```

AVEC INTERFACE :

```
python3 agent.py <carte.json> <scenario.json> <dossier_donnees> <trace_sortie.json> --gui
```

Exemple :

```
python3 agent.py cartes/appartement_01.json cartes/scenario_01.json donnees sortie.json --gui
```

## Tester

Pour lancer l'intégralité des tests automatisés, exécutez la commande suivante depuis la racine du projet :

```
python3 -m unittest discover tests
```
Résultat attendu : `Ran 31 tests ... OK` (sans dépendance externe).

Les tests couvrent la planification (du meilleure chemin, longueur connue), la replanification
après découverte d'un mur, la lecture du dictionnaire (une émotion chacune,
premier mot gagnant, aucun mot), le sélecteur et le bouclage 7↔0, les quatre
cas de repli, la validation (un fichier cassé par catégorie) et le résident
inaccessible.


Le projet intègre une suite de tests automatisés basée sur le module standard `unittest`. Elle permet de vérifier la robustesse de l'agent, le bon fonctionnement de la simulation et la conformité stricte aux exigences de validation des entrées (Section 5.6).

Les tests sont répartis en quatre modules, plus un fichier d'outils partagés :

| Fichier | Tests | Ce qui est vérifié |
|---|---|---|
| `tests/test_agent.py` | 18 | dictionnaire, carte mentale, ordre des sous-objectifs, armoire, règle de repli |
| `tests/test_navigation.py` | 3 | BFS, replanification, résident inaccessible |
| `tests/test_simulation.py` | 3 | scénario complet, programme lancé sur des fichiers cassés |
| `tests/test_validation.py` | 16 | un fichier invalide par catégorie (section 5.6) |
| `tests/outils_tests.py` | — | fonctions d'aide partagées (pas un fichier de tests) |

### 1. Agent (`tests/test_agent.py`)

- **Dictionnaire :** un mot connu ; deux mots connus (le premier rencontré l'emporte) ;
  aucun mot connu (émotion indéterminée) ; un message réel pour chacune des 8 émotions.
- **Perception et carte mentale :** mise à jour à partir des 4 cases voisines,
  mémoire conservée après un déplacement, bords de carte.
- **Sous-objectifs :** ordre `GO_DICO` → `VERIF_RESIDENT` → `GO_ARMOIRE` → `GO_RESIDENT`,
  enchaînement de plusieurs demandes avec remise à zéro de l'état.
- **Armoire :** tri des 15 candidats (distance sur la roue, écart d'intensité,
  intensité faible d'abord, sens horaire) ; sélecteur avec bouclage des colonnes 7 ↔ 0
  et blocage vertical sur les lignes 0 et 2 ; casiers vides mémorisés.
- **Règle de repli :** les 4 cas — casier exact garni (`aucun`), autre intensité
  (`intensite`), émotion voisine (`voisine_1`), aucun casier garni à distance ≤ 2 (`armoire vide`).

### 2. Navigation (`tests/test_navigation.py`)

- **Planification :** sur la grille de l'annexe B, chemin de longueur connue (6 pas).
- **Replanification :** un mur découvert sur le trajet prévu donne un contournement.
- **Résident inaccessible :** résident muré → échec `resident inaccessible`, prouvé
  **avant** l'armoire : aucun `PRENDRE`, aucun `DONNER`.

### 3. Simulation (`tests/test_simulation.py`)

- **Scénario complet :** message → dictionnaire → vérification du résident → armoire →
  livraison, en un nombre de tours borné.
- **Programme sur fichiers cassés :** scénario sans armoire, armoire introuvable →
  code de retour non nul, pas de `Traceback`, aucune trace écrite.

### 4. Validation (`tests/test_validation.py`)

Chaque fichier invalide doit provoquer un arrêt propre (code non nul et message sur
`stderr`), et le test vérifie que c'est **la bonne erreur** qui est signalée :

- **Lecture :** fichier absent, fichier non UTF-8, JSON invalide, mauvais `format` ou `version`.
- **Carte :** champ manquant ou de mauvais type, grille non rectangulaire, position hors
  grille, symbole incohérent avec la position déclarée, identifiant de résident en double.
- **Scénario :** scénario prévu pour une autre carte, demande adressée à un résident absent.
- **Armoire :** casier hors dimensions, `casier_depart` hors de l'armoire, étiquette
  émotion/intensité incohérente.
- **Dictionnaire :** mot présent dans deux entrées, émotion inconnue.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `agent.py` | Contient le comportement de l'agent (perception locale, carte mentale, prise de décision) et orchestre l'exécution dans la boucle principale (main).|
| `simulateur.py` |Modélise l'environnement global : gère la grille, le contenu des conteneurs et traite les actions de l'agent en lui envoyant ses perceptions locales.|
| `validation.py` |Contrôle la conformité des fichiers d'entrée (JSON, grille, objets) selon la section 5.6 et interrompt proprement le programme avec un message sur la sortie d'erreur en cas d'anomalie.|
| `reconfort_io.py` |Gère les E/S (charge les 4 fichiers d'entrée et génère la trace de sortie) ; sert de base minimale à compléter pour les validations. (base fournie)|
| `interface.py` |affichage pygame facultatif avec un 5ème argument (`--gui`)|
| `tests/` |Dossier contenant la suite de tests automatisés pour vérifier la robustesse et la conformité du projet.|

## État

### Ce qui fonctionne

* **Architecture globale et orchestration (`reconfort_io.py`, `agent.py`, `simulateur.py`) :**
  * Chargement conforme des 4 fichiers d'entrée.
  * Boucle de simulation principale.
  * Génération exacte de la trace de sortie et rendu graphique interactif en Pygame avec orientation dynamique du sprite.
* **Navigation et exploration locale :**
  * Découverte progressive de la carte par champ de vision restreint (brouillard de guerre) et construction continue d'une carte mentale.
  * Planification de chemin (BFS) sur les zones connues avec contournement des obstacles.
* **Résolution méthodique des requêtes :**
  * Enchaînement strict des sous-objectifs : `GO_DICO` $\rightarrow$ `VERIF_RESIDENT` $\rightarrow$ `GO_ARMOIRE` $\rightarrow$ `GO_RESIDENT`.
  * Analyse du message textuel par consultation du dictionnaire (priorité d'apparition des mots-clés).
  * Traitement séquentiel de plusieurs plaintes consécutives avec réinitialisation d'état.
* **Fouille de l'armoire (Roue des émotions de Plutchik) :**
  * Génération priorisée des casiers candidats (émotion exacte, voisins horaires/anti-horaires, intensités).
  * Navigation du sélecteur de casier avec bouclage circulaire horizontal ($7 \leftrightarrow 0$) et blocage vertical.
  * Mémorisation des casiers découverts vides pour éviter d'y réinsister.
* **Validation des données (Section 5.6) :**
  * Détection stricte des fichiers absents, illisibles, JSON invalides, incohérences de grille/symboles ou doublons.
  * Interruption propre sur `sys.stderr` avec un code de retour non nul.

---

### Ce qui ne fonctionne pas / Limites identifiées

* **Détours dus à l'hypothèse du chemin optimal :** le robot fonce vers les zones inconnues en partant du principes 
  qu'elles sont libres. Dans un appartement en impasses, il peut s'engager dans un couloir sans issue avant de faire demi-tour.
* **Coût de la vérification du résident :** Le robot est d'abord obligé de vérifier si le résident qui a fait la requêt est
  accéssible avant d'aller prendre l'objet dans l'armoire, puisque l'option redesposer un objet dans l'armoire n'existe pas. Ce problème ralonge le temps d'exécution et de résolution d'une demande fournit par un résident. 
* **Replanification réactive uniquement :**
  L'agent replanifie sa trajectoire uniquement lorsqu'il se heurte directement à un mur imprévu sur la case immédiatement suivante, plutôt que d'anticiper un contournement global dès qu'un obstacle obstrue son chemin théorique.
* **Interface graphique :** fermer la fenêtre **pendant** la simulation arrête le programme
  avant l'écriture de la trace.
* **Analyse du message rudimentaire :** seul le premier mot reconnu compte. 
  Les négations et les mots absents du dictionnaire ne sont pas compris.
* **Absence de re-consultation dynamique du dictionnaire :**
  Si aucun casier de l'armoire ne correspond aux candidats générés lors de la première lecture, l'agent abandonne la plainte au lieu de tenter de réanalyser le message ou d'étendre la recherche à des émotions de repli plus éloignées.
* **Tests du programme complet :** les tests de validation appellent directement les fonctions
  de lecture et de validation. Aucun test automatique ne lance `agent.py` en entier sur un
  fichier cassé.

Si vous avez l'occasion de remarquer des limites ou des disfonctionnement à notre projet, n'hésitez pas à nous en faire part. 

## Vidéo

`demo.mp4`, également déclarée dans `rendu.json`.