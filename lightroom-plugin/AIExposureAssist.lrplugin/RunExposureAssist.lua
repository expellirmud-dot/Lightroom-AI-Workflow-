--[[
AI Exposure Assist — Run Exposure Assist command.

WO-007: exports Lightroom-rendered JPEG previews for the current
selection and prepares an ordered manifest handoff.

Safety:
- Never accesses .lrcat, .lrdata, RAW contents, or preview caches directly.
- Lightroom SDK is the only source of selection and rendered previews.
- No AI, XMP mutation, HTTP server, watcher, or catalog mutation.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrExportSession = import "LrExportSession"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"

local RunExposureAssist = {}

-- Deterministic preview naming expected by the Python boundary.
function RunExposureAssist.previewName(seq, rawPath)
    local stem = LrPathUtils.removeExtension(LrPathUtils.leafName(rawPath))
    return string.format("%06d__%s.jpg", seq, stem)
end

-- Lightroom accepts an export-settings property table.
function RunExposureAssist.buildExportSettings(previewDir)
    return {
        LR_export_destinationType = "specificFolder",
        LR_export_destinationPathPrefix = previewDir,
        LR_export_useSubfolder = false,
        LR_format = "JPEG",
        LR_jpeg_quality = 0.9,
        LR_export_colorSpace = "sRGB",
        LR_size_doConstrain = false,
        LR_outputSharpeningOn = false,
        LR_collisionHandling = "rename",
    }
end

function RunExposureAssist.run()
    local catalog = LrApplication.activeCatalog()
    local targets = catalog:getTargetPhotos() or {}

    local photos = {}
    for _, photo in ipairs(targets) do
        photos[#photos + 1] = photo
    end

    if #photos == 0 then
        LrDialogs.message(
            "AI Exposure Assist",
            "No photos are selected. Select one copied test photo and try again.",
            "info"
        )
        return nil
    end

    local catalogPath = catalog:getPath()
    local jobPreviewDir = LrPathUtils.child(
        LrPathUtils.parent(catalogPath),
        "runtime/jobs/active/previews"
    )
    LrFileUtils.createAllDirectories(jobPreviewDir)

    local session = LrExportSession {
        photosToExport = photos,
        exportSettings = RunExposureAssist.buildExportSettings(jobPreviewDir),
    }

    session:doExportOnCurrentTask()

    local manifestEntries = {}
    for i, photo in ipairs(photos) do
        local rawPath = photo:getRawMetadata("path")
        local xmpPath = LrPathUtils.replaceExtension(rawPath, "xmp")
        local previewPath = LrPathUtils.child(
            jobPreviewDir,
            RunExposureAssist.previewName(i, rawPath)
        )
        manifestEntries[#manifestEntries + 1] = {
            image_id = LrPathUtils.removeExtension(LrPathUtils.leafName(rawPath)),
            raw_path = rawPath,
            xmp_path = xmpPath,
            preview_path = previewPath,
            seq = i,
        }
    end

    LrDialogs.message(
        "AI Exposure Assist",
        "Export completed for " .. #photos .. " selected photo(s).\n\n"
            .. "Preview folder:\n" .. jobPreviewDir,
        "info"
    )

    return manifestEntries
end

-- Files declared through LrLibraryMenuItems are executed directly by
-- Lightroom. Start the work on an asynchronous Lightroom task and always
-- surface runtime failures to the user instead of failing silently.
LrTasks.startAsyncTask(function()
    local ok, err = xpcall(RunExposureAssist.run, debug.traceback)
    if not ok then
        LrDialogs.message(
            "AI Exposure Assist — Error",
            tostring(err),
            "critical"
        )
    end
end)

return RunExposureAssist
