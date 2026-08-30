-- AI Exposure Assist — Lightroom Classic plug-in metadata.

return {
    LrSdkVersion = 10.0,
    LrSdkMinimumVersion = 6.0,

    LrToolkitIdentifier = "com.expellirmud.aiExposureAssist",
    LrPluginName = "AI Exposure Assist",

    LrLibraryMenuItems = {
        {
            title = "AI Exposure Assist — Diagnose Current Folder",
            file = "DiagnoseCurrentFolder.lua",
        },
        {
            title = "AI Exposure Assist — Prepare AI Package",
            file = "PrepareAIPackage.lua",
        },
        {
            title = "AI Exposure Assist — Import / Apply AI Results",
            file = "ImportApplyAIResults.lua",
        },
        {
            title = "AI Exposure Assist — Prepare Next AI Package",
            file = "PrepareNextAIPackage.lua",
        },
        {
            title = "AI Exposure Assist — Prepare Current Folder (Legacy Single Pass)",
            file = "RunExposureAssist.lua",
        },
        {
            title = "AI Exposure Assist — Apply Prepared Job (Legacy Single Pass)",
            file = "ApplyPreparedJob.lua",
        },
    },

    VERSION = {
        major = 1,
        minor = 2,
        revision = 0,
        build = 1,
    },
}
