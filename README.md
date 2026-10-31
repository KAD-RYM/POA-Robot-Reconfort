# Robot de réconfort — HARAUT Kevin & KADDOUR Reyam

Projet de semestre, Master Informatique. Un robot qui n'a qu'une perception 
locale des quatre cases autour de lui (Nord, Sud, Ouest et Est)
reçoit un message d'un résident lui indiquant son état actuel.
Il consulte un dictionnaire pour analyser le message reçu et en conclure 
une émotion et une intensité, puis fouille une armoire pour y récupérer 
l'objet adéquat parmi ceux disponibles, et le rapporte au résident.

- **Langage :**  Python — Version : 3.10 ou plus
- **Dépendances :**  aucune pour le programme. 
`pygame` seulement pour l'affichage graphique, qui est facultatif. Il s'installe avec `pip install pygame`, puis il faut ajouter `--gui` en 5e argument de lancement.

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
Résultat attendu : `Ran 32 tests ... OK` (sans dépendance externe).

Les tests couvrent la planification (plus court chemin, longueur connue), la replanification
après découverte d'un mur, la lecture du dictionnaire (une émotion chacune,
premier mot gagnant, aucun mot), le sélecteur et le bouclage 7↔0, les quatre
cas de repli, la validation (un fichier cassé par catégorie) et le résident
inaccessible.


Le projet intègre une suite de tests automatisés basée sur le module standard `unittest`. Elle permet de vérifier la robustesse de l'agent, le bon fonctionnement de la simulation et la conformité stricte aux exigences de validation des entrées (Section 5.6).

Les tests sont répartis en trois modules :

| Fichier | Tests | Ce qui est vérifié |
|---|---|---|
| `tests/test_agent.py` | 17 | dictionnaire, carte mentale, ordre des sous-objectifs, perception, planification, armoire, règle de repli |
| `tests/test_simulation.py` | 3 | scénario complet, résident muré (petite grille et grande pièce ouverte) |
| `tests/test_validation.py` | 12 | un fichier invalide par catégorie (section 5.6) |

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

### 2. Navigation (`tests/test_agent.py` et `tests/test_simulation.py`)

- **Planification :** sur la grille de l'annexe B, chemin de longueur connue (6 pas).
- **Replanification :** un mur découvert sur le trajet prévu donne un contournement.
- **Résident inaccessible :** résident muré → échec `resident inaccessible`, prouvé
  **avant** l'armoire : aucun `PRENDRE`, aucun `DONNER`.

### 3. Simulation (`tests/test_simulation.py`)

- **Scénario complet :** message → dictionnaire → vérification du résident → armoire →
  livraison, en un nombre de tours borné.
- **Résident muré dans une grande pièce :** résident enfermé au milieu d'une pièce ouverte →
  le robot abandonne en moins de 200 tours (BFS borné à la grille).

### 4. Validation (`tests/test_validation.py`)

Chaque fichier invalide doit provoquer un arrêt propre (code non nul et message sur
`stderr`), et le test vérifie que c'est **la bonne erreur** qui est signalée :

- **Lecture :** fichier absent, JSON invalide, mauvaise `version`.
- **Carte :** champ manquant ou de mauvais type, grille non rectangulaire, position hors
  grille, symbole incohérent avec la position déclarée, identifiant de résident en double.
- **Scénario :** scénario prévu pour une autre carte.
- **Armoire :** casier hors dimensions, `casier_depart` hors de l'armoire.
- **Dictionnaire :** mot présent dans deux entrées.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `agent.py` | Contient le comportement de l'agent (perception locale, carte mentale, prise de décision) et orchestre l'exécution dans la boucle principale (main).|
| `simulateur.py` |Modélise l'environnement global : gère la grille, le contenu des conteneurs et traite les actions de l'agent en lui envoyant ses perceptions locales.|
| `validation.py` |Contrôle la conformité des fichiers d'entrée (JSON, grille, objets) selon la section 5.6 et interrompt proprement le programme avec un message sur la sortie d'erreur en cas d'anomalie.|
| `reconfort_io.py` |Gère les E/S (charge les 4 fichiers d'entrée et génère la trace de sortie). (base fournie)|
| `interface.py` | Affichage pygame facultatif avec un 5ème argument (`--gui`).|
| `tests/` |Dossier contenant la suite de tests automatisés pour vérifier la robustesse et la conformité du projet.|

## État

### Ce qui fonctionne

* **Architecture globale et orchestration (`reconfort_io.py`, `agent.py`, `simulateur.py`) :**
  * Chargement conforme des 4 fichiers d'entrée.
  * Boucle de simulation principale.
  * Génération exacte de la trace de sortie et affichage graphique facultatif en Pygame (le robot est représenté par un chat).
* **Navigation et exploration locale :**
  * Découverte progressive de la carte par champ de vision restreint (brouillard de guerre) et construction continue d'une carte mentale.
  * Planification de chemin (BFS) sur la carte mentale, limitée aux dimensions de la grille, avec contournement des obstacles.
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

* **Détours dus à l'hypothèse optimiste :** le robot fonce vers les zones inconnues en partant du principe 
  qu'elles sont libres. Dans un appartement en impasses, il peut s'engager dans un couloir sans issue avant de faire demi-tour.
* **Coût de la vérification du résident :** Le robot est d'abord obligé de vérifier si le résident qui a fait la requête est
  accessible avant d'aller prendre l'objet dans l'armoire, puisque l'option redéposer un objet dans l'armoire n'existe pas. Ce problème rallonge le temps d'exécution et de résolution d'une demande par un résident. 
* **Replanification complète :**
  Quand la prochaine case du chemin se révèle être un mur, le BFS est relancé entièrement au lieu de réparer le plan localement : simple et sûr, mais plus de calcul sur une grande carte.
* **Analyse du message rudimentaire :** seul le premier mot reconnu compte. 
  Les négations et les mots absents du dictionnaire ne sont pas compris.
* **Tests du programme complet :** les tests de validation appellent directement les fonctions
  de lecture et de validation. Aucun test automatique ne lance `agent.py` en entier sur un
  fichier cassé.

## Vidéo

`demo.mp4`, également déclarée dans `rendu.json`.