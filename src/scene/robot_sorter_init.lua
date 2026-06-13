-- ============================================================
-- Script Lua principal de la scène CoppeliaSim
-- À placer sur l'objet "SCARA_base" ou un dummy "SceneManager"
-- Mode : Non-threaded child script
-- ============================================================

-- ── Variables globales ────────────────────────────────────────
local jointHandles = {}
local gripperHandle = nil
local conveyorHandle = nil
local visionSensorHandle = nil
local tipHandle = nil

-- Noms des joints dans la scène
local JOINT_NAMES = {
    "SCARA_joint1",
    "SCARA_joint2",
    "SCARA_joint3",
    "SCARA_joint4",
    "SCARA_joint5",
    "SCARA_joint6",
}

-- Vitesse du convoyeur (m/s)
local conveyorSpeed = 0.05
local conveyorRunning = false

-- ── Initialisation (appelée une fois au démarrage) ────────────
function sysCall_init()
    print("[SceneInit] Initialisation de la scène robot sorter...")

    -- Récupération des joints du robot
    for i, name in ipairs(JOINT_NAMES) do
        local ok, h = pcall(sim.getObject, "/" .. name)
        if ok and h ~= -1 then
            jointHandles[i] = h
            -- Mode contrôle en position pour les joints rotatifs
            sim.setJointMode(h, sim.jointmode_kinematic, 0)
            print(string.format("  [OK] Joint '%s' = %d", name, h))
        else
            print(string.format("  [WARN] Joint '%s' introuvable !", name))
        end
    end

    -- Gripper
    local ok, h = pcall(sim.getObject, "/SCARA_gripper")
    if ok then
        gripperHandle = h
        sim.setJointMode(h, sim.jointmode_kinematic, 0)
        print("  [OK] Gripper = " .. h)
    else
        print("  [WARN] Gripper '/SCARA_gripper' introuvable.")
    end

    -- Tip (effecteur)
    local ok2, h2 = pcall(sim.getObject, "/SCARA_tip")
    if ok2 then
        tipHandle = h2
        print("  [OK] Tip = " .. h2)
    end

    -- Capteur de vision
    local ok3, h3 = pcall(sim.getObject, "/Vision_sensor")
    if ok3 then
        visionSensorHandle = h3
        print("  [OK] Vision sensor = " .. h3)
    end

    -- Convoyeur
    local ok4, h4 = pcall(sim.getObject, "/Conveyor/motor")
    if ok4 then
        conveyorHandle = h4
        print("  [OK] Convoyeur moteur = " .. h4)
    end

    -- Position initiale HOME (tous les joints à 0)
    for _, h in ipairs(jointHandles) do
        sim.setJointTargetPosition(h, 0)
    end

    print("[SceneInit] Scène initialisée.")
end

-- ── Boucle d'actualisation (appelée à chaque pas de simulation) ──
function sysCall_actuation()
    -- Lecture des signaux depuis Python (API ZMQ)
    handleConveyorSignals()
    handleRobotSignals()
end

-- ── Sensing (lecture capteurs) ────────────────────────────────
function sysCall_sensing()
    -- Mise à jour du signal de position du tip pour Python
    if tipHandle then
        local pos = sim.getObjectPosition(tipHandle, -1)
        sim.setFloatSignal("tip_x", pos[1])
        sim.setFloatSignal("tip_y", pos[2])
        sim.setFloatSignal("tip_z", pos[3])
    end
end

-- ── Nettoyage ─────────────────────────────────────────────────
function sysCall_cleanup()
    print("[SceneInit] Nettoyage de la scène.")
    if conveyorHandle then
        sim.setJointTargetVelocity(conveyorHandle, 0)
    end
end

-- ═════════════════════════════════════════════════════════════
-- Gestion convoyeur via signaux flottants
-- ═════════════════════════════════════════════════════════════
function handleConveyorSignals()
    if conveyorHandle == nil then return end

    -- Signal "start"
    local startSig = sim.getFloatSignal("conveyor_start")
    if startSig then
        conveyorSpeed = startSig
        conveyorRunning = true
        sim.setJointTargetVelocity(conveyorHandle, conveyorSpeed)
        sim.clearFloatSignal("conveyor_start")
    end

    -- Signal "stop"
    local stopSig = sim.getFloatSignal("conveyor_stop")
    if stopSig then
        conveyorRunning = false
        sim.setJointTargetVelocity(conveyorHandle, 0)
        sim.clearFloatSignal("conveyor_stop")
    end

    -- Signal "set_speed"
    local speedSig = sim.getFloatSignal("conveyor_set_speed")
    if speedSig then
        conveyorSpeed = speedSig
        if conveyorRunning then
            sim.setJointTargetVelocity(conveyorHandle, conveyorSpeed)
        end
        sim.clearFloatSignal("conveyor_set_speed")
    end
end

-- ═════════════════════════════════════════════════════════════
-- Gestion robot via signaux (mode fallback sans contrôle direct)
-- ═════════════════════════════════════════════════════════════
function handleRobotSignals()
    -- Ouverture/fermeture gripper via signal
    local gripperCmd = sim.getFloatSignal("gripper_cmd")
    if gripperCmd and gripperHandle then
        sim.setJointTargetPosition(gripperHandle, gripperCmd)
        sim.clearFloatSignal("gripper_cmd")
    end
end

-- ═════════════════════════════════════════════════════════════
-- Génération d'objets à trier (spawner)
-- Appelle cette fonction pour faire apparaître des objets
-- sur le convoyeur à intervalles réguliers.
-- ═════════════════════════════════════════════════════════════

-- Couleurs disponibles
local COLORS = {
    {1.0, 0.1, 0.1, "rouge"},
    {0.1, 0.8, 0.1, "vert"},
    {0.1, 0.2, 0.9, "bleu"},
    {1.0, 0.9, 0.0, "jaune"},
}

local spawnInterval = 3.0  -- secondes entre chaque apparition
local lastSpawnTime = 0
local spawnPositionX = 0.0
local spawnPositionY = 0.50
local spawnPositionZ = 0.06
local objectCounter = 0

function spawnObject()
    local t = sim.getSimulationTime()
    if t - lastSpawnTime < spawnInterval then return end
    lastSpawnTime = t

    -- Choix aléatoire de la couleur
    math.randomseed(math.floor(t * 1000))
    local colorData = COLORS[math.random(1, #COLORS)]
    local r, g, b, colorName = colorData[1], colorData[2], colorData[3], colorData[4]

    -- Création du cube
    local size = 0.04
    local handle = sim.createPrimitiveShape(sim.primitiveshape_cuboid, {size, size, size}, 0)

    -- Position sur le convoyeur
    sim.setObjectPosition(handle, -1, {spawnPositionX, spawnPositionY, spawnPositionZ})

    -- Couleur de l'objet
    sim.setShapeColor(handle, nil, sim.colorcomponent_ambient_diffuse, {r, g, b})

    -- Physique activée
    sim.setObjectSpecialProperty(handle, sim.objectspecialproperty_collidable
        + sim.objectspecialproperty_measurable
        + sim.objectspecialproperty_renderable
        + sim.objectspecialproperty_detectable)

    objectCounter = objectCounter + 1
    local name = string.format("Object_%s_%d", colorName, objectCounter)
    sim.setObjectAlias(handle, name)

    print(string.format("[Spawner] Objet créé : %s à t=%.2fs", name, t))
end

--Décommentez pour activer le spawner automatique :
 function sysCall_actuation()
    handleConveyorSignals()
    handleRobotSignals()
    spawnObject()
 end
