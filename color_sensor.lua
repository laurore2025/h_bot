 sim = require 'sim'
function sysCall_init()
    sensor = sim.getObject('/color_sensor')
    dejDetecte = false
    enAttente = false
end
function sysCall_sensing()
    if enAttente then
        local signal = sim.getStringSignal("couleurDetectee")
        if signal == nil then
            enAttente = false
        end
        return
    end
    sim.handleVisionSensor(sensor)
    local img = sim.getVisionSensorImg(sensor)
    if not img then return end
    local mid = math.floor(#img / 2)
    mid = mid - (mid % 3)
    local r = string.byte(img, mid+1)/255
    local g = string.byte(img, mid+2)/255
    local b = string.byte(img, mid+3)/255
    -- Seuil plus élevé pour éviter le fond du convoyeur
    if math.max(r, g, b) < 0.5 then
        dejDetecte = false
        return
    end
    if dejDetecte then return end
    local couleur
    if r > g and r > b then couleur = "rouge"
    elseif g > r and g > b then couleur = "vert"
    else couleur = "bleu"
    end
    sim.setStringSignal("couleurDetectee", couleur)
    print("Couleur detectee : " .. couleur)
    dejDetecte = true
    enAttente = true
end