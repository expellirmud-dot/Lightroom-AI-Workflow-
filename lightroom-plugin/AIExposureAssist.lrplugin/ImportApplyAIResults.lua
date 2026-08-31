--[[
AI Exposure Assist — Import / Apply AI Results

Short-lived Lightroom command:
- opens the latest prepared package;
- refuses incomplete external decisions without mutation;
- validates/freezes the exact decision set through Python;
- builds a guarded Catalog Exposure2012-only plan;
- applies and verifies that plan in Lightroom;
- recovers legacy technical verification failures without double-applying;
- exits at SESSION_COMPLETE or RERENDER_REQUIRED.

It never prepares the next pass and never calls an AI provider.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrTasks = import "LrTasks"
local LrProgressScope = import "LrProgressScope"
local Support = require "SessionPackageSupport"
local CatalogApplyBarrier = require "CatalogApplyBarrier"

local ImportApplyAIResults = {}
ImportApplyAIResults.isRunning = false

local function showResultsNotReady(pointer, missing)
    local examples = {}
    for i = 1, math.min(#missing, 8) do
        examples[#examples + 1] = missing[i]
    end
    local suffix = ""
    if #missing > 0 then
        suffix = "\nMissing decision files: " .. tostring(#missing)
        if #examples > 0 then
            suffix = suffix .. "\nExamples: " .. table.concat(examples, ", ")
        end
    end
    LrDialogs.message(
        "AI Exposure Assist — AI_RESULTS_NOT_READY",
        "Session: " .. tostring(pointer.session_id) .. "\n"
            .. "Pass: " .. tostring(pointer.pass_number) .. "\n\n"
            .. "Package folder:\n" .. tostring(pointer.pass_dir) .. "\n\n"
            .. "Decision folder:\n" .. LrPathUtils.child(pointer.pass_dir, "decisions")
            .. suffix
            .. "\n\nNothing was changed in Lightroom. Finish the external AI run first, then use this command again.",
        "info"
    )
end

local function confirmationErrorDetail(bridgeResultPath)
    if not Support.fileExists(bridgeResultPath) then
        return ""
    end
    local result = Support.readJsonFile(bridgeResultPath)
    if type(result.error) == "string" and result.error ~= "" then
        return "\n\n" .. result.error
    end
    return ""
end

function ImportApplyAIResults.run()
    if ImportApplyAIResults.isRunning then
        LrDialogs.message("AI Exposure Assist", "An AI result import/apply is already running.", "warning")
        return
    end

    ImportApplyAIResults.isRunning = true
    local success, err = LrTasks.pcall(function()
        local pointer = Support.loadLatestPointer()
        local sessionState = Support.readSessionState(pointer)
        local currentPass = tonumber(pointer.pass_number) or 1
        local evidencePath = LrPathUtils.child(pointer.pass_dir, "catalog-apply-evidence.json")
        local recoverableApplyFailure, failedEvidenceIds = CatalogApplyBarrier.evidenceHasFailures(
            Support,
            evidencePath
        )

        -- A pre-WO-039 bug could mark the session converged after a technical
        -- verify mismatch even though Lightroom later committed the targets.
        -- Such evidence is explicitly recoverable; a genuinely completed pass
        -- still exits immediately.
        if sessionState.is_converged == true and not recoverableApplyFailure then
            LrDialogs.message(
                "AI Exposure Assist — Session Complete",
                "Session " .. tostring(pointer.session_id) .. " is already converged. No further apply is required.",
                "info"
            )
            return
        end

        if Support.fileExists(evidencePath) and not recoverableApplyFailure then
            LrDialogs.message(
                "AI Exposure Assist — Pass Already Applied",
                "Pass " .. tostring(currentPass) .. " already has verified apply evidence.\n\n"
                    .. "This command will not prepare another pass automatically.\n"
                    .. "After Lightroom finishes rerendering, use 'Prepare Next AI Package'.",
                "info"
            )
            return
        end

        local decisionsReady, missing = Support.decisionReadiness(pointer)
        if not decisionsReady then
            showResultsNotReady(pointer, missing)
            return
        end

        local catalog = LrApplication.activeCatalog()
        local photos, sourceFolder = Support.getActiveFolderPhotos(catalog)
        Support.ensureSameActiveFolder(pointer, sourceFolder)

        local photoMap = {}
        for _, photo in ipairs(photos) do
            photoMap[tostring(photo.localIdentifier)] = photo
        end

        local stagingDir = LrPathUtils.child(Support.REPO_ROOT, "runtime\\staging")
        local bridgeResultPath = LrPathUtils.child(stagingDir, "bridge-result-" .. pointer.session_id .. ".json")
        local progress = LrProgressScope({
            title = "AI Exposure Assist",
            caption = "Pass " .. tostring(currentPass) .. ": validating external decisions...",
        })

        local frozenPath = LrPathUtils.child(pointer.pass_dir, "ai-decisions.json")
        if not Support.fileExists(frozenPath) then
            local analyzeArgs = " --analyze-session-pass"
                .. " --session-id \"" .. pointer.session_id .. "\""
                .. " --pass-number " .. tostring(currentPass)
                .. " --bridge-result \"" .. bridgeResultPath .. "\""
            local analyzeCommand = "cd /D \"" .. Support.REPO_ROOT .. "\" && uv run lr-ai-exposure" .. analyzeArgs
            if LrTasks.execute(analyzeCommand) ~= 0 then
                progress:done()
                error("Pass " .. tostring(currentPass) .. " external decision validation/freeze failed.")
            end
        end

        progress:setCaption("Pass " .. tostring(currentPass) .. ": building Catalog apply plan...")
        local planPath = LrPathUtils.child(pointer.pass_dir, "catalog-apply-plan.json")
        if not Support.fileExists(planPath) then
            local planArgs = " --apply-session-pass"
                .. " --session-id \"" .. pointer.session_id .. "\""
                .. " --pass-number " .. tostring(currentPass)
                .. " --authorize-apply \"" .. pointer.session_id .. "\""
                .. " --bridge-result \"" .. bridgeResultPath .. "\""
            local planCommand = "cd /D \"" .. Support.REPO_ROOT .. "\" && uv run lr-ai-exposure" .. planArgs
            if LrTasks.execute(planCommand) ~= 0 then
                progress:done()
                error("Pass " .. tostring(currentPass) .. " Catalog apply planning failed.")
            end
        end

        local plan = Support.readJsonFile(planPath)
        local resultPath = LrPathUtils.child(
            stagingDir,
            "catalog-apply-result-" .. pointer.session_id .. "-pass-" .. tostring(currentPass) .. ".json"
        )

        if recoverableApplyFailure then
            progress:setCaption(
                "Pass " .. tostring(currentPass) .. ": reconciling "
                    .. tostring(#failedEvidenceIds) .. " prior Catalog verification failures..."
            )
        else
            progress:setCaption("Pass " .. tostring(currentPass) .. ": applying Exposure2012 in Lightroom Catalog...")
        end

        -- Always rebuild the result from current Catalog truth.  The barrier is
        -- absolute-target and idempotent: already-correct targets are verified
        -- without applying a delta twice.
        CatalogApplyBarrier.applyCatalogPlan(Support, catalog, photoMap, plan, resultPath)

        progress:setCaption("Pass " .. tostring(currentPass) .. ": confirming Lightroom-observed results...")
        local confirmArgs = " -m lr_ai_exposure.catalog_confirm"
            .. " --session-id \"" .. pointer.session_id .. "\""
            .. " --pass-number " .. tostring(currentPass)
            .. " --apply-result \"" .. resultPath .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local confirmCommand = "cd /D \"" .. Support.REPO_ROOT .. "\" && uv run python" .. confirmArgs
        if LrTasks.execute(confirmCommand) ~= 0 then
            progress:done()
            error(
                "Pass " .. tostring(currentPass)
                    .. " Catalog confirmation failed. Session state was not advanced."
                    .. confirmationErrorDetail(bridgeResultPath)
            )
        end

        local result = Support.readJsonFile(bridgeResultPath)
        if result.status ~= "ok" then
            progress:done()
            error("Pass " .. tostring(currentPass) .. " Catalog confirmation returned an error.")
        end
        progress:done()

        local maxPasses = tonumber((sessionState.policy or {}).maximum_passes) or 4
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
            "AI Exposure Assist — RERENDER_REQUIRED",
            "Pass " .. tostring(currentPass) .. " was confirmed.\n\n"
                .. "Verified Catalog applies: " .. tostring(result.applied_count or 0) .. "\n"
                .. "PASS: " .. tostring(result.pass_count or 0) .. "\n"
                .. "REVIEW: " .. tostring(result.review_count or 0) .. "\n\n"
                .. "This command is finished. Allow Lightroom to refresh/rerender the adjusted previews. Then use 'Prepare Next AI Package'.",
            "info"
        )
    end)

    if not success then
        LrDialogs.message("AI Exposure Assist Error", tostring(err), "critical")
    end
    ImportApplyAIResults.isRunning = false
end

LrTasks.startAsyncTask(function()
    ImportApplyAIResults.run()
end)

return ImportApplyAIResults
