"""
Logique de tri du robot SCARA.
Définit les zones de dépôt, les stratégies de tri et la séquence d'opérations.
"""

import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

from robot_controller import RobotController
from vision_sensor import VisionSensor, DetectedObject


@dataclass
class DropZone:
    """Zone de dépôt pour une catégorie d'objets."""
    name: str
    color: str
    position: Tuple[float, float, float]    # centre de la zone (m)
    capacity: int = 10
    count: int = 0
    offset_step: float = 0.06              # décalage entre objets posés

    def next_drop_position(self) -> Tuple[float, float, float]:
        """Calcule la prochaine position de dépôt (empilement en grille)."""
        row = self.count // 3
        col = self.count % 3
        x = self.position[0] + col * self.offset_step
        y = self.position[1] + row * self.offset_step
        z = self.position[2]
        return (x, y, z)

    def is_full(self) -> bool:
        return self.count >= self.capacity

    def register_drop(self) -> None:
        self.count += 1


@dataclass
class SortingStats:
    """Statistiques de la session de tri."""
    total_sorted: int = 0
    by_color: Dict[str, int] = field(default_factory=dict)
    failed_picks: int = 0
    start_time: float = field(default_factory=time.time)

    def record(self, color: str) -> None:
        self.total_sorted += 1
        self.by_color[color] = self.by_color.get(color, 0) + 1

    def record_failure(self) -> None:
        self.failed_picks += 1

    def elapsed(self) -> float:
        return time.time() - self.start_time

    def print_report(self) -> None:
        elapsed = self.elapsed()
        print("\n" + "=" * 50)
        print("       RAPPORT DE TRI")
        print("=" * 50)
        print(f"  Durée totale    : {elapsed:.1f} s")
        print(f"  Objets triés    : {self.total_sorted}")
        print(f"  Échecs de prise : {self.failed_picks}")
        print(f"  Détail par couleur : {self.by_color}")
        for color, count in self.by_color.items():
            print(f"    - {color:10s} : {count}")
        for color, count in sorted(self.by_color.items(), key=lambda x: -x[1]):
            pct = count / self.total_sorted * 100 if self.total_sorted > 0 else 0
            bar = "█" * count + "░" * max(0, 10 - count)
            print(f"    - {color:10s} : {count:3d} obj  [{bar}]  {pct:5.1f}%")
        if elapsed > 0:
            print(f"  Cadence         : {self.total_sorted / elapsed * 60:.1f} obj/min")
        print("=" * 50)


