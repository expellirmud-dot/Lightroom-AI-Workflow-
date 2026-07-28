import json
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class BridgeIdentity:
    id_local: str
    path: str
    uuid: Optional[str] = None

@dataclass(frozen=True)
class BridgeRequest:
    protocol_version: str
    job_id: str
    selected_count: int
    requested_mode: str
    photos: List[BridgeIdentity]
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BridgeRequest':
        if data.get("protocol_version") != "1.0":
            raise ValueError(f"Unsupported protocol version: {data.get('protocol_version')}")
            
        photos = [BridgeIdentity(**p) for p in data.get("photos", [])]
        
        if len(photos) != data.get("selected_count"):
            raise ValueError("selected_count does not match photos length")
            
        return cls(
            protocol_version=data["protocol_version"],
            job_id=data["job_id"],
            selected_count=data["selected_count"],
            requested_mode=data["requested_mode"],
            photos=photos
        )

@dataclass(frozen=True)
class BridgeResult:
    job_id: str
    status: str  # "ok", "error"
    mode: str
    applied: int
    evidence_path: Optional[str] = None
    error_message: Optional[str] = None

def get_refresh_ids(evidence_payload: dict) -> List[str]:
    """Return only image_ids that reached APPLIED_VERIFIED state."""
    refresh_ids = []
    for res in evidence_payload.get("results", []):
        if res.get("status") == "APPLIED_VERIFIED":
            refresh_ids.append(res.get("image_id"))
    return refresh_ids

