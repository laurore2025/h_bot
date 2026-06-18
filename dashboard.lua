sim = require 'sim'
simUI = require 'simUI'

ui = nil
compteur = {rouge = 0, vert = 0, bleu = 0}
derniereColor = ""

function sysCall_init()
    ui = simUI.create([[
        <ui title="Tri de cubes" closeable="false" resizable="false" placement="relative" position="0,0" size="280,220">
            <label text="Couleur detectee :" style="font-weight:bold"/>
            <label id="1" text="---" style="font-size:16px"/>
            <label text=" "/>
            <label text="Cubes tries :" style="font-weight:bold"/>
            <label id="2" text="Rouge : 0"/>
            <label id="3" text="Vert  : 0"/>
            <label id="4" text="Bleu  : 0"/>
            <label text=" "/>
        </ui>
    ]])
    convoyeurActif = true
end



function sysCall_sensing()
    local couleur = sim.getStringSignal("couleurDetectee")
    if couleur ~= nil and couleur ~= derniereColor then
        derniereColor = couleur
        simUI.setLabelText(ui, 1, couleur)
        compteur[couleur] = compteur[couleur] + 1
        simUI.setLabelText(ui, 2, "Rouge : " .. compteur.rouge)
        simUI.setLabelText(ui, 3, "Vert  : " .. compteur.vert)
        simUI.setLabelText(ui, 4, "Bleu  : " .. compteur.bleu)
    end
end

function sysCall_cleanup()
    if ui then simUI.destroy(ui) end
end
