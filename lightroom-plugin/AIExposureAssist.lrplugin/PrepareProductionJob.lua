--[[
AI Exposure Assist — Prepare Production Job

Bounded WO-053 one-job preparation shell. It captures the active Lightroom
folder identity and current Catalog Exposure2012, writes one protocol-2.0
selection snapshot, and delegates read-only preview/package preparation to
Python. It never calls an AI provider and never mutates Lightroom Develop
settings.

This module is the production preparation step delegated by the normal
Continue Exposure Workflow route. It remains non-mutating and has no Catalog
writer of its own.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrTasks = import "LrTasks"
local Support = require "SessionPackageSupport"

local PrepareProductionJob = {}
PrepareProductionJob.isRunning = false

local function ensureProductionPreviews(photos, targetSize)
    local pending = #photos
    if pending == 0 then
        return
    end

    local failures = {}
    local requests = {}
    for _, photo in ipairs(photos) do
        local imageId = tostring(photo.localIdentifier)
        requests[#requests + 1] = photo:requestJpegThumbnail(
            targetSize,
            targetSize,
            function(jpegData, err)
                if jpegData == nil then
                    failures[#failures + 1] = imageId .. ": " .. tostring(err or "thumbnail render failed")
                end
                pending = pending - 1
            end
        )
    end

    -- requestJpegThumbnail renders a requested preview when Lightroom does not
    -- already have one. Keep request objects alive until every callback fires.
    -- This avoids failing the production handoff merely because the user has not
    -- previously opened every photo at Standard Preview size.
    local maxWaitIterations = 900 -- 90 seconds, bounded
    for _ = 1, maxWaitIterations do
        if pending == 0 then
            break
        end
        LrTasks.sleep(0.10)
    end

    if pending ~= 0 then
        error("PREVIEW_WARM_TIMEOUT: Lightroom did not finish " .. tostring(pending)
            .. " preview request(s) within 90 seconds.")
    end
    if #failures > 0 then
        error("PREVIEW_WARM_FAILED: " .. table.concat(failures, "; "))
    end

    -- Release request handles only after callbacks have completed.
    requests = nil
end

function PrepareProductionJob.run()
    if PrepareProductionJob.isRunning then
        LrDialogs.message(
            "AI Exposure Assist",
            "Production job preparation is already running.",
            "warning"
        )
        return
    end

    PrepareProductionJob.isRunning = true
    local success, err = LrTasks.pcall(function()
        local catalog = LrApplication.activeCatalog()
        local photos, sourceFolder, exclusions = Support.getActiveFolderPhotos(catalog)

        local choice = LrDialogs.confirm(
            "AI Exposure Assist — Prepare Production Job",
            "Source Folder:\n" .. tostring(sourceFolder) .. "\n\n"
                .. "Eligible RAW photos: " .. tostring(#photos) .. "\n\n"
                .. "Prepare one production analysis package?\n"
                .. "• Current Catalog Exposure2012 is captured read-only\n"
                .. "• Existing Lightroom preview cache is read through the validated snapshot path\n"
                .. "• One manifest/contact-sheet/visual-semantics package is created\n"
                .. "• No AI provider is called by this command\n"
                .. "• No Lightroom Develop setting is changed",
            "Prepare Production Job",
            "Cancel"
        )
        if choice ~= "ok" then
            return
        end

        -- Ensure the requested Standard Preview-class tier exists before Python
        -- snapshots the cache. This is read/render preparation only; it does not
        -- change Develop settings or Catalog Exposure values.
        ensureProductionPreviews(photos, 1440)

        local jobId = "job-" .. tostring(os.time())
        local lrdataPath = Support.loadPreviewCachePath()
        local stagingDir = LrPathUtils.child(Support.REPO_ROOT, "runtime\\staging")
        local resultPath = LrPathUtils.child(stagingDir, "production-bridge-result-" .. jobId .. ".json")
        local selectionPath = Support.writeProductionSelectionSnapshot(
            photos, sourceFolder, exclusions, jobId
        )

        local args = " --prepare-production-job"
            .. " --selection \"" .. selectionPath .. "\""
            .. " --lrdata \"" .. lrdataPath .. "\""
            .. " --bridge-result \"" .. resultPath .. "\""
        local command = "cd /D \"" .. Support.REPO_ROOT .. "\" && uv run lr-ai-exposure" .. args
        if LrTasks.execute(command) ~= 0 then
            local detail = ""
            if Support.fileExists(resultPath) then
                local failed = Support.readJsonFile(resultPath)
                detail = tostring(failed.error or "")
            end
            if string.find(detail, "ACTIVE_PRODUCTION_JOB_EXISTS", 1, true) then
                LrDialogs.message(
                    "AI Exposure Assist — Existing Production Job",
                    "An active one-job production workflow already owns this source folder.\n\n"
                        .. detail
                        .. "\n\nDo not create a duplicate job. Resume the existing job instead.",
                    "warning"
                )
                return
            end
            error("Could not prepare the production job. " .. detail)
        end

        local result = Support.readJsonFile(resultPath)
        if result.status ~= "ok" then
            error(tostring(result.error or "Production job preparation returned an error."))
        end
        if type(result.job_dir) ~= "string" or result.job_dir == "" then
            error("Production preparation did not return job_dir.")
        end
        if tostring(result.workflow_state or "") ~= "ANALYZING" then
            error("Production preparation returned an unexpected workflow state.")
        end

        LrDialogs.message(
            "AI Exposure Assist — ANALYZING",
            "Production package prepared.\n\n"
                .. "Job: " .. tostring(result.job_id or jobId) .. "\n"
                .. "Images: " .. tostring(result.total_images or #photos) .. "\n\n"
                .. "Job folder:\n" .. tostring(result.job_dir) .. "\n\n"
                .. "The package is ready for the bounded visual-semantics step. "
                .. "No Lightroom Develop setting has been changed.",
            "info"
        )
    end)

    PrepareProductionJob.isRunning = false
    if not success then
        LrDialogs.message("AI Exposure Assist Error", tostring(err), "critical")
    end
end

if not Support.deferAutoStart then
    LrTasks.startAsyncTask(function()
        PrepareProductionJob.run()
    end)
end

return PrepareProductionJob
