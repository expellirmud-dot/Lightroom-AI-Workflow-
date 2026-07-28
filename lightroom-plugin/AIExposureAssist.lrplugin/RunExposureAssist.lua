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
local LrJson = import "LrJson"

local RunExposureAssist = {}

function RunExposureAssist.run()
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
    local stagingDir = LrPathUtils.child(
        LrPathUtils.parent(catalogPath),
        "runtime/staging"
    )
    LrFileUtils.createAllDirectories(stagingDir)

    local selectionData = {}
    for _, photo in ipairs(photos) do
        local path = photo:getRawMetadata("path")
        local id_local = photo:getRawMetadata("id_local")
        local uuid = photo:getRawMetadata("uuid")
        
        table.insert(selectionData, {
            id_local = id_local,
            path = path,
            uuid = uuid
        })
    end

    local jobData = {
        job_id = "job-staging",
        photos = selectionData
    }
    
    local json = ""
    if LrJson and LrJson.encode then
        json = LrJson.encode(jobData)
    else
        -- Fallback if LrJson doesn't exist
        error("LrJson not found. Cannot encode JSON securely.")
    end
    
    local selectionPath = LrPathUtils.child(stagingDir, "selection.json")
    local ok, err = LrFileUtils.writeFile(selectionPath, json)
    
    if ok then
        LrDialogs.message(
            "AI Exposure Assist",
            "Selected " .. #photos .. " photos.\nWritten to:\n" .. selectionPath,
            "info"
        )
    else
        LrDialogs.message(
            "AI Exposure Assist",
            "Failed to write selection.json: " .. tostring(err),
            "critical"
        )
    end
end

LrTasks.startAsyncTask(function()
    RunExposureAssist.run()
end)

return RunExposureAssist
