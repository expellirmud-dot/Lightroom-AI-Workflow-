--[[
AI Exposure Assist — Manifest Handoff
Extracts selected-photo identities and writes them to selection.json.
Does NOT request jpeg thumbnails through Lightroom SDK.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local Json = require "Json"
local LrProgressScope = import "LrProgressScope"

local RunExposureAssist = {}
RunExposureAssist.isRunning = false

local function writeUtf8File(path, content)
    local file, openError = io.open(path, "wb")
    if not file then
        error("Could not open file for writing: "
            .. tostring(path)
            .. " — "
            .. tostring(openError))
    end

    local ok, writeError = file:write(content)
    local closeOk, closeError = file:close()

    if not ok then
        error("Could not write file: "
            .. tostring(path)
            .. " — "
            .. tostring(writeError))
    end

    if closeOk == nil then
        error("Could not close file: "
            .. tostring(path)
            .. " — "
            .. tostring(closeError))
    end
end

function RunExposureAssist.run()
    if RunExposureAssist.isRunning then
        LrDialogs.message("AI Exposure Assist", "A job is already running.", "warning")
        return
    end
    
    RunExposureAssist.isRunning = true
    
    local success, err = LrTasks.pcall(function()
        local catalog = LrApplication.activeCatalog()
        local targets = catalog:getTargetPhotos() or {}
        
        local photos = {}
        for _, photo in ipairs(targets) do
            photos[#photos + 1] = photo
        end

        if #photos == 0 then
            LrDialogs.message(
                "AI Exposure Assist",
                "No photos are selected. Select copied test photos and try again.",
                "info"
            )
            return nil
        end

        local catalogPath = catalog:getPath()
        -- Use the repository root for testing, but typically this would be a config.
        -- For WO-026, we will launch it from the known python path.
        local repoRoot = LrPathUtils.parent(LrPathUtils.parent(catalogPath))
        if LrPathUtils.leafName(catalogPath) == "Lightroom-AI-Workflow-" then
             repoRoot = catalogPath
        end
        -- In an actual plugin, we'd find the python script next to the plugin or in a configured path.
        -- We'll just hardcode D:\ai-tools\lightroom-ai-exposure for this environment
        repoRoot = "D:\\ai-tools\\lightroom-ai-exposure"
        local stagingDir = LrPathUtils.child(repoRoot, "runtime\\staging")
        LrFileUtils.createAllDirectories(stagingDir)

        local selectionData = {}
        local photoMap = {}
        for _, photo in ipairs(photos) do
            local path = photo:getRawMetadata("path")
            local id_local = tostring(photo.localIdentifier)
            local uuid = photo:getRawMetadata("uuid")
            
            table.insert(selectionData, {
                id_local = id_local,
                path = path,
                uuid = uuid
            })
            photoMap[id_local] = photo
        end

        local jobId = "job-" .. tostring(os.time())
        local jobData = {
            protocol_version = "1.0",
            job_id = jobId,
            selected_count = #photos,
            requested_mode = "ANALYZE_ONLY", -- By default
            photos = selectionData
        }
        
        -- Prompt user for apply authorization
        local modeResult = LrDialogs.confirm(
            "AI Exposure Assist",
            "Do you want to apply the AI exposure changes or just analyze?",
            "Apply Changes",
            "Cancel",
            "Analyze Only"
        )
        
        if modeResult == "cancel" then
            return
        elseif modeResult == "ok" then
            jobData.requested_mode = "APPLY"
        else
            jobData.requested_mode = "ANALYZE_ONLY"
        end
        
        local json = Json.encode(jobData)
        
        local selectionPath = LrPathUtils.child(stagingDir, "selection.json")
        writeUtf8File(selectionPath, json)

        
        local progressScope = LrProgressScope({
            title = "AI Exposure Assist",
            caption = "Running " .. jobData.requested_mode .. "...",
            functionContext = context
        })
        
        -- Build the CLI command
        local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. jobId .. ".json")
        local pythonCmd = "uv run lr-ai-exposure"

        -- --lrdata MUST point at the .lrdata directory itself, never the catalog
        -- parent directory. Source it explicitly from config/settings.json
        -- "preview_cache_path" and fail closed if it is missing or empty. Do NOT
        -- infer lrdata from the catalog parent (LrPathUtils.parent(catalogPath)),
        -- which resolves to a non-.lrdata directory and breaks cache extraction.
        local settingsPath = LrPathUtils.child(repoRoot, "config\\settings.json")
        local sFile = io.open(settingsPath, "rb")
        if not sFile then
            error("Cannot read config/settings.json for preview_cache_path: " .. tostring(settingsPath))
        end
        local settingsContent = sFile:read("*a")
        sFile:close()
        local settings = Json.decode(settingsContent)
        if type(settings) ~= "table" then
            error("config/settings.json is not a JSON object")
        end
        local lrdataPath = settings.preview_cache_path
        if type(lrdataPath) ~= "string" or lrdataPath == "" then
            error("config/settings.json missing non-empty preview_cache_path (do not infer lrdata from catalog parent)")
        end

        local args = " --selection \"" .. selectionPath .. "\" --lrdata \"" .. lrdataPath .. "\" --bridge-result \"" .. bridgeResultPath .. "\""
        if jobData.requested_mode == "APPLY" then
            args = args .. " --apply --authorize-apply " .. jobId
        else
            args = args .. " --analyze-only"
        end
        
        local fullCmd = "cd /D \"" .. repoRoot .. "\" && " .. pythonCmd .. args
        
        -- Execute
        local exitStatus = LrTasks.execute(fullCmd)
        progressScope:done()
        
        if progressScope:isCanceled() then
            LrDialogs.message("AI Exposure Assist", "Job was cancelled.", "info")
            return
        end
        
        -- Read the result artifact
        local file = io.open(bridgeResultPath, "rb")
        if not file then
            error("Bridge result file absent: " .. tostring(bridgeResultPath))
        end
        local bridgeContent = file:read("*a")
        file:close()
        
        local bridgeResult = Json.decode(bridgeContent)
        if not bridgeResult then
            error("Malformed bridge result JSON")
        end

        if bridgeResult.protocol_version ~= "1.0" then
            error("Protocol version mismatch")
        end

        -- C. Process/status consistency: fail closed on contradictory settlement
        --    BEFORE any success-only identity check, so a safe error result with
        --    job_id == "unknown" surfaces its real upstream cause instead of a
        --    "Job ID mismatch" mask.
        if bridgeResult.status == "error" and exitStatus == 0 then
            error("Process exit 0 contradicts error status")
        end
        if bridgeResult.status == "ok" and exitStatus ~= 0 then
            error("Process exit non-zero contradicts ok status")
        end

        -- D. Authoritative error path: surface the upstream error and stop. Do
        --    NOT run success-only request_id, job_id, manifest, evidence,
        --    refresh, or apply validation on an error result.
        if bridgeResult.status == "error" then
            error(tostring(bridgeResult.error))
        end

        -- E. Success-only path (status == "ok"): validate identity and artifacts.
        if bridgeResult.job_id ~= jobId then
            error("Job ID mismatch")
        end

        local evidencePath = bridgeResult.analysis_evidence
        if jobData.requested_mode == "APPLY" and bridgeResult.apply_evidence and bridgeResult.apply_evidence ~= "" then
            evidencePath = bridgeResult.apply_evidence
        end

        if not evidencePath or evidencePath == "" or not LrFileUtils.exists(evidencePath) then
            error("Reported artifact does not exist: " .. tostring(evidencePath))
        end
        
        -- Capture diagnostics
        local logPath = LrPathUtils.child(stagingDir, "plugin-diagnostics.log")
        local logLines = {
            "Command: " .. fullCmd,
            "Exit code: " .. tostring(exitStatus),
            "Bridge result path: " .. bridgeResultPath,
            "Analysis evidence path: " .. tostring(bridgeResult.analysis_evidence),
            "Apply evidence path: " .. tostring(bridgeResult.apply_evidence)
        }
        writeUtf8File(logPath, table.concat(logLines, "\n"))
        
        local eFile = io.open(evidencePath, "rb")
        local evidenceContent = eFile:read("*a")
        eFile:close()
        local evidencePayload = Json.decode(evidenceContent)
        
        if not evidencePayload then
            error("Failed to parse evidence artifact")
        end
        
        if jobData.requested_mode == "APPLY" then
            local refreshIds = {}
            for _, res in ipairs(evidencePayload.results or {}) do
                if res.status == "APPLIED_VERIFIED" then
                    table.insert(refreshIds, res.image_id)
                end
            end
            
            if #refreshIds > 0 then
                catalog:withWriteAccessDo("Refresh Exposure Metadata", function()
                    for _, id in ipairs(refreshIds) do
                        local p = photoMap[tostring(id)]
                        if p then
                            p:readMetadata()
                        end
                    end
                end)
            end
            
            LrDialogs.message("AI Exposure Assist", "Applied and refreshed " .. tostring(#refreshIds) .. " photos.", "info")
        else
            LrDialogs.message("AI Exposure Assist", "Analysis complete for " .. tostring(#photos) .. " photos.", "info")
        end
        
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
