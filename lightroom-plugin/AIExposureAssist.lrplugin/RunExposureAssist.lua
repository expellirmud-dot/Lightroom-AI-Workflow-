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
    -- We write to a staging directory; Python will create the unique job folder
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
        
        selectionData[#selectionData + 1] = '    {\n      "id_local": ' .. tostring(id_local) .. ',\n      "path": "' .. tostring(path):gsub('\\', '\\\\') .. '",\n      "uuid": "' .. tostring(uuid) .. '"\n    }'
    end

    local json = '{\n  "job_id": "job-staging",\n  "photos": [\n' .. table.concat(selectionData, ",\n") .. '\n  ]\n}'
    
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
