local Json = require "Json"

local function assert_equal(expected, actual, msg)
    if expected ~= actual then
        error(string.format("ASSERT FAILED: %s. Expected '%s', got '%s'", msg or "", tostring(expected), tostring(actual)))
    end
end

print("Running Json tests...")

-- Test: encode selection payload (ordered identities & Thai filename, Windows paths)
local selectionData = {
    {
        id_local = "123",
        path = "C:\\Users\\Expellirmud\\Pictures\\LR\\ToTo\\ภาพถ่าย.raw",
        uuid = "A1-B2-C3-D4"
    },
    {
        id_local = "456",
        path = "D:\\photos\\test \"quote\" \\ slash.raw",
        uuid = "E5-F6-G7-H8"
    }
}
local jobData = {
    protocol_version = "1.0",
    job_id = "job-12345",
    selected_count = 2,
    requested_mode = "ANALYZE_ONLY",
    photos = selectionData
}
local encoded_job = Json.encode(jobData)
assert(encoded_job ~= nil, "Encoded job should not be nil")
assert(string.find(encoded_job, "123"), "Should contain ordered identity 123")
assert(string.find(encoded_job, "456"), "Should contain ordered identity 456")
assert(string.find(encoded_job, "C:\\\\Users\\\\Expellirmud\\\\Pictures\\\\LR\\\\ToTo\\\\ภาพถ่าย.raw"), "Should contain Windows path with Thai text")
assert(string.find(encoded_job, "test \\\"quote\\\""), "Should contain escaped quotes")

-- Test: decode evidence payload
local evidenceJSON = '{"results": [{"image_id": "123", "status": "APPLIED_VERIFIED"}]}'
local decoded_evidence = Json.decode(evidenceJSON)
assert_equal("123", decoded_evidence.results[1].image_id, "Decoded image_id")
assert_equal("APPLIED_VERIFIED", decoded_evidence.results[1].status, "Decoded status")

-- Test: malformed JSON rejection
local malformed_json = '{"key": "value", missing_quote}'
local status, err = pcall(function()
    Json.decode(malformed_json)
end)
assert(status == false, "Malformed JSON should fail")
assert(string.find(tostring(err), "expected string for key"), "Should report parsing error")

print("All JSON tests passed!")

print("Running JSON Regression tests (WO-028)...")
local bridgeJSON = [[
{
  "protocol_version": "1.0",
  "status": "ok",
  "job_id": "job-123",
  "mode": "ANALYZE_ONLY",
  "decision_count": 1,
  "applied": 0,
  "ai_decisions": "D:\\ai-tools\\โฟลเดอร์\\ai-decisions.json",
  "analysis_evidence": "D:\\ai-tools\\โฟลเดอร์\\analysis-evidence.json",
  "apply_evidence": null,
  "error": null
}
]]
local bridgeDecoded = Json.decode(bridgeJSON)
assert_equal("1.0", bridgeDecoded.protocol_version, "protocol_version remains readable after decode")
assert_equal("job-123", bridgeDecoded.job_id, "job_id remains readable after decode")
assert_equal(1, bridgeDecoded.decision_count, "number decoded properly")
assert_equal(Json.null, bridgeDecoded.apply_evidence, "decode null object fields")
assert_equal(Json.null, bridgeDecoded.error, "decode null object fields")
assert_equal("D:\\ai-tools\\โฟลเดอร์\\ai-decisions.json", bridgeDecoded.ai_decisions, "Windows escaped backslashes and Thai UTF-8 paths")

local nullArray = '[1, null, 3]'
local decodedNullArray = Json.decode(nullArray)
assert_equal(1, decodedNullArray[1], "array element 1")
assert_equal(Json.null, decodedNullArray[2], "decode null inside arrays without losing position")
assert_equal(3, decodedNullArray[3], "array element 3")

local escapes = '["\\"\\\\\\/\\b\\f\\n\\r\\t"]'
local decodedEscapes = Json.decode(escapes)
assert_equal("\"\\/\b\f\n\r\t", decodedEscapes[1], "supported escapes b, f, n, r, t, slash and backslash")

local function assert_decode_error(json_str, pattern, msg)
    local ok, err = pcall(function() Json.decode(json_str) end)
    if ok then error(string.format("ASSERT FAILED: %s. Expected error matching '%s'.", msg, pattern)) end
    if not string.find(tostring(err), pattern) then error(string.format("ASSERT FAILED: %s. Expected '%s', got '%s'.", msg, pattern, tostring(err))) end
end

assert_decode_error('["\\x"]', "invalid escape char", "unsupported escape fails closed")
assert_decode_error('["\\', "truncated escape", "truncated escape fails closed")

print("All JSON Regression tests passed!")
return true
