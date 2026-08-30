--[[
AI Exposure Assist — Prepare Next AI Package

Short-lived Lightroom command used only after the current pass has verified
Catalog apply evidence and Lightroom has rerendered. It captures a new immutable
preview pass through the existing Python render barrier and exits at PACKAGE_READY.

It never imports AI results, applies Exposure2012, calls an AI provider, or polls.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrTasks = import "LrTasks"
local Support = require "SessionPackageSupport"

local PrepareNextAIPackage = {}
PrepareNextAIPackage.isRunning = false

function PrepareNextAIPackage.run()
    if PrepareNextAIPackage.isRunning then
        LrDialogs.message("AI Exposure Assist", "A next-package preparation is already running.", "warning")
        return
    end

    PrepareNextAIPackage.isRunning = true
    local success, err = LrTasks.pcall(function()
        local pointer = Support.loadLatestPointer()
        local sessionState = Support.readSessionState(pointer)
        local currentPass = tonumber(pointer.pass_number) or 1
        local maxPasses = tonumber((sessionState.policy or {}).maximum_passes) or 4

        if sessionState.is_converged == true then
            LrDialogs.message(
                "AI Exposure Assist — Session Complete",
                "Session " .. tostring(pointer.session_id) .. " is already converged. No next package is required.",
                "info"
            )
            return
        end

        if currentPass >= maxPasses then
            LrDialogs.message(
                "AI Exposure Assist — Session Stopped",
                "The current pass reached the configured maximum of " .. tostring(maxPasses) .. " passes.",
                "info"
            )
            return
        end

        local evidencePath = LrPathUtils.child(pointer.pass_dir, "catalog-apply-evidence.json")
        if not Support.fileExists(evidencePath) then
            LrDialogs.message(
                "AI Exposure Assist — APPLY_REQUIRED_FIRST",
                "Pass " .. tostring(currentPass) .. " has no verified Catalog apply evidence.\n\n"
                    .. "Finish the external AI run and use 'Import / Apply AI Results' first.",
                "info"
            )
            return
        end

        local catalog = LrApplication.activeCatalog()
        local photos, sourceFolder, exclusions = Support.getActiveFolderPhotos(catalog)
        Support.ensureSameActiveFolder(pointer, sourceFolder)

        local nextPass = currentPass + 1
        local lrdataPath = Support.loadPreviewCachePath()
        local stagingDir = LrPathUtils.child(Support.REPO_ROOT, "runtime\\staging")
        local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. pointer.session_id .. ".json")
        local selectionPath = Support.writeSelectionSnapshot(
            photos, sourceFolder, exclusions, pointer.session_id, nextPass
        )

        local prepArgs = " --prepare-session-pass"
            .. " --session-id \"" .. pointer.session_id .. "\""
            .. " --pass-number " .. tostring(nextPass)
            .. " --parent-pass-id \"" .. tostring(pointer.pass_id or "") .. "\""
            .. " --selection \"" .. selectionPath .. "\""
            .. " --lrdata \"" .. lrdataPath .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local prepCommand = "cd /D \"" .. Support.REPO_ROOT .. "\" && uv run lr-ai-exposure" .. prepArgs
        if LrTasks.execute(prepCommand) ~= 0 then
            error(
                "Failed to prepare Pass " .. tostring(nextPass)
                    .. ". Lightroom preview freshness may not be proven yet; no AI package was advanced."
            )
        end

        local prepared = Support.readJsonFile(bridgeResultPath)
        if prepared.status ~= "ok" then
            error("Pass " .. tostring(nextPass) .. " package preparation returned an error.")
        end
        if type(prepared.pass_dir) ~= "string" or prepared.pass_dir == "" then
            error("Pass " .. tostring(nextPass) .. " package preparation did not return pass_dir.")
        end

        LrDialogs.message(
            "AI Exposure Assist — PACKAGE_READY",
            "Next AI package saved successfully.\n\n"
                .. "Session: " .. tostring(pointer.session_id) .. "\n"
                .. "Pass: " .. tostring(nextPass) .. "\n\n"
                .. "Package folder:\n" .. tostring(prepared.pass_dir) .. "\n\n"
                .. "Decision folder:\n" .. tostring(prepared.decision_directory or LrPathUtils.child(prepared.pass_dir, "decisions")) .. "\n\n"
                .. "The Lightroom plug-in is finished. Run the external AI later and return to 'Import / Apply AI Results' only when decisions are complete.",
            "info"
        )
    end)

    if not success then
        LrDialogs.message("AI Exposure Assist Error", tostring(err), "critical")
    end
    PrepareNextAIPackage.isRunning = false
end

LrTasks.startAsyncTask(function()
    PrepareNextAIPackage.run()
end)

return PrepareNextAIPackage
