from __future__ import annotations

from pathlib import Path

from lr_ai_exposure.job import Manifest, ManifestEntry, read_manifest, write_manifest
from lr_ai_exposure.render_barrier import validate_render_barrier
from lr_ai_exposure.session import create_session


def _entry(*, preview_sha256: str, source_preview_sha256: str | None) -> ManifestEntry:
    return ManifestEntry(
        image_id="1",
        raw_path="D:/Photos/1.NEF",
        source_xmp_path="D:/Photos/1.xmp",
        backup_relative_path="xmp_backups/1.xmp",
        preview_path="previews/1.jpg",
        seq=1,
        extraction_status="FOUND",
        uuid="uuid-1",
        preview_bytes=123,
        preview_sha256=preview_sha256,
        preview_orientation="DA",
        source_preview_sha256=source_preview_sha256,
    )


def test_manifest_round_trip_preserves_raw_preview_fingerprint(tmp_path: Path) -> None:
    manifest = Manifest(
        job_id="sess-orientation",
        entries=[_entry(preview_sha256="normalized-sha", source_preview_sha256="raw-sha")],
        total_selected=1,
        total_found=1,
    )
    write_manifest(tmp_path, manifest)
    loaded = read_manifest(tmp_path)
    assert loaded.entries[0].preview_sha256 == "normalized-sha"
    assert loaded.entries[0].preview_orientation == "DA"
    assert loaded.entries[0].source_preview_sha256 == "raw-sha"


def _adjusted_state(tmp_path: Path, last_preview_sha256: str):
    state = create_session(
        tmp_path,
        "sess-orientation",
        "D:/Photos",
        [
            {
                "id_local": "1",
                "uuid": "uuid-1",
                "path": "D:/Photos/1.NEF",
                "catalog_exposure2012": 0.0,
            }
        ],
    )
    state.images["1"].status = "ADJUST"
    state.images["1"].expected_exposure2012 = 0.0
    state.images["1"].last_preview_sha256 = last_preview_sha256
    return state


def test_render_barrier_compares_raw_fingerprint_not_normalized_artifact_hash(tmp_path: Path) -> None:
    state = _adjusted_state(tmp_path / "same", "raw-old")
    manifest = Manifest(
        job_id="sess-orientation",
        entries=[_entry(preview_sha256="normalized-new", source_preview_sha256="raw-old")],
    )
    result = validate_render_barrier(state, manifest, {"1": 0.0})
    assert result["1"] == "WAITING_FOR_RERENDER_HASH_UNCHANGED"

    fresh_state = _adjusted_state(tmp_path / "fresh", "raw-old")
    fresh_manifest = Manifest(
        job_id="sess-orientation",
        entries=[_entry(preview_sha256="normalized-new", source_preview_sha256="raw-new")],
    )
    fresh = validate_render_barrier(fresh_state, fresh_manifest, {"1": 0.0})
    assert fresh["1"] == "FRESH"


def test_render_barrier_historical_manifest_falls_back_to_preview_sha(tmp_path: Path) -> None:
    state = _adjusted_state(tmp_path / "legacy", "legacy-sha")
    legacy_manifest = Manifest(
        job_id="sess-orientation",
        entries=[_entry(preview_sha256="legacy-sha", source_preview_sha256=None)],
    )
    result = validate_render_barrier(state, legacy_manifest, {"1": 0.0})
    assert result["1"] == "WAITING_FOR_RERENDER_HASH_UNCHANGED"
