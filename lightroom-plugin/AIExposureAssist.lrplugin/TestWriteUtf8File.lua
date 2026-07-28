local function assert_equal(expected, actual, msg)
    if expected ~= actual then
        error(string.format("ASSERT FAILED: %s. Expected '%s', got '%s'", msg or "", tostring(expected), tostring(actual)))
    end
end

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

print("Running writeUtf8File tests...")

-- Test: selection.json is written successfully & Thai UTF-8 survives round-trip & Windows paths survive round-trip
local testPath = "test_selection.json"
local testContent = '{"path": "C:\\\\Thai\\\\ภาพถ่าย.raw"}'
writeUtf8File(testPath, testContent)

local f = io.open(testPath, "rb")
local readContent = f:read("*a")
f:close()
assert_equal(testContent, readContent, "Thai UTF-8 and Windows paths survive round-trip")
os.remove(testPath)

-- Test: open failure is reported clearly
local invalidPath = "X:\\NonExistentDrive\\test.json"
local status, err = pcall(function() writeUtf8File(invalidPath, "test") end)
assert(status == false, "Open failure should throw error")
assert(string.find(tostring(err), "Could not open file for writing"), "Open failure clearly reported")

print("All writeUtf8File tests passed!")
