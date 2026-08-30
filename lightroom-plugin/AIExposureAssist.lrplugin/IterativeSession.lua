--[[
AI Exposure Assist — Whole-Folder Iterative Exposure Session

WO-035 splits the workflow at the AI boundary. This entrypoint only prepares
Pass 1 and then stops in WAITING_FOR_AI. It does not invoke an AI provider and
does not mutate the Lightroom Catalog.

WO-034 Catalog safeguards remain in this module as the runtime contract used by
the resume path: Catalog Exposure2012 is authoritative, absolute targets are
drift-checked, and only Exposure2012 may be applied.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local Json = require "Json"

local IterativeSession = {}
IterativeSession.isRunning = false

local REPO_ROOT = "D:\\ai-tools\\lightroom-ai-exposure"

local function sdkCall(func)
    local ok, value = LrTasks.pcall(func)
    if not ok then
        return nil, tostring(value)
    end
    return value, nil
end

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

local function getCatalogExposure2012(photo)
    local settings, err = sdkCall(function()
        return photo:getDevelopSettings()
    end)
    if not settings then
        return nil, "getDevelopSettings failed: " .. tostring(err)
    end
    local exposure = settings.Exposure2012
    if exposure == nil then
        exposure = 0.0
    end
    if type(exposure) ~= "number" then
        return nil, "Catalog Exposure2012 is not numeric"
    end
    return exposure, nil
end

local function getActiveFolderPhotos(catalog)
    local ActiveFolderResolver = require "ActiveFolderResolver"
    local resolverResult = ActiveFolderResolver.resolveActiveFolder(catalog)
    if resolverResult.error then
        error("Folder Resolution Error: " .. resolverResult.error .. "\nOpen exactly one Lightroom folder in the Library source panel before starting an exposure session.")
    end

    local activeFolder = resolverResult.active_folder
    local folderPhotos, photosError = sdkCall(function()
        return activeFolder:getPhotos(true) or {}
    end)
    if not folderPhotos then
        error("Could not enumerate active folder recursively: " .. tostring(photosError))
    end

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
        error("The active Lightroom folder hierarchy contains no eligible proprietary-RAW master photos.")
    end

    return photos, activeFolder:getPath(), {
        folderPhotoCount = #folderPhotos,
        skippedVirtualCopies = skippedVirtualCopies,
        skippedVideos = skippedVideos,
        skippedUnsupportedFormats = skippedUnsupportedFormats,
        skippedMissingPaths = skippedMissingPaths,
        skippedDuplicatePaths = skippedDuplicatePaths,
    }
end

local function buildSelectionPayload(photos, sourceFolder, exclusions, sessionId, passNumber)
    local data = {}
    for _, photo in ipairs(photos) do
        local exposure, exposureError = getCatalogExposure2012(photo)
        if exposure == nil then
            error("Cannot read Catalog Exposure2012 for image " .. tostring(photo.localIdentifier) .. ": " .. tostring(exposureError))
        end
        table.insert(data, {
            id_local = tostring(photo.localIdentifier),
            path = photo:getRawMetadata("path"),
            uuid = photo:getRawMetadata("uuid"),
            catalog_exposure2012 = exposure,
        })
    end
    return {
        protocol_version = "1.1",
        session_id = sessionId,
        pass_number = passNumber,
        selected_count = #photos,
        source_folder = sourceFolder,
        folder_photo_count = exclusions.folderPhotoCount,
        photos = data,
    }
end

local function writeSelectionSnapshot(stagingDir, photos, sourceFolder, exclusions, sessionId, passNumber)
    local payload = buildSelectionPayload(photos, sourceFolder, exclusions, sessionId, passNumber)
    local path = LrPathUtils.child(
        stagingDir,
        "selection-" .. sessionId .. "-pass-" .. tostring(passNumber) .. ".json"
    )
    writeUtf8File(path, Json.encode(payload))
    return path
end

-- Kept here as a static WO-034 safety contract. The start entrypoint never calls
-- this function; Catalog mutation is executed only by ResumeIterativeSession.lua.
local function applyCatalogPlan(catalog, photoMap, plan, resultPath)
    local tolerance = tonumber(plan.catalog_exposure_tolerance) or 0.01
    local results = {}

    catalog:withWriteAccessDo("AI Exposure Assist — Exposure2012", function()
        for _, item in ipairs(plan.items or {}) do
            local imageId = tostring(item.image_id)
            local photo = photoMap[imageId]
            local expectedBefore = tonumber(item.expected_before_exposure2012)
            local target = tonumber(item.target_exposure2012)
            local result = {
                image_id = imageId,
                expected_before_exposure2012 = expectedBefore,
                target_exposure2012 = target,
            }

            if not photo then
                result.status = "PHOTO_ID_NOT_FOUND"
            elseif expectedBefore == nil or target == nil then
                result.status = "PLAN_VALUE_INVALID"
            else
                local observedBefore, beforeError = getCatalogExposure2012(photo)
                result.observed_before_exposure2012 = observedBefore
                if observedBefore == nil then
                    result.status = "CATALOG_READ_FAILED"
                    result.error = beforeError
                elseif math.abs(observedBefore - expectedBefore) > tolerance then
                    result.status = "CATALOG_DRIFT"
                else
                    local applyOk, applyError = LrTasks.pcall(function()
                        photo:applyDevelopSettings({ Exposure2012 = target })
                    end)
                    if not applyOk then
                        result.status = "CATALOG_APPLY_FAILED"
                        result.error = tostring(applyError)
                    else
                        local observedAfter, afterError = getCatalogExposure2012(photo)
                        result.observed_after_exposure2012 = observedAfter
                        if observedAfter == nil then
                            result.status = "CATALOG_VERIFY_FAILED"
                            result.error = afterError
                        elseif math.abs(observedAfter - target) <= tolerance then
                            result.status = "APPLIED_VERIFIED"
                        else
                            result.status = "CATALOG_VERIFY_MISMATCH"
                        end
                    end
                end
            end
            table.insert(results, result)
        end
    end)

    local payload = {
        protocol_version = "1.1",
        operation = "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY_RESULT",
        session_id = plan.session_id,
        pass_id = plan.pass_id,
        pass_number = plan.pass_number,
        results = results,
    }
    writeUtf8File(resultPath, Json.encode(payload))
    return payload
end

function IterativeSession.run()
    if IterativeSession.isRunning then
        LrDialogs.message("AI Exposure Assist", "A session preparation is already running.", "warning")
        return
    end

    IterativeSession.isRunning = true
    local success, err = LrTasks.pcall(function()
        local catalog = LrApplication.activeCatalog()
        local photos, sourceFolder, exclusions = getActiveFolderPhotos(catalog)

        local confirmStart = LrDialogs.confirm(
            "AI Exposure Assist — Prepare Iterative Session",
            "Source Folder:\n" .. tostring(sourceFolder) .. "\n\n"
                .. "Eligible RAW photos: " .. tostring(#photos) .. "\n\n"
                .. "Prepare Pass 1 now?\n"
                .. "• Current Catalog Exposure2012 will be captured\n"
                .. "• Lightroom previews/manifest/schema will be prepared\n"
                .. "• The workflow will stop at WAITING_FOR_AI\n"
                .. "• No AI provider will be called\n"
                .. "• No Lightroom Develop setting will be changed",
            "Prepare Pass 1",
            "Cancel"
        )
        if confirmStart ~= "ok" then
            return
        end

        local stagingDir = LrPathUtils.child(REPO_ROOT, "runtime\\staging")
        LrFileUtils.createAllDirectories(stagingDir)
        local sessionId = "sess-" .. tostring(os.time())
        local lrdataPath = loadPreviewCachePath(REPO_ROOT)
        local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. sessionId .. ".json")
        local selectionPath = writeSelectionSnapshot(
            stagingDir, photos, sourceFolder, exclusions, sessionId, 1
        )

        local startArgs = " --start-session"
            .. " --session-id \"" .. sessionId .. "\""
            .. " --selection \"" .. selectionPath .. "\""
            .. " --lrdata \"" .. lrdataPath .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local startCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. startArgs
        if LrTasks.execute(startCommand) ~= 0 then
            error("Failed to prepare Catalog-authoritative Pass 1.")
        end

        local result = readJsonFile(bridgeResultPath)
        if result.status ~= "ok" then
            error("Pass 1 preparation returned an error.")
        end
        if type(result.pass_dir) ~= "string" or result.pass_dir == "" then
            error("Pass 1 preparation did not return pass_dir.")
        end

        local decisionDir = result.decision_directory or LrPathUtils.child(result.pass_dir, "decisions")
        local taskPath = result.ai_task or LrPathUtils.child(result.pass_dir, "AI_TASK.md")
        LrDialogs.message(
            "AI Exposure Assist — WAITING_FOR_AI",
            "Session prepared successfully.\n\n"
                .. "Session: " .. tostring(sessionId) .. "\n"
                .. "Pass: 1\n"
                .. "Eligible RAW: " .. tostring(#photos) .. "\n\n"
                .. "Decision folder:\n" .. tostring(decisionDir) .. "\n\n"
                .. "AI task:\n" .. tostring(taskPath) .. "\n\n"
                .. "Nothing has been changed in Lightroom. When decision JSON files are ready, use:\n"
                .. "AI Exposure Assist — Resume Pending Iterative Session",
            "info"
        )
    end)

    if not success then
        LrDialogs.message("AI Exposure Assist Error", tostring(err), "critical")
    end
    IterativeSession.isRunning = false
end

LrTasks.startAsyncTask(function()
    IterativeSession.run()
end)

return IterativeSession
