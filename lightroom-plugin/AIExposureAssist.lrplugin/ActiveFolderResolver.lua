-- ActiveFolderResolver.lua
-- Robust resolver for Lightroom active folder.
-- Lightroom SDK calls may yield, so use LrTasks.pcall when available.

local ActiveFolderResolver = {}

local LrTasks = nil
if type(import) == "function" then
    local ok, value = pcall(function()
        return import "LrTasks"
    end)
    if ok then
        LrTasks = value
    end
end

local function protectedCall(func)
    if LrTasks and type(LrTasks.pcall) == "function" then
        return LrTasks.pcall(func)
    end
    -- Fallback keeps the resolver testable outside Lightroom. In Lightroom,
    -- LrTasks.pcall is preferred because SDK calls may yield.
    return pcall(func)
end

local function sdkCall(func)
    local ok, value = protectedCall(func)
    if ok then
        return true, value, nil
    end
    return false, nil, tostring(value)
end

local function hasMethod(source, methodName)
    local ok, value = protectedCall(function()
        return type(source[methodName]) == "function"
    end)
    return ok and value == true
end

-- Inspect a Lightroom active source without silently converting SDK failures
-- into "not a folder". source:type() is the primary class identity when it is
-- available; capability/path checks are supporting evidence only.
function ActiveFolderResolver.inspectSource(source)
    local info = {
        name = "<unknown>",
        path = nil,
        is_folder = false,
        reason = nil,
        capabilities = {},
        source_type = "unknown",
        source_type_status = "UNAVAILABLE",
        source_type_error = nil,
        get_path_status = "NOT_ATTEMPTED",
        get_path_error = nil
    }

    if type(source) == "string" then
        info.name = source
        info.reason = "Source is a string, not a Lightroom source object"
        return info
    end

    if type(source) ~= "table" and type(source) ~= "userdata" then
        info.reason = "Source is neither table nor userdata"
        return info
    end

    local nameOk, nameValue = sdkCall(function()
        return source:getName()
    end)
    if nameOk and type(nameValue) == "string" and nameValue ~= "" then
        info.name = nameValue
    end

    local hasGetPath = hasMethod(source, "getPath")
    local hasGetChildren = hasMethod(source, "getChildren")
    local hasGetPhotos = hasMethod(source, "getPhotos")
    local hasGetParent = hasMethod(source, "getParent")

    if hasGetPath then table.insert(info.capabilities, "getPath") end
    if hasGetChildren then table.insert(info.capabilities, "getChildren") end
    if hasGetPhotos then table.insert(info.capabilities, "getPhotos") end
    if hasGetParent then table.insert(info.capabilities, "getParent") end

    local typeOk, sourceType, typeError = sdkCall(function()
        return source:type()
    end)
    if typeOk then
        info.source_type = tostring(sourceType)
        info.source_type_status = "PASS"
        table.insert(info.capabilities, "type=" .. info.source_type)
    else
        info.source_type_status = "FAIL"
        info.source_type_error = typeError
    end

    -- Lightroom's own class identity is authoritative. Do not demote a real
    -- LrFolder merely because a subsequent getPath() call fails.
    if typeOk and sourceType == "LrFolder" then
        info.is_folder = true
    end

    if hasGetPath then
        local pathOk, pathValue, pathError = sdkCall(function()
            return source:getPath()
        end)
        if pathOk and type(pathValue) == "string" and pathValue ~= "" then
            info.path = pathValue
            info.get_path_status = "PASS"
        elseif pathOk then
            info.get_path_status = "INVALID_VALUE"
            info.get_path_error = "getPath() returned nil, empty, or non-string"
        else
            info.get_path_status = "FAIL"
            info.get_path_error = pathError
        end
    else
        info.get_path_status = "UNAVAILABLE"
        info.get_path_error = "No getPath() capability"
    end

    -- Compatibility fallback for mocks/older SDK-like objects where type()
    -- cannot be queried: a usable path plus getPhotos is enough to classify.
    if not info.is_folder and (not typeOk or sourceType == nil or sourceType == "unknown") then
        if info.get_path_status == "PASS" and hasGetPhotos then
            info.is_folder = true
        end
    end

    if info.is_folder then
        if info.get_path_status == "PASS" then
            info.reason = nil
        else
            info.reason = "Recognized LrFolder, but path lookup failed: " .. tostring(info.get_path_error)
        end
    elseif typeOk and sourceType ~= "LrFolder" then
        info.reason = "Active source type is " .. tostring(sourceType) .. ", not LrFolder"
    elseif info.get_path_status ~= "PASS" then
        info.reason = tostring(info.get_path_error or "Unable to establish folder identity")
    elseif not hasGetPhotos then
        info.reason = "Has path but missing getPhotos capability"
    else
        info.reason = "Unable to establish folder identity"
    end

    return info
end

function ActiveFolderResolver.resolveActiveFolder(catalog)
    local sourcesOk, activeSources, sourcesError = sdkCall(function()
        return catalog:getActiveSources() or {}
    end)

    local result = {
        active_source_count = 0,
        folder_count = 0,
        active_folder = nil,
        active_folder_path = nil,
        sources_info = {},
        error = nil
    }

    if not sourcesOk then
        result.error = "Could not read Lightroom active sources: " .. tostring(sourcesError)
        return result
    end

    result.active_source_count = #activeSources
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
                name = info.name,
                info = info
            })
        end
    end

    result.folder_count = #foundFolders

    if #foundFolders == 0 then
        result.error = "None of the active sources are Lightroom folders."
    elseif #foundFolders > 1 then
        result.error = "Exactly one folder is required, but " .. tostring(#foundFolders) .. " folders are selected."
    else
        result.active_folder = foundFolders[1].source
        result.active_folder_path = foundFolders[1].path
        if result.active_folder_path == nil then
            result.error = "Active source is LrFolder but its path could not be read: "
                .. tostring(foundFolders[1].info.get_path_error or "unknown getPath() failure")
        end
    end

    return result
end

return ActiveFolderResolver
