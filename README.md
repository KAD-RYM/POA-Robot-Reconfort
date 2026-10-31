# Robot de réconfort — HARAUT Kevin & KADDOUR Reyam

Projet de semestre, Master Informatique. Un robot à perception locale
reçoit un message d'un résident lui indiquant son état actuel.
Consulte un dictionnaire pour analyser le message reçu et en conclure 
une émotion et une intensité, puis fouille une armoire pour y récupérer 
l'objet adéquat parmi ceux disponibles, et le rapporte au résident.

Langage : Python — Version : 3.10 ou plus

## Lancer

```
python agent.py <carte.json> <scenario.json> <dossier_donnees> <trace_sortie.json>
```

Exemple :

```
python agent.py cartes/appartement_01.json cartes/scenario_01.json donnees sortie.json
```

Dépendances : aucune pour le programme. 
`pygame` seulement pour l'affichage graphique qui facultatif, s'intalle avec `pip install pygame`, puis ajouter `--gui` en 5e argument de lancement.

Exemple :

```
python agent.py cartes/appartement_01.json cartes/scenario_01.json donnees sortie.json --gui
```

## Tester

```
python3 -m unittest discover tests
```

Les tests couvrent la planification (BFS, longueur connue), la replanification
après découverte d'un mur, la lecture du dictionnaire (une émotion chacune,
premier mot gagnant, aucun mot), le sélecteur et le bouclage 7↔0, les quatre
cas de repli, la validation (un fichier cassé par catégorie) et le résident
inaccessible.


Le projet intègre une suite de tests automatisés basée sur le module standard `unittest`. Elle permet de vérifier la robustesse de l'agent, le bon fonctionnement de la simulation et la conformité stricte aux exigences de validation des entrées (Section 5.6).

### Exécution des tests

Pour lancer l'intégralité des tests automatisés, exécutez la commande suivante depuis la racine du projet :


python3 -m unittest discover tests

### Structure et couverture de la suite de tests

Les tests sont répartis dans trois modules complémentaires au sein du dossier `tests/` :

#### 1. Mécaniques et Décisions de l'Agent (`tests/test_agent.py`)

* **Analyse de la plainte (Dictionnaire) :**
  * **Mot clé unique :** Détection exacte de l'émotion et de l'intensité associées.
  * **Mots multiples :** Prise en compte du premier mot reconnu dans la phrase (priorité d'apparition).
  * **Absence de mot :** Gestion du cas où aucun mot n'est présent dans le dictionnaire (retourne `None`).
* **Perception & Carte mentale :**
  * Mise à jour et mémorisation dynamique des cases observées dans le champ de vision local.
  * Rétention de la carte mentale après chaque déplacement (persistance des obstacles connus).
* **Gestion des objectifs & Priorités :**
  * Respect de l'ordre strict des sous-objectifs : `GO_DICO` $\rightarrow$ `VERIF_RESIDENT` $\rightarrow$ `GO_ARMOIRE` $\rightarrow$ `GO_RESIDENT`.
  * Enchaînement et réinitialisation de l'état interne lors du traitement successif de plusieurs plaintes.
* **Fouille de l'Armoire & Physique :**
  * **Roue des émotions de Plutchik :** Tri des candidats selon la distance émotionnelle et l'intensité.
  * **Sélecteur de casiers :** Vérification du bouclage circulaire horizontal (colonnes $7 \leftrightarrow 0$) et du blocage vertical sur les bordures (lignes $0$ et $2$).
  * **Mémoire de l'armoire :** Enregistrement des casiers vides pour éviter d'y retourner et basculement vers le candidat suivant.

#### 2. Tests d'Intégration & Simulation (`tests/test_simulation.py`)

* **Scénario complet autonome :** Validation bout-en-bout d'une résolution de requête (réception du message, consultation du dictionnaire, vérification du résident, fouille de l'armoire, récupération de l'objet et livraison au résident en moins de 20 tours).
* **Replanification dynamique :** Déplacement et contournement automatique lorsque le chemin prévu est bloqué par un mur découvert en cours de route.
* **Gestion des échecs :** Abandon propre de la mission lorsque le résident est physiquement inaccessible.

#### 3. Validation des Fichiers d'Entrée (`tests/test_validation.py`)

Vérification que toute donnée corrompue provoque une interruption propre (`sys.exit` avec code non nul) et l'affichage d'un message explicatif sur `sys.stderr` (exigences de la section 5.6) :

* **Carte :** Champ obligatoire manquant, grille non rectangulaire, coordonnées hors limites, incohérence entre le symbole de la grille et la position déclarée, ou identifiants de résidents en double.
* **Scénario :** Incohérence entre la carte ciblée et la carte fournie, ou demande adressée à un résident inexistant.
* **Armoire :** Coordonnées de casier hors dimensions ou incohérence des étiquettes émotion/intensité.
* **Dictionnaire :** Présence d'un même mot dans deux entrées différentes ou émotions/intensités inconnues.


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

* **Gestion du résident inaccessible avec un objet en main :**
  Comme l'agent ne vérifie pas l'accessibilité du résident *avant* d'aller à l'armoire, il récupère l'objet en premier. Si le chemin vers le résident se retrouve bloqué par des murs (inaccessible), le robot se retrouve bloqué avec l'objet en main et doit abandonner la livraison après coup.
* **Replanification réactive uniquement :**
  L'agent replanifie sa trajectoire uniquement lorsqu'il se heurte directement à un mur imprévu sur la case immédiatement suivante, plutôt que d'anticiper un contournement global dès qu'un obstacle obstrue son chemin théorique.
* **Optimisation de la trajectoire du sélecteur d'armoire :**
  Le sélecteur d'armoire parcourt la grille de manière linéaire/séquentielle vers les casiers candidats. Il ne calcule pas le chemin physique le plus court (ex: utilisation optimale du bouclage circulaire $7 \leftrightarrow 0$) pour basculer d'un casier à un autre.
* **Absence de re-consultation dynamique du dictionnaire :**
  Si aucun casier de l'armoire ne correspond aux candidats générés lors de la première lecture, l'agent abandonne la plainte au lieu de tenter de réanalyser le message ou d'étendre la recherche à des émotions de repli plus éloignées.

## Vidéo

`demo.mp4`, également déclarée dans `rendu.json`.