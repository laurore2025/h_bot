# Projet RobotSorter
## Groupe H_bot (Groupe 6)

## Membres du groupe
- **Nicodem Laurore** 
Developpeur Web | Entrepreneur

- **Nicolas Christian Toussaint** 

- **Lovensky Désir**

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
- **Nicodem Laurore** | Chef d'équipe | Gestion du repository, la documentation du projet, Montage de la video et participation dans la programmation langage LUA. 

- **Nicolas Christian Toussaint** | Vision et ui | Programmation de la caméra pour la détection des couleurs et configuration du tableau de bord (UI) pour le comptage des objets.


- **Lovensky Désir** | Lovensky Désir | Conception de la scène 3D : intégration du bras robotique, des cubes à trier et du tapis roulant dans CoppeliaSim |


## Tests réalisés

## Améliorations possibles
Dans une perspective d’amélioration, le projet RoboSorter pourrait être enrichi en automatisant le tri successif de plusieurs objets dans une même exécution, afin de démontrer un cycle complet de fonctionnement sans intervention manuelle. Il serait également pertinent d’ajouter un retour systématique du bras robotique en position HOME après chaque dépôt, ainsi qu’une meilleure synchronisation entre le convoyeur et le robot, par exemple en arrêtant automatiquement le tapis lorsqu’un objet entre dans la zone de détection. Enfin, l’interface pourrait être améliorée par l’affichage de l’état du robot en temps réel (détection, prise, dépôt, retour), du nombre total d’objets triés et, à plus long terme, par l’intégration d’une génération automatique de cubes et d’indicateurs de performance pour rapprocher davantage la simulation d’un système industriel réel.
## Difficultés rencontrées
Durant la réalisation du projet, l’une des principales difficultés rencontrées a concerné la programmation en Lua dans CoppeliaSim. Bien que la logique générale du tri ait été définie et que les instructions nécessaires aient été écrites, leur exécution ne produisait pas toujours le comportement attendu dans la simulation. Nous avons notamment rencontré des difficultés liées à la synchronisation entre le convoyeur, la détection de couleur et les mouvements du bras robotique, ainsi qu’à l’exécution correcte de certaines commandes de prise et de dépôt. Ces contraintes nous ont amenés à effectuer plusieurs ajustements, tests et corrections afin d’améliorer progressivement la cohérence du fonctionnement global du système.
