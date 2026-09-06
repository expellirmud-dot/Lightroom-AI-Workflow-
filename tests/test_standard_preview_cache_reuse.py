from __future__ import annotations

import hashlib
import io
import sqlite3
from pathlib import Path

from PIL import Image

from lr_ai_exposure.cache_extractor import extract_batch, snapshot_cache_dbs
from lr_ai_exposure.cache_probe import find_cached_preview_tier, find_preview_record
from lr_ai_exposure.job import Manifest, ManifestEntry, read_manifest, write_manifest
from lr_ai_exposure.session import SessionError
from lr_ai_exposure.session_lifecycle import prepare_session_pass


def _jpeg_bytes(width: int, height: int, *, marker: int = 120) -> bytes:
    image = Image.new("RGB", (width, height), (marker, 80, 40))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=91)
    return out.getvalue()


def _write_cache(
    root: Path,
    *,
    image_id: str = "1",
    uuid: str = "ABCD1234-0000-0000-0000-000000000000",
    digest: str = "digest1234",
    orientation: str = "AB",
    tiers: dict[int, bytes] | None = None,
) -> tuple[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(root / "previews.db") as db:
        db.execute(
            "CREATE TABLE ImageCacheEntry (imageId TEXT, uuid TEXT, digest TEXT, orientation TEXT)"
        )
        db.execute(
            "INSERT INTO ImageCacheEntry VALUES (?, ?, ?, ?)",
            (image_id, uuid, digest, orientation),
        )
    with sqlite3.connect(root / "root-pixels.db") as db:
        db.execute("CREATE TABLE RootPixels (uuid TEXT, jpegData BLOB)")
        db.execute(
            "INSERT INTO RootPixels VALUES (?, ?)",
            (uuid, _jpeg_bytes(320, 213, marker=30)),
        )
    bucket = root / uuid[:1] / uuid[:4]
    bucket.mkdir(parents=True, exist_ok=True)
    for tier, data in (tiers or {}).items():
        (bucket / f"{uuid}-{digest}_{tier}").write_bytes(data)
    return uuid, digest


def test_preview_record_resolves_digest_with_orientation(tmp_path: Path) -> None:
    cache = tmp_path / "Catalog Previews.lrdata"
    uuid, digest = _write_cache(cache, orientation="DA", tiers={1440: _jpeg_bytes(1440, 960)})
    found = find_preview_record(str(cache / "previews.db"), "1")
    assert found == {
        "status": "FOUND",
        "uuid": uuid,
        "digest": digest,
        "orientation": "DA",
    }


def test_tier_selection_prefers_exact_then_smallest_larger_and_never_smaller(tmp_path: Path) -> None:
    exact = tmp_path / "exact.lrdata"
    uuid, digest = _write_cache(
        exact,
        tiers={960: _jpeg_bytes(960, 640), 1440: _jpeg_bytes(1440, 960), 1920: _jpeg_bytes(1920, 1280)},
    )
    selected = find_cached_preview_tier(exact, uuid, digest, 1440)
    assert selected["status"] == "FOUND"
    assert selected["tier"] == 1440

    larger = tmp_path / "larger.lrdata"
    uuid2, digest2 = _write_cache(
        larger,
        tiers={960: _jpeg_bytes(960, 640), 1920: _jpeg_bytes(1920, 1280), 2560: _jpeg_bytes(2560, 1707)},
    )
    fallback = find_cached_preview_tier(larger, uuid2, digest2, 1440)
    assert fallback["status"] == "FOUND"
    assert fallback["tier"] == 1920

    small = tmp_path / "small.lrdata"
    uuid3, digest3 = _write_cache(small, tiers={320: _jpeg_bytes(320, 213), 960: _jpeg_bytes(960, 640)})
    not_ready = find_cached_preview_tier(small, uuid3, digest3, 1440)
    assert not_ready["status"] == "PREVIEW_TIER_NOT_READY"
    assert not_ready["tier"] is None
    assert not_ready["available_tiers"] == [320, 960]


def test_canonical_extract_copies_exact_ab_bytes_and_records_tier(tmp_path: Path) -> None:
    cache = tmp_path / "Catalog Previews.lrdata"
    source = _jpeg_bytes(1440, 960, marker=177)
    uuid, digest = _write_cache(cache, tiers={1440: source})
    snapshot = tmp_path / "snapshot"
    snapshot_cache_dbs(str(cache), str(snapshot))

    results = extract_batch(
        [{"id_local": "1", "path": "D:/photos/a.NEF"}],
        str(snapshot),
        str(tmp_path / "out"),
        lrdata_dir=str(cache),
        target_preview_size=1440,
    )
    assert results[0]["status"] == "FOUND"
    assert results[0]["source_preview_tier"] == 1440
    assert results[0]["source_preview_sha256"] == hashlib.sha256(source).hexdigest()
    assert Path(results[0]["output"]).read_bytes() == source


def test_canonical_extract_reuses_render_then_only_normalizes_orientation(tmp_path: Path) -> None:
    cache = tmp_path / "Catalog Previews.lrdata"
    source = _jpeg_bytes(1440, 960, marker=201)
    _write_cache(cache, orientation="DA", tiers={1440: source})
    snapshot = tmp_path / "snapshot"
    snapshot_cache_dbs(str(cache), str(snapshot))

    results = extract_batch(
        [{"id_local": "1", "path": "D:/photos/a.NEF"}],
        str(snapshot),
        str(tmp_path / "out"),
        lrdata_dir=str(cache),
        target_preview_size=1440,
    )
    assert results[0]["status"] == "FOUND"
    assert results[0]["source_preview_tier"] == 1440
    assert results[0]["source_preview_sha256"] == hashlib.sha256(source).hexdigest()
    with Image.open(results[0]["output"]) as image:
        assert image.size == (960, 1440)


def test_canonical_extract_fails_closed_when_only_small_tiers_exist(tmp_path: Path) -> None:
    cache = tmp_path / "Catalog Previews.lrdata"
    _write_cache(cache, tiers={320: _jpeg_bytes(320, 213), 960: _jpeg_bytes(960, 640)})
    snapshot = tmp_path / "snapshot"
    snapshot_cache_dbs(str(cache), str(snapshot))
    results = extract_batch(
        [{"id_local": "1", "path": "D:/photos/a.NEF"}],
        str(snapshot),
        str(tmp_path / "out"),
        lrdata_dir=str(cache),
        target_preview_size=1440,
    )
    assert results[0]["status"] == "PREVIEW_TIER_NOT_READY"
    assert results[0]["output"] is None
    assert results[0]["available_preview_tiers"] == [320, 960]


def test_manifest_round_trip_preserves_source_preview_tier_and_old_manifest_can_omit_it(tmp_path: Path) -> None:
    entry = ManifestEntry(
        image_id="1",
        raw_path="D:/photos/a.NEF",
        source_xmp_path="D:/photos/a.xmp",
        backup_relative_path="xmp_backups/a.xmp",
        preview_path="previews/a.jpg",
        seq=1,
        extraction_status="FOUND",
        uuid="uuid-1",
        preview_bytes=100,
        preview_sha256="artifact",
        source_preview_sha256="source",
        source_preview_tier=1440,
    )
    write_manifest(tmp_path, Manifest(job_id="job", entries=[entry], total_selected=1, total_found=1))
    loaded = read_manifest(tmp_path)
    assert loaded.entries[0].source_preview_tier == 1440

    import json
    raw = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    raw["entries"][0].pop("source_preview_tier")
    (tmp_path / "manifest.json").write_text(json.dumps(raw), encoding="utf-8")
    historical = read_manifest(tmp_path)
    assert historical.entries[0].source_preview_tier is None


def test_session_preparation_does_not_admit_smaller_only_preview(tmp_path: Path) -> None:
    import json
    import pytest

    cache = tmp_path / "Catalog Previews.lrdata"
    uuid, _digest = _write_cache(
        cache, tiers={320: _jpeg_bytes(320, 213), 960: _jpeg_bytes(960, 640)}
    )
    source = tmp_path / "photos"
    source.mkdir()
    raw = source / "a.NEF"
    raw.write_bytes(b"RAW")
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps(
            {
                "source_folder": str(source),
                "photos": [
                    {
                        "id_local": "1",
                        "uuid": uuid,
                        "path": str(raw),
                        "catalog_exposure2012": 0.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    runtime = tmp_path / "runtime"
    with pytest.raises(SessionError, match="PREVIEW_TIER_NOT_READY"):
        prepare_session_pass(
            runtime,
            cache,
            selection,
            session_id="sess-tier-not-ready",
            target_preview_size=1440,
        )
    session_dir = runtime / "sessions" / "sess-tier-not-ready"
    if session_dir.exists():
        state = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
        assert state["passes"] == []
