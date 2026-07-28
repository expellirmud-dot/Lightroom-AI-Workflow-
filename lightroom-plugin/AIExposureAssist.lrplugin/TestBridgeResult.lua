local Json = require "Json"

local function assert_equal(expected, actual, msg)
    if expected ~= actual then
        error(string.format("ASSERT FAILED: %s. Expected '%s', got '%s'", msg or "", tostring(expected), tostring(actual)))
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

local function simulatePluginReadBridgeResult(bridgeResultPath, jobId, exitStatus, jobDataRequestedMode, fileExistsFunc, readFileFunc)
    -- Mock behavior
    local fileContent = readFileFunc(bridgeResultPath)
    if not fileContent then
        error("Bridge result file absent: " .. tostring(bridgeResultPath))
    end
    
    local bridgeResult = Json.decode(fileContent)
    if not bridgeResult then
        error("Malformed bridge result JSON")
    end
    
    if bridgeResult.protocol_version ~= "1.0" then
        error("Protocol version mismatch")
    end
    
    if bridgeResult.job_id ~= jobId then
        error("Job ID mismatch")
    end
    
    if bridgeResult.status == "error" and exitStatus == 0 then
        error("Process exit 0 contradicts error status")
    end
    if bridgeResult.status == "ok" and exitStatus ~= 0 then
        error("Process exit non-zero contradicts ok status")
    end
    
    if bridgeResult.status == "error" then
        error(tostring(bridgeResult.error))
    end
    
    local evidencePath = bridgeResult.analysis_evidence
    if jobDataRequestedMode == "APPLY" and bridgeResult.apply_evidence and bridgeResult.apply_evidence ~= "" then
        evidencePath = bridgeResult.apply_evidence
    end
    
    if not evidencePath or evidencePath == "" or not fileExistsFunc(evidencePath) then
        error("Reported artifact does not exist: " .. tostring(evidencePath))
    end
    
    return true
end

print("Running Bridge Result tests...")

-- Test: successful result-file handoff & artifact path in nested job directory & spaces and Thai text in Windows paths
local thaiPath = "C:\\งาน\\evidence ภาพ.json"
local validResult = Json.encode({
    protocol_version = "1.0",
    status = "ok",
    job_id = "job-123",
    mode = "ANALYZE_ONLY",
    decision_count = 1,
    applied = 0,
    ai_decisions = "C:\\decisions.json",
    analysis_evidence = thaiPath
})

local function mockExists(path) return path == thaiPath end
local function mockReadFile(path) if path == "bridge.json" then return validResult end return nil end

simulatePluginReadBridgeResult("bridge.json", "job-123", 0, "ANALYZE_ONLY", mockExists, mockReadFile)

-- Test: missing result file
assert_error(function()
    simulatePluginReadBridgeResult("missing.json", "job-123", 0, "ANALYZE_ONLY", mockExists, function() return nil end)
end, "Bridge result file absent", "Fail closed on missing result file")

-- Test: malformed JSON
assert_error(function()
    simulatePluginReadBridgeResult("bridge.json", "job-123", 0, "ANALYZE_ONLY", mockExists, function() return "{bad json" end)
end, "Malformed bridge result", "Fail closed on malformed JSON")

-- Test: protocol mismatch
local badProto = Json.encode({protocol_version = "2.0", status = "ok", job_id = "job-123"})
assert_error(function()
    simulatePluginReadBridgeResult("bridge.json", "job-123", 0, "ANALYZE_ONLY", mockExists, function() return badProto end)
end, "Protocol version mismatch", "Fail closed on protocol mismatch")

-- Test: job_id mismatch
local badJobId = Json.encode({protocol_version = "1.0", status = "ok", job_id = "job-999"})
assert_error(function()
    simulatePluginReadBridgeResult("bridge.json", "job-123", 0, "ANALYZE_ONLY", mockExists, function() return badJobId end)
end, "Job ID mismatch", "Fail closed on job_id mismatch")

-- Test: exit 0 with error result
local errorResult = Json.encode({protocol_version = "1.0", status = "error", job_id = "job-123", error = "something failed"})
assert_error(function()
    simulatePluginReadBridgeResult("bridge.json", "job-123", 0, "ANALYZE_ONLY", mockExists, function() return errorResult end)
end, "Process exit 0 contradicts error status", "Fail closed on exit 0 with error status")

-- Test: non-zero exit with ok result
assert_error(function()
    simulatePluginReadBridgeResult("bridge.json", "job-123", 1, "ANALYZE_ONLY", mockExists, function() return validResult end)
end, "Process exit non%-zero contradicts ok status", "Fail closed on non-zero exit with ok status")

-- Test: missing evidence file
local noEvResult = Json.encode({
    protocol_version = "1.0",
    status = "ok",
    job_id = "job-123",
    mode = "ANALYZE_ONLY",
    analysis_evidence = "C:\\doesnotexist.json"
})
assert_error(function()
    simulatePluginReadBridgeResult("bridge.json", "job-123", 0, "ANALYZE_ONLY", function() return false end, function() return noEvResult end)
end, "Reported artifact does not exist", "Fail closed on missing evidence file")

-- Test: stale result file (e.g. wrong job ID left behind from previous run)
local staleResult = Json.encode({protocol_version = "1.0", status = "ok", job_id = "old-job-id"})
assert_error(function()
    simulatePluginReadBridgeResult("bridge.json", "job-123", 0, "ANALYZE_ONLY", mockExists, function() return staleResult end)
end, "Job ID mismatch", "Fail closed on stale result file")

print("All Bridge Result tests passed!")
