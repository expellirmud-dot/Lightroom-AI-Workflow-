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


def backup_xmp(xmp_path: Path, backup_dir: Path, dry_run: bool = False) -> Path:
    """Create a collision-safe byte-preserving backup of an XMP file.
    
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
        
    return target_path
