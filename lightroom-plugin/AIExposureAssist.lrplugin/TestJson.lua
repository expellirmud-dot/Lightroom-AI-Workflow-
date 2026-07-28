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
return true
