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
            local id_local = tostring(photo:localIdentifier())
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
        local ok, fileErr = LrFileUtils.writeFile(selectionPath, json)
        
        if not ok then
            error("Failed to write selection.json: " .. tostring(fileErr))
        end
        
        local progressScope = LrProgressScope({
            title = "AI Exposure Assist",
            caption = "Running " .. jobData.requested_mode .. "...",
            functionContext = context
        })
        
        -- Build the CLI command
        local pythonCmd = "uv run lr-ai-exposure"
        local args = " --selection \"" .. selectionPath .. "\""
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
        -- The CLI writes apply-evidence.json or analysis-evidence.json in the job directory
        local jobDir = LrPathUtils.child(LrPathUtils.child(stagingDir, "jobs"), jobId)
        local evidenceFile = "analysis-evidence.json"
        if jobData.requested_mode == "APPLY" then
            evidenceFile = "apply-evidence.json"
        end
        
        local evidencePath = LrPathUtils.child(jobDir, evidenceFile)
        
        if not LrFileUtils.exists(evidencePath) then
            -- Fallback to bridge output if not written there
            LrDialogs.message("AI Exposure Assist", "Job finished but no evidence artifact found at " .. evidencePath .. " (Exit status: " .. tostring(exitStatus) .. ")", "critical")
            return
        end
        
        local evidenceContent = LrFileUtils.readFile(evidencePath)
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
