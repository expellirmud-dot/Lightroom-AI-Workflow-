-- WO-015: Lightroom SDK Probe for stable identity
local LrApplication = import 'LrApplication'
local LrTasks = import 'LrTasks'
local LrFileUtils = import 'LrFileUtils'
local LrPathUtils = import 'LrPathUtils'

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
    LrFileUtils.writeFile(outPath, out)
end)
