local LrTasks = import "LrTasks"
local Json = require "Json"

local CatalogApplyBarrier = {}

local function withinTolerance(actual, expected, tolerance)
    return type(actual) == "number"
        and type(expected) == "number"
        and math.abs(actual - expected) <= tolerance
end

function CatalogApplyBarrier.evidenceHasFailures(Support, evidencePath)
    if not Support.fileExists(evidencePath) then
        return false, {}
    end
    local evidence = Support.readJsonFile(evidencePath)
    local failed = evidence.failed_image_ids
    if type(failed) ~= "table" or #failed == 0 then
        return false, {}
    end
    local ids = {}
    for _, imageId in ipairs(failed) do
        ids[#ids + 1] = tostring(imageId)
    end
    return true, ids
end

function CatalogApplyBarrier.applyCatalogPlan(Support, catalog, photoMap, plan, resultPath)
    local tolerance = tonumber(plan.catalog_exposure_tolerance) or 0.01
    local results = {}
    local pending = {}

    -- Lightroom may not expose a Develop mutation through getDevelopSettings()
    -- until the write-access callback has returned. The transaction therefore
    -- only validates the precondition and requests the absolute target value.
    catalog:withWriteAccessDo("AI Exposure Assist — Exposure2012", function()
        for _, item in ipairs(plan.items or {}) do
            local imageId = tostring(item.image_id)
            local photo = photoMap[imageId]
            local expectedBefore = tonumber(item.expected_before_exposure2012)
            local target = tonumber(item.target_exposure2012)
            local result = {
                image_id = imageId,
                expected_before_exposure2012 = expectedBefore,
                target_exposure2012 = target,
            }

            if not photo then
                result.status = "PHOTO_ID_NOT_FOUND"
            elseif expectedBefore == nil or target == nil then
                result.status = "PLAN_VALUE_INVALID"
            else
                local observedBefore, beforeError = Support.getCatalogExposure2012(photo)
                result.observed_before_exposure2012 = observedBefore
                if observedBefore == nil then
                    result.status = "CATALOG_READ_FAILED"
                    result.error = beforeError
                elseif withinTolerance(observedBefore, target, tolerance) then
                    -- Retry/recovery is idempotent: if Lightroom already owns the
                    -- absolute target, do not apply the delta again.
                    result.status = "APPLIED_VERIFIED"
                    result.observed_after_exposure2012 = observedBefore
                    result.verification_mode = "TARGET_ALREADY_PRESENT"
                    result.verify_attempts = 0
                elseif not withinTolerance(observedBefore, expectedBefore, tolerance) then
                    result.status = "CATALOG_DRIFT"
                else
                    local applyOk, applyError = LrTasks.pcall(function()
                        photo:applyDevelopSettings({ Exposure2012 = target })
                    end)
                    if not applyOk then
                        result.status = "CATALOG_APPLY_FAILED"
                        result.error = tostring(applyError)
                    else
                        result.status = "APPLY_REQUESTED"
                        pending[#pending + 1] = {
                            photo = photo,
                            target = target,
                            result = result,
                        }
                    end
                end
            end
            results[#results + 1] = result
        end
    end)

    -- Verification is deliberately outside withWriteAccessDo. Polling is
    -- bounded so this short-lived command can never become a resident listener.
    local maxVerifyAttempts = 25
    local verifySleepSeconds = 0.10
    for attempt = 1, maxVerifyAttempts do
        local unresolved = 0
        for _, item in ipairs(pending) do
            local result = item.result
            if result.status == "APPLY_REQUESTED" then
                local observedAfter, afterError = Support.getCatalogExposure2012(item.photo)
                result.observed_after_exposure2012 = observedAfter
                if observedAfter == nil then
                    result.verify_error = afterError
                    unresolved = unresolved + 1
                elseif withinTolerance(observedAfter, item.target, tolerance) then
                    result.status = "APPLIED_VERIFIED"
                    result.verification_mode = "POST_COMMIT_POLL"
                    result.verify_attempts = attempt
                else
                    unresolved = unresolved + 1
                end
            end
        end

        if unresolved == 0 then
            break
        end
        if attempt < maxVerifyAttempts then
            LrTasks.sleep(verifySleepSeconds)
        end
    end

    for _, item in ipairs(pending) do
        local result = item.result
        if result.status == "APPLY_REQUESTED" then
            result.status = "CATALOG_VERIFY_TIMEOUT"
            result.verify_attempts = maxVerifyAttempts
        end
    end

    local payload = {
        protocol_version = "1.1",
        operation = "LIGHTROOM_CATALOG_EXPOSURE2012_APPLY_RESULT",
        session_id = plan.session_id,
        pass_id = plan.pass_id,
        pass_number = plan.pass_number,
        results = results,
    }
    Support.writeUtf8File(resultPath, Json.encode(payload))
    return payload
end

return CatalogApplyBarrier
