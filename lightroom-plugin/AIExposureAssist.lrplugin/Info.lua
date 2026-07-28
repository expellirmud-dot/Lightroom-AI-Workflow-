--[[
AI Exposure Assist — Lightroom Classic plug-in metadata.

WO-006 skeleton only. This file declares valid Lightroom SDK plug-in
metadata. It performs no Python execution, preview export, AI logic,
catalog mutation, or XMP writes.
]]

return {
    LrPluginInfo = {
        AUTHOR = { "AI Exposure Assist Project" },
        VERSION = { 1, 0, 0 },
        CONTACT = { "noreply@example.com" },
        URL = { "https://github.com/expellirmud-dot/Lightroom-AI-Workflow-" },
    },
    LrPluginInit = {
        init = "PluginInit.lua",
    },
}
