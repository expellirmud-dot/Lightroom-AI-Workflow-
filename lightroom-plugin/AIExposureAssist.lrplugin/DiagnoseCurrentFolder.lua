-- Read-only aggregated diagnostic for the current Lightroom folder.

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local LrProgressScope = import "LrProgressScope"
local Json = require "Json"

local DiagnoseCurrentFolder = {}
DiagnoseCurrentFolder.isRunning = false

local REPO_ROOT = "D:\\ai-tools\\lightroom-ai-exposure"
local SAMPLE_LIMIT = 5

local function writeUtf8File(path, content)
    local file, openError = io.open(path, "wb")
    if not file then
        error("Could not open diagnostic file for writing: " .. tostring(path) .. " - " .. tostring(openError))
    end
    local ok, writeError = file:write(content)
    local closeOk, closeError = file:close()
    if not ok then
        error("Could not write diagnostic file: " .. tostring(path) .. " - " .. tostring(writeError))
    end
    if closeOk == nil then
        error("Could not close diagnostic file: " .. tostring(path) .. " - " .. tostring(closeError))
    end
end

local function readFile(path)
    local file = io.open(path, "rb")
    if not file then
        error("File absent: " .. tostring(path))
    end
    local content = file:read("*a")
    file:close()
    return content
end

local function readJsonFile(path)
    local value = Json.decode(readFile(path))
    if type(value) ~= "table" then
        error("Malformed JSON object: " .. tostring(path))
    end
    return value
end

local function safeCall(defaultValue, func)
    local ok, value = pcall(func)
    if ok then
        return value
    end
    return defaultValue
end

local function safeMetadata(photo, key)
    return safeCall(nil, function()
        return photo:getRawMetadata(key)
    end)
end

local function appendSample(samples, category, sample)
    if samples[category] == nil then
        samples[category] = {}
    end
    if #samples[category] < SAMPLE_LIMIT then
        table.insert(samples[category], sample)
    end
end

local function photoSample(photo, metadata)
    local path = metadata.path
    local filename = metadata.fileName
    if (type(filename) ~= "string" or filename == "") and type(path) == "string" and path ~= "" then
        filename = LrPathUtils.leafName(path)
    end
    return {
        filename = filename,
        id_local = tostring(photo.localIdentifier),
        uuid = metadata.uuid,
        path = path,
        file_format = metadata.fileFormat,
        file_format_display = metadata.fileFormat == nil and "<nil>" or tostring(metadata.fileFormat),
        file_format_type = type(metadata.fileFormat),
        is_virtual_copy = metadata.isVirtualCopy == true,
        is_video = metadata.isVideo == true,
        path_exists = type(path) == "string" and path ~= "" and not not LrFileUtils.exists(path)
    }
end

