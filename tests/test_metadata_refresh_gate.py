import pytest
from lr_ai_exposure.bridge import get_refresh_ids

def test_refresh_gate_allows_only_applied_verified():
    payload = {
        "job_id": "job1",
        "results": [
            {"image_id": "1", "status": "APPLIED_VERIFIED"},
            {"image_id": "2", "status": "FAILED_AFTER_REPLACE_ROLLED_BACK"},
            {"image_id": "3", "status": "SKIPPED"},
            {"image_id": "4", "status": "PROPOSED"},
            {"image_id": "5", "status": "APPLIED_VERIFIED"}
        ]
    }

    refresh_ids = get_refresh_ids(payload)
    assert refresh_ids == ["1", "5"]

def test_refresh_gate_empty_results():
    assert get_refresh_ids({"job_id": "job1", "results": []}) == []

def test_refresh_gate_no_results_key():
    assert get_refresh_ids({"job_id": "job1"}) == []
