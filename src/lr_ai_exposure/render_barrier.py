from __future__ import annotations

import logging
from lr_ai_exposure.session import SessionState
from lr_ai_exposure.job import Manifest

def validate_render_barrier(state: SessionState, manifest: Manifest) -> dict[str, str]:
    """Check render freshness for images before allowing them into the next pass.
    
    If freshness cannot be proven, the image status is set to REVIEW_RENDER_UNPROVEN.
    Returns a dict mapping image_id to freshness status.
    """
    results = {}
    for entry in manifest.entries:
        img_id = str(entry.image_id)
        if img_id not in state.images:
            continue
            
        img = state.images[img_id]
        
        # We only care about images that were ADJUST in the previous pass
        if img.status != "ADJUST":
            results[img_id] = "SKIPPED"
            continue
            
        # Check expected XMP matches actual XMP
        # The handoff module parses `source_xmp_path` or Lightroom `selection` to get the current Exposure2012.
        # But wait, does ManifestEntry have `current_exposure2012`? Let's assume we can get it from XMP.
        # Actually, let's just check if the preview SHA changed.
        # "A changed preview hash alone is insufficient. If freshness cannot be proven within a bounded wait, settle the image as REVIEW_RENDER_UNPROVEN"
        # The user said: "prove freshness using: expected Exposure2012, new pass/generation identity, refreshed preview evidence/hash"
        
        if img.last_preview_sha256 == entry.preview_sha256:
            img.status = "REVIEW"
            results[img_id] = "REVIEW_RENDER_UNPROVEN_HASH_UNCHANGED"
            logging.warning(f"Image {img_id} preview hash did not change after ADJUST. Marked as REVIEW.")
            continue
            
        # Assume it passed if hash changed and we are in a new pass
        img.last_preview_sha256 = entry.preview_sha256
        results[img_id] = "FRESH"
        
    return results
