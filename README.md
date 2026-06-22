# Projet RobotSorter
## Groupe H_bot (Groupe 6)

## Membres du groupe
- **Nicodem Laurore** 
Developpeur Web | Entrepreneur

- **Nicolas Christian Toussaint** 

## Description du projet
RoboSorter est une simulation robotique développée sous CoppeliaSim permettant de trier automatiquement des objets selon leur couleur à l'aide d'un bras robotique articulé. Un capteur de vision détecte les objets rouges, verts et bleus circulant sur un convoyeur puis transmet les informations au système de contrôle. Le bras robotique saisit ensuite chaque objet et le dépose dans le bac correspondant grâce à la cinématique inverse et à une logique de décision automatisée.

## Lien GitHub 
link ==> [Repository project](https://github.com/laurore2025/h_bot)

## Scène CoppeliaSim
--  [robotsorterxian.ttt](https://github.com/laurore2025/h_bot/blob/main/robotsorterxian.ttt)


## Capture / Vidéo de la simulation

[lien ](https://go.screenpal.com/watch/cO13ofnusmA)

## Composants / Modèles 3D utilisés

#### 1) Robot manipulateur
UR5
Alias : /UR5
Type : shape (compound)
Rôle dans le projet : bras robotique principal chargé de saisir les objets sur le convoyeur puis de les déposer dans les bacs selon leur couleur.

#### 2) Préhenseur / pince
RG2
Alias : /UR5/RG2
Type : shape (cuboid) affiché dans la sélection, mais fonctionnellement il s’agit du gripper monté au bout du robot
Rôle : ouvrir/fermer pour attraper puis relâcher les cubes.

#### 3) Convoyeur
Conveyor
Alias : /conveyor
Type : dummy dans votre capture
Rôle : support logique/repère du convoyeur qui transporte les cubes vers la zone de prise.

#### 4) Objets à trier
cube_bleu
Alias : /cube_bleu
Type : shape (cuboid)
Position visible : x 0.000 ; y 0.450 ; z 0.250
cube_vert
Alias : /cube_vert
Type : shape (cuboid)
Position visible : x -0.200 ; y 0.450 ; z 0.250
cube_rouge
Alias : /cube_rouge
Type : shape (cuboid)
Position visible : x -0.400 ; y 0.450 ; z 0.250

Rôle global des cubes : objets manipulés et triés par couleur.

#### 5) Bacs de tri
bac_bleu
Alias : /bac_bleu
Type : shape (cuboid)
Position visible : x 0.300 ; y -0.450 ; z 0.025
bac_vert
Alias : /bac_vert
Type : shape (cuboid)
Position visible : x 0.000 ; y -0.450 ; z 0.025
bac_rouge
Alias : /bac_rouge
Type : shape (cuboid)
Position visible : x -0.300 ; y -0.450 ; z 0.025

##### Rôle global des bacs : zones de dépôt finales pour le tri.

## Répartition du travail
- **Nicodem Laurore** | Chef d'équipe | Gestion du repository, la documentation du projet, Montage de la video et participation dans la programmation. 

- **Nicolas Christian Toussaint** | Vision et ui | Programmation de la caméra pour la détection des couleurs et configuration du tableau de bord (UI) pour le comptage des objets.

## Tests réalisés

## Améliorations possibles
## Difficultés rencontrées
