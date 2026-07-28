--[[
AI Exposure Assist — Lightroom Classic plug-in metadata.

This file follows the Lightroom Classic SDK Info.lua contract. The menu item
is declared here so Lightroom can load and expose the command without relying
on runtime menu registration.
]]

return {
    LrSdkVersion = 10.0,
    LrSdkMinimumVersion = 6.0,

    LrToolkitIdentifier = "com.expellirmud.aiExposureAssist",
    LrPluginName = "AI Exposure Assist",

    LrLibraryMenuItems = {
        {
            title = "AI Exposure Assist",
            file = "RunExposureAssist.lua",
            enabledWhen = "photosSelected",
        },
    },

    VERSION = {
        major = 1,
        minor = 0,
        revision = 0,
        build = 1,
    },
}
