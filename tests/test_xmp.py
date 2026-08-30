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
    b1, sha1 = backup_xmp(src, backup_dir, dry_run=False)
    assert b1.name == "photo.xmp.bak"
    assert b1.read_text() == "dummy xmp content"
    assert len(sha1) == 64

    # Second backup (collision)
    b2, sha2 = backup_xmp(src, backup_dir, dry_run=False)
    assert b2.name == "photo.xmp.1.bak"
    assert sha2 == sha1

    # Dry run backup
    b3, sha3 = backup_xmp(src, backup_dir, dry_run=True)
    assert b3.name == "photo.xmp.dry_run"

from lr_ai_exposure.xmp import rollback_xmp

def test_rollback_xmp(tmp_path: Path):
    """Prove rollback requires matching SHA-256."""
    src = tmp_path / "photo.xmp"
    src.write_text("modified")

    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    backup_file = backup_dir / "photo.xmp.bak"
    backup_file.write_text("original")

    import hashlib
    correct_sha = hashlib.sha256(b"original").hexdigest()

    # Fails with wrong SHA
    with pytest.raises(XmpError, match="SHA-256 mismatch"):
        rollback_xmp(src, backup_file, "wrong_sha")

    # Succeeds with right SHA
    rollback_xmp(src, backup_file, correct_sha)
    assert src.read_text() == "original"


from lr_ai_exposure.xmp import write_exposure_2012

def test_write_exposure_dry_run(tmp_path: Path):
    """In dry-run mode, never modify source XMP; emit a proposal artifact only."""
    src = tmp_path / "photo.xmp"
    src.write_bytes(b'<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="0.00"/></rdf:RDF>')
    backup_dir = tmp_path / "backup"

    msg = write_exposure_2012(src, 0.5, backup_dir, dry_run=True)

    # Assert dry_run backup created
    assert (backup_dir / "photo.xmp.dry_run").exists()

    # Assert source unmodified
    assert src.read_bytes() == b'<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="0.00"/></rdf:RDF>'

    assert "DRY RUN" in msg
    assert "+0.50" in msg

def test_write_exposure_real_mode_attr(tmp_path: Path):
    """Write through a temporary file, validate, then atomically replace (attribute)."""
    # This xml is malformed slightly but enough for our regex. But we must make it valid for ElementTree to parse in read_exposure_2012.
    src = tmp_path / "photo.xmp"
    xml_content = (
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="+0.35"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    ).encode('utf-8')
    src.write_bytes(xml_content)
    backup_dir = tmp_path / "backup"

    msg = write_exposure_2012(src, -1.2, backup_dir, dry_run=False)

    assert (backup_dir / "photo.xmp.bak").exists()
    assert "SUCCESS" in msg
    assert "-1.20" in msg

    new_content = src.read_bytes()
    assert b'crs:Exposure2012="-1.20"' in new_content
    # Validate other bytes preserved exactly
    assert len(new_content) == len(xml_content)

def test_write_exposure_real_mode_elem(tmp_path: Path):
    """Write through a temporary file, validate, then atomically replace (element)."""
    src = tmp_path / "photo.xmp"
    xml_content = (
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/">\n'
        '   <crs:Exposure2012>0.00</crs:Exposure2012>\n'
        '  </rdf:Description>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    ).encode('utf-8')
    src.write_bytes(xml_content)
    backup_dir = tmp_path / "backup"

    msg = write_exposure_2012(src, 2.5, backup_dir, dry_run=False)

    new_content = src.read_bytes()
    assert b'<crs:Exposure2012>+2.50</crs:Exposure2012>' in new_content

def test_write_exposure_preserves_unrelated(tmp_path: Path):
    """Preserve all unrelated metadata, namespaces, and encoding."""
    src = tmp_path / "photo.xmp"
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="+0.35" crs:Contrast="10" crs:Highlights="-20">\n'
        '   <crs:Shadows>5</crs:Shadows>\n'
        '  </rdf:Description>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    ).encode('utf-8')
    src.write_bytes(xml_content)
    backup_dir = tmp_path / "backup"

    write_exposure_2012(src, 1.0, backup_dir, dry_run=False)

    new_content = src.read_bytes()
    assert b'crs:Contrast="10"' in new_content
    assert b'crs:Highlights="-20"' in new_content
    assert b'<crs:Shadows>5</crs:Shadows>' in new_content
    assert b'crs:Exposure2012="+1.00"' in new_content

def test_write_exposure_fails_validation_leaves_intact(tmp_path: Path):
    """Prove failure paths leave original bytes intact."""
    src = tmp_path / "photo.xmp"
    xml_content = (
        '<?xml version="1.0"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about="" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/" crs:Exposure2012="+0.35"/>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
    ).encode('utf-8')
    src.write_bytes(xml_content)
    backup_dir = tmp_path / "backup"

    with pytest.raises(XmpError, match="New exposure must be finite"):
        write_exposure_2012(src, float("inf"), backup_dir, dry_run=False)

    assert src.read_bytes() == xml_content
