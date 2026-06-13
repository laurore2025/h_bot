"""
Point d'entrée principal du robot sorter CoppeliaSim.

Usage :
    python main.py [--host 127.0.0.1] [--port 23000] [--max 20] [--timeout 120]

Prérequis :
    pip install coppeliasim-zmqremoteapi-client
    CoppeliaSim ouvert avec la scène robot_sorter.ttt chargée et la simulation lancée.
"""

import argparse
import sys
import time

# -----Connexion à CoppeliaSim via l'API ZMQ
try:
    from coppeliasim_zmqremoteapi_client import RemoteAPIClient
except ImportError:
    print(
        "[ERREUR] Package manquant.\n"
        "  Installez-le avec : pip install coppeliasim-zmqremoteapi-client\n"
        "  Documentation     : https://github.com/CoppeliaRobotics/zmqRemoteApi"
    )
    sys.exit(1)

from robot_controller import RobotController
from vision_sensor import VisionSensor
from sorter_logic import SorterLogic, DropZone
from conveyor import Conveyor


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 23000

# Zone de saisie des objets sur le convoyeur (en mètres, repère base robot)
PICKUP_AREA = {
    "x_min": -0.10,
    "x_max":  0.10,
    "y_min":  0.20,
    "y_max":  0.45,
    "z":      0.02,   # hauteur des objets sur le convoyeur
}

# Zones de dépôt par couleur — positions (x, y, z) en mètres
DROP_ZONES_CONFIG = [
    {"name": "Zone Rouge",    "color": "rouge",   "position": ( 0.40,  0.10, 0.0)},
    {"name": "Zone Verte",    "color": "vert",    "position": ( 0.40, -0.10, 0.0)},
    {"name": "Zone Bleue",    "color": "bleu",    "position": ( 0.15, -0.40, 0.0)},
    {"name": "Zone Jaune",    "color": "jaune",   "position": (-0.15, -0.40, 0.0)},
    {"name": "Zone Inconnue", "color": "inconnu", "position": (-0.40,  0.10, 0.0)},
]


# ─────────────────────────────────────────────────────────────────────────────
# Fonctions
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Robot SCARA Sorter — CoppeliaSim")
    parser.add_argument("--host",    default=DEFAULT_HOST, help="IP de CoppeliaSim")
    parser.add_argument("--port",    default=DEFAULT_PORT, type=int, help="Port ZMQ")
    parser.add_argument("--max",     default=0,  type=int,   help="Nombre max d'objets (0=infini)")
    parser.add_argument("--timeout", default=0,  type=float, help="Timeout en secondes (0=infini)")
    parser.add_argument("--speed",   default=0.5, type=float, help="Vitesse robot [0.0-1.0]")
    parser.add_argument("--conveyor-speed", default=0.05, type=float, help="Vitesse convoyeur m/s")
    return parser.parse_args()


def connect_to_coppelia(host: str, port: int):
    """Établit la connexion ZMQ avec CoppeliaSim."""
    print(f"\n[CoppeliaSim] Connexion à {host}:{port} ...")
    try:
        client = RemoteAPIClient(host=host, port=port)
        sim = client.require("sim")
        print("[CoppeliaSim] Connecté !")
        return client, sim
    except Exception as e:
        print(f"[ERREUR] Connexion impossible : {e}")
        print("  → Vérifiez que CoppeliaSim est ouvert et que la simulation est lancée.")
        sys.exit(1)


def wait_for_simulation(sim, timeout: float = 10.0) -> bool:
    """Attend que la simulation soit en cours d'exécution."""
    print("[CoppeliaSim] Attente de la simulation...")
    start = time.time()
    while time.time() - start < timeout:
        state = sim.getSimulationState()
        if state == sim.simulation_advancing_running:
            print("[CoppeliaSim] Simulation active.")
            return True
        time.sleep(0.2)
    print("[ERREUR] La simulation n'a pas démarré dans le délai imparti.")
    return False


def setup_system(sim, args) -> tuple:
    """Instancie et initialise tous les composants du système."""
    print("\n[Setup] ── Initialisation des composants ──")

    # Robot
    robot = RobotController(sim)
    if not robot.initialize():
        print("[ERREUR] Impossible d'initialiser le robot.")
        sys.exit(1)
    robot.set_speed(args.speed)

    # Capteur de vision
    vision = VisionSensor(sim, "/Vision_sensor")
    vision.initialize()  # non bloquant si absent

    # Convoyeur
    conveyor = Conveyor(sim, "/Conveyor")
    conveyor.initialize()

    # Logique de tri
    sorter = SorterLogic(robot, vision)
    sorter.set_pickup_area(**PICKUP_AREA)

    # Zones de dépôt
    for cfg in DROP_ZONES_CONFIG:
        sorter.add_drop_zone(
            DropZone(
                name=cfg["name"],
                color=cfg["color"],
                position=cfg["position"],
            )
        )

    print("\n[Setup] Système prêt.\n")
    return robot, vision, conveyor, sorter


# Main

def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("   ROBOT SCARA SORTER — CoppeliaSim")
    print("=" * 60)

    # 1. Connexion
    client, sim = connect_to_coppelia(args.host, args.port)

    # 2. Attendre que la simulation soit active
    if not wait_for_simulation(sim):
        sys.exit(1)

    # 3. Initialisation
    robot, vision, conveyor, sorter = setup_system(sim, args)

    # 4. Démarrage du convoyeur
    conveyor.start(speed=args.conveyor_speed)
    time.sleep(1.0)  # laisse les objets se stabiliser

    # 5. Boucle de tri
    try:
        sorter.run_sorting_cycle(
            max_objects=args.max,
            timeout=args.timeout,
        )
    except KeyboardInterrupt:
        print("\n[Main] Interruption clavier. Arrêt propre...")
        sorter.stop()
    finally:
        conveyor.stop()
        robot.go_home()
        print("\n[Main] Session terminée.")


if __name__ == "__main__":
    main()
