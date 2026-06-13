"""
Spawner d'objets colorés sur le convoyeur.

Lance des objets aléatoires (cubes, sphères, cylindres) de différentes couleurs
sur le convoyeur CoppeliaSim pendant que la simulation tourne.

Usage :
    python spawn_objects.py [--count 10] [--interval 2.5] [--shapes cube sphere]
"""

import argparse
import math
import random
import sys
import time

try:
    from coppeliasim_zmqremoteapi_client import RemoteAPIClient
except ImportError:
    print("[ERREUR] Installez : pip install coppeliasim-zmqremoteapi-client")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

COLORS = {
    "rouge":  (1.0, 0.10, 0.10),
    "vert":   (0.10, 0.80, 0.10),
    "bleu":   (0.10, 0.20, 0.90),
    "jaune":  (1.0,  0.90, 0.00),
}

SHAPES = {
    "cube":     "primitiveshape_cuboid",
    "sphere":   "primitiveshape_spheroid",
    "cylindre": "primitiveshape_cylinder",
}

# Position de spawn : début du convoyeur
SPAWN_X = 0.00
SPAWN_Y = 0.70       # extrémité haute du convoyeur
SPAWN_Z = 0.06       # au-dessus du tapis
OBJECT_SIZE = 0.04   # côté / diamètre des objets (m)


# ─────────────────────────────────────────────────────────────────────────────
# Spawner
# ─────────────────────────────────────────────────────────────────────────────

