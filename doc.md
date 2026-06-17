Robot SCARA Sorter — CoppeliaSim
Robot trieur SCARA 6 axes piloté en Python via l'API ZMQ de CoppeliaSim.

Architecture du projet
robot_sorter/
├── src/
│   ├── main.py              # Point d'entrée — lance le tri
│   ├── robot_controller.py  # Contrôle des joints, IK, pick & place
│   ├── vision_sensor.py     # Détection et classification des objets
│   ├── sorter_logic.py      # Orchestration du tri et zones de dépôt
│   └── conveyor.py          # Contrôle du convoyeur
├── scene/
│   ├── build_scene.py         # Constructeur automatique de la scène .ttt
│   ├── spawn_objects.py       # Spawner d'objets colorés sur le convoyeur
│   └── robot_sorter_init.lua  # Script Lua embarqué dans la scène
└── requirements.txt

Installation
pip install -r requirements.txt

Démarrage rapide — Construction automatique de la scène
C'est la méthode recommandée : elle génère le fichier .ttt complet automatiquement.

# 1. Ouvrez CoppeliaSim (simulation ARRÊTÉE ■)
# 2. Construisez la scène depuis Python :
cd robot_sorter/scene
python build_scene.py --out robot_sorter.ttt
# 3. Ouvrez robot_sorter.ttt dans CoppeliaSim, puis lancez la simulation (▶)
# 4. Dans un autre terminal, spawnez des objets :
python spawn_objects.py --count 15 --interval 2.5
# 5. Dans un autre terminal, lancez le tri :
cd ../src
python main.py

Options de build_scene.py
Option	Défaut	Description
--host	127.0.0.1	IP de CoppeliaSim
--port	23000	Port ZMQ
--out	robot_sorter.ttt	Nom du fichier de scène généré
Options de spawn_objects.py
Option	Défaut	Description
--count	10	Nombre d'objets à créer
--interval	2.5	Délai entre chaque spawn (s)
--colors	toutes	rouge vert bleu jaune
--shapes	toutes	cube sphere cylindre
--loop	off	Spawn en continu jusqu'à Ctrl+C
--loop-interval	3.0	Délai entre spawns en mode boucle (s)
Exemples :

# Seulement des cubes rouges et bleus, toutes les 3 secondes en boucle
python spawn_objects.py --colors rouge bleu --shapes cube --loop --loop-interval 3
# Séquence fixe de 5 objets
python spawn_objects.py --count 5 --colors rouge vert bleu jaune rouge

Prérequis CoppeliaSim (méthode manuelle)
Si vous préférez utiliser votre propre scène .ttt existante :

Ouvrez CoppeliaSim (version ≥ 4.6)
Chargez votre scène contenant le robot SCARA
Attachez scene/robot_sorter_init.lua comme child script non-threadé sur SCARA_base
Lancez la simulation (▶)
Noms d'objets attendus dans la scène
Objet dans la scène	Rôle
SCARA_joint1 … SCARA_joint6	6 axes du robot
SCARA_gripper	Joint du gripper
SCARA_tip	Dummy à l'extrémité outil
SCARA_base	Base du robot
Vision_sensor	Capteur de vision overhead
Conveyor	Convoyeur (body)
Conveyor/motor	Joint moteur du convoyeur
Adaptez les noms dans robot_controller.py (JOINT_NAMES) et main.py si votre scène utilise d'autres identifiants.

Lancement
cd robot_sorter/src
# Tri infini jusqu'à Ctrl+C
python main.py
# Trier 20 objets maximum
python main.py --max 20
# Timeout de 2 minutes, vitesse robot à 80%
python main.py --timeout 120 --speed 0.8
# CoppeliaSim sur une autre machine
python main.py --host 192.168.1.10 --port 23000

Options disponibles
Option	Défaut	Description
--host	127.0.0.1	IP de la machine CoppeliaSim
--port	23000	Port ZMQ
--max	0 (infini)	Nombre max d'objets à trier
--timeout	0 (infini)	Durée max de la session (secondes)
--speed	0.5	Vitesse robot [0.0 – 1.0]
--conveyor-speed	0.05	Vitesse du convoyeur (m/s)
Zones de dépôt (configuration)
Éditez main.py → DROP_ZONES_CONFIG pour ajuster les positions :

DROP_ZONES_CONFIG = [
    {"name": "Zone Rouge",  "color": "rouge", "position": (0.40,  0.10, 0.0)},
    {"name": "Zone Verte",  "color": "vert",  "position": (0.40, -0.10, 0.0)},
    {"name": "Zone Bleue",  "color": "bleu",  "position": (0.15, -0.40, 0.0)},
    {"name": "Zone Jaune",  "color": "jaune", "position": (-0.15,-0.40, 0.0)},
]

Séquence de tri (pour chaque objet)
1. Scan vision → détection couleur + position 3D
2. Approche haute (z + 8 cm) au-dessus de l'objet
3. Descente sur l'objet
4. Fermeture gripper
5. Soulèvement
6. Transit vers la zone de dépôt
7. Descente au point de dépôt
8. Ouverture gripper
9. Remontée
10. Retour HOME ou objet suivant

Adaptation des paramètres DH (cinématique inverse)
Dans robot_controller.py, modifiez L1 et L2 selon les dimensions réelles de vos bras :

L1 = 0.35  # longueur bras 1 (m)
L2 = 0.25  # longueur bras 2 (m)

Ajout d'une nouvelle couleur
# Dans votre code ou dans main.py, avant de lancer le tri :
vision.add_color_threshold(
    name="orange",
    r_min=0.8, r_max=1.0,
    g_min=0.3, g_max=0.6,
    b_min=0.0, b_max=0.1,
)
sorter.add_drop_zone(DropZone(
    name="Zone Orange",
    color="orange",
    position=(0.0, -0.45, 0.0),
))
