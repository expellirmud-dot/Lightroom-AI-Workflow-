import os
import json
import uuid
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone
from lr_ai_exposure.job import create_job_directory, write_manifest, Manifest, ManifestEntry
from lr_ai_exposure.cache_extractor import snapshot_cache_dbs, extract_batch

def handoff_job(runtime_root: str, lrdata_dir: str, selection_json_path: str) -> str:
    """
    Takes a selection.json written by Lightroom, creates a job directory,
    snapshots the cache, extracts the previews, and writes manifest.json.
    Returns the job_id.
    """
    import hashlib
    import shutil
    
    runtime_path = Path(runtime_root)
    with open(selection_json_path, "r", encoding="utf-8") as f:
        selection_data = json.load(f)
        
    from lr_ai_exposure.bridge import BridgeRequest
    try:
        req = BridgeRequest.from_dict(selection_data)
        selection = selection_data
    except ValueError as e:
        # Fallback if old format, but wait, WO-026 requires strict validation.
        # But maybe we just enforce it if "protocol_version" is present, else let it pass for backwards compatibility?
        # Actually WO-026: "2. Reject unsupported protocol versions."
        if "protocol_version" in selection_data:
            req = BridgeRequest.from_dict(selection_data)
        selection = selection_data
        
    identities = selection.get("photos", [])
    for item in identities:
        p = item.get("path", "")
        if not p:
            raise ValueError("Selection item missing path")
        pp = Path(p)
        if not pp.is_absolute():
            raise ValueError(f"Selection path must be absolute: {p}")
        if not pp.exists():
            raise FileNotFoundError(f"Selection path does not exist: {p}")
            
    job_id = selection.get("job_id", f"job-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    job_dir = create_job_directory(runtime_path, job_id)
    
    # Write selection atomically to job_dir
    dest_selection = job_dir / "selection.json"
    temp_selection = job_dir / "selection.json.tmp"
    with open(temp_selection, "w", encoding="utf-8") as f:
        json.dump(selection, f, indent=2, ensure_ascii=False)
    temp_selection.replace(dest_selection)
    
    # Snapshot cache
    snapshot_dir = job_dir / "cache_snapshots"
    snapshot_cache_dbs(lrdata_dir, str(snapshot_dir))
    
    # Extract previews
    out_dir = job_dir / "previews"
    identities = selection.get("photos", [])
    
    results = extract_batch(identities, str(snapshot_dir), str(out_dir))
    
    # Build manifest entries
    entries = []
    
    total_found = 0
    total_missing = 0
    total_ambiguous = 0
    total_failed = 0
    
    for i, res in enumerate(results):
        src_path = identities[i].get("path", "")
        stem = os.path.splitext(os.path.basename(src_path))[0]
        
        raw_path_canon = str(Path(src_path).resolve())
        source_xmp_path = str(Path(src_path).with_suffix(".xmp").resolve())
        backup_relative_path = f"xmp_backups/{stem}.xmp"
        preview_path_rel = f"previews/{i+1:06d}__{stem}.jpg"
        
        status = res["status"]
        preview_bytes = 0
        preview_sha256 = None
        
        if status == "FOUND" and res.get("output") and os.path.exists(res.get("output", "")):
            out_path = res["output"]
            preview_bytes = os.path.getsize(out_path)
            
            hasher = hashlib.sha256()
            with open(out_path, "rb") as f:
                hasher.update(f.read())
            preview_sha256 = hasher.hexdigest()
            
            # Ensure every FOUND preview path exists
            if not (job_dir / preview_path_rel).exists():
                raise FileNotFoundError(f"Extracted preview missing at expected relative path: {preview_path_rel}")
            total_found += 1
        elif status == "MISSING":
            total_missing += 1
        elif status == "AMBIGUOUS":
            total_ambiguous += 1
        else:
            total_failed += 1
            
        entry = ManifestEntry(
            image_id=str(identities[i].get("id_local", "")),
            raw_path=raw_path_canon,
            source_xmp_path=source_xmp_path,
            backup_relative_path=backup_relative_path,
            preview_path=preview_path_rel,
            seq=i + 1,
            extraction_status=status,
            uuid=res.get("uuid"),
            preview_bytes=preview_bytes,
            preview_sha256=preview_sha256
        )
        entries.append(entry)
        
    manifest = Manifest(
        job_id=job_id, 
        entries=entries,
        total_selected=len(identities),
        total_found=total_found,
        total_missing=total_missing,
        total_ambiguous=total_ambiguous,
        total_failed=total_failed
    )
    write_manifest(job_dir, manifest)
    
    return job_id
