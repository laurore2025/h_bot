""""
Usage :
    python build_scene.py [--host 127.0.0.1] [--port 23000] [--out robot_sorter.ttt]

Prérequis :
    pip install coppeliasim-zmqremoteapi-client
    CoppeliaSim ouvert, simulation ARRÊTÉE (pas en cours d'exécution)
"""

import argparse
import math
import os
import sys

try:
    from coppeliasim_zmqremoteapi_client import RemoteAPIClient
except ImportError:
    print("[ERREUR] Installez : pip install coppeliasim-zmqremoteapi-client")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Paramètres géométriques du robot SCARA
# ─────────────────────────────────────────────────────────────────────────────

ROBOT = {
    "base_height":   0.05,   # hauteur du socle (m)
    "base_radius":   0.08,   # rayon du socle
    "link1_length":  0.35,   # longueur bras 1
    "link1_radius":  0.025,
    "link2_length":  0.25,   # longueur bras 2
    "link2_radius":  0.020,
    "wrist_height":  0.06,   # hauteur du poignet
    "wrist_radius":  0.018,
    "tool_length":   0.08,   # longueur de l'outil/gripper
    "tool_radius":   0.015,
}

CONVEYOR = {
    "length":  0.80,
    "width":   0.20,
    "height":  0.02,
    "pos_x":   0.00,
    "pos_y":   0.35,
    "pos_z":   0.00,
}

DROP_ZONES = [
    {"name": "Zone_Rouge",    "color": (0.9, 0.1, 0.1), "pos": ( 0.40,  0.10, 0.0)},
    {"name": "Zone_Verte",    "color": (0.1, 0.8, 0.1), "pos": ( 0.40, -0.10, 0.0)},
    {"name": "Zone_Bleue",    "color": (0.1, 0.2, 0.9), "pos": ( 0.15, -0.40, 0.0)},
    {"name": "Zone_Jaune",    "color": (0.9, 0.9, 0.0), "pos": (-0.15, -0.40, 0.0)},
    {"name": "Zone_Inconnue", "color": (0.5, 0.5, 0.5), "pos": (-0.40,  0.10, 0.0)},
]

LUA_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "robot_sorter_init.lua")


# ─────────────────────────────────────────────────────────────────────────────
# Constructeur de scène
# ─────────────────────────────────────────────────────────────────────────────

