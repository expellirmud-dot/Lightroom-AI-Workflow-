local LrApplication = import "LrApplication"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local Json = require "Json"

local Support = {}

Support.REPO_ROOT = "D:\\ai-tools\\lightroom-ai-exposure"

function Support.sdkCall(func)
    local ok, value = LrTasks.pcall(func)
    if not ok then
        return nil, tostring(value)
    end
    return value, nil
end

function Support.writeUtf8File(path, content)
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

function Support.fileExists(path)
    local file = io.open(path, "rb")
    if file then
        file:close()
        return true
    end
    return false
end

function Support.readJsonFile(path)
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

function Support.normalizePath(path)
    local value = tostring(path or ""):gsub("/", "\\")
    value = value:gsub("\\+$", "")
    return string.lower(value)
end

function Support.loadPreviewCachePath()
    local settingsPath = LrPathUtils.child(Support.REPO_ROOT, "config\\settings.json")
    local settings = Support.readJsonFile(settingsPath)
    local path = settings.preview_cache_path
    if type(path) ~= "string" or path == "" then
        error("config/settings.json missing non-empty preview_cache_path")
    end
    return path
end

function Support.getCatalogExposure2012(photo)
    local settings, err = Support.sdkCall(function()
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

function Support.getActiveFolderPhotos(catalog)
    local ActiveFolderResolver = require "ActiveFolderResolver"
    local resolverResult = ActiveFolderResolver.resolveActiveFolder(catalog)
    if resolverResult.error then
        error("Folder Resolution Error: " .. resolverResult.error .. "\nOpen exactly one Lightroom folder in the Library source panel.")
    end

    local activeFolder = resolverResult.active_folder
    local folderPhotos, photosError = Support.sdkCall(function()
        return activeFolder:getPhotos(true) or {}
    end)
    if not folderPhotos then
        error("Could not enumerate active folder recursively: " .. tostring(photosError))
    end

    local photos = {}
    local seenPaths = {}
    local exclusions = {
        folderPhotoCount = #folderPhotos,
        skippedVirtualCopies = 0,
        skippedVideos = 0,
        skippedUnsupportedFormats = 0,
        skippedMissingPaths = 0,
        skippedDuplicatePaths = 0,
    }

    for _, photo in ipairs(folderPhotos) do
        local isVirtualCopy = photo:getRawMetadata("isVirtualCopy")
        local isVideo = photo:getRawMetadata("isVideo")
        local fileFormat = photo:getRawMetadata("fileFormat")
        local path = photo:getRawMetadata("path")

        if isVirtualCopy then
            exclusions.skippedVirtualCopies = exclusions.skippedVirtualCopies + 1
        elseif isVideo then
            exclusions.skippedVideos = exclusions.skippedVideos + 1
        elseif fileFormat ~= "RAW" then
            exclusions.skippedUnsupportedFormats = exclusions.skippedUnsupportedFormats + 1
        elseif type(path) ~= "string" or path == "" then
            exclusions.skippedMissingPaths = exclusions.skippedMissingPaths + 1
        else
            local pathKey = string.lower(path)
            if seenPaths[pathKey] then
                exclusions.skippedDuplicatePaths = exclusions.skippedDuplicatePaths + 1
            else
                seenPaths[pathKey] = true
                photos[#photos + 1] = photo
            end
        end
    end

    if #photos == 0 then
        error("The active Lightroom folder hierarchy contains no eligible proprietary-RAW master photos.")
    end

    return photos, activeFolder:getPath(), exclusions
end

function Support.buildSelectionPayload(photos, sourceFolder, exclusions, sessionId, passNumber)
    local data = {}
    for _, photo in ipairs(photos) do
        local exposure, exposureError = Support.getCatalogExposure2012(photo)
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

function Support.writeSelectionSnapshot(photos, sourceFolder, exclusions, sessionId, passNumber)
    local stagingDir = LrPathUtils.child(Support.REPO_ROOT, "runtime\\staging")
    LrFileUtils.createAllDirectories(stagingDir)
    local payload = Support.buildSelectionPayload(photos, sourceFolder, exclusions, sessionId, passNumber)
    local path = LrPathUtils.child(
        stagingDir,
        "selection-" .. sessionId .. "-pass-" .. tostring(passNumber) .. ".json"
    )
    Support.writeUtf8File(path, Json.encode(payload))
    return path
end

function Support.loadLatestPointer()
    local path = LrPathUtils.child(Support.REPO_ROOT, "runtime\\staging\\latest-session.json")
    if not Support.fileExists(path) then
        error("No prepared iterative session was found. Prepare an AI package first.")
    end
    local pointer = Support.readJsonFile(path)
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

function Support.readSessionState(pointer)
    return Support.readJsonFile(LrPathUtils.child(pointer.session_dir, "session.json"))
end

function Support.ensureSameActiveFolder(pointer, sourceFolder)
    local passState = Support.readJsonFile(LrPathUtils.child(pointer.pass_dir, "pass-state.json"))
    local expected = passState.source_root
    if type(expected) ~= "string" or expected == "" then
        error("Prepared pass has no persisted source_root")
    end
    if Support.normalizePath(expected) ~= Support.normalizePath(sourceFolder) then
        error(
            "Active Lightroom folder does not match the prepared session.\nExpected: "
                .. tostring(expected) .. "\nActive: " .. tostring(sourceFolder)
        )
    end
end

function Support.decisionReadiness(pointer)
    local frozenPath = LrPathUtils.child(pointer.pass_dir, "ai-decisions.json")
    if Support.fileExists(frozenPath) then
        return true, {}, "FROZEN"
    end

    local manifest = Support.readJsonFile(LrPathUtils.child(pointer.pass_dir, "manifest.json"))
    local decisionDir = LrPathUtils.child(pointer.pass_dir, "decisions")
    local missing = {}
    local expectedCount = 0
    for _, entry in ipairs(manifest.entries or {}) do
        if entry.extraction_status == "FOUND" then
            expectedCount = expectedCount + 1
            local decisionPath = LrPathUtils.child(decisionDir, tostring(entry.image_id) .. ".json")
            if not Support.fileExists(decisionPath) then
                missing[#missing + 1] = tostring(entry.image_id)
            end
        end
    end
    return #missing == 0 and expectedCount > 0, missing, "RAW_FILES"
end

function Support.applyCatalogPlan(catalog, photoMap, plan, resultPath)
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
                local observedBefore, beforeError = Support.getCatalogExposure2012(photo)
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
                        local observedAfter, afterError = Support.getCatalogExposure2012(photo)
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
    Support.writeUtf8File(resultPath, Json.encode(payload))
    return payload
end

return Support
