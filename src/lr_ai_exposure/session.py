from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


class SessionError(ValueError):
    """Raised when an exposure session is missing, invalid, or corrupted."""


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
    baseline_exposure2012: float = 0.0
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


def resolve_session_dir(runtime_directory: Path, session_id: str) -> Path:
    if not session_id or session_id in {".", ".."} or "/" in session_id or "\\" in session_id:
        raise SessionError(f"Invalid session_id: {session_id!r}")
    sessions_root = (Path(runtime_directory) / "sessions").resolve()
    session_dir = (sessions_root / session_id).resolve()
    try:
        session_dir.relative_to(sessions_root)
    except ValueError as exc:
        raise SessionError(f"Session path escapes sessions root: {session_id}") from exc
    return session_dir


def load_session(session_dir: Path) -> SessionState:
    path = Path(session_dir) / "session.json"
    if not path.exists():
        raise SessionError(f"No session found at {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"Malformed session.json: {exc}") from exc

    if not isinstance(raw, dict):
        raise SessionError("session.json must be a JSON object")

    images: dict[str, SessionImageState] = {}
    for k, v in raw.get("images", {}).items():
        hist = [ExposureHistory(**h) for h in v.get("history", [])]
        v_copy = dict(v)
        v_copy["history"] = hist
        # Backward-compatible load for sessions created before WO-034.
        baseline = float(v_copy.get("baseline_exposure2012", v_copy.get("expected_exposure2012") or 0.0))
        v_copy["baseline_exposure2012"] = baseline
        if v_copy.get("expected_exposure2012") is None:
            v_copy["expected_exposure2012"] = baseline
        images[k] = SessionImageState(**v_copy)

    return SessionState(
        session_id=raw["session_id"],
        source_folder=raw["source_folder"],
        images=images,
        passes=raw.get("passes", []),
        is_converged=raw.get("is_converged", False),
        policy=raw.get("policy", {}),
    )


def write_session_state(session_dir: Path, state: SessionState) -> Path:
    path = Path(session_dir) / "session.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    images_dict: dict[str, dict[str, Any]] = {}
    for k, v in state.images.items():
        images_dict[k] = {
            "image_id": v.image_id,
            "uuid": v.uuid,
            "raw_path": v.raw_path,
            "source_xmp_path": v.source_xmp_path,
            "backup_relative_path": v.backup_relative_path,
            "baseline_exposure2012": v.baseline_exposure2012,
            "scene_group_id": v.scene_group_id,
            "is_reference": v.is_reference,
            "status": v.status,
            "cumulative_delta_ev": v.cumulative_delta_ev,
            "previous_pass_id": v.previous_pass_id,
            "expected_exposure2012": v.expected_exposure2012,
            "last_preview_sha256": v.last_preview_sha256,
            "oscillations": v.oscillations,
            "history": [
                {
                    "pass_id": h.pass_id,
                    "delta_ev": h.delta_ev,
                    "expected_exposure2012": h.expected_exposure2012,
                }
                for h in v.history
            ],
        }
    payload = {
        "protocol_version": "1.1",
        "session_id": state.session_id,
        "source_folder": state.source_folder,
        "images": images_dict,
        "passes": state.passes,
        "is_converged": state.is_converged,
        "policy": state.policy,
    }
    tmp = path.with_name("session.json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _catalog_exposure_from_selection(item: dict[str, Any]) -> float:
    raw = item.get("catalog_exposure2012", item.get("exposure2012", 0.0))
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise SessionError(
            f"Selection image {item.get('id_local')} has invalid catalog_exposure2012: {raw!r}"
        )
    value = float(raw)
    if value != value or value in {float("inf"), float("-inf")}:
        raise SessionError(
            f"Selection image {item.get('id_local')} has non-finite catalog_exposure2012"
        )
    return value


def create_session(
    session_dir: Path,
    session_id: str,
    source_folder: str,
    selection: list[dict[str, Any]],
    policy: dict[str, Any] | None = None,
) -> SessionState:
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    default_policy = {
        "tolerance": 0.10,
        "quantization": 0.05,
        "maximum_delta_ev": 1.0,
        "cumulative_delta_ev": 2.0,
        "maximum_passes": 4,
        "catalog_exposure_tolerance": 0.01,
    }
    if policy:
        default_policy.update(policy)

    state = SessionState(
        session_id=session_id,
        source_folder=source_folder,
        policy=default_policy,
    )
    for item in selection:
        image_id = str(item["id_local"])
        raw_path = str(Path(item["path"]).resolve())
        xmp_path = str(Path(raw_path).with_suffix(".xmp").resolve())
        baseline = _catalog_exposure_from_selection(item)
        state.images[image_id] = SessionImageState(
            image_id=image_id,
            uuid=item.get("uuid", ""),
            raw_path=raw_path,
            source_xmp_path=xmp_path,
            backup_relative_path=f"xmp_backups/{Path(raw_path).stem}.xmp",
            baseline_exposure2012=baseline,
            expected_exposure2012=baseline,
        )
    write_session_state(session_dir, state)

    policy_path = session_dir / "policy.json"
    policy_tmp = session_dir / "policy.json.tmp"
    policy_tmp.write_text(json.dumps(default_policy, indent=2) + "\n", encoding="utf-8")
    policy_tmp.replace(policy_path)

    return state
