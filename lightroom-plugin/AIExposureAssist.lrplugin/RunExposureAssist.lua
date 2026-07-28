--[[
AI Exposure Assist — Run Exposure Assist command.

WO-006 skeleton only. The entry point invoked from Plug-in Extras.
It reports selection state or a not-yet-implemented message and
performs no side effects. Preview export, manifest handoff, AI
judgment, and XMP writes are implemented in later Work Orders.
]]

local RunExposureAssist = {}

function RunExposureAssist.run(context)
    -- WO-006: no-op command. Defers to PluginInit notification.
    local LrPlugin = import "LrPlugin"
    LrPlugin.invokePluginExtra("AI Exposure Assist")
end

return RunExposureAssist
