-- ActiveFolderResolver.lua
-- Robust resolver for Lightroom active folder

local ActiveFolderResolver = {}

-- Safely execute a function and return its result or fallback
local function safeCall(fallback, func)
    local ok, result = pcall(func)
    if ok then
        return result
    end
    return fallback
end

-- Inspect a source to see if it walks and quacks like an LrFolder
function ActiveFolderResolver.inspectSource(source)
    local info = {
        name = "<unknown>",
        path = nil,
        is_folder = false,
        reason = nil,
        capabilities = {}
    }

    if type(source) == "string" then
        info.name = source
        info.reason = "Source is a string, not an object"
        return info
    end
    
    if type(source) ~= "table" and type(source) ~= "userdata" then
        info.reason = "Source is neither table nor userdata"
        return info
    end

    info.name = safeCall("<unknown>", function() return source:getName() or "<unknown>" end)
    
    local hasGetPath = safeCall(false, function() return type(source.getPath) == "function" end)
    local hasGetChildren = safeCall(false, function() return type(source.getChildren) == "function" end)
    local hasGetPhotos = safeCall(false, function() return type(source.getPhotos) == "function" end)
    local hasGetParent = safeCall(false, function() return type(source.getParent) == "function" end)
    local sourceType = safeCall("unknown", function() return type(source.type) == "function" and source:type() or "unknown" end)
    
    if hasGetPath then table.insert(info.capabilities, "getPath") end
    if hasGetChildren then table.insert(info.capabilities, "getChildren") end
    if hasGetPhotos then table.insert(info.capabilities, "getPhotos") end
    if hasGetParent then table.insert(info.capabilities, "getParent") end
    if sourceType ~= "unknown" then table.insert(info.capabilities, "type=" .. tostring(sourceType)) end

    -- Try to get the path
    if hasGetPath then
        local pathStr = safeCall(nil, function() return source:getPath() end)
        if type(pathStr) == "string" and pathStr ~= "" then
            info.path = pathStr
            -- If it has a path, and it has getPhotos, it's highly likely a folder.
            -- Collections usually don't have getPath(), or it throws an error/returns nil.
            if hasGetPhotos then
                info.is_folder = true
            else
                info.reason = "Has path but missing getPhotos"
            end
        else
            info.reason = "getPath() returned nil, empty, or non-string (likely a Collection or smart source)"
        end
    else
        info.reason = "No getPath() capability (likely a Collection or smart source)"
    end

    return info
end

function ActiveFolderResolver.resolveActiveFolder(catalog)
    local activeSources = safeCall({}, function() return catalog:getActiveSources() or {} end)
    local result = {
        active_source_count = #activeSources,
        folder_count = 0,
        active_folder = nil,
        active_folder_path = nil,
        sources_info = {},
        error = nil
    }

    if #activeSources == 0 then
        result.error = "No active sources selected in Lightroom."
        return result
    end

    local foundFolders = {}
    
    for _, source in ipairs(activeSources) do
        local info = ActiveFolderResolver.inspectSource(source)
        table.insert(result.sources_info, info)
        
        if info.is_folder then
            table.insert(foundFolders, {
                source = source,
                path = info.path,
                name = info.name
            })
        end
    end

    result.folder_count = #foundFolders

    if #foundFolders == 0 then
        result.error = "None of the active sources are folders (Collections/Smart Collections are not supported)."
    elseif #foundFolders > 1 then
        result.error = "Exactly one folder is required, but " .. tostring(#foundFolders) .. " folders are selected."
    else
        -- Exactly one folder
        result.active_folder = foundFolders[1].source
        result.active_folder_path = foundFolders[1].path
    end

    return result
end

return ActiveFolderResolver
