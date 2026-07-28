import pytest
from lr_ai_exposure.bridge import BridgeRequest, BridgeIdentity

def test_bridge_request_parses_valid_payload():
    payload = {
        "protocol_version": "1.0",
        "job_id": "job_123",
        "selected_count": 2,
        "requested_mode": "ANALYZE_ONLY",
        "photos": [
            {"id_local": "1", "path": "/path/1.cr2", "uuid": "u1"},
            {"id_local": "2", "path": "/path/2.cr2", "uuid": "u2"}
        ]
    }
    
    req = BridgeRequest.from_dict(payload)
    assert req.protocol_version == "1.0"
    assert req.job_id == "job_123"
    assert req.selected_count == 2
    assert req.requested_mode == "ANALYZE_ONLY"
    assert len(req.photos) == 2
    assert req.photos[0].id_local == "1"
    
def test_bridge_request_rejects_unsupported_protocol():
    payload = {
        "protocol_version": "2.0",
        "job_id": "job_123",
        "selected_count": 0,
        "requested_mode": "ANALYZE_ONLY",
        "photos": []
    }
    with pytest.raises(ValueError, match="Unsupported protocol version"):
        BridgeRequest.from_dict(payload)
        
def test_bridge_request_validates_count():
    payload = {
        "protocol_version": "1.0",
        "job_id": "job_123",
        "selected_count": 5,
        "requested_mode": "ANALYZE_ONLY",
        "photos": [
            {"id_local": "1", "path": "/path/1.cr2", "uuid": "u1"}
        ]
    }
    with pytest.raises(ValueError, match="selected_count does not match"):
        BridgeRequest.from_dict(payload)
