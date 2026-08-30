--[[
AI Exposure Assist — Prepare AI Package

Short-lived Lightroom command:
- captures active-folder identities and Catalog Exposure2012;
- delegates read-only Previews.lrdata snapshot/extraction to Python;
- writes a durable pass package;
- exits at PACKAGE_READY.

It never calls an AI provider, polls for results, or mutates Lightroom Develop settings.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrTasks = import "LrTasks"
local Support = require "SessionPackageSupport"

local PrepareAIPackage = {}
PrepareAIPackage.isRunning = false

function PrepareAIPackage.run()
    if PrepareAIPackage.isRunning then
        LrDialogs.message("AI Exposure Assist", "A package preparation is already running.", "warning")
        return
    end

    PrepareAIPackage.isRunning = true
    local success, err = LrTasks.pcall(function()
        local catalog = LrApplication.activeCatalog()
        local photos, sourceFolder, exclusions = Support.getActiveFolderPhotos(catalog)

        local confirmStart = LrDialogs.confirm(
            "AI Exposure Assist — Prepare AI Package",
            "Source Folder:\n" .. tostring(sourceFolder) .. "\n\n"
                .. "Eligible RAW photos: " .. tostring(#photos) .. "\n\n"
                .. "Prepare Pass 1 package now?\n"
                .. "• Current Catalog Exposure2012 will be captured\n"
                .. "• Python will read the Lightroom preview cache through a validated read-only snapshot\n"
                .. "• Lightroom-rendered JPEG previews, manifest, task, skills, and schema will be saved to disk\n"
                .. "• No AI provider will be called\n"
                .. "• No Lightroom Develop setting will be changed\n"
                .. "• The plug-in will finish after the package is saved",
            "Prepare Package",
            "Cancel"
        )
        if confirmStart ~= "ok" then
            return
        end

        local sessionId = "sess-" .. tostring(os.time())
        local lrdataPath = Support.loadPreviewCachePath()
        local stagingDir = LrPathUtils.child(Support.REPO_ROOT, "runtime\\staging")
        local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. sessionId .. ".json")
        local selectionPath = Support.writeSelectionSnapshot(
            photos, sourceFolder, exclusions, sessionId, 1
        )

        local startArgs = " --start-session"
            .. " --session-id \"" .. sessionId .. "\""
            .. " --selection \"" .. selectionPath .. "\""
            .. " --lrdata \"" .. lrdataPath .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local startCommand = "cd /D \"" .. Support.REPO_ROOT .. "\" && uv run lr-ai-exposure" .. startArgs
        if LrTasks.execute(startCommand) ~= 0 then
            error("Failed to prepare Pass 1 AI package.")
        end

        local result = Support.readJsonFile(bridgeResultPath)
        if result.status ~= "ok" then
            error("Pass 1 package preparation returned an error.")
        end
        if type(result.pass_dir) ~= "string" or result.pass_dir == "" then
            error("Pass 1 package preparation did not return pass_dir.")
        end

        local decisionDir = result.decision_directory or LrPathUtils.child(result.pass_dir, "decisions")
        local taskPath = result.ai_task or LrPathUtils.child(result.pass_dir, "AI_TASK.md")
        LrDialogs.message(
            "AI Exposure Assist — PACKAGE_READY",
            "AI package saved successfully.\n\n"
                .. "Session: " .. tostring(sessionId) .. "\n"
                .. "Pass: 1\n"
                .. "Eligible RAW: " .. tostring(#photos) .. "\n\n"
                .. "Package folder:\n" .. tostring(result.pass_dir) .. "\n\n"
                .. "AI task:\n" .. tostring(taskPath) .. "\n\n"
                .. "Decision folder:\n" .. tostring(decisionDir) .. "\n\n"
                .. "The Lightroom plug-in is finished. You may run the external AI later, even after closing Lightroom. When decisions are ready, reopen the same Lightroom folder and use 'Import / Apply AI Results'.",
            "info"
        )
    end)

    if not success then
        LrDialogs.message("AI Exposure Assist Error", tostring(err), "critical")
    end
    PrepareAIPackage.isRunning = false
end

LrTasks.startAsyncTask(function()
    PrepareAIPackage.run()
end)

return PrepareAIPackage
