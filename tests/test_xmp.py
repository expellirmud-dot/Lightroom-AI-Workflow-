"""Tests for WO-010 XMP reading and backup."""

from __future__ import annotations

import pytest
from pathlib import Path

from lr_ai_exposure.xmp import XmpError, backup_xmp, read_exposure_2012


def test_read_exposure_attribute(tmp_path: Path):
    """Parse crs:Exposure2012 safely from XMP as RDF attribute."""
    xmp_file = tmp_path / "test.xmp"
    xmp_file.write_text(
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="+0.35"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    )
    
    val = read_exposure_2012(xmp_file)
    assert val == 0.35


def test_read_exposure_element(tmp_path: Path):
    """Parse crs:Exposure2012 safely from XMP as XML element."""
    xmp_file = tmp_path / "test.xmp"
    xmp_file.write_text(
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/">\n'
        '   <crs:Exposure2012>-1.20</crs:Exposure2012>\n'
        '  </rdf:Description>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    )
    
    val = read_exposure_2012(xmp_file)
    assert val == -1.20


def test_read_missing_exposure(tmp_path: Path):
    xmp_file = tmp_path / "test.xmp"
    xmp_file.write_text(
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    )
    
    with pytest.raises(XmpError, match="not found in XMP"):
        read_exposure_2012(xmp_file)


def test_read_malformed_xml(tmp_path: Path):
    xmp_file = tmp_path / "test.xmp"
    xmp_file.write_text('<?xml version="1.0"?><broken')
    
    with pytest.raises(XmpError, match="Malformed XML"):
        read_exposure_2012(xmp_file)


def test_read_invalid_number(tmp_path: Path):
    xmp_file = tmp_path / "test.xmp"
    xmp_file.write_text(
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="abc"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    )
    
    with pytest.raises(XmpError, match="not a valid number"):
        read_exposure_2012(xmp_file)


def test_read_ambiguous_exposure(tmp_path: Path):
    xmp_file = tmp_path / "test.xmp"
    xmp_file.write_text(
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="1" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="0.1"/>\n'
        '  <rdf:Description rdf:about="2" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="0.2"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    )
    
    with pytest.raises(XmpError, match="Ambiguous"):
        read_exposure_2012(xmp_file)


def test_backup_xmp(tmp_path: Path):
    """Create collision-safe byte-preserving backups."""
    src = tmp_path / "src" / "photo.xmp"
    src.parent.mkdir()
    src.write_text("dummy xmp content")
    
    backup_dir = tmp_path / "backup"
    
    # First backup
    b1 = backup_xmp(src, backup_dir, dry_run=False)
    assert b1.name == "photo.xmp.bak"
    assert b1.read_text() == "dummy xmp content"
    
    # Second backup (collision)
    b2 = backup_xmp(src, backup_dir, dry_run=False)
    assert b2.name == "photo.xmp.1.bak"
    
    # Dry run backup
    b3 = backup_xmp(src, backup_dir, dry_run=True)
    assert b3.name == "photo.xmp.dry_run"
