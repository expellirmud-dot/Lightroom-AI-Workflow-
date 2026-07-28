"""XMP reading and backup utilities.

Implements WO-010: Safely locate, parse, and back up XMP sidecars without
modifying source XMP.
"""

from __future__ import annotations

import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


class XmpError(ValueError):
    """Raised when XMP is missing, malformed, or ambiguous."""


def read_exposure_2012(xmp_path: Path) -> float:
    """Read crs:Exposure2012 from an XMP file safely.
    
    Supports both RDF attribute and XML element serialization.
    Raises XmpError on missing, malformed, ambiguous, or invalid values.
    """
    if not xmp_path.is_file():
        raise XmpError(f"XMP file not found: {xmp_path}")
        
    try:
        tree = ET.parse(xmp_path)
    except ET.ParseError as e:
        raise XmpError(f"Malformed XML: {e}") from e
        
    root = tree.getroot()
    
    # Namespaces
    ns = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "crs": "http://ns.adobe.com/camera-raw-settings/1.0/"
    }
    
    # We must search for Exposure2012 both as an attribute on rdf:Description 
    # and as an element <crs:Exposure2012> inside rdf:Description.
    
    found_values: list[str] = []
    
    # Search all rdf:Description tags
    for desc in root.findall(".//rdf:Description", ns):
        # 1. Check attribute (most common)
        crs_exposure_attr = f"{{{ns['crs']}}}Exposure2012"
        if crs_exposure_attr in desc.attrib:
            found_values.append(desc.attrib[crs_exposure_attr])
            
        # 2. Check child element
        # Depending on formatting, it might be <crs:Exposure2012>val</crs:Exposure2012>
        for child in desc.findall("crs:Exposure2012", ns):
            if child.text is not None:
                found_values.append(child.text.strip())

    if not found_values:
        raise XmpError("crs:Exposure2012 not found in XMP")
        
    if len(found_values) > 1:
        # If they are exactly the same, we might accept it, but strictly it's ambiguous 
        # if multiple descriptions define it differently. Let's ensure they all match.
        if len(set(found_values)) > 1:
            raise XmpError("Ambiguous crs:Exposure2012 values found")
            
    raw_val = found_values[0]
    
    try:
        val = float(raw_val)
    except ValueError as e:
        raise XmpError(f"crs:Exposure2012 is not a valid number: {raw_val}") from e
        
    if not math.isfinite(val):
        raise XmpError(f"crs:Exposure2012 is not finite: {raw_val}")
        
    return val


import hashlib

def backup_xmp(xmp_path: Path, backup_dir: Path, dry_run: bool = False) -> tuple[Path, str]:
    """Create a collision-safe byte-preserving backup of an XMP file.
    
    Returns (backup_path, sha256_hash).
    Uses .dry_run suffix if dry_run=True, otherwise .bak.
    """
    if not xmp_path.is_file():
        raise XmpError(f"XMP file not found for backup: {xmp_path}")
        
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    suffix = ".dry_run" if dry_run else ".bak"
    
    base_name = f"{xmp_path.stem}.xmp"
    target_path = backup_dir / f"{base_name}{suffix}"
    
    # Collision safety: append number if exists
    counter = 1
    while target_path.exists():
        target_path = backup_dir / f"{base_name}.{counter}{suffix}"
        counter += 1
        
    # Byte-preserving copy
    try:
        shutil.copy2(xmp_path, target_path)
    except OSError as e:
        raise XmpError(f"Failed to copy XMP backup: {e}") from e
        
    # Compute SHA-256 of backup
    sha256 = hashlib.sha256(target_path.read_bytes()).hexdigest()
    return target_path, sha256


def rollback_xmp(xmp_path: Path, backup_path: Path, expected_sha256: str) -> None:
    """Roll back an XMP file from a backup, proving identity via SHA-256."""
    if not backup_path.is_file():
        raise XmpError(f"Backup file not found for rollback: {backup_path}")
        
    actual_sha256 = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise XmpError(f"Rollback aborted: backup SHA-256 mismatch. Expected {expected_sha256}, got {actual_sha256}")
        
    try:
        shutil.copy2(backup_path, xmp_path)
        restored_sha256 = hashlib.sha256(xmp_path.read_bytes()).hexdigest()
        if restored_sha256 != expected_sha256:
            raise XmpError("Rollback completed but restored target SHA-256 does not match!")
    except OSError as e:
        raise XmpError(f"Failed to rollback XMP: {e}") from e

import re
import os

def write_exposure_2012(xmp_path: Path, new_exposure: float, backup_dir: Path, dry_run: bool = False) -> str:
    """Surgically write a new Exposure2012 value to XMP, preserving all other bytes.
    
    Returns a proposal message if dry_run, otherwise returns success message.
    """
    if not math.isfinite(new_exposure):
        raise XmpError(f"New exposure must be finite, got {new_exposure}")

    # Read current to ensure valid and single definition
    old_exposure = read_exposure_2012(xmp_path)
    
    # Format new value as signed decimal (e.g., +0.25, -1.10, 0.00)
    new_exposure_str = f"{new_exposure:+.2f}"
    if new_exposure_str == "+0.00" or new_exposure_str == "-0.00":
        new_exposure_str = "0.00"
        
    if dry_run:
        backup_xmp(xmp_path, backup_dir, dry_run=True)
        return f"DRY RUN: Proposed change crs:Exposure2012 from {old_exposure} to {new_exposure_str}"
        
    # Real mode
    backup_path, backup_sha = backup_xmp(xmp_path, backup_dir, dry_run=False)
    
    raw_content = xmp_path.read_bytes()
    
    # Surgical replacement using regex on bytes to avoid encoding/decoding corruption
    pat_attr = b'(crs:Exposure2012=")([^"]+)(")'
    pat_elem = b'(<crs:Exposure2012>)([^<]+)(</crs:Exposure2012>)'
    
    def _repl_attr(m):
        return m.group(1) + new_exposure_str.encode('utf-8') + m.group(3)

    def _repl_elem(m):
        return m.group(1) + new_exposure_str.encode('utf-8') + m.group(3)
        
    modified_content = re.sub(pat_attr, _repl_attr, raw_content)
    modified_content = re.sub(pat_elem, _repl_elem, modified_content)
    
    if modified_content == raw_content:
        # If the string value hasn't changed because it already equals the formatted value, it's fine.
        # But if it failed to match, we raise.
        if f"{old_exposure:+.2f}" != new_exposure_str and str(old_exposure) != new_exposure_str:
            raise XmpError("Failed to surgically replace Exposure2012")
            
    temp_path = xmp_path.with_name(xmp_path.name + ".tmp")
    try:
        temp_path.write_bytes(modified_content)
        # Validate temp file before atomic replace
        test_val = read_exposure_2012(temp_path)
        # atomic replace
        os.replace(temp_path, xmp_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise XmpError(f"Failed to write and validate temp XMP: {e}") from e

    return f"SUCCESS: Changed crs:Exposure2012 from {old_exposure} to {new_exposure_str}"
