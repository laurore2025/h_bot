"""
Contrôle du convoyeur dans CoppeliaSim.
Gère la vitesse de défilement et la détection des objets arrivant.
"""

import time
from typing import Optional, Callable


class Conveyor:
    """
    Interface avec le convoyeur de la scène CoppeliaSim.
    Supporte deux modes : script Lua embarqué ou joint moteur.
    """

    def __init__(self, sim, conveyor_name: str = "/Conveyor"):
        self.sim = sim
        self.conveyor_name = conveyor_name
        self.handle: Optional[int] = None
        self.motor_handle: Optional[int] = None
        self._speed: float = 0.05       # m/s
        self._running: bool = False
        self._on_object_detected: Optional[Callable] = None

    def initialize(self) -> bool:
        """Récupère les handles du convoyeur."""
        try:
            self.handle = self.sim.getObject(self.conveyor_name)
            print(f"[Conveyor] '{self.conveyor_name}' → handle {self.handle}")

            # Essaie de trouver le joint moteur du convoyeur
            try:
                self.motor_handle = self.sim.getObject(f"{self.conveyor_name}/motor")
                print(f"[Conveyor] Moteur → handle {self.motor_handle}")
            except Exception:
                print("[Conveyor] Pas de joint moteur trouvé, mode script Lua.")

            return True
        except Exception as e:
            print(f"[Conveyor] Erreur initialisation : {e}")
            return False

    def start(self, speed: Optional[float] = None) -> None:
        """Démarre le convoyeur."""
        if speed is not None:
            self._speed = speed
        self._running = True

        if self.motor_handle is not None:
            self.sim.setJointTargetVelocity(self.motor_handle, self._speed)
            print(f"[Conveyor] Démarré (vitesse moteur = {self._speed:.3f} rad/s)")
        else:
            self._send_lua_command("start", self._speed)
            print(f"[Conveyor] Démarré via script Lua (vitesse = {self._speed:.3f} m/s)")

    def stop(self) -> None:
        """Arrête le convoyeur."""
        self._running = False
        if self.motor_handle is not None:
            self.sim.setJointTargetVelocity(self.motor_handle, 0.0)
        else:
            self._send_lua_command("stop", 0.0)
        print("[Conveyor] Arrêté.")

    def set_speed(self, speed: float) -> None:
        """Change la vitesse du convoyeur en temps réel."""
        self._speed = max(0.0, speed)
        if self._running:
            if self.motor_handle is not None:
                self.sim.setJointTargetVelocity(self.motor_handle, self._speed)
            else:
                self._send_lua_command("set_speed", self._speed)
        print(f"[Conveyor] Vitesse réglée à {self._speed:.3f}")

    def pause_for_pick(self, duration: float = 1.5) -> None:
        """
        Pause temporaire du convoyeur pendant la prise d'un objet.

        Args:
            duration : durée de la pause en secondes
        """
        print(f"[Conveyor] Pause {duration:.1f}s pour prise...")
        self.stop()
        time.sleep(duration)
        self.start()

    def on_object_detected(self, callback: Callable) -> None:
        """
        Enregistre un callback appelé quand un objet arrive en zone de prise.

        Args:
            callback : fonction(handle_objet) appelée à la détection
        """
        self._on_object_detected = callback

    def _send_lua_command(self, command: str, value: float) -> None:
        """Envoie une commande au script Lua du convoyeur via signal."""
        try:
            self.sim.setFloatSignal(f"conveyor_{command}", value)
        except Exception as e:
            print(f"[Conveyor] Erreur signal Lua '{command}' : {e}")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def speed(self) -> float:
        return self._speed