class SorterLogic:
    """
    Orchestrateur de la logique de tri.
    Coordonne le capteur de vision, le robot et les zones de dépôt.
    """

    def __init__(self, robot: RobotController, vision: VisionSensor):
        self.robot = robot
        self.vision = vision
        self.drop_zones: Dict[str, DropZone] = {}
        self.stats = SortingStats()
        self.running = False

        # Zone de détection des objets sur le convoyeur
        self.pickup_area: Optional[Tuple[float, float, float, float]] = None
        # Hauteur de saisie (z) des objets sur le convoyeur
        self.pickup_z: float = 0.02
        # Hauteur de transit entre pick et place
        self.transit_z: float = 0.20

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def setup_default_zones(self) -> None:
        """
        Configure les zones de dépôt par défaut.
        Adapte les coordonnées à votre scène CoppeliaSim.
        """
        zones = [
            DropZone(
                name="Zone Rouge",
                color="rouge",
                position=(0.40, 0.10, 0.0),
            ),
            DropZone(
                name="Zone Verte",
                color="vert",
                position=(0.40, -0.10, 0.0),
            ),
            DropZone(
                name="Zone Bleue",
                color="bleu",
                position=(0.15, -0.40, 0.0),
            ),
            DropZone(
                name="Zone Jaune",
                color="jaune",
                position=(-0.15, -0.40, 0.0),
            ),
            DropZone(
                name="Zone Inconnue",
                color="inconnu",
                position=(-0.40, 0.10, 0.0),
            ),
        ]
        for zone in zones:
            self.drop_zones[zone.color] = zone
            print(f"  [Zone] '{zone.name}' → {zone.position}")

    def add_drop_zone(self, zone: DropZone) -> None:
        """Ajoute ou remplace une zone de dépôt."""
        self.drop_zones[zone.color] = zone
        print(f"[SorterLogic] Zone '{zone.name}' ajoutée pour couleur '{zone.color}'.")

    def set_pickup_area(
        self,
        x_min: float, x_max: float,
        y_min: float, y_max: float,
        z: float = 0.02
    ) -> None:
        """Définit la zone de détection et de saisie des objets."""
        self.pickup_area = (x_min, x_max, y_min, y_max)
        self.pickup_z = z
        print(f"[SorterLogic] Zone de prise : x=[{x_min},{x_max}], y=[{y_min},{y_max}], z={z}")

    # ------------------------------------------------------------------
    # Boucle principale de tri
    # ------------------------------------------------------------------

    def run_sorting_cycle(self, max_objects: int = 0, timeout: float = 0.0) -> None:
        """
        Lance la boucle principale de tri.

        Args:
            max_objects : nombre max d'objets à trier (0 = infini)
            timeout     : durée max en secondes (0 = infini)
        """
        print("\n[SorterLogic] ═══ DÉMARRAGE DU TRI ═══")
        self.running = True
        self.stats = SortingStats()

        self.robot.go_home()
        time.sleep(0.5)

        while self.running:
            # Vérifications d'arrêt
            if max_objects > 0 and self.stats.total_sorted >= max_objects:
                print(f"\n[SorterLogic] Objectif atteint ({max_objects} objets).")
                break
            if timeout > 0 and self.stats.elapsed() >= timeout:
                print(f"\n[SorterLogic] Timeout atteint ({timeout:.0f}s).")
                break

            # Scan de la scène
            print("\n[SorterLogic] ── Scan de la scène...")
            objects = self.vision.detect_objects_by_color(self.pickup_area)
            self.vision.print_summary()

            if not objects:
                print("[SorterLogic] Aucun objet détecté. Attente...")
                time.sleep(1.0)
                continue

            # Trier par proximité du home pour optimiser les trajets
            objects.sort(key=lambda o: (o.position[0]**2 + o.position[1]**2)**0.5)

            for obj in objects:
                if not self.running:
                    break
                self._sort_one_object(obj)

        self.running = False
        self.robot.go_home()
        self.stats.print_report()

    def stop(self) -> None:
        """Arrête la boucle de tri proprement."""
        print("[SorterLogic] Arrêt demandé.")
        self.running = False

    # ------------------------------------------------------------------
    # Tri d'un objet
    # ------------------------------------------------------------------

    def _sort_one_object(self, obj: DetectedObject) -> bool:
        """
        Exécute la séquence pick & place pour un objet.

        Returns:
            True si le tri a réussi.
        """
        color = obj.color
        zone = self.drop_zones.get(color) or self.drop_zones.get("inconnu")

        if zone is None:
            print(f"[SorterLogic] Aucune zone pour '{color}'. Objet ignoré.")
            return False

        if zone.is_full():
            print(f"[SorterLogic] Zone '{zone.name}' pleine ! Objet ignoré.")
            return False

        x_obj, y_obj, _ = obj.position
        z_obj = self.pickup_z

        print(f"\n[SorterLogic] Tri objet {obj.obj_id} ({color}) → {zone.name}")
        print(f"  Source  : ({x_obj:.3f}, {y_obj:.3f}, {z_obj:.3f})")

        # === PICK ===
        success = self.robot.pick(x_obj, y_obj, z_obj)
        if not success:
            print(f"  [ÉCHEC] Prise impossible pour objet {obj.obj_id}.")
            self.stats.record_failure()
            return False

        # === TRANSIT en hauteur ===
        x_tip, y_tip, _ = self.robot.get_tip_position() or (x_obj, y_obj, self.transit_z)
        self.robot.move_to_cartesian(x_tip, y_tip, self.transit_z)

        # === PLACE ===
        drop_pos = zone.next_drop_position()
        print(f"  Dépôt   : ({drop_pos[0]:.3f}, {drop_pos[1]:.3f}, {drop_pos[2]:.3f})")
        self.robot.place(drop_pos[0], drop_pos[1], drop_pos[2])

        zone.register_drop()
        self.stats.record(color)

        print(f"  [OK] Objet {obj.obj_id} trié. Total : {self.stats.total_sorted}")
        return True

    # ------------------------------------------------------------------
    # Diagnostic
    # ------------------------------------------------------------------

    def print_zone_status(self) -> None:
        """Affiche l'état de remplissage de toutes les zones."""
        print("\n[Zones de dépôt]")
        for zone in self.drop_zones.values():
            bar = "█" * zone.count + "░" * (zone.capacity - zone.count)
            print(f"  {zone.name:15s} [{bar}] {zone.count}/{zone.capacity}")
