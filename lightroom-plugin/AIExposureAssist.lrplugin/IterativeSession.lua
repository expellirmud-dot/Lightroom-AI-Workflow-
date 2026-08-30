--[[
AI Exposure Assist — Whole-Folder Iterative Exposure Session

Orchestrates multi-pass exposure assistance for an entire Lightroom folder hierarchy:
1. Recursively collects all eligible RAW masters from the active folder tree.
2. Initializes an Exposure Session (Pass 1).
3. Evaluates scene groups, references, and PASS / ADJUST / REVIEW decisions.
4. Applies Exposure2012 adjustments with transactional safety.
5. Refreshes metadata in Lightroom for applied photos.
6. Validates render freshness barrier before capturing Pass N+1.
7. Iterates until convergence, maximum passes, or safe stop.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local LrProgressScope = import "LrProgressScope"
local Json = require "Json"

local IterativeSession = {}
IterativeSession.isRunning = false

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
                    error("Select exactly one Lightroom folder before starting an exposure session.")
                end
                activeFolder = source
            end
        end
    end

    if activeFolder == nil then
        error("Open exactly one Lightroom folder in the Library source panel before starting an exposure session.")
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

function IterativeSession.run()
    if IterativeSession.isRunning then
        LrDialogs.message("AI Exposure Assist", "An exposure session is already running.", "warning")
        return
    end

    IterativeSession.isRunning = true
    local success, err = LrTasks.pcall(function()
        local catalog = LrApplication.activeCatalog()
        local photos, sourceFolder, exclusions = getActiveFolderPhotos(catalog)

        local photoMap = {}
        for _, photo in ipairs(photos) do
            photoMap[tostring(photo.localIdentifier)] = photo
        end

        local confirmStart = LrDialogs.confirm(
            "AI Exposure Assist — Start Iterative Session",
            "Source Folder:\n" .. tostring(sourceFolder) .. "\n\n"
                .. "Eligible RAW photos: " .. tostring(#photos) .. "\n\n"
                .. "Start multi-pass Exposure Session?\n"
                .. "• Whole-folder analysis & scene grouping\n"
                .. "• Only crs:Exposure2012 will be adjusted\n"
                .. "• Automatic re-render freshness barrier verification\n"
                .. "• Repeats until converged or safe review",
            "Start Session",
            "Cancel"
        )
        if confirmStart ~= "ok" then
            return
        end

        local stagingDir = LrPathUtils.child(REPO_ROOT, "runtime\\staging")
        LrFileUtils.createAllDirectories(stagingDir)

        local sessionId = "sess-" .. tostring(os.time())
        local selectionData = {}
        for _, photo in ipairs(photos) do
            table.insert(selectionData, {
                id_local = tostring(photo.localIdentifier),
                path = photo:getRawMetadata("path"),
                uuid = photo:getRawMetadata("uuid"),
            })
        end

        local selectionPayload = {
            protocol_version = "1.0",
            session_id = sessionId,
            selected_count = #photos,
            source_folder = sourceFolder,
            folder_photo_count = exclusions.folderPhotoCount,
            photos = selectionData,
        }
        local selectionPath = LrPathUtils.child(stagingDir, "selection-" .. sessionId .. ".json")
        writeUtf8File(selectionPath, Json.encode(selectionPayload))

        local lrdataPath = loadPreviewCachePath(REPO_ROOT)
        local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. sessionId .. ".json")

        -- 1. Start Session & Prepare Pass 1
        local progress = LrProgressScope({
            title = "AI Exposure Assist",
            caption = "Initializing Session and preparing Pass 1...",
        })

        local startArgs = " --start-session"
            .. " --session-id \"" .. sessionId .. "\""
            .. " --selection \"" .. selectionPath .. "\""
            .. " --lrdata \"" .. lrdataPath .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local startCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. startArgs

        local startExit = LrTasks.execute(startCommand)
        if startExit ~= 0 then
            error("Failed to start session. Check bridge result and logs.")
        end

        local currentPass = 1
        local maxPasses = 4
        local totalAppliedEver = 0

        while currentPass <= maxPasses do
            progress:setCaption("Pass " .. tostring(currentPass) .. ": Analyzing scene groups and exposure...")

            -- 2. Analyze Pass N
            local analyzeArgs = " --analyze-session-pass"
                .. " --session-id \"" .. sessionId .. "\""
                .. " --pass-number " .. tostring(currentPass)
                .. " --bridge-result \"" .. bridgeResultPath .. "\""
            local analyzeCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. analyzeArgs
            local analyzeExit = LrTasks.execute(analyzeCommand)
            if analyzeExit ~= 0 then
                error("Pass " .. tostring(currentPass) .. " analysis failed.")
            end

            progress:setCaption("Pass " .. tostring(currentPass) .. ": Applying adjustments and verifying XMP...")

            -- 3. Apply Pass N
            local applyArgs = " --apply-session-pass"
                .. " --session-id \"" .. sessionId .. "\""
                .. " --pass-number " .. tostring(currentPass)
                .. " --authorize-apply \"" .. sessionId .. "\""
                .. " --bridge-result \"" .. bridgeResultPath .. "\""
            local applyCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. applyArgs
            local applyExit = LrTasks.execute(applyCommand)
            if applyExit ~= 0 then
                error("Pass " .. tostring(currentPass) .. " apply failed.")
            end

            local result = readJsonFile(bridgeResultPath)
            local appliedIds = result.applied_image_ids or {}
            local appliedCount = result.applied or #appliedIds
            totalAppliedEver = totalAppliedEver + appliedCount

            -- 4. Refresh metadata in Lightroom for applied photos
            if #appliedIds > 0 then
                progress:setCaption("Pass " .. tostring(currentPass) .. ": Refreshing Lightroom metadata for " .. tostring(#appliedIds) .. " photos...")
                catalog:withWriteAccessDo("Refresh Exposure Metadata", function()
                    for _, imageId in ipairs(appliedIds) do
                        if photoMap[imageId] then
                            photoMap[imageId]:readMetadata()
                        end
                    end
                end)
            end

            -- Check if converged or completed
            if result.is_converged or currentPass >= maxPasses or appliedCount == 0 then
                progress:done()
                LrDialogs.message(
                    "AI Exposure Assist — Session Complete",
                    "Session: " .. sessionId .. "\n"
                        .. "Source: " .. tostring(sourceFolder) .. "\n\n"
                        .. "Total Passes: " .. tostring(currentPass) .. "\n"
                        .. "Photos Adjusted: " .. tostring(totalAppliedEver) .. "\n"
                        .. "Settled PASS: " .. tostring(result.pass_count or 0) .. "\n"
                        .. "Settled REVIEW: " .. tostring(result.review_count or 0) .. "\n\n"
                        .. "All metadata has been refreshed authoritative in Lightroom.",
                    "info"
                )
                break
            end

            -- 5. Prepare for Next Pass
            local nextPass = currentPass + 1
            local continueAction = LrDialogs.confirm(
                "AI Exposure Assist — Pass " .. tostring(currentPass) .. " Complete",
                "Pass " .. tostring(currentPass) .. " results:\n"
                    .. "• Adjusted: " .. tostring(appliedCount) .. "\n"
                    .. "• PASS: " .. tostring(result.pass_count or 0) .. "\n"
                    .. "• REVIEW: " .. tostring(result.review_count or 0) .. "\n\n"
                    .. "Lightroom metadata refreshed. Continue to Pass " .. tostring(nextPass) .. " to recheck residual exposure?",
                "Continue to Pass " .. tostring(nextPass),
                "Stop Here"
            )

            if continueAction ~= "ok" then
                progress:done()
                LrDialogs.message(
                    "AI Exposure Assist — Session Paused",
                    "Session stopped at Pass " .. tostring(currentPass) .. ".\nCurrent adjustments remain safely applied.",
                    "info"
                )
                break
            end

            progress:setCaption("Pass " .. tostring(nextPass) .. ": Validating render freshness barrier and capturing fresh previews...")

            local prepArgs = " --prepare-session-pass"
                .. " --session-id \"" .. sessionId .. "\""
                .. " --pass-number " .. tostring(nextPass)
                .. " --parent-pass-id \"" .. tostring(result.pass_id or "") .. "\""
                .. " --selection \"" .. selectionPath .. "\""
                .. " --lrdata \"" .. lrdataPath .. "\""
                .. " --bridge-result \"" .. bridgeResultPath .. "\""
            local prepCommand = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. prepArgs
            local prepExit = LrTasks.execute(prepCommand)
            if prepExit ~= 0 then
                error("Failed to prepare Pass " .. tostring(nextPass) .. ".")
            end

            currentPass = nextPass
        end
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
