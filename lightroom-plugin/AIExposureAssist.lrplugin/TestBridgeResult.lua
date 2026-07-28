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

-- Asserts the call throws AND that the resulting error string does NOT contain
-- `forbidden` (used to prove a masking message is no longer reported).
local function assert_error_without(func, expectedPattern, forbiddenPattern, msg)
    local status, err = pcall(func)
    if status then
        error(string.format("ASSERT FAILED: %s. Expected error matching '%s', but no error was thrown.", msg, expectedPattern))
    end
    local errStr = tostring(err)
    if not string.find(errStr, expectedPattern) then
        error(string.format("ASSERT FAILED: %s. Expected error matching '%s', but got '%s'.", msg, expectedPattern, errStr))
    end
    if string.find(errStr, forbiddenPattern) then
        error(string.format("ASSERT FAILED: %s. Error must not contain '%s', but got '%s'.", msg, forbiddenPattern, errStr))
    end
end

-- Asserts the call returns true (success path continues) without error.
local function assert_ok(func, msg)
    local status, err = pcall(func)
    if not status then
        error(string.format("ASSERT FAILED: %s. Expected success, but got error: %s", msg, tostring(err)))
    end
end

local function simulatePluginReadBridgeResult(bridgeResultPath, jobId, exitStatus, jobDataRequestedMode, fileExistsFunc, readFileFunc)
    -- Mirrors RunExposureAssist.lua bridge-result validation order.
    local fileContent = readFileFunc(bridgeResultPath)
    if not fileContent then
        error("Bridge result file absent: " .. tostring(bridgeResultPath))
    end

    local bridgeResult = Json.decode(fileContent)
    if not bridgeResult then
        error("Malformed bridge result JSON")
    end

    -- A/B. Parse + protocol_version
    if bridgeResult.protocol_version ~= "1.0" then
        error("Protocol version mismatch")
    end

    -- C. Process/status consistency: fail closed BEFORE success-only identity
    --    checks, so an error result with job_id == "unknown" surfaces its real
    --    upstream cause instead of a "Job ID mismatch" mask.
    if bridgeResult.status == "error" and exitStatus == 0 then
        error("Process exit 0 contradicts error status")
    end
    if bridgeResult.status == "ok" and exitStatus ~= 0 then
        error("Process exit non-zero contradicts ok status")
    end

    -- D. Authoritative error path: surface upstream error and stop. Do NOT run
    --    success-only request_id, job_id, manifest, evidence, refresh, or apply
    --    validation on an error result.
    if bridgeResult.status == "error" then
        error(tostring(bridgeResult.error))
    end

    -- E. Success-only path (status == "ok"): validate identity and artifacts.
    if bridgeResult.job_id ~= jobId then
        error("Job ID mismatch")
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

------------------------------------------------------------------
-- WO-028: bridge-result validation order regression cases
--
-- Proves the masking defect is fixed: a safe error result with
-- job_id == "unknown" surfaces its real upstream cause instead of the
-- secondary "Job ID mismatch" mask, while fail-closed behavior on
-- contradictory process settlement and on genuine identity mismatch is
-- preserved.
------------------------------------------------------------------
print("Running WO-028 bridge-result order cases...")

local SOURCE_DB_ERROR = "Handoff failed: Source DBs not found in C:\\Users\\Expellirmud\\Pictures\\LR\\ToTo"

-- Case 1: exit=1, status=error, job_id="unknown", real upstream error.
-- Expected: upstream error is surfaced; "Job ID mismatch" is NOT reported.
local case1Result = Json.encode({
    protocol_version = "1.0",
    status = "error",
    job_id = "unknown",
    mode = "ANALYZE_ONLY",
    decision_count = 0,
    applied = 0,
    analysis_evidence = "",
    apply_evidence = nil,
    error = SOURCE_DB_ERROR
})
assert_error_without(
    function()
        simulatePluginReadBridgeResult(
            "bridge.json", "job-1785272109", 1, "ANALYZE_ONLY",
            mockExists, function() return case1Result end)
    end,
    "Source DBs not found", "Job ID mismatch",
    "Case 1: upstream error surfaces before success-only job_id check"
)

-- Case 2: exit=0, status=ok, matching job_id, existing evidence.
-- Expected: success validation continues (returns true).
local case2Evidence = "C:\\case2\\evidence.json"
local case2Result = Json.encode({
    protocol_version = "1.0",
    status = "ok",
    job_id = "job-match",
    mode = "ANALYZE_ONLY",
    decision_count = 1,
    applied = 0,
    analysis_evidence = case2Evidence
})
local function case2Exists(path) return path == case2Evidence end
assert_ok(
    function()
        return simulatePluginReadBridgeResult(
            "bridge.json", "job-match", 0, "ANALYZE_ONLY",
            case2Exists, function() return case2Result end)
    end,
    "Case 2: success validation continues for matching job_id + existing evidence"
)

-- Case 3: exit=0, status=error. Expected: contradictory settlement fails closed.
local case3Result = Json.encode({
    protocol_version = "1.0",
    status = "error",
    job_id = "job-x",
    error = "late error"
})
assert_error(
    function()
        simulatePluginReadBridgeResult(
            "bridge.json", "job-x", 0, "ANALYZE_ONLY",
            mockExists, function() return case3Result end)
    end,
    "Process exit 0 contradicts error status",
    "Case 3: exit 0 with error status fails closed"
)

-- Case 4: exit!=0, status=ok. Expected: contradictory settlement fails closed.
assert_error(
    function()
        simulatePluginReadBridgeResult(
            "bridge.json", "job-match", 1, "ANALYZE_ONLY",
            case2Exists, function() return case2Result end)
    end,
    "Process exit non%-zero contradicts ok status",
    "Case 4: non-zero exit with ok status fails closed"
)

-- Case 5: status=ok, job_id mismatch. Expected: "Job ID mismatch" still reported.
local case5Result = Json.encode({
    protocol_version = "1.0",
    status = "ok",
    job_id = "different-job"
})
assert_error(
    function()
        simulatePluginReadBridgeResult(
            "bridge.json", "job-expected", 0, "ANALYZE_ONLY",
            mockExists, function() return case5Result end)
    end,
    "Job ID mismatch",
    "Case 5: genuine job_id mismatch still reported on success path"
)

print("All WO-028 bridge-result order cases passed!")
