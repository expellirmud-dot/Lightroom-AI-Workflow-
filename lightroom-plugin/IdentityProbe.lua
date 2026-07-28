-- WO-015: Lightroom SDK Probe for stable identity
local LrApplication = import 'LrApplication'
local LrTasks = import 'LrTasks'
local LrFileUtils = import 'LrFileUtils'
local LrPathUtils = import 'LrPathUtils'

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

LrTasks.startAsyncTask(function()
    local catalog = LrApplication.activeCatalog()
    local photo = catalog:getTargetPhoto()
    if not photo then return end
    
    local path = photo:getRawMetadata('path')
    local id_local = photo:getRawMetadata('id_local')
    local uuid = photo:getRawMetadata('uuid')
    
    -- Format as JSON
    local out = '{\n  "path": "' .. tostring(path):gsub('\\', '\\\\') .. '",\n  "id_local": "' .. tostring(id_local) .. '",\n  "uuid": "' .. tostring(uuid) .. '"\n}'
    
    local outPath = LrPathUtils.child(LrPathUtils.parent(catalog:getPath()), "runtime/jobs/identity_probe.json")
    LrFileUtils.createAllDirectories(LrPathUtils.parent(outPath))
    writeUtf8File(outPath, out)
end)
