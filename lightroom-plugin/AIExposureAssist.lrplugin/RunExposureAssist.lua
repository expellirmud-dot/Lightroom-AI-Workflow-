--[[
AI Exposure Assist — Prepare Current Lightroom Folder

Reads every eligible proprietary-RAW master photo in exactly one active
Lightroom folder, asks Python to snapshot the preview cache and extract the
complete folder once, then stops. It does not call an AI and does not write XMP.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local LrProgressScope = import "LrProgressScope"
local Json = require "Json"

local RunExposureAssist = {}
RunExposureAssist.isRunning = false

local REPO_ROOT = "D:\\ai-tools\\lightroom-ai-exposure"

local function writeUtf8File(path, content)
    local file, openError = io.open(path, "wb")
    if not file then
        error("Could not open file for writing: " .. tostring(path) .. " — " .. tostring(openError))
    end
    local ok, writeError = file:write(content)
    local closeOk, closeError = file:close()
    if not ok then
        error("Could not write file: " .. tostring(path) .. " — " .. tostring(writeError))
    end
    if closeOk == nil then
        error("Could not close file: " .. tostring(path) .. " — " .. tostring(closeError))
    end
end

local function readJsonFile(path)
    local file = io.open(path, "rb")
    if not file then
        error("File absent: " .. tostring(path))
    end
    local content = file:read("*a")
    file:close()
    local value = Json.decode(content)
    if type(value) ~= "table" then
        error("Malformed JSON object: " .. tostring(path))
    end
    return value
end

local function loadPreviewCachePath(repoRoot)
    local settingsPath = LrPathUtils.child(repoRoot, "config\\settings.json")
    local settings = readJsonFile(settingsPath)
    local path = settings.preview_cache_path
    if type(path) ~= "string" or path == "" then
        error("config/settings.json missing non-empty preview_cache_path")
    end
    return path
end

local function getActiveFolderPhotos(catalog)
    local activeSources = catalog:getActiveSources() or {}
    local activeFolder = nil

    for _, source in ipairs(activeSources) do
        if type(source) ~= "string" then
            local ok, sourceType = pcall(function()
                return source:type()
            end)
            if ok and sourceType == "LrFolder" then
                if activeFolder ~= nil then
                    error("Select exactly one Lightroom folder before preparing a job.")
                end
                activeFolder = source
            end
        end
    end

    if activeFolder == nil then
        error("Open exactly one Lightroom folder in the Library source panel before preparing a job.")
    end

    local folderPhotos = activeFolder:getPhotos(true) or {}
    local photos = {}
    local seenPaths = {}
    local skippedVirtualCopies = 0
    local skippedVideos = 0
    local skippedUnsupportedFormats = 0
    local skippedMissingPaths = 0
    local skippedDuplicatePaths = 0

    for _, photo in ipairs(folderPhotos) do
        local isVirtualCopy = photo:getRawMetadata("isVirtualCopy")
        local isVideo = photo:getRawMetadata("isVideo")
        local fileFormat = photo:getRawMetadata("fileFormat")
        local path = photo:getRawMetadata("path")

        if isVirtualCopy then
            skippedVirtualCopies = skippedVirtualCopies + 1
        elseif isVideo then
            skippedVideos = skippedVideos + 1
        elseif fileFormat ~= "RAW" then
            -- DNG/JPG/TIFF/PSD normally store metadata in the source file.
            -- This project is sidecar-only and must never modify originals.
            skippedUnsupportedFormats = skippedUnsupportedFormats + 1
        elseif type(path) ~= "string" or path == "" then
            skippedMissingPaths = skippedMissingPaths + 1
        else
            local pathKey = string.lower(path)
            if seenPaths[pathKey] then
                skippedDuplicatePaths = skippedDuplicatePaths + 1
            else
                seenPaths[pathKey] = true
                photos[#photos + 1] = photo
            end
        end
    end

    if #photos == 0 then
        error("The active Lightroom folder contains no eligible proprietary-RAW master photos.")
    end

    return photos, activeFolder:getPath(), {
        folderPhotoCount = #folderPhotos,
        skippedVirtualCopies = skippedVirtualCopies,
        skippedVideos = skippedVideos,
        skippedUnsupportedFormats = skippedUnsupportedFormats,
        skippedMissingPaths = skippedMissingPaths,
        skippedDuplicatePaths = skippedDuplicatePaths
    }
end

local function validateBridgeResult(result, expectedJobId, exitStatus)
    if result.protocol_version ~= "1.0" then
        error("Protocol version mismatch")
    end
    if result.status == "error" and exitStatus == 0 then
        error("Process exit 0 contradicts error status")
    end
    if result.status == "ok" and exitStatus ~= 0 then
        error("Process exit non-zero contradicts ok status")
    end
    if result.status == "error" then
        error(tostring(result.error))
    end
    if result.job_id ~= expectedJobId then
        error("Job ID mismatch")
    end
    if result.mode ~= "PREPARE" then
        error("Unexpected bridge mode: " .. tostring(result.mode))
    end
    for _, field in ipairs({ "job_dir", "manifest", "preview_directory", "decision_directory", "decision_schema", "ai_task" }) do
        local path = result[field]
        if type(path) ~= "string" or path == "" or not LrFileUtils.exists(path) then
            error("Reported prepared-job artifact does not exist: " .. tostring(field) .. "=" .. tostring(path))
        end
    end
end

function RunExposureAssist.run()
    if RunExposureAssist.isRunning then
        LrDialogs.message("AI Exposure Assist", "A folder prepare job is already running.", "warning")
        return
    end

    RunExposureAssist.isRunning = true
    local success, err = LrTasks.pcall(function()
        local catalog = LrApplication.activeCatalog()
        local photos, sourceFolder, exclusions = getActiveFolderPhotos(catalog)

        local stagingDir = LrPathUtils.child(REPO_ROOT, "runtime\\staging")
        LrFileUtils.createAllDirectories(stagingDir)

        local jobId = "job-" .. tostring(os.time())
        local selectionData = {}
        for _, photo in ipairs(photos) do
            table.insert(selectionData, {
                id_local = tostring(photo.localIdentifier),
                path = photo:getRawMetadata("path"),
                uuid = photo:getRawMetadata("uuid")
            })
        end

        local selectionPayload = {
            protocol_version = "1.0",
            job_id = jobId,
            selected_count = #photos,
            requested_mode = "PREPARE",
            source_folder = sourceFolder,
            folder_photo_count = exclusions.folderPhotoCount,
            skipped_virtual_copies = exclusions.skippedVirtualCopies,
            skipped_videos = exclusions.skippedVideos,
            skipped_unsupported_formats = exclusions.skippedUnsupportedFormats,
            skipped_missing_paths = exclusions.skippedMissingPaths,
            skipped_duplicate_paths = exclusions.skippedDuplicatePaths,
            photos = selectionData
        }
        local selectionPath = LrPathUtils.child(stagingDir, "selection-" .. jobId .. ".json")
        writeUtf8File(selectionPath, Json.encode(selectionPayload))

        local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. jobId .. ".json")
        local lrdataPath = loadPreviewCachePath(REPO_ROOT)
        local args = " --prepare-job"
            .. " --selection \"" .. selectionPath .. "\""
            .. " --lrdata \"" .. lrdataPath .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local command = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. args

        local progress = LrProgressScope({
            title = "AI Exposure Assist",
            caption = "Preparing the current folder: " .. tostring(#photos) .. " RAW master photos..."
        })
        local exitStatus = LrTasks.execute(command)
        progress:done()

        local result = readJsonFile(bridgeResultPath)
        validateBridgeResult(result, jobId, exitStatus)

        local diagnosticsPath = LrPathUtils.child(stagingDir, "plugin-diagnostics.log")
        writeUtf8File(diagnosticsPath, table.concat({
            "Operation: PREPARE_FOLDER",
            "Command: " .. command,
            "Exit code: " .. tostring(exitStatus),
            "Job ID: " .. jobId,
            "Source folder: " .. tostring(sourceFolder),
            "Eligible RAW master photos: " .. tostring(#photos),
            "Skipped virtual copies: " .. tostring(exclusions.skippedVirtualCopies),
            "Skipped videos: " .. tostring(exclusions.skippedVideos),
            "Skipped unsupported formats: " .. tostring(exclusions.skippedUnsupportedFormats),
            "Skipped missing paths: " .. tostring(exclusions.skippedMissingPaths),
            "Skipped duplicate paths: " .. tostring(exclusions.skippedDuplicatePaths),
            "Job directory: " .. tostring(result.job_dir),
            "AI task: " .. tostring(result.ai_task)
        }, "\n"))

        LrDialogs.message(
            "AI Exposure Assist — Folder Prepared",
            "Source folder:\n" .. tostring(sourceFolder) .. "\n\n"
                .. "Prepared " .. tostring(result.total_found or 0) .. " previews from "
                .. tostring(result.total_selected or #photos) .. " eligible RAW master photos.\n\n"
                .. "Give this job folder to any vision-capable AI app:\n"
                .. tostring(result.job_dir) .. "\n\n"
                .. "The AI must read AI_TASK.md and save decisions in:\n"
                .. tostring(result.decision_directory) .. "\n\n"
                .. "After decisions are complete, run ‘AI Exposure Assist — Apply Prepared Job’.",
            "info"
        )
    end)

    if not success then
        LrDialogs.message("AI Exposure Assist Error", tostring(err), "critical")
    end
    RunExposureAssist.isRunning = false
end

LrTasks.startAsyncTask(function()
    RunExposureAssist.run()
end)

return RunExposureAssist
