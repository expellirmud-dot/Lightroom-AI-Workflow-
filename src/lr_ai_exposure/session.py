from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from lr_ai_exposure.ai_judge import SinglePassDecision, Action

class SessionError(Exception):
    pass

@dataclass
class ExposureHistory:
    pass_id: str
    delta_ev: float
    expected_exposure2012: float

@dataclass
class SessionImageState:
    image_id: str
    uuid: str
    raw_path: str
    source_xmp_path: str
    backup_relative_path: str
    scene_group_id: str = "ungrouped"
    is_reference: bool = False
    status: Literal["PENDING", "PASS", "ADJUST", "REVIEW"] = "PENDING"
    cumulative_delta_ev: float = 0.0
    previous_pass_id: str | None = None
    expected_exposure2012: float | None = None
    last_preview_sha256: str | None = None
    oscillations: int = 0
    history: list[ExposureHistory] = field(default_factory=list)

@dataclass
class SessionState:
    session_id: str
    source_folder: str
    images: dict[str, SessionImageState] = field(default_factory=dict)
    passes: list[str] = field(default_factory=list)
    is_converged: bool = False
    policy: dict[str, Any] = field(default_factory=dict)

def load_session(session_dir: Path) -> SessionState:
    path = session_dir / "session.json"
    if not path.exists():
        raise SessionError(f"No session found at {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    images = {}
    for k, v in raw.get("images", {}).items():
        hist = []
        for h in v.get("history", []):
            hist.append(ExposureHistory(**h))
        v["history"] = hist
        images[k] = SessionImageState(**v)
    return SessionState(
        session_id=raw["session_id"],
        source_folder=raw["source_folder"],
        images=images,
        passes=raw.get("passes", []),
        is_converged=raw.get("is_converged", False),
        policy=raw.get("policy", {})
    )

def write_session_state(session_dir: Path, state: SessionState) -> None:
    path = session_dir / "session.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    images_dict = {}
    for k, v in state.images.items():
        images_dict[k] = {
            "image_id": v.image_id,
            "uuid": v.uuid,
            "raw_path": v.raw_path,
            "source_xmp_path": v.source_xmp_path,
            "backup_relative_path": v.backup_relative_path,
            "scene_group_id": v.scene_group_id,
            "is_reference": v.is_reference,
            "status": v.status,
            "cumulative_delta_ev": v.cumulative_delta_ev,
            "previous_pass_id": v.previous_pass_id,
            "expected_exposure2012": v.expected_exposure2012,
            "last_preview_sha256": v.last_preview_sha256,
            "oscillations": v.oscillations,
            "history": [{"pass_id": h.pass_id, "delta_ev": h.delta_ev, "expected_exposure2012": h.expected_exposure2012} for h in v.history]
        }
    payload = {
        "session_id": state.session_id,
        "source_folder": state.source_folder,
        "images": images_dict,
        "passes": state.passes,
        "is_converged": state.is_converged,
        "policy": state.policy
    }
    tmp = path.with_name("session.json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)

def create_session(session_dir: Path, session_id: str, source_folder: str, selection: list[dict[str, Any]]) -> SessionState:
    state = SessionState(session_id=session_id, source_folder=source_folder)
    for idx, item in enumerate(selection):
        image_id = str(item["id_local"])
        state.images[image_id] = SessionImageState(
            image_id=image_id,
            uuid=item.get("uuid", ""),
            raw_path=item["path"],
            source_xmp_path=item.get("xmp_path", ""),
            backup_relative_path=f"xmp_backups/{image_id}.xmp"
        )
    write_session_state(session_dir, state)
    return state
