--[[
AI Exposure Assist — Resume Pending Iterative Session

This command owns the durable side of the WO-035 AI handoff:
- Missing decision files are a normal WAITING_FOR_AI state.
- Existing frozen analysis/plan/apply artifacts are reused rather than repeated.
- Catalog mutation remains WO-034 Exposure2012-only and drift-checked.
- After a verified apply, the command stops so Lightroom can rerender.
- A later Resume prepares the next pass and returns to WAITING_FOR_AI.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local LrProgressScope = import "LrProgressScope"
local Json = require "Json"

local ResumeIterativeSession = {}
ResumeIterativeSession.isRunning = false

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

local function fileExists(path)
    local file = io.open(path, "rb")
    if file then
        file:close()
        return true
    end
    return false
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

local function normalizePath(path)
    local value = tostring(path or ""):gsub("/", "\\")
    value = value:gsub("\\+$", "")
    return string.lower(value)
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
        error("Folder Resolution Error: " .. resolverResult.error .. "\nOpen the same Lightroom folder used to prepare the pending session.")
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

local function loadLatestPointer()
    local path = LrPathUtils.child(REPO_ROOT, "runtime\\staging\\latest-session.json")
    if not fileExists(path) then
        error("No pending iterative session was found. Prepare a session first.")
    end
    local pointer = readJsonFile(path)
    if type(pointer.session_id) ~= "string" or pointer.session_id == "" then
        error("latest-session.json has no valid session_id")
    end
    if type(pointer.pass_dir) ~= "string" or pointer.pass_dir == "" then
        error("latest-session.json has no valid pass_dir")
    end
    if type(pointer.session_dir) ~= "string" or pointer.session_dir == "" then
        error("latest-session.json has no valid session_dir")
    end
    return pointer
end

local function readSessionState(pointer)
    return readJsonFile(LrPathUtils.child(pointer.session_dir, "session.json"))
end

local function ensureSameActiveFolder(pointer, sourceFolder)
    local passState = readJsonFile(LrPathUtils.child(pointer.pass_dir, "pass-state.json"))
    local expected = passState.source_root
    if type(expected) ~= "string" or expected == "" then
        error("Pending pass has no persisted source_root")
    end
    if normalizePath(expected) ~= normalizePath(sourceFolder) then
        error(
            "Active Lightroom folder does not match the pending session.\nExpected: "
                .. tostring(expected) .. "\nActive: " .. tostring(sourceFolder)
        )
    end
end

local function decisionReadiness(pointer)
    local frozenPath = LrPathUtils.child(pointer.pass_dir, "ai-decisions.json")
    if fileExists(frozenPath) then
        return true, {}, "FROZEN"
    end

    local manifest = readJsonFile(LrPathUtils.child(pointer.pass_dir, "manifest.json"))
    local decisionDir = LrPathUtils.child(pointer.pass_dir, "decisions")
    local missing = {}
    local expectedCount = 0
    for _, entry in ipairs(manifest.entries or {}) do
        if entry.extraction_status == "FOUND" then
            expectedCount = expectedCount + 1
            local decisionPath = LrPathUtils.child(decisionDir, tostring(entry.image_id) .. ".json")
            if not fileExists(decisionPath) then
                missing[#missing + 1] = tostring(entry.image_id)
            end
        end
    end
    return #missing == 0 and expectedCount > 0, missing, "RAW_FILES"
end

local function showWaitingForAI(pointer, missing)
    local previewMissing = {}
    for i = 1, math.min(#missing, 8) do
        previewMissing[#previewMissing + 1] = missing[i]
    end
    local suffix = ""
    if #missing > 0 then
        suffix = "\nMissing decision files: " .. tostring(#missing)
        if #previewMissing > 0 then
            suffix = suffix .. "\nExamples: " .. table.concat(previewMissing, ", ")
        end
    end
    LrDialogs.message(
        "AI Exposure Assist — WAITING_FOR_AI",
        "Session: " .. tostring(pointer.session_id) .. "\n"
            .. "Pass: " .. tostring(pointer.pass_number) .. "\n\n"
            .. "Decision folder:\n" .. LrPathUtils.child(pointer.pass_dir, "decisions")
            .. suffix
            .. "\n\nNo Lightroom setting was changed. Add the remaining decision JSON files, then Resume again.",
        "info"
    )
end

local function prepareNextPass(pointer, photos, sourceFolder, exclusions)
    local nextPass = tonumber(pointer.pass_number) + 1
    local stagingDir = LrPathUtils.child(REPO_ROOT, "runtime\\staging")
    local lrdataPath = loadPreviewCachePath(REPO_ROOT)
    local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. pointer.session_id .. ".json")
    local selectionPath = writeSelectionSnapshot(
        stagingDir, photos, sourceFolder, exclusions, pointer.session_id, nextPass
    )

    local prepArgs = " --prepare-session-pass"
        .. " --session-id \"" .. pointer.session_id .. "\""
        .. " --pass-number " .. tostring(nextPass)
        .. " --parent-pass-id \"" .. tostring(pointer.pass_id or "") .. "\""
        .. " --selection \"" .. selectionPath .. "\""
        .. " --lrdata \"" .. lrdataPath .. "\""
        .. " --bridge-result \"" .. bridgeResultPath .. "\""
    local prepCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. prepArgs
    if LrTasks.execute(prepCommand) ~= 0 then
        error("Failed to prepare Pass " .. tostring(nextPass) .. ". Lightroom previews may not be fresh yet.")
    end

    local prepared = readJsonFile(bridgeResultPath)
    if prepared.status ~= "ok" then
        error("Pass " .. tostring(nextPass) .. " preparation returned an error.")
    end
    LrDialogs.message(
        "AI Exposure Assist — WAITING_FOR_AI",
        "Pass " .. tostring(nextPass) .. " is prepared.\n\n"
            .. "Session: " .. tostring(pointer.session_id) .. "\n"
            .. "Decision folder:\n" .. tostring(prepared.decision_directory or LrPathUtils.child(prepared.pass_dir, "decisions"))
            .. "\n\nNo AI provider was called. Add decision JSON files, then Resume again.",
        "info"
    )
end

function ResumeIterativeSession.run()
    if ResumeIterativeSession.isRunning then
        LrDialogs.message("AI Exposure Assist", "A resume operation is already running.", "warning")
        return
    end

    ResumeIterativeSession.isRunning = true
    local success, err = LrTasks.pcall(function()
        local pointer = loadLatestPointer()
        local sessionState = readSessionState(pointer)
        if sessionState.is_converged == true then
            LrDialogs.message(
                "AI Exposure Assist — Session Complete",
                "Session " .. tostring(pointer.session_id) .. " is already converged. No further apply is required.",
                "info"
            )
            return
        end

        local catalog = LrApplication.activeCatalog()
        local photos, sourceFolder, exclusions = getActiveFolderPhotos(catalog)
        ensureSameActiveFolder(pointer, sourceFolder)

        local maxPasses = tonumber((sessionState.policy or {}).maximum_passes) or 4
        local currentPass = tonumber(pointer.pass_number) or 1
        local evidencePath = LrPathUtils.child(pointer.pass_dir, "catalog-apply-evidence.json")

        -- A confirmed pass is never re-applied. A later Resume becomes the
        -- explicit Lightroom-rerender boundary before preparing the next pass.
        if fileExists(evidencePath) then
            if currentPass >= maxPasses then
                LrDialogs.message(
                    "AI Exposure Assist — Session Stopped",
                    "The confirmed pass reached the configured maximum of " .. tostring(maxPasses) .. " passes.",
                    "info"
                )
                return
            end
            prepareNextPass(pointer, photos, sourceFolder, exclusions)
            return
        end

        local decisionsReady, missing = decisionReadiness(pointer)
        if not decisionsReady then
            showWaitingForAI(pointer, missing)
            return
        end

        local photoMap = {}
        for _, photo in ipairs(photos) do
            photoMap[tostring(photo.localIdentifier)] = photo
        end

        local stagingDir = LrPathUtils.child(REPO_ROOT, "runtime\\staging")
        local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. pointer.session_id .. ".json")
        local progress = LrProgressScope({
            title = "AI Exposure Assist",
            caption = "Pass " .. tostring(currentPass) .. ": validating prepared decisions...",
        })

        local frozenPath = LrPathUtils.child(pointer.pass_dir, "ai-decisions.json")
        if not fileExists(frozenPath) then
            local analyzeArgs = " --analyze-session-pass"
                .. " --session-id \"" .. pointer.session_id .. "\""
                .. " --pass-number " .. tostring(currentPass)
                .. " --bridge-result \"" .. bridgeResultPath .. "\""
            local analyzeCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. analyzeArgs
            if LrTasks.execute(analyzeCommand) ~= 0 then
                error("Pass " .. tostring(currentPass) .. " decision validation/freeze failed.")
            end
        end

        progress:setCaption("Pass " .. tostring(currentPass) .. ": building Catalog apply plan...")
        local planPath = LrPathUtils.child(pointer.pass_dir, "catalog-apply-plan.json")
        if not fileExists(planPath) then
            local planArgs = " --apply-session-pass"
                .. " --session-id \"" .. pointer.session_id .. "\""
                .. " --pass-number " .. tostring(currentPass)
                .. " --authorize-apply \"" .. pointer.session_id .. "\""
                .. " --bridge-result \"" .. bridgeResultPath .. "\""
            local planCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. planArgs
            if LrTasks.execute(planCommand) ~= 0 then
                error("Pass " .. tostring(currentPass) .. " Catalog apply planning failed.")
            end
        end

        local plan = readJsonFile(planPath)
        local resultPath = LrPathUtils.child(
            stagingDir,
            "catalog-apply-result-" .. pointer.session_id .. "-pass-" .. tostring(currentPass) .. ".json"
        )

        if not fileExists(resultPath) then
            progress:setCaption("Pass " .. tostring(currentPass) .. ": applying Exposure2012 in Lightroom Catalog...")
            applyCatalogPlan(catalog, photoMap, plan, resultPath)
        end

        progress:setCaption("Pass " .. tostring(currentPass) .. ": confirming Lightroom-observed results...")
        local confirmArgs = " -m lr_ai_exposure.catalog_confirm"
            .. " --session-id \"" .. pointer.session_id .. "\""
            .. " --pass-number " .. tostring(currentPass)
            .. " --apply-result \"" .. resultPath .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local confirmCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run python" .. confirmArgs
        if LrTasks.execute(confirmCommand) ~= 0 then
            error("Pass " .. tostring(currentPass) .. " Catalog confirmation failed.")
        end

        local result = readJsonFile(bridgeResultPath)
        if result.status ~= "ok" then
            error("Pass " .. tostring(currentPass) .. " Catalog confirmation returned an error.")
        end
        progress:done()

        if result.is_converged or currentPass >= maxPasses then
            LrDialogs.message(
                "AI Exposure Assist — Session Complete",
                "Session: " .. tostring(pointer.session_id) .. "\n"
                    .. "Pass completed: " .. tostring(currentPass) .. "\n"
                    .. "Verified Catalog applies: " .. tostring(result.applied_count or 0) .. "\n"
                    .. "PASS: " .. tostring(result.pass_count or 0) .. "\n"
                    .. "REVIEW: " .. tostring(result.review_count or 0),
                "info"
            )
            return
        end

        LrDialogs.message(
            "AI Exposure Assist — WAITING_FOR_RERENDER",
            "Pass " .. tostring(currentPass) .. " was confirmed.\n\n"
                .. "Verified Catalog applies: " .. tostring(result.applied_count or 0) .. "\n"
                .. "PASS: " .. tostring(result.pass_count or 0) .. "\n"
                .. "REVIEW: " .. tostring(result.review_count or 0) .. "\n\n"
                .. "Allow Lightroom to refresh its previews. Then use Resume Pending Iterative Session again. The next Resume will prepare Pass " .. tostring(currentPass + 1) .. " and stop at WAITING_FOR_AI.",
            "info"
        )
    end)

    if not success then
        LrDialogs.message("AI Exposure Assist Error", tostring(err), "critical")
    end
    ResumeIterativeSession.isRunning = false
end

LrTasks.startAsyncTask(function()
    ResumeIterativeSession.run()
end)

return ResumeIterativeSession
