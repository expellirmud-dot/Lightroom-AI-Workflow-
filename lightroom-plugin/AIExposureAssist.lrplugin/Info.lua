-- AI Exposure Assist — Lightroom Classic plug-in metadata.

return {
    LrSdkVersion = 10.0,
    LrSdkMinimumVersion = 6.0,

    LrToolkitIdentifier = "com.expellirmud.aiExposureAssist",
    LrPluginName = "AI Exposure Assist",

    LrLibraryMenuItems = {
        {
            title = "AI Exposure Assist — Prepare Current Folder",
            file = "RunExposureAssist.lua",
        },
        {
            title = "AI Exposure Assist — Apply Prepared Job",
            file = "ApplyPreparedJob.lua",
        },
    },

    VERSION = {
        major = 1,
        minor = 1,
        revision = 0,
        build = 2,
    },
}