local function collectLightroomEvidence(catalog)
    local activeSources = safeCall({}, function()
        return catalog:getActiveSources() or {}
    end)
    local sourceEvidence = {}
    local activeFolders = {}
    for _, source in ipairs(activeSources) do
        local sourceType = type(source) == "string" and "string" or safeCall("unknown", function()
            return source:type()
        end)
        local sourceName = type(source) == "string" and source or safeCall(nil, function()
            return source:getName()
        end)
        local sourcePath = type(source) == "string" and nil or safeCall(nil, function()
            return source:getPath()
        end)
        table.insert(sourceEvidence, {
            type = sourceType,
            name = sourceName,
            path = sourcePath
        })
        if sourceType == "LrFolder" then
            table.insert(activeFolders, source)
        end
    end

    local payload = {
        catalog_path = safeCall(nil, function()
            return catalog:getPath()
        end),
        active_sources = sourceEvidence,
        active_folder_count = #activeFolders,
        active_folder_path = nil,
        direct_photo_count = 0,
        child_folder_count = 0,
        recursive_photo_count = 0,
        enumeration_status = "SKIPPED_DEPENDENCY",
        observed_file_formats = {},
        counts = {
            eligible_raw = 0,
            virtual_copies = 0,
            videos = 0,
            unsupported_formats = 0,
            empty_paths = 0,
            offline_paths = 0,
            duplicate_paths = 0
        },
        samples = {},
        eligible_photos = {}
    }

    if #activeFolders ~= 1 then
        payload.enumeration_error = "Exactly one active LrFolder is required; observed " .. tostring(#activeFolders)
        return payload
    end

    local activeFolder = activeFolders[1]
    payload.active_folder_path = safeCall(nil, function()
        return activeFolder:getPath()
    end)

    local function countFolders(f)
        local count = 0
        local kids = safeCall({}, function() return f:getChildren() or {} end)
        for _, k in ipairs(kids) do
            count = count + 1 + countFolders(k)
        end
        return count
    end
    payload.child_folder_count = countFolders(activeFolder)

    local ok_direct, directPhotos = pcall(function()
        return activeFolder:getPhotos(false) or {}
    end)
    local ok_recurse, recursivePhotos = pcall(function()
        return activeFolder:getPhotos(true) or {}
    end)

    if not ok_recurse then
        payload.enumeration_status = "FAIL"
        payload.enumeration_error = tostring(recursivePhotos)
        return payload
    end

    payload.enumeration_status = "PASS"
    payload.direct_photo_count = ok_direct and #directPhotos or 0
    payload.recursive_photo_count = #recursivePhotos
    local folderPhotos = recursivePhotos

    local formatMap = {}
    local seenPaths = {}

    for _, photo in ipairs(folderPhotos) do
        local metadata = {
            isVirtualCopy = safeMetadata(photo, "isVirtualCopy"),
            isVideo = safeMetadata(photo, "isVideo"),
            fileFormat = safeMetadata(photo, "fileFormat"),
            path = safeMetadata(photo, "path"),
            uuid = safeMetadata(photo, "uuid"),
            fileName = safeMetadata(photo, "fileName")
        }
        local sample = photoSample(photo, metadata)
        local formatType = type(metadata.fileFormat)
        local formatDisplay = metadata.fileFormat == nil and "<nil>" or tostring(metadata.fileFormat)
        local formatKey = formatType .. ":" .. formatDisplay
        if formatMap[formatKey] == nil then
            formatMap[formatKey] = {
                value = metadata.fileFormat,
                value_display = formatDisplay,
                value_type = formatType,
                count = 0
            }
        end
        formatMap[formatKey].count = formatMap[formatKey].count + 1

        local category = nil
        if metadata.isVirtualCopy then
            payload.counts.virtual_copies = payload.counts.virtual_copies + 1
            category = "virtual_copies"
        elseif metadata.isVideo then
            payload.counts.videos = payload.counts.videos + 1
            category = "videos"
        elseif metadata.fileFormat ~= "RAW" then
            payload.counts.unsupported_formats = payload.counts.unsupported_formats + 1
            category = metadata.fileFormat == nil and "unknown_formats" or "unsupported_formats"
        elseif type(metadata.path) ~= "string" or metadata.path == "" then
            payload.counts.empty_paths = payload.counts.empty_paths + 1
            category = "empty_paths"
        elseif not LrFileUtils.exists(metadata.path) then
            payload.counts.offline_paths = payload.counts.offline_paths + 1
            category = "offline_paths"
        else
            local pathKey = string.lower(metadata.path)
            if seenPaths[pathKey] then
                payload.counts.duplicate_paths = payload.counts.duplicate_paths + 1
                category = "duplicate_paths"
            else
                seenPaths[pathKey] = true
                payload.counts.eligible_raw = payload.counts.eligible_raw + 1
                table.insert(payload.eligible_photos, sample)
                category = "eligible_raw"
            end
        end
        appendSample(payload.samples, category, sample)
    end

    for _, item in pairs(formatMap) do
        table.insert(payload.observed_file_formats, item)
    end
    table.sort(payload.observed_file_formats, function(a, b)
        return (a.value_type .. ":" .. a.value_display) < (b.value_type .. ":" .. b.value_display)
    end)
    return payload
end

local function validateBridgeResult(result, diagnosticId, exitStatus)
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
    if result.job_id ~= diagnosticId then
        error("Diagnostic ID mismatch")
    end
    if result.mode ~= "DIAGNOSE_CURRENT_FOLDER" or result.diagnostic_completed ~= true then
        error("Unexpected or incomplete diagnostic bridge result")
    end
    for _, field in ipairs({ "preflight_json", "diagnostic_txt" }) do
        local path = result[field]
        if type(path) ~= "string" or path == "" or not LrFileUtils.exists(path) then
            error("Reported diagnostic artifact does not exist: " .. tostring(field) .. "=" .. tostring(path))
        end
    end
end

function DiagnoseCurrentFolder.run()
    if DiagnoseCurrentFolder.isRunning then
        LrDialogs.message("AI Exposure Assist", "A current-folder diagnostic is already running.", "warning")
        return
    end

    DiagnoseCurrentFolder.isRunning = true
    local success, err = LrTasks.pcall(function()
        local diagnosticId = "diagnostic-" .. tostring(os.time())
        local payload = collectLightroomEvidence(LrApplication.activeCatalog())
        payload.protocol_version = "1.0"
        payload.operation = "DIAGNOSE_CURRENT_FOLDER"
        payload.diagnostic_id = diagnosticId
        payload.plugin = { version = "1.1.0", build = 3 }

        local stagingDir = LrPathUtils.child(REPO_ROOT, "runtime\\staging")
        LrFileUtils.createAllDirectories(stagingDir)
        local inputPath = LrPathUtils.child(stagingDir, "diagnostic-input-" .. diagnosticId .. ".json")
        local bridgeResultPath = LrPathUtils.child(stagingDir, "diagnostic-bridge-" .. diagnosticId .. ".json")
        writeUtf8File(inputPath, Json.encode(payload))

        local command = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure"
            .. " --diagnose-current-folder"
            .. " --diagnostic-input \"" .. inputPath .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local progress = LrProgressScope({
            title = "AI Exposure Assist",
            caption = "Collecting current-folder diagnostic evidence..."
        })
        local exitStatus = LrTasks.execute(command)
        progress:done()

        local result = readJsonFile(bridgeResultPath)
        validateBridgeResult(result, diagnosticId, exitStatus)
        local summary = readFile(result.diagnostic_txt)
        if #summary > 3500 then
            summary = string.sub(summary, 1, 3500) .. "\n[Summary truncated; see the report file.]"
        end
        LrDialogs.message(
            "AI Exposure Assist - Diagnostic Complete",
            summary .. "\nReport:\n" .. tostring(result.preflight_json),
            result.overall_readiness == "READY_FOR_SESSION" and "info" or "warning"
        )
    end)

    if not success then
        LrDialogs.message("AI Exposure Assist Diagnostic Error", tostring(err), "critical")
    end
    DiagnoseCurrentFolder.isRunning = false
end

LrTasks.startAsyncTask(function()
    DiagnoseCurrentFolder.run()
end)

return DiagnoseCurrentFolder
