-- TestActiveFolderResolver.lua
local ActiveFolderResolver = require 'ActiveFolderResolver'

local passed = 0
local failed = 0

local function assert_equal(expected, actual, desc)
    if expected == actual then
        passed = passed + 1
        print("PASS: " .. desc)
    else
        failed = failed + 1
        print("FAIL: " .. desc .. " (expected " .. tostring(expected) .. ", got " .. tostring(actual) .. ")")
    end
end

local function run_tests()
    -- Mock LrFolder
    local MockFolder = {}
    MockFolder.__index = MockFolder
    function MockFolder:getName() return "TestFolder" end
    function MockFolder:getPath() return "C:\\Photos\\TestFolder" end
    function MockFolder:getChildren() return {} end
    function MockFolder:getPhotos() return {} end
    function MockFolder:getParent() return nil end

    -- Mock Collection (no getPath, or getPath throws/returns nil)
    local MockCollection = {}
    MockCollection.__index = MockCollection
    function MockCollection:getName() return "TestCollection" end
    function MockCollection:getPath() return nil end
    function MockCollection:getChildren() return {} end
    function MockCollection:getPhotos() return {} end

    local function createCatalog(sources)
        return {
            getActiveSources = function() return sources end
        }
    end

    print("--- Test ActiveFolderResolver ---")

    -- Test 1: Single valid folder
    local cat1 = createCatalog({ setmetatable({}, MockFolder) })
    local res1 = ActiveFolderResolver.resolveActiveFolder(cat1)
    assert_equal(1, res1.active_source_count, "One source")
    assert_equal(1, res1.folder_count, "One folder")
    assert_equal(nil, res1.error, "No error")
    assert_equal("C:\\Photos\\TestFolder", res1.sources_info[1].path, "Path extracted")

    -- Test 2: Collection
    local cat2 = createCatalog({ setmetatable({}, MockCollection) })
    local res2 = ActiveFolderResolver.resolveActiveFolder(cat2)
    assert_equal(1, res2.active_source_count, "One source")
    assert_equal(0, res2.folder_count, "Zero folders")
    assert_equal("None of the active sources are folders (Collections/Smart Collections are not supported).", res2.error, "Error on collection")

    -- Test 3: Multiple folders
    local cat3 = createCatalog({ setmetatable({}, MockFolder), setmetatable({}, MockFolder) })
    local res3 = ActiveFolderResolver.resolveActiveFolder(cat3)
    assert_equal(2, res3.active_source_count, "Two sources")
    assert_equal(2, res3.folder_count, "Two folders")
    assert_equal("Exactly one folder is required, but 2 folders are selected.", res3.error, "Error on multiple folders")

    -- Test 4: Missing getPath capability entirely
    local MockWeird = {}
    MockWeird.__index = MockWeird
    function MockWeird:getName() return "Weird" end
    local cat4 = createCatalog({ setmetatable({}, MockWeird) })
    local res4 = ActiveFolderResolver.resolveActiveFolder(cat4)
    assert_equal(0, res4.folder_count, "Zero folders")
    assert_equal("No getPath() capability (likely a Collection or smart source)", res4.sources_info[1].reason, "Reason for rejection")

    print("\nTotal passed: " .. tostring(passed))
    print("Total failed: " .. tostring(failed))
    
    if failed > 0 then
        os.exit(1)
    end
end

run_tests()
