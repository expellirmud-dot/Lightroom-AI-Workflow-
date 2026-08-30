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
            title = "AI Exposure Assist — Prepare Whole-Folder Iterative Session",
            file = "IterativeSession.lua",
        },
        {
            title = "AI Exposure Assist — Resume Pending Iterative Session",
            file = "ResumeIterativeSession.lua",
        },
        {
            title = "AI Exposure Assist — Prepare Current Folder (Single Pass)",
            file = "RunExposureAssist.lua",
        },
        {
            title = "AI Exposure Assist — Apply Prepared Job (Single Pass)",
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
