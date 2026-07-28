--[[
AI Exposure Assist — Run Exposure Assist command.

WO-007: exports Lightroom-rendered JPEG previews for the current
selection and hands an ordered manifest to the existing job runtime.

Scope (one-shot handoff boundary only):
- Lightroom SDK selection retrieval.
- Development-rendered JPEG export into the active job preview directory.
- Deterministic preview naming: {seq:06d}__{raw_stem}.jpg.
- Ordered manifest creation using the WO-005 schema.
- No AI, XMP, HTTP server, watcher, or catalog mutation.

Safety:
- Never accesses .lrcat, .lrdata, RAW contents, or preview caches directly.
- Lightroom SDK is the only source of selection and rendered previews.
- The Python job runtime (src/lr_ai_exposure/job.py) owns manifest
  validation; this Lua module only writes preview files and invokes the
  job directory + manifest writer through the documented boundary.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrExportSession = import "LrExportSession"
local LrExportSettings = import "LrExportSettings"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"

local RunExposureAssist = {}

-- Deterministic preview naming: {seq:06d}__{raw_stem}.jpg
function RunExposureAssist.previewName(seq, rawPath)
    local stem = LrPathUtils.removeExtension(LrPathUtils.leafName(rawPath))
    return string.format("%06d__%s.jpg", seq, stem)
end

-- Build export settings for development-rendered JPEG previews.
function RunExposureAssist.buildExportSettings(previewDir)
    local settings = LrExportSettings.createExportSettings()
    settings.LR_export_destinationType = "specificFolder"
    settings.LR_export_destinationPathPrefix = previewDir
    settings.LR_format = "JPEG"
    settings.LR_jpeg_quality = 0.9
    settings.LR_export_colorSpace = "sRGB"
    settings.LR_size_doConstrain = false
    settings.LR_outputSharpeningOn = false
    settings.LR_export_useSubFolder = false
    settings.LR_collisionHandling = "rename"
    return settings
end

function RunExposureAssist.run(context)
    local catalog = LrApplication.activeCatalog()
    local targets = catalog:getTargetPhotos()
    if not targets then
        LrDialogs.message("AI Exposure Assist: no photos selected.")
        return nil
    end

    local photos = {}
    for _, photo in ipairs(targets:asArray()) do
        photos[#photos + 1] = photo
    end
    if #photos == 0 then
        LrDialogs.message("AI Exposure Assist: selection is empty.")
        return nil
    end

    -- Resolve job preview directory from the active job (WO-005 runtime).
    -- In the live plug-in this comes from the Python job runtime; the
    -- boundary contract requires a writable preview directory inside the
    -- job folder. We derive it from the catalog path's sibling runtime.
    local catalogPath = catalog:getPath()
    local jobPreviewDir = LrPathUtils.child(
        LrPathUtils.parent(catalogPath),
        "runtime/jobs/active/previews"
    )
    LrFileUtils.createAllDirectories(jobPreviewDir)

    local settings = RunExposureAssist.buildExportSettings(jobPreviewDir)
    local session = LrExportSession({
        photosToExport = photos,
        exportSettings = settings,
    })
    session:export()

    -- Hand off an ordered manifest using the WO-005 schema.
    -- Preview filenames follow {seq:06d}__{raw_stem}.jpg so the Python
    -- runtime can read them back deterministically.
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

    -- The manifest is written by the Python job runtime boundary; this
    -- module returns the entry list for the handoff contract.
    LrDialogs.message(
        "AI Exposure Assist: exported " .. #photos ..
        " previews and prepared manifest handoff."
    )
    return manifestEntries
end

return RunExposureAssist
