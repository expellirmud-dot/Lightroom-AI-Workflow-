--[[
AI Exposure Assist — Apply Latest Prepared Job

Loads the durable job created by RunExposureAssist.lua, validates external AI
decisions through Python, applies only guarded non-zero Exposure2012 deltas,
and refreshes Lightroom metadata for APPLIED_VERIFIED images currently selected.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local LrProgressScope = import "LrProgressScope"
local Json = require "Json"

local ApplyPreparedJob = {}
ApplyPreparedJob.isRunning = false

local REPO_ROOT = "D:\\ai-tools\\lightroom-ai-exposure"

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

local function validateBridgeResult(result, expectedJobId, exitStatus)
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
    if result.job_id ~= expectedJobId then
        error("Job ID mismatch")
    end
    if result.mode ~= "APPLY_SAVED_JOB" then
        error("Unexpected bridge mode: " .. tostring(result.mode))
    end
    if type(result.apply_evidence) ~= "string"
        or result.apply_evidence == ""
        or not LrFileUtils.exists(result.apply_evidence) then
        error("Apply evidence absent: " .. tostring(result.apply_evidence))
    end
end

function ApplyPreparedJob.run()
    if ApplyPreparedJob.isRunning then
        LrDialogs.message("AI Exposure Assist", "An apply job is already running.", "warning")
        return
    end

    ApplyPreparedJob.isRunning = true
    local success, err = LrTasks.pcall(function()
        local pointerPath = LrPathUtils.child(REPO_ROOT, "runtime\\staging\\latest-prepared-job.json")
        local pointer = readJsonFile(pointerPath)
        local jobId = pointer.job_id
        if type(jobId) ~= "string" or jobId == "" then
            error("latest-prepared-job.json does not contain a job_id")
        end

        local confirmation = LrDialogs.confirm(
            "AI Exposure Assist — Apply Prepared Job",
            "Apply validated exposure decisions for " .. jobId .. "?\n\n"
                .. "Only crs:Exposure2012 may change. Every changed XMP is backed up and verified.",
            "Apply Exposure",
            "Cancel"
        )
        if confirmation ~= "ok" then
            return
        end

        local catalog = LrApplication.activeCatalog()
        local targets = catalog:getTargetPhotos() or {}
        local photoMap = {}
        for _, photo in ipairs(targets) do
            photoMap[tostring(photo.localIdentifier)] = photo
        end

        local stagingDir = LrPathUtils.child(REPO_ROOT, "runtime\\staging")
        LrFileUtils.createAllDirectories(stagingDir)
        local bridgeResultPath = LrPathUtils.child(stagingDir, "apply-bridge-result-" .. jobId .. ".json")
        local args = " --apply-job \"" .. jobId .. "\""
            .. " --authorize-apply \"" .. jobId .. "\""
            .. " --bridge-result \"" .. bridgeResultPath .. "\""
        local command = "cd /D \"" .. REPO_ROOT .. "\" && uv run lr-ai-exposure" .. args

        local progress = LrProgressScope({
            title = "AI Exposure Assist",
            caption = "Validating decisions and applying exposure..."
        })
        local exitStatus = LrTasks.execute(command)
        progress:done()

        local result = readJsonFile(bridgeResultPath)
        validateBridgeResult(result, jobId, exitStatus)
        local evidence = readJsonFile(result.apply_evidence)

        local refreshIds = {}
        local notSelectedCount = 0
        for _, item in ipairs(evidence.results or {}) do
            if item.status == "APPLIED_VERIFIED" then
                local imageId = tostring(item.image_id)
                if photoMap[imageId] then
                    table.insert(refreshIds, imageId)
                else
                    notSelectedCount = notSelectedCount + 1
                end
            end
        end

        if #refreshIds > 0 then
            catalog:withWriteAccessDo("Refresh Exposure Metadata", function()
                for _, imageId in ipairs(refreshIds) do
                    photoMap[imageId]:readMetadata()
                end
            end)
        end

        local diagnosticsPath = LrPathUtils.child(stagingDir, "plugin-diagnostics.log")
        writeUtf8File(diagnosticsPath, table.concat({
            "Operation: APPLY_SAVED_JOB",
            "Command: " .. command,
            "Exit code: " .. tostring(exitStatus),
            "Job ID: " .. jobId,
            "Applied: " .. tostring(result.applied or 0),
            "Skipped: " .. tostring(result.skipped or 0),
            "Errors: " .. tostring(result.errors or 0),
            "Refreshed in Lightroom: " .. tostring(#refreshIds),
            "Applied but not currently selected: " .. tostring(notSelectedCount)
        }, "\n"))

        local extra = ""
        if notSelectedCount > 0 then
            extra = "\n\n" .. tostring(notSelectedCount)
                .. " applied photos were not in the current selection. Use Lightroom ‘Read Metadata from Files’ for those photos."
        end
        LrDialogs.message(
            "AI Exposure Assist — Apply Complete",
            "Applied: " .. tostring(result.applied or 0)
                .. "\nSkipped: " .. tostring(result.skipped or 0)
                .. "\nErrors: " .. tostring(result.errors or 0)
                .. "\nRefreshed in Lightroom: " .. tostring(#refreshIds)
                .. extra,
            "info"
        )
    end)

    if not success then
        LrDialogs.message("AI Exposure Assist Error", tostring(err), "critical")
    end
    ApplyPreparedJob.isRunning = false
end

LrTasks.startAsyncTask(function()
    ApplyPreparedJob.run()
end)

return ApplyPreparedJob
