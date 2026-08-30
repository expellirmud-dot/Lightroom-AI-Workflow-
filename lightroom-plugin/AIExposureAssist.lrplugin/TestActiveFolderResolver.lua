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

local function assert_contains(actual, expectedPart, desc)
    if type(actual) == "string" and string.find(actual, expectedPart, 1, true) then
        passed = passed + 1
        print("PASS: " .. desc)
    else
        failed = failed + 1
        print("FAIL: " .. desc .. " (expected substring " .. tostring(expectedPart) .. ", got " .. tostring(actual) .. ")")
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
    function MockFolder:type() return "LrFolder" end

    -- Mock Collection
    local MockCollection = {}
    MockCollection.__index = MockCollection
    function MockCollection:getName() return "TestCollection" end
    function MockCollection:getPath() return nil end
    function MockCollection:getChildren() return {} end
    function MockCollection:getPhotos() return {} end
    function MockCollection:type() return "LrCollection" end

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
    assert_equal("LrFolder", res1.sources_info[1].source_type, "LrFolder type preserved")

    -- Test 2: Collection must not be classified as folder even though it has getPhotos
    local cat2 = createCatalog({ setmetatable({}, MockCollection) })
    local res2 = ActiveFolderResolver.resolveActiveFolder(cat2)
    assert_equal(1, res2.active_source_count, "One collection source")
    assert_equal(0, res2.folder_count, "Collection is not a folder")
    assert_contains(res2.sources_info[1].reason, "not LrFolder", "Collection rejection has exact reason")

    -- Test 3: Multiple folders
    local cat3 = createCatalog({ setmetatable({}, MockFolder), setmetatable({}, MockFolder) })
    local res3 = ActiveFolderResolver.resolveActiveFolder(cat3)
    assert_equal(2, res3.active_source_count, "Two sources")
    assert_equal(2, res3.folder_count, "Two folders")
    assert_equal("Exactly one folder is required, but 2 folders are selected.", res3.error, "Error on multiple folders")

    -- Test 4: Missing type() may use compatibility fallback if path + getPhotos are valid
    local MockLegacyFolder = {}
    MockLegacyFolder.__index = MockLegacyFolder
    function MockLegacyFolder:getName() return "LegacyFolder" end
    function MockLegacyFolder:getPath() return "C:\\Photos\\Legacy" end
    function MockLegacyFolder:getPhotos() return {} end
    local res4 = ActiveFolderResolver.resolveActiveFolder(createCatalog({ setmetatable({}, MockLegacyFolder) }))
    assert_equal(1, res4.folder_count, "Compatibility fallback recognizes path + getPhotos")

    -- Test 5: A real LrFolder is not silently reclassified when getPath fails.
    local MockFolderPathFailure = {}
    MockFolderPathFailure.__index = MockFolderPathFailure
    function MockFolderPathFailure:getName() return "BrokenPathFolder" end
    function MockFolderPathFailure:type() return "LrFolder" end
    function MockFolderPathFailure:getPath() error("simulated Lightroom path failure") end
    function MockFolderPathFailure:getChildren() return {} end
    function MockFolderPathFailure:getPhotos() return {} end
    local res5 = ActiveFolderResolver.resolveActiveFolder(createCatalog({ setmetatable({}, MockFolderPathFailure) }))
    assert_equal(1, res5.folder_count, "LrFolder identity survives getPath failure")
    assert_contains(res5.error, "Active source is LrFolder", "Path failure is reported separately")
    assert_contains(res5.sources_info[1].get_path_error, "simulated Lightroom path failure", "Underlying path error preserved")

    print("\nTotal passed: " .. tostring(passed))
    print("Total failed: " .. tostring(failed))

    if failed > 0 then
        os.exit(1)
    end
end

run_tests()
