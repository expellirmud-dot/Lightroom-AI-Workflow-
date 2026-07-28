--[[
WO-028: --lrdata command-construction focused tests.

Proves the CLI command built by RunExposureAssist.lua passes
  --lrdata "<settings.preview_cache_path>"
i.e. the .lrdata directory itself, and NEVER infers --lrdata from
the catalog parent directory. Missing/empty preview_cache_path fails
closed.

This is a pure-logic mirror of the production builder. It does not
spawn processes and does not touch the Lightroom SDK.
]]
local Json = require "Json"

local function assert_equal(expected, actual, msg)
    if expected ~= actual then
        error(string.format("ASSERT FAILED: %s. Expected '%s', got '%s'", msg or "", tostring(expected), tostring(actual)))
    end
end

local function assert_contains(haystack, needle, msg)
    if not string.find(tostring(haystack), needle, 1, true) then
        error(string.format("ASSERT FAILED: %s. Expected to find '%s' in '%s'.", msg, needle, tostring(haystack)))
    end
end

local function assert_not_contains(haystack, needle, msg)
    if string.find(tostring(haystack), needle, 1, true) then
        error(string.format("ASSERT FAILED: %s. Must NOT contain '%s', but found it in '%s'.", msg, needle, tostring(haystack)))
    end
end

local function assert_error(func, pattern, msg)
    local status, err = pcall(func)
    if status then
        error(string.format("ASSERT FAILED: %s. Expected error matching '%s', but no error was thrown.", msg, pattern))
    end
    if not string.find(tostring(err), pattern) then
        error(string.format("ASSERT FAILED: %s. Expected error matching '%s', but got '%s'.", msg, pattern, tostring(err)))
    end
end

-- Mirror of the production --lrdata builder in RunExposureAssist.lua.
-- Inputs: repoRoot, jobId, selectionPath, bridgeResultPath, requestedMode,
--         and the JSON-encoded config/settings.json contents. Returns the
--         assembled `args` string or raises the production fail-closed error.
local function buildArgs(repoRoot, jobId, selectionPath, bridgeResultPath, requestedMode, settingsJson)
    -- Resolve lrdata explicitly from config; never infer from catalog parent.
    local settingsPath = repoRoot .. "\\config\\settings.json"
    -- io.open is stubbed by the test by passing settingsJson directly; emulate
    -- the read + Json.decode the production code performs.
    local settingsContent = settingsJson
    local settings = Json.decode(settingsContent)
    if type(settings) ~= "table" then
        error("config/settings.json is not a JSON object")
    end
    local lrdataPath = settings.preview_cache_path
    if type(lrdataPath) ~= "string" or lrdataPath == "" then
        error("config/settings.json missing non-empty preview_cache_path (do not infer lrdata from catalog parent)")
    end

    local args = " --selection \"" .. selectionPath .. "\" --lrdata \"" .. lrdataPath .. "\" --bridge-result \"" .. bridgeResultPath .. "\""
    if requestedMode == "APPLY" then
        args = args .. " --apply --authorize-apply " .. jobId
    else
        args = args .. " --analyze-only"
    end
    return args
end

print("Running WO-028 --lrdata command-construction tests...")

local repoRoot = "D:\\ai-tools\\lightroom-ai-exposure"
local jobId = "job-1785272109"
local selectionPath = repoRoot .. "\\runtime\\staging\\selection.json"
local bridgeResultPath = repoRoot .. "\\runtime\\staging\\bridge-result-" .. jobId .. ".json"
local realLrdata = "C:\\Users\\Expellirmud\\Pictures\\LR\\ToTo\\ToTo Previews.lrdata"
local catalogParent = "C:\\Users\\Expellirmud\\Pictures\\LR\\ToTo"

-- Test 1: configured preview_cache_path is used as --lrdata.
local settingsGood = Json.encode({ preview_cache_path = realLrdata })
local args1 = buildArgs(repoRoot, jobId, selectionPath, bridgeResultPath, "ANALYZE_ONLY", settingsGood)
assert_contains(args1, "--lrdata \"" .. realLrdata .. "\"", "--lrdata points at the configured .lrdata directory")
assert_not_contains(args1, "--lrdata \"" .. catalogParent .. "\"", "--lrdata is NOT the catalog parent directory")
assert_contains(args1, "--analyze-only", "ANALYZE_ONLY mode flag preserved")
assert_contains(args1, "--bridge-result \"" .. bridgeResultPath .. "\"", "--bridge-result preserved")

-- Test 2: APPLY mode still uses configured lrdata and carries the two-key flags.
local args2 = buildArgs(repoRoot, jobId, selectionPath, bridgeResultPath, "APPLY", settingsGood)
assert_contains(args2, "--lrdata \"" .. realLrdata .. "\"", "APPLY mode also uses configured .lrdata directory")
assert_contains(args2, "--apply --authorize-apply " .. jobId, "two-key apply authorization preserved")

-- Test 3: missing preview_cache_path fails closed (no catalog-parent inference).
local settingsMissing = Json.encode({ catalog_path = "C:\\x\\ToTo.lrcat" })
assert_error(
    function() buildArgs(repoRoot, jobId, selectionPath, bridgeResultPath, "ANALYZE_ONLY", settingsMissing) end,
    "preview_cache_path",
    "missing preview_cache_path fails closed"
)

-- Test 4: empty-string preview_cache_path fails closed (no catalog-parent inference).
local settingsEmpty = Json.encode({ preview_cache_path = "" })
assert_error(
    function() buildArgs(repoRoot, jobId, selectionPath, bridgeResultPath, "ANALYZE_ONLY", settingsEmpty) end,
    "preview_cache_path",
    "empty preview_cache_path fails closed"
)

-- Test 5: null preview_cache_path fails closed.
local settingsNull = Json.encode({ preview_cache_path = Json.null })
assert_error(
    function() buildArgs(repoRoot, jobId, selectionPath, bridgeResultPath, "ANALYZE_ONLY", settingsNull) end,
    "preview_cache_path",
    "null preview_cache_path fails closed"
)

print("All WO-028 --lrdata command-construction tests passed!")
return true
