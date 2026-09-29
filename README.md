# Base fournie : projet « Robot de réconfort »

Ce dossier contient le strict minimum pour démarrer : de quoi **lire les
entrées** et **écrire la sortie**. Tout le reste (perception, carte mentale,
planification, consultation du dictionnaire, fouille de l'armoire, boucle de
décision) est le sujet du projet.

## Contenu

```
reconfort_io.py                 lecture des 4 fichiers, écriture de la trace
demo.py                         exemple d'utilisation ; ne résout rien
rendu.json                      modèle à compléter (noms, commande, vidéo)
MODELE_README.md                squelette du README de votre dépôt
donnees/dictionnaire.json       250 formes -> (émotion, intensité)
donnees/armoire_standard.json   24 casiers : 8 émotions x 3 intensités
cartes/appartement_01..05.json  cinq appartements
cartes/scenario_01..05.json     le scénario associé à chacun
```

## Démarrer

```
cd base_fournie
python demo.py cartes/appartement_01.json cartes/scenario_01.json donnees sortie.json
```

La démo charge les quatre fichiers, affiche un résumé, découpe chaque
message en mots, et écrit une trace où toutes les demandes échouent. C'est
le squelette : à vous de le remplir.

Les quatre arguments sont exactement ceux du contrat d'appel de l'énoncé
(section 2) : carte, scénario, dossier de données, trace à écrire. Votre
programme devra les accepter dans le même ordre, et vous déclarerez la
commande qui le lance dans `rendu.json`.

## Ce que `reconfort_io.py` fait, et ne fait pas

**Fait** : ouvrir les fichiers, signaler proprement un fichier absent, mal
encodé ou syntaxiquement invalide, vérifier les champs `format` et
`version`, accumuler les pas et les livraisons, écrire la trace au bon
format.

**Ne fait pas** : toutes les autres validations de la section 5.6 de
l'énoncé (grille rectangulaire, positions dans les bornes, résident sur un
mur, casier hors de l'armoire, résident inconnu…). Elles sont notées, et
elles sont à vous.

Ne contient évidemment ni `plus_court_chemin`, ni `lire_emotion`, ni
`choisir_casier`. Ne les cherchez pas.

## Cinq cartes, ce n'est pas assez

La correction utilise en plus des jeux que vous n'avez pas. Fabriquez-vous
d'autres cartes : c'est un exercice utile en soi, et c'est le seul moyen de
savoir si votre robot marche vraiment.

## Deux rappels

Votre agent n'a le droit de lire ni le champ `grille` de la carte, ni le
champ `objet` des casiers. Il découvre les murs case par case à travers ses
perceptions, et le contenu des casiers en se plaçant devant. Voir les
sections 3.2 et 3.3 de l'énoncé : c'est vérifié à la correction.

Si l'algorithmique des graphes ne vous est pas familière, lisez l'annexe B
de l'énoncé avant d'écrire quoi que ce soit : elle contient tout le
nécessaire.