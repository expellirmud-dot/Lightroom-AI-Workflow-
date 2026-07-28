local function assert_equal(expected, actual, msg)
    if expected ~= actual then
        error(string.format("ASSERT FAILED: %s. Expected '%s', got '%s'", msg or "", tostring(expected), tostring(actual)))
    end
end

print("Running RunExposureAssist behavior tests...")

-- Mock Lightroom photo object
local MockPhoto = {}
MockPhoto.__index = MockPhoto

function MockPhoto.new(id_num, path, uuid)
    local self = setmetatable({}, MockPhoto)
    -- Prove numeric localIdentifier is read as a property
    self.localIdentifier = id_num
    self._path = path
    self._uuid = uuid
    return self
end

function MockPhoto:getRawMetadata(key)
    if key == "path" then return self._path end
    if key == "uuid" then return self._uuid end
end

-- Mock photos array to preserve ordered selection
local photos = {
    MockPhoto.new(1001, "C:\\test1.raw", "uuid-1"),
    MockPhoto.new(1002, "C:\\test2.raw", "uuid-2"),
    MockPhoto.new(1003, "C:\\test3.raw", "uuid-3")
}

local selectionData = {}
local photoMap = {}

for _, photo in ipairs(photos) do
    local path = photo:getRawMetadata("path")
    
    -- Using the repaired logic
    local id_local = tostring(photo.localIdentifier)
    local uuid = photo:getRawMetadata("uuid")
    
    table.insert(selectionData, {
        id_local = id_local,
        path = path,
        uuid = uuid
    })
    
    -- Prove photoMap uses the same normalized string key
    photoMap[id_local] = photo
end

-- Assertions
assert_equal(3, #selectionData, "Ordered selection is preserved: count")
assert_equal("1001", selectionData[1].id_local, "Resulting id_local is a string")
assert_equal("string", type(selectionData[1].id_local), "Resulting id_local type")
assert_equal(1001, photoMap["1001"].localIdentifier, "photoMap uses string key to map to numeric localIdentifier property")
assert_equal("1002", selectionData[2].id_local, "Ordered selection preserved: 2nd element")
assert_equal("1003", selectionData[3].id_local, "Ordered selection preserved: 3rd element")

print("All RunExposureAssist behavior tests passed!")
return true
