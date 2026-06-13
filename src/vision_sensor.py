"""
Module de détection d'objets via le capteur de vision CoppeliaSim.
Analyse les images pour détecter et classifier les objets à trier.
"""

import math
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass


@dataclass
class DetectedObject:
    """Représente un objet détecté par le capteur de vision."""
    obj_id: int
    position: Tuple[float, float, float]     # (x, y, z) en mètres
    color: str                               # "rouge", "vert", "bleu", "inconnu"
    color_rgb: Tuple[float, float, float]    # valeurs RGB normalisées [0-1]
    size: float                              # taille estimée (m)
    shape: str = "inconnu"                  # "cube", "sphere", "cylindre"
    confidence: float = 1.0                 # confiance de la détection [0-1]

    def __repr__(self):
        return (
            f"DetectedObject(id={self.obj_id}, color='{self.color}', "
            f"pos=({self.position[0]:.3f}, {self.position[1]:.3f}, {self.position[2]:.3f}), "
            f"size={self.size:.3f})"
        )


class VisionSensor:
    """
    Interface avec le capteur de vision CoppeliaSim.
    Gère la capture d'image et la détection d'objets.
    """

    # Seuils de détection des couleurs (RGB normalisé 0-1)
    COLOR_THRESHOLDS: Dict[str, Dict] = {
        "rouge": {
            "r_min": 0.55, "r_max": 1.0,
            "g_min": 0.0,  "g_max": 0.35,
            "b_min": 0.0,  "b_max": 0.35,
        },
        "vert": {
            "r_min": 0.0,  "r_max": 0.35,
            "g_min": 0.55, "g_max": 1.0,
            "b_min": 0.0,  "b_max": 0.35,
        },
        "bleu": {
            "r_min": 0.0,  "r_max": 0.35,
            "g_min": 0.0,  "g_max": 0.35,
            "b_min": 0.55, "b_max": 1.0,
        },
        "jaune": {
            "r_min": 0.55, "r_max": 1.0,
            "g_min": 0.55, "g_max": 1.0,
            "b_min": 0.0,  "b_max": 0.25,
        },
    }

    def __init__(self, sim, sensor_name: str = "/Vision_sensor"):
        """
        Args:
            sim         : API CoppeliaSim
            sensor_name : chemin du capteur dans la scène
        """
        self.sim = sim
        self.sensor_name = sensor_name
        self.sensor_handle: Optional[int] = None
        self.resolution: Tuple[int, int] = (256, 256)
        self._last_image: Optional[bytes] = None
        self._detected_objects: List[DetectedObject] = []

    def initialize(self) -> bool:
        """Récupère le handle du capteur et sa résolution."""
        try:
            self.sensor_handle = self.sim.getObject(self.sensor_name)
            res = self.sim.getVisionSensorResolution(self.sensor_handle)
            self.resolution = (res[0], res[1])
            print(f"[VisionSensor] '{self.sensor_name}' → handle {self.sensor_handle}, "
                  f"résolution {self.resolution[0]}x{self.resolution[1]}")
            return True
        except Exception as e:
            print(f"[VisionSensor] Erreur initialisation : {e}")
            return False

    # ------------------------------------------------------------------
    # Capture & analyse
    # ------------------------------------------------------------------

    def capture(self) -> bool:
        """Déclenche une capture d'image."""
        if self.sensor_handle is None:
            return False
        try:
            img, res = self.sim.getVisionSensorImg(self.sensor_handle)
            self._last_image = img
            return True
        except Exception as e:
            print(f"[VisionSensor] Erreur capture : {e}")
            return False

    def detect_objects_by_color(
        self, search_area: Optional[Tuple[float, float, float, float]] = None
    ) -> List[DetectedObject]:
        """
        Détecte les objets dans la scène via le capteur de proximité colorimétrique.
        Utilise les handles d'objets CoppeliaSim pour une détection fiable.

        Args:
            search_area : (x_min, x_max, y_min, y_max) zone de recherche

        Returns:
            Liste des objets détectés.
        """
        detected = []
        try:
            # Approche directe : parcourir les objets de la scène
            obj_handles = self._get_scene_objects()
            for i, handle in enumerate(obj_handles):
                result = self._analyze_object(handle, i, search_area)
                if result is not None:
                    detected.append(result)
        except Exception as e:
            print(f"[VisionSensor] Erreur détection : {e}")

        self._detected_objects = detected
        return detected

    def get_nearest_object(
        self,
        ref_pos: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ) -> Optional[DetectedObject]:
        """Retourne l'objet détecté le plus proche d'une position de référence."""
        if not self._detected_objects:
            return None
        return min(
            self._detected_objects,
            key=lambda o: math.dist(o.position, ref_pos)
        )

    def get_objects_by_color(self, color: str) -> List[DetectedObject]:
        """Filtre les objets par couleur."""
        return [o for o in self._detected_objects if o.color == color]

    # ------------------------------------------------------------------
    # Analyse couleur
    # ------------------------------------------------------------------

    def classify_color(self, r: float, g: float, b: float) -> str:
        """
        Détermine la couleur d'un objet à partir de ses composantes RGB.

        Args:
            r, g, b : composantes RGB normalisées [0-1]

        Returns:
            Nom de la couleur ou "inconnu"
        """
        for color_name, thresh in self.COLOR_THRESHOLDS.items():
            if (thresh["r_min"] <= r <= thresh["r_max"] and
                    thresh["g_min"] <= g <= thresh["g_max"] and
                    thresh["b_min"] <= b <= thresh["b_max"]):
                return color_name
        return "inconnu"

    def add_color_threshold(
        self,
        name: str,
        r_min: float, r_max: float,
        g_min: float, g_max: float,
        b_min: float, b_max: float
    ) -> None:
        """Ajoute ou modifie un seuil de couleur."""
        self.COLOR_THRESHOLDS[name] = {
            "r_min": r_min, "r_max": r_max,
            "g_min": g_min, "g_max": g_max,
            "b_min": b_min, "b_max": b_max,
        }
        print(f"[VisionSensor] Couleur '{name}' enregistrée.")

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    def _get_scene_objects(self) -> List[int]:
        """Retourne les handles des objets de forme dans la scène."""
        handles = []
        try:
            # Récupère tous les objets solides (shapes)
            i = 0
            while True:
                handle = self.sim.getObjects(i, self.sim.object_shape_type)
                if handle == -1:
                    break
                handles.append(handle)
                i += 1
        except Exception:
            pass
        return handles

    def _analyze_object(
        self,
        handle: int,
        obj_id: int,
        search_area: Optional[Tuple[float, float, float, float]]
    ) -> Optional[DetectedObject]:
        """Analyse un objet et retourne ses caractéristiques si pertinent."""
        try:
            pos = self.sim.getObjectPosition(handle, -1)
            x, y, z = pos[0], pos[1], pos[2]

            # Filtre par zone si spécifiée
            if search_area is not None:
                x_min, x_max, y_min, y_max = search_area
                if not (x_min <= x <= x_max and y_min <= y <= y_max):
                    return None

            # Récupère la couleur de l'objet
            color_data = self.sim.getShapeColor(handle, None, self.sim.colorcomponent_ambient_diffuse)
            r, g, b = color_data[1][0], color_data[1][1], color_data[1][2]
            color_name = self.classify_color(r, g, b)

            if color_name == "inconnu":
                return None

            # Taille approximative via la boîte englobante
            bbox = self.sim.getShapeBB(handle)
            size = max(bbox) if bbox else 0.05

            return DetectedObject(
                obj_id=handle,
                position=(x, y, z),
                color=color_name,
                color_rgb=(r, g, b),
                size=size,
            )
        except Exception:
            return None

    def print_summary(self) -> None:
        """Affiche un résumé des objets détectés."""
        print(f"\n[VisionSensor] {len(self._detected_objects)} objet(s) détecté(s) :")
        for obj in self._detected_objects:
            print(f"  {obj}")
