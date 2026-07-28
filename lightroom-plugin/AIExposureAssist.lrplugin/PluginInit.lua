--[[
AI Exposure Assist — Plug-in initialization.

WO-006 skeleton only. Registers the `AI Exposure Assist` command under
Plug-in Extras. The command reports selection state or a clear
not-yet-implemented message. No side effects, no catalog writes,
no subprocess, no network, no preview export, no file mutation.
]]

local LrPlugin = import "LrPlugin"

local function showNotImplemented(context)
    -- WO-006: placeholder command. Reports selection count when available,
    -- otherwise a clear not-yet-implemented message.
    local catalog = import("LrApplication").activeCatalog()
    local targets = catalog:getTargetPhotos()
    local count = 0
    if targets then
        for _ in targets:ipairs() do
            count = count + 1
        end
    end
    import("LrDialogs").message(
        "AI Exposure Assist is not yet implemented.\n"
        .. "Selected photos: " .. count .. "\n"
        .. "Preview export and AI judgment arrive in later Work Orders."
    )
end

LrPlugin.bindToPluginExtras(
    "AI Exposure Assist",
    function(context)
        showNotImplemented(context)
    end
)