class SceneBuilder:
    def __init__(self, sim):
        self.sim = sim
        self.handles = {}   # nom → handle

    # ------------------------------------------------------------------
    # Sol et environnement
    # ------------------------------------------------------------------

    def build_ground(self):
        print("[Scene] Création du sol...")
        h = self.sim.createPrimitiveShape(
            self.sim.primitiveshape_cuboid,
            [2.0, 2.0, 0.01], 0
        )
        self.sim.setObjectPosition(h, -1, [0, 0, -0.005])
        self.sim.setShapeColor(h, None, self.sim.colorcomponent_ambient_diffuse, [0.3, 0.3, 0.3])
        self.sim.setObjectAlias(h, "Ground")
        self.sim.setObjectSpecialProperty(
            h,
            self.sim.objectspecialproperty_collidable +
            self.sim.objectspecialproperty_measurable +
            self.sim.objectspecialproperty_renderable +
            self.sim.objectspecialproperty_detectable
        )
        self.handles["Ground"] = h
        return h

    def build_lights(self):
        print("[Scene] Ajout des lumières...")
        positions = [
            [1.0,  1.0, 2.0],
            [-1.0, -1.0, 2.0],
        ]
        for i, pos in enumerate(positions):
            h = self.sim.createDummy(0.01)
            self.sim.setObjectPosition(h, -1, pos)
            self.sim.setObjectAlias(h, f"Light_{i+1}")
            self.handles[f"Light_{i+1}"] = h

    # ------------------------------------------------------------------
    # Robot SCARA 6 axes
    # ------------------------------------------------------------------

    def build_robot(self):
        print("[Scene] Construction du robot SCARA 6 axes...")

        # ── Socle ──────────────────────────────────────────────────────
        base_h = self.sim.createPrimitiveShape(
            self.sim.primitiveshape_cylinder,
            [ROBOT["base_radius"] * 2, ROBOT["base_radius"] * 2, ROBOT["base_height"]],
            0
        )
        self.sim.setObjectPosition(base_h, -1, [0, 0, ROBOT["base_height"] / 2])
        self.sim.setShapeColor(base_h, None, self.sim.colorcomponent_ambient_diffuse, [0.2, 0.2, 0.8])
        self.sim.setObjectAlias(base_h, "SCARA_base")
        self._make_static(base_h)
        self.handles["SCARA_base"] = base_h
        z_base_top = ROBOT["base_height"]

        # ── Joint 1 : rotation base (Z) ───────────────────────────────
        j1 = self._create_joint("SCARA_joint1", base_h, self.sim.joint_revolute_subtype,
                                 [0, 0, z_base_top], [0, 0, 0])

        # ── Bras 1 ────────────────────────────────────────────────────
        link1_h = self._create_link(
            "SCARA_link1", j1,
            ROBOT["link1_length"], ROBOT["link1_radius"],
            [ROBOT["link1_length"] / 2, 0, 0],  # décalage selon X
            [0, math.pi / 2, 0],                  # rotation pour orienter selon X
            [0.8, 0.3, 0.1]
        )
        z_j2 = 0

        # ── Joint 2 : rotation coude (Z) ──────────────────────────────
        j2 = self._create_joint("SCARA_joint2", link1_h, self.sim.joint_revolute_subtype,
                                 [ROBOT["link1_length"], 0, z_j2], [0, 0, 0])

        # ── Bras 2 ────────────────────────────────────────────────────
        link2_h = self._create_link(
            "SCARA_link2", j2,
            ROBOT["link2_length"], ROBOT["link2_radius"],
            [ROBOT["link2_length"] / 2, 0, 0],
            [0, math.pi / 2, 0],
            [0.8, 0.5, 0.1]
        )

        # ── Joint 3 : translation verticale (prismatique) ─────────────
        j3 = self._create_joint("SCARA_joint3", link2_h, self.sim.joint_prismatic_subtype,
                                 [ROBOT["link2_length"], 0, 0], [0, 0, 0])

        # ── Colonne verticale ─────────────────────────────────────────
        col_h = self._create_link(
            "SCARA_column", j3,
            ROBOT["wrist_height"], ROBOT["wrist_radius"],
            [0, 0, -ROBOT["wrist_height"] / 2],
            [0, 0, 0],
            [0.6, 0.6, 0.6]
        )

        # ── Joint 4 : rotation poignet 1 (Z) ──────────────────────────
        j4 = self._create_joint("SCARA_joint4", col_h, self.sim.joint_revolute_subtype,
                                 [0, 0, -ROBOT["wrist_height"]], [0, 0, 0])

        # ── Poignet ───────────────────────────────────────────────────
        wrist_h = self._create_link(
            "SCARA_wrist", j4,
            ROBOT["wrist_height"] / 2, ROBOT["wrist_radius"],
            [0, 0, -ROBOT["wrist_height"] / 4],
            [0, 0, 0],
            [0.7, 0.7, 0.7]
        )

        # ── Joint 5 : rotation poignet 2 (X) ──────────────────────────
        j5 = self._create_joint("SCARA_joint5", wrist_h, self.sim.joint_revolute_subtype,
                                 [0, 0, -ROBOT["wrist_height"] / 2], [0, math.pi / 2, 0])

        # ── Joint 6 : rotation outil (Z) ──────────────────────────────
        j6 = self._create_joint("SCARA_joint6", j5, self.sim.joint_revolute_subtype,
                                 [0, 0, 0], [0, -math.pi / 2, 0])

        # ── Corps de l'outil ─────────────────────────────────────────
        tool_h = self._create_link(
            "SCARA_tool", j6,
            ROBOT["tool_length"], ROBOT["tool_radius"],
            [0, 0, -ROBOT["tool_length"] / 2],
            [0, 0, 0],
            [0.9, 0.9, 0.9]
        )

        # ── Gripper (joint prismatique) ────────────────────────────────
        self._create_joint("SCARA_gripper", tool_h, self.sim.joint_prismatic_subtype,
                            [0, 0, -ROBOT["tool_length"]], [0, 0, 0])

        # ── Tip (point de référence outil) ────────────────────────────
        tip_h = self.sim.createDummy(0.015)
        self.sim.setObjectPosition(tip_h, tool_h, [0, 0, -ROBOT["tool_length"]])
        self.sim.setObjectAlias(tip_h, "SCARA_tip")
        self.sim.setObjectParent(tip_h, tool_h, False)
        self.handles["SCARA_tip"] = tip_h

        print("  [OK] Robot SCARA créé — 6 joints, tip, gripper")
        return base_h

    # ------------------------------------------------------------------
    # Convoyeur
    # ------------------------------------------------------------------

    def build_conveyor(self):
        print("[Scene] Construction du convoyeur...")
        c = CONVEYOR

        # Corps du convoyeur
        body_h = self.sim.createPrimitiveShape(
            self.sim.primitiveshape_cuboid,
            [c["width"], c["length"], c["height"]], 0
        )
        self.sim.setObjectPosition(body_h, -1, [c["pos_x"], c["pos_y"], c["height"] / 2])
        self.sim.setShapeColor(body_h, None, self.sim.colorcomponent_ambient_diffuse, [0.4, 0.4, 0.4])
        self.sim.setObjectAlias(body_h, "Conveyor")
        self._make_static(body_h)
        self.handles["Conveyor"] = body_h

        # Rouleaux (décoratifs)
        n_rollers = 6
        for i in range(n_rollers):
            y = c["pos_y"] - c["length"] / 2 + (i + 0.5) * c["length"] / n_rollers
            r_h = self.sim.createPrimitiveShape(
                self.sim.primitiveshape_cylinder,
                [c["width"] + 0.01, c["width"] + 0.01, 0.02], 0
            )
            self.sim.setObjectPosition(r_h, -1, [c["pos_x"], y, c["height"] + 0.01])
            self.sim.setObjectOrientation(r_h, -1, [math.pi / 2, 0, 0])
            self.sim.setShapeColor(r_h, None, self.sim.colorcomponent_ambient_diffuse, [0.6, 0.6, 0.6])
            self.sim.setObjectAlias(r_h, f"Conveyor_roller_{i+1}")
            self._make_static(r_h)
            self.sim.setObjectParent(r_h, body_h, False)

        # Joint moteur (pour contrôle vitesse)
        motor_h = self._create_joint(
            "motor", body_h, self.sim.joint_revolute_subtype,
            [c["pos_x"], c["pos_y"], c["height"] + 0.01],
            [math.pi / 2, 0, 0],
            velocity_mode=True
        )
        self.handles["Conveyor_motor"] = motor_h

        print(f"  [OK] Convoyeur créé ({c['length']}m × {c['width']}m)")
        return body_h

    # ------------------------------------------------------------------
    # Zones de dépôt
    # ------------------------------------------------------------------

    def build_drop_zones(self):
        print("[Scene] Création des zones de dépôt...")
        zone_size = 0.25
        zone_thickness = 0.005

        for zone in DROP_ZONES:
            h = self.sim.createPrimitiveShape(
                self.sim.primitiveshape_cuboid,
                [zone_size, zone_size, zone_thickness], 0
            )
            px, py, pz = zone["pos"]
            self.sim.setObjectPosition(h, -1, [px, py, pz + zone_thickness / 2])
            r, g, b = zone["color"]
            self.sim.setShapeColor(h, None, self.sim.colorcomponent_ambient_diffuse, [r, g, b])
            self.sim.setShapeColor(h, None, self.sim.colorcomponent_transparency, [0.5])
            self.sim.setObjectAlias(h, zone["name"])
            self._make_static(h)
            self.handles[zone["name"]] = h

            # Label (dummy)
            label_h = self.sim.createDummy(0.001)
            self.sim.setObjectPosition(label_h, -1, [px, py, pz + 0.05])
            self.sim.setObjectAlias(label_h, f"{zone['name']}_label")
            self.sim.setObjectParent(label_h, h, False)

            print(f"  [OK] {zone['name']} à ({px:.2f}, {py:.2f}, {pz:.2f})")

    # ------------------------------------------------------------------
    # Capteur de vision
    # ------------------------------------------------------------------

    def build_vision_sensor(self):
        print("[Scene] Ajout du capteur de vision...")
        sensor_h = self.sim.createVisionSensor(
            0,          # options
            [256, 256], # résolution
            [
                0.01,   # near clipping
                5.0,    # far clipping
                60.0,   # angle (degrés)
                1.0,    # ratio X/Y
                0.0, 0.0  # offset
            ]
        )
        # Positionné au-dessus du convoyeur, pointant vers le bas
        self.sim.setObjectPosition(sensor_h, -1, [
            CONVEYOR["pos_x"],
            CONVEYOR["pos_y"],
            1.2
        ])
        self.sim.setObjectOrientation(sensor_h, -1, [math.pi, 0, 0])  # pointe vers le bas
        self.sim.setObjectAlias(sensor_h, "Vision_sensor")
        self.handles["Vision_sensor"] = sensor_h
        print("  [OK] Vision sensor à z=1.2m, résolution 256×256")
        return sensor_h

    # ------------------------------------------------------------------
    # Script Lua
    # ------------------------------------------------------------------

    def attach_lua_script(self, target_handle: int):
        print("[Scene] Intégration du script Lua...")
        if not os.path.exists(LUA_SCRIPT_PATH):
            print(f"  [WARN] Script Lua introuvable : {LUA_SCRIPT_PATH}")
            return

        with open(LUA_SCRIPT_PATH, "r", encoding="utf-8") as f:
            lua_code = f.read()

        try:
            script_h = self.sim.addScript(self.sim.scripttype_childscript)
            self.sim.setScriptStringAttribute(
                script_h,
                self.sim.scriptstringattribute_scripttext,
                lua_code
            )
            self.sim.setScriptAttribute(
                script_h,
                self.sim.scriptattribute_objecthandle,
                target_handle
            )
            print("  [OK] Script Lua attaché à SCARA_base.")
        except Exception as e:
            print(f"  [WARN] Impossible d'attacher le script Lua : {e}")
            print("  → Attachez manuellement robot_sorter_init.lua à l'objet SCARA_base.")

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------

    def save_scene(self, path: str):
        print(f"\n[Scene] Sauvegarde → {path}")
        try:
            self.sim.saveScene(path)
            print(f"  [OK] Scène sauvegardée : {path}")
        except Exception as e:
            print(f"  [ERREUR] Sauvegarde impossible : {e}")
            print("  → Sauvegardez manuellement depuis CoppeliaSim (File → Save Scene As...)")

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    def _create_joint(
        self, name, parent_h, joint_type, position, orientation,
        velocity_mode=False
    ):
        h = self.sim.createJoint(joint_type, self.sim.jointmode_kinematic, 0)
        self.sim.setObjectPosition(h, -1, position)
        self.sim.setObjectOrientation(h, -1, orientation)
        self.sim.setObjectAlias(h, name)
        self.sim.setObjectParent(h, parent_h, False)
        if velocity_mode:
            self.sim.setJointMode(h, self.sim.jointmode_kinematic, 0)
        self.handles[name] = h
        return h

    def _create_link(self, name, parent_h, length, radius, rel_pos, rel_ori, color):
        h = self.sim.createPrimitiveShape(
            self.sim.primitiveshape_cylinder,
            [radius * 2, radius * 2, length], 0
        )
        self.sim.setObjectPosition(h, parent_h, rel_pos)
        self.sim.setObjectOrientation(h, parent_h, rel_ori)
        self.sim.setShapeColor(h, None, self.sim.colorcomponent_ambient_diffuse, color)
        self.sim.setObjectAlias(h, name)
        self.sim.setObjectParent(h, parent_h, False)
        self.handles[name] = h
        return h

    def _make_static(self, handle):
        """Rend un objet statique (non soumis à la physique)."""
        self.sim.setObjectInt32Param(
            handle,
            self.sim.shapeintparam_static,
            1
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Constructeur de scène CoppeliaSim")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=23000, type=int)
    parser.add_argument("--out",  default="robot_sorter.ttt", help="Nom du fichier de sortie")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("   CONSTRUCTEUR DE SCÈNE — SCARA Sorter")
    print("=" * 60)
    print(f"\n  Connexion à CoppeliaSim {args.host}:{args.port}")
    print("  ⚠  La simulation doit être ARRÊTÉE (pas en cours d'exécution)\n")

    # Connexion
    try:
        client = RemoteAPIClient(host=args.host, port=args.port)
        sim = client.require("sim")
        print("[OK] Connecté à CoppeliaSim\n")
    except Exception as e:
        print(f"[ERREUR] Connexion impossible : {e}")
        sys.exit(1)

    # Vérifie que la simulation est arrêtée
    state = sim.getSimulationState()
    if state != sim.simulation_stopped:
        print("[ERREUR] Arrêtez la simulation avant de construire la scène (■).")
        sys.exit(1)

    # Nouvelle scène vide
    sim.closeScene()
    sim.loadScene("")
    print("[OK] Nouvelle scène vide créée\n")

    builder = SceneBuilder(sim)

    # Construction étape par étape
    print("─" * 40)
    builder.build_ground()
    builder.build_lights()

    print("─" * 40)
    base_h = builder.build_robot()

    print("─" * 40)
    builder.build_conveyor()

    print("─" * 40)
    builder.build_drop_zones()

    print("─" * 40)
    builder.build_vision_sensor()

    print("─" * 40)
    builder.attach_lua_script(base_h)

    # Résumé des handles créés
    print("\n[Handles créés]")
    for name, h in builder.handles.items():
        print(f"  {name:25s} → {h}")

    # Sauvegarde
    print("\n─" * 40)
    output_path = os.path.abspath(args.out)
    builder.save_scene(output_path)

    print("\n" + "=" * 60)
    print("  SCÈNE CONSTRUITE AVEC SUCCÈS")
    print("=" * 60)
    print(f"\n  Fichier : {output_path}")
    print("\n  Prochaines étapes :")
    print("  1. Ouvrez la scène dans CoppeliaSim")
    print("  2. Ajustez les longueurs de bras si nécessaire")
    print("  3. Lancez la simulation (▶)")
    print("  4. Exécutez : python src/main.py")
    print()


if __name__ == "__main__":
    main()