class ObjectSpawner:
    def __init__(self, sim):
        self.sim = sim
        self.spawned_handles = []
        self.counter = 0

    def spawn_one(
        self,
        color_name: str = None,
        shape_name: str = "cube",
        size: float = OBJECT_SIZE
    ) -> int:
        """
        Crée un objet sur le convoyeur.

        Args:
            color_name : "rouge", "vert", "bleu", "jaune" ou None (aléatoire)
            shape_name : "cube", "sphere", "cylindre" ou None (aléatoire)
            size       : taille de l'objet en mètres

        Returns:
            Handle de l'objet créé
        """
        # Couleur aléatoire si non spécifiée
        if color_name is None or color_name not in COLORS:
            color_name = random.choice(list(COLORS.keys()))
        r, g, b = COLORS[color_name]

        # Forme aléatoire si non spécifiée
        if shape_name is None or shape_name not in SHAPES:
            shape_name = random.choice(list(SHAPES.keys()))

        shape_type_str = SHAPES[shape_name]
        shape_type = getattr(self.sim, shape_type_str)

        # Dimensions selon la forme
        if shape_name == "cube":
            dims = [size, size, size]
        elif shape_name == "sphere":
            dims = [size, size, size]
        else:  # cylindre
            dims = [size, size, size * 1.5]

        # Création de l'objet
        h = self.sim.createPrimitiveShape(shape_type, dims, 0)

        # Position avec léger aléa latéral
        x_jitter = random.uniform(-0.03, 0.03)
        self.sim.setObjectPosition(h, -1, [SPAWN_X + x_jitter, SPAWN_Y, SPAWN_Z])

        # Rotation aléatoire sur Z
        rz = random.uniform(0, math.pi)
        self.sim.setObjectOrientation(h, -1, [0, 0, rz])

        # Couleur
        self.sim.setShapeColor(h, None, self.sim.colorcomponent_ambient_diffuse, [r, g, b])

        # Propriétés physiques
        self.sim.setObjectSpecialProperty(
            h,
            self.sim.objectspecialproperty_collidable +
            self.sim.objectspecialproperty_measurable +
            self.sim.objectspecialproperty_renderable +
            self.sim.objectspecialproperty_detectable
        )

        # Masse (physique activée)
        self.sim.setObjectInt32Param(h, self.sim.shapeintparam_static, 0)

        self.counter += 1
        name = f"Obj_{color_name}_{shape_name}_{self.counter}"
        self.sim.setObjectAlias(h, name)
        self.spawned_handles.append(h)

        print(f"  [Spawn #{self.counter:03d}] {name:35s} taille={size:.3f}m")
        return h

    def spawn_batch(
        self,
        count: int,
        interval: float = 2.0,
        colors: list = None,
        shapes: list = None
    ) -> None:
        """
        Spawn plusieurs objets avec un intervalle régulier.

        Args:
            count    : nombre d'objets à créer
            interval : délai entre chaque spawn (secondes)
            colors   : liste de couleurs à utiliser (None = toutes)
            shapes   : liste de formes à utiliser (None = toutes)
        """
        available_colors = colors or list(COLORS.keys())
        available_shapes = shapes or list(SHAPES.keys())

        print(f"\n[Spawner] Spawn de {count} objet(s) — intervalle {interval}s")
        print(f"  Couleurs disponibles : {available_colors}")
        print(f"  Formes disponibles   : {available_shapes}\n")

        for i in range(count):
            color = random.choice(available_colors)
            shape = random.choice(available_shapes)
            self.spawn_one(color_name=color, shape_name=shape)
            if i < count - 1:
                time.sleep(interval)

        print(f"\n[Spawner] {count} objet(s) créé(s). Total session : {self.counter}")

    def spawn_sequence(self, sequence: list, interval: float = 2.0) -> None:
        """
        Spawn une séquence prédéfinie d'objets.

        Args:
            sequence : liste de dicts {"color": "rouge", "shape": "cube"}
            interval : délai entre chaque spawn
        """
        print(f"\n[Spawner] Séquence de {len(sequence)} objet(s) prédéfinis")
        for i, spec in enumerate(sequence):
            color = spec.get("color")
            shape = spec.get("shape", "cube")
            size  = spec.get("size", OBJECT_SIZE)
            self.spawn_one(color_name=color, shape_name=shape, size=size)
            if i < len(sequence) - 1:
                time.sleep(interval)

    def clear_all(self) -> None:
        """Supprime tous les objets spawnés par cette session."""
        print(f"[Spawner] Suppression de {len(self.spawned_handles)} objet(s)...")
        for h in self.spawned_handles:
            try:
                self.sim.removeObject(h)
            except Exception:
                pass
        self.spawned_handles.clear()
        print("[Spawner] Nettoyé.")

    def get_count(self) -> int:
        return self.counter


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Spawner d'objets pour CoppeliaSim")
    parser.add_argument("--host",     default="127.0.0.1")
    parser.add_argument("--port",     default=23000, type=int)
    parser.add_argument("--count",    default=10,    type=int,   help="Nombre d'objets")
    parser.add_argument("--interval", default=2.5,   type=float, help="Délai entre objets (s)")
    parser.add_argument("--colors",   nargs="+",     default=None,
                        choices=list(COLORS.keys()),  help="Couleurs à utiliser")
    parser.add_argument("--shapes",   nargs="+",     default=None,
                        choices=list(SHAPES.keys()),  help="Formes à utiliser")
    parser.add_argument("--loop",     action="store_true",
                        help="Boucle infinie (spawn en continu)")
    parser.add_argument("--loop-interval", default=3.0, type=float,
                        help="Délai entre chaque lot en mode boucle (s)")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("   SPAWNER D'OBJETS — CoppeliaSim SCARA Sorter")
    print("=" * 60)

    try:
        client = RemoteAPIClient(host=args.host, port=args.port)
        sim = client.require("sim")
        print(f"[OK] Connecté à CoppeliaSim {args.host}:{args.port}")
    except Exception as e:
        print(f"[ERREUR] {e}")
        sys.exit(1)

    # Vérifie que la simulation tourne
    state = sim.getSimulationState()
    if state != sim.simulation_advancing_running:
        print("[ERREUR] La simulation doit être en cours d'exécution (▶).")
        sys.exit(1)

    spawner = ObjectSpawner(sim)

    try:
        if args.loop:
            print("\n[Spawner] Mode boucle — Ctrl+C pour arrêter\n")
            while True:
                spawner.spawn_batch(
                    count=1,
                    interval=0,
                    colors=args.colors,
                    shapes=args.shapes
                )
                time.sleep(args.loop_interval)
        else:
            spawner.spawn_batch(
                count=args.count,
                interval=args.interval,
                colors=args.colors,
                shapes=args.shapes
            )

    except KeyboardInterrupt:
        print("\n[Spawner] Arrêt par l'utilisateur.")

    print(f"\n[Spawner] Session terminée. {spawner.get_count()} objet(s) créé(s) au total.")


if __name__ == "__main__":
    main()
