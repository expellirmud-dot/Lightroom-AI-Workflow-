--[[
AI Exposure Assist — cached-thumbnail pilot command.

This bounded live-pilot implementation requests JPEG thumbnails through the
supported Lightroom SDK preview API. It does not read .lrdata directly and it
does not run an export session.

Safety:
- Lightroom SDK is the only source of selected photos and preview bytes.
- No RAW, catalog, .lrdata, XMP, AI, network, or delivery export mutation.
- Output is an AI-analysis artifact only.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"

local RunExposureAssist = {}

local THUMBNAIL_WIDTH = 600
local THUMBNAIL_HEIGHT = 600
local REQUEST_TIMEOUT_SECONDS = 120

function RunExposureAssist.previewName(seq, rawPath)
    local stem = LrPathUtils.removeExtension(LrPathUtils.leafName(rawPath))
    return string.format("%06d__%s.jpg", seq, stem)
end

local function selectedPhotos()
    local catalog = LrApplication.activeCatalog()
    local targets = catalog:getTargetPhotos() or {}
    local photos = {}
    for _, photo in ipairs(targets) do
        photos[#photos + 1] = photo
    end
    return catalog, photos
end

function RunExposureAssist.run()
    local catalog, photos = selectedPhotos()

    if #photos == 0 then
        LrDialogs.message(
            "AI Exposure Assist",
            "No photos are selected. Select copied test photos and try again.",
            "info"
        )
        return nil
    end

    local catalogPath = catalog:getPath()
    local previewDir = LrPathUtils.child(
        LrPathUtils.parent(catalogPath),
        "runtime/jobs/active/cached-thumbnails"
    )
    LrFileUtils.createAllDirectories(previewDir)

    local completed = 0
    local succeeded = 0
    local failures = {}
    local previewPaths = {}

    for index, photo in ipairs(photos) do
        local rawPath = photo:getRawMetadata("path")
        local previewPath = LrPathUtils.child(
            previewDir,
            RunExposureAssist.previewName(index, rawPath)
        )

        photo:requestJpegThumbnail(
            THUMBNAIL_WIDTH,
            THUMBNAIL_HEIGHT,
            function(jpegData, errorMessage)
                if jpegData then
                    local ok, writeError = LrFileUtils.writeFile(previewPath, jpegData)
                    if ok then
                        succeeded = succeeded + 1
                        previewPaths[#previewPaths + 1] = previewPath
                    else
                        failures[#failures + 1] =
                            RunExposureAssist.previewName(index, rawPath)
                            .. ": write failed: " .. tostring(writeError)
                    end
                else
                    failures[#failures + 1] =
                        RunExposureAssist.previewName(index, rawPath)
                        .. ": thumbnail unavailable: " .. tostring(errorMessage)
                end
                completed = completed + 1
            end
        )
    end

    local waited = 0
    while completed < #photos and waited < REQUEST_TIMEOUT_SECONDS do
        LrTasks.sleep(0.1)
        waited = waited + 0.1
    end

    if completed < #photos then
        failures[#failures + 1] =
            "Timed out waiting for " .. (#photos - completed) .. " thumbnail(s)."
    end

    local message =
        "Cached-thumbnail request completed.\n\n"
        .. "Selected: " .. #photos .. "\n"
        .. "Saved: " .. succeeded .. "\n"
        .. "Failed: " .. #failures .. "\n\n"
        .. "Folder:\n" .. previewDir

    if #failures > 0 then
        message = message .. "\n\nFirst error:\n" .. failures[1]
    end

    LrDialogs.message(
        "AI Exposure Assist",
        message,
        (#failures == 0 and succeeded == #photos) and "info" or "warning"
    )

    return {
        selected = #photos,
        saved = succeeded,
        failed = #failures,
        preview_paths = previewPaths,
        preview_directory = previewDir,
    }
end

LrTasks.startAsyncTask(function()
    RunExposureAssist.run()
end)

return RunExposureAssist
