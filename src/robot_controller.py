"""
Contrôleur du robot SCARA 6 axes dans CoppeliaSim
Gère les mouvements articulaires, la cinématique et le gripper
"""

import math
import time
from typing import List, Tuple, Optional


class RobotController:
    """
    Contrôleur haut niveau pour le robot SCARA 6 axes.
    Utilise l'API ZMQ de CoppeliaSim.
    """

    # Noms des joints dans la scène CoppeliaSim
    JOINT_NAMES = [
        "SCARA_joint1",
        "SCARA_joint2",
        "SCARA_joint3",
        "SCARA_joint4",
        "SCARA_joint5",
        "SCARA_joint6",
    ]

    # Limites articulaires [min_rad, max_rad]
    JOINT_LIMITS = [
        (-math.pi, math.pi),        # J1 : rotation base
        (-math.pi / 2, math.pi / 2), # J2 : épaule
        (-math.pi, math.pi),        # J3 : coude
        (-math.pi, math.pi),        # J4 : poignet 1
        (-math.pi / 2, math.pi / 2), # J5 : poignet 2
        (-math.pi, math.pi),        # J6 : rotation outil
    ]

    # Position de repos (home) en radians
    HOME_POSITION = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def __init__(self, sim, sim_client=None):
        """
        Initialise le contrôleur.

        Args:
            sim       : handle vers l'objet sim de l'API ZMQ CoppeliaSim
            sim_client: client ZMQ (pour le mode RemoteAPI)
        """
        self.sim = sim
        self.sim_client = sim_client
        self.joint_handles: List[int] = []
        self.gripper_handle: Optional[int] = None
        self.tip_handle: Optional[int] = None
        self.base_handle: Optional[int] = None

        self._speed = 0.5       # vitesse normalisée (0-1)
        self._accel = 0.3       # accélération normalisée (0-1)
        self._step_delay = 0.05  # délai entre chaque pas de simulation (s)

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """
        Récupère les handles de tous les joints et du gripper depuis la scène.

        Returns:
            True si tous les handles ont été trouvés.
        """
        try:
            # Joints
            for name in self.JOINT_NAMES:
                h = self.sim.getObject(f"/{name}")
                self.joint_handles.append(h)
                print(f"  [OK] Joint '{name}' → handle {h}")

            # Effecteur / tip
            try:
                self.tip_handle = self.sim.getObject("/SCARA_tip")
                print(f"  [OK] Tip → handle {self.tip_handle}")
            except Exception:
                print("  [WARN] Tip '/SCARA_tip' introuvable.")

            # Base du robot
            try:
                self.base_handle = self.sim.getObject("/SCARA_base")
                print(f"  [OK] Base → handle {self.base_handle}")
            except Exception:
                print("  [WARN] Base '/SCARA_base' introuvable.")

            # Gripper
            try:
                self.gripper_handle = self.sim.getObject("/SCARA_gripper")
                print(f"  [OK] Gripper → handle {self.gripper_handle}")
            except Exception:
                print("  [WARN] Gripper '/SCARA_gripper' introuvable.")

            print(f"\n[RobotController] {len(self.joint_handles)} joints initialisés.")
            return len(self.joint_handles) == 6

        except Exception as e:
            print(f"[ERREUR] Initialisation robot : {e}")
            return False

    # ------------------------------------------------------------------
    # Contrôle des joints
    # ------------------------------------------------------------------

    def set_joint_position(self, joint_index: int, angle_rad: float) -> None:
        """Positionne un joint à l'angle voulu (en radians)."""
        angle_rad = self._clamp_joint(joint_index, angle_rad)
        self.sim.setJointTargetPosition(self.joint_handles[joint_index], angle_rad)

    def get_joint_position(self, joint_index: int) -> float:
        """Retourne la position actuelle d'un joint en radians."""
        return self.sim.getJointPosition(self.joint_handles[joint_index])

    def get_all_joint_positions(self) -> List[float]:
        """Retourne la liste des positions de tous les joints."""
        return [self.get_joint_position(i) for i in range(6)]

    def move_to_joint_config(
        self,
        target_angles: List[float],
        steps: int = 50,
        wait: bool = True
    ) -> None:
        """
        Mouvement interpolé vers une configuration articulaire cible.

        Args:
            target_angles : liste de 6 angles cibles en radians
            steps         : nombre de pas d'interpolation
            wait          : attendre la fin du mouvement
        """
        if len(target_angles) != 6:
            raise ValueError("Il faut exactement 6 angles cibles.")

        current = self.get_all_joint_positions()
        for step in range(1, steps + 1):
            t = step / steps
            # Interpolation linéaire
            interp = [
                current[i] + t * (target_angles[i] - current[i])
                for i in range(6)
            ]
            for i, angle in enumerate(interp):
                self.set_joint_position(i, angle)
            if wait:
                self.sim.step()
                time.sleep(self._step_delay)

    def go_home(self) -> None:
        """Envoie le robot en position home."""
        print("[Robot] → Position HOME")
        self.move_to_joint_config(self.HOME_POSITION, steps=80)

    # ------------------------------------------------------------------
    # Contrôle du gripper
    # ------------------------------------------------------------------

    def open_gripper(self) -> None:
        """Ouvre le gripper."""
        if self.gripper_handle is not None:
            self.sim.setJointTargetPosition(self.gripper_handle, 0.04)
            print("[Gripper] Ouvert")
        self._wait_sim_steps(10)

    def close_gripper(self) -> None:
        """Ferme le gripper (saisie d'un objet)."""
        if self.gripper_handle is not None:
            self.sim.setJointTargetPosition(self.gripper_handle, 0.0)
            print("[Gripper] Fermé")
        self._wait_sim_steps(10)

    # ------------------------------------------------------------------
    # Mouvements cartésiens (IK simplifié SCARA)
    # ------------------------------------------------------------------

    def move_to_cartesian(
        self,
        x: float,
        y: float,
        z: float,
        yaw: float = 0.0,
        steps: int = 60,
    ) -> bool:
        """
        Déplace le robot vers une position cartésienne (x, y, z) en mètres.
        Utilise la cinématique inverse analytique simplifiée du SCARA.

        Pour un robot SCARA avec 4 DDL planaires + 2 DDL de poignet.

        Args:
            x, y, z : position cible dans le repère de la base (m)
            yaw     : orientation outil autour de Z (rad)
            steps   : nombre de pas d'interpolation

        Returns:
            True si la position est atteignable.
        """
        # Paramètres DH du SCARA (à adapter à votre modèle)
        L1 = 0.35  # longueur lien 1 (m)
        L2 = 0.25  # longueur lien 2 (m)

        # IK planaire (J1, J2)
        r = math.sqrt(x**2 + y**2)
        if r > L1 + L2 or r < abs(L1 - L2):
            print(f"[IK] Position ({x:.3f}, {y:.3f}, {z:.3f}) hors portée !")
            return False

        cos_q2 = (r**2 - L1**2 - L2**2) / (2 * L1 * L2)
        cos_q2 = max(-1.0, min(1.0, cos_q2))
        q2 = -math.acos(cos_q2)  # coude bas (configuration standard)

        k1 = L1 + L2 * math.cos(q2)
        k2 = L2 * math.sin(q2)
        q1 = math.atan2(y, x) - math.atan2(k2, k1)

        # J3 : translation verticale (prismatique ou rotatif selon modèle)
        q3 = -z  # adapter selon votre configuration

        # J4-J5-J6 : orientation poignet
        q4 = 0.0
        q5 = 0.0
        q6 = yaw - q1 - q2  # maintien de l'orientation outil

        self.move_to_joint_config([q1, q2, q3, q4, q5, q6], steps=steps)
        return True

    # ------------------------------------------------------------------
    # Opérations de pick & place
    # ------------------------------------------------------------------

    def pick(self, x: float, y: float, z: float, approach_height: float = 0.08) -> bool:
        """
        Séquence complète de saisie d'un objet.

        Args:
            x, y, z        : position de l'objet
            approach_height: hauteur d'approche au-dessus de l'objet
        """
        print(f"[Pick] Approche ({x:.3f}, {y:.3f}, {z + approach_height:.3f})")
        self.open_gripper()

        # 1. Approche haute
        ok = self.move_to_cartesian(x, y, z + approach_height)
        if not ok:
            return False

        # 2. Descente sur l'objet
        print(f"[Pick] Descente sur ({x:.3f}, {y:.3f}, {z:.3f})")
        self.move_to_cartesian(x, y, z, steps=30)

        # 3. Fermeture gripper
        self.close_gripper()
        self._wait_sim_steps(15)

        # 4. Montée avec l'objet
         
        # 4. Montée avec l'objet
        print("[Pick] Soulèvement")
        self.move_to_cartesian(x, y, z + approach_height)
        # 4. Montée avec l'objet (retour à la hauteur d'approche, même X/Y)
        z_lift = z + approach_height
        print(f"[Pick] Soulèvement → ({x:.3f}, {y:.3f}, {z_lift:.3f})")
        self.move_to_cartesian(x, y, z_lift)
        return True

    def place(self, x: float, y: float, z: float, approach_height: float = 0.08) -> None:
        """
        Séquence complète de dépôt d'un objet.

        Args:
            x, y, z        : position de dépôt
            approach_height: hauteur d'approche
        """
        print(f"[Place] Vers ({x:.3f}, {y:.3f}, {z + approach_height:.3f})")

        # 1. Approche
        self.move_to_cartesian(x, y, z + approach_height)

        # 2. Descente
        print(f"[Place] Dépôt en ({x:.3f}, {y:.3f}, {z:.3f})")
        self.move_to_cartesian(x, y, z, steps=30)

        # 3. Ouverture gripper
        self.open_gripper()
        self._wait_sim_steps(15)

        # 4. Retrait
        self.move_to_cartesian(x, y, z + approach_height)

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    def _clamp_joint(self, index: int, angle: float) -> float:
        lo, hi = self.JOINT_LIMITS[index]
        return max(lo, min(hi, angle))

    def _wait_sim_steps(self, n: int) -> None:
        for _ in range(n):
            self.sim.step()
            time.sleep(self._step_delay)

    def set_speed(self, speed: float) -> None:
        """Règle la vitesse (0.0 - 1.0)."""
        self._speed = max(0.05, min(1.0, speed))

    def get_tip_position(self) -> Optional[Tuple[float, float, float]]:
        """Retourne la position cartésienne de l'effecteur."""
        if self.tip_handle is None:
            return None
        pos = self.sim.getObjectPosition(self.tip_handle, -1)
        return (pos[0], pos[1], pos[2])
