import pytest
import hashlib
from pathlib import Path
from lr_ai_exposure.apply_transaction import execute_apply_transaction, RollbackFatalError
from lr_ai_exposure.xmp import XmpError, read_exposure_2012

def test_execute_apply_transaction_success(tmp_path):
    xmp_path = tmp_path / "test.xmp"
    xmp_content = b"""<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00        ">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
   crs:Exposure2012="0.00"/>
 </rdf:RDF>
</x:xmpmeta>"""
    xmp_path.write_bytes(xmp_content)
    
    backup_dir = tmp_path / "backups"
    
    evidence = execute_apply_transaction(xmp_path, 0.50, backup_dir, dry_run=False)
    
    assert evidence["status"] == "APPLIED_VERIFIED"
    assert "SUCCESS" in evidence["message"]
    assert evidence["original_sha256"] is not None
    assert evidence["backup_sha256"] == evidence["original_sha256"]
    assert evidence["final_sha256"] != evidence["original_sha256"]
    
    # Verify file contents actually changed
    assert read_exposure_2012(xmp_path) == 0.50
    
def test_execute_apply_transaction_dry_run(tmp_path):
    xmp_path = tmp_path / "test.xmp"
    xmp_content = b"""<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00        ">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
   crs:Exposure2012="0.00"/>
 </rdf:RDF>
</x:xmpmeta>"""
    xmp_path.write_bytes(xmp_content)
    
    backup_dir = tmp_path / "backups"
    
    evidence = execute_apply_transaction(xmp_path, 0.50, backup_dir, dry_run=True)
    
    assert evidence["status"] == "PROPOSED"
    assert "DRY RUN" in evidence["message"]
    assert evidence["original_sha256"] is not None
    # No real backup hash since it's dry run
    assert evidence["backup_sha256"] is None

def test_execute_apply_transaction_automatic_rollback(tmp_path, monkeypatch):
    xmp_path = tmp_path / "test.xmp"
    xmp_content = b"""<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00        ">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
   crs:Exposure2012="0.00"/>
 </rdf:RDF>
</x:xmpmeta>"""
    xmp_path.write_bytes(xmp_content)
    
    backup_dir = tmp_path / "backups"
    
    original_sha256 = hashlib.sha256(xmp_content).hexdigest()
    
    # Mock read_exposure_2012 to fail during post-replace validation
    import lr_ai_exposure.apply_transaction
    original_read = lr_ai_exposure.apply_transaction.read_exposure_2012
    
    # We only want it to fail AFTER write_exposure_2012 succeeds (post-replace)
    # The read_exposure_2012 is called at the end of the transaction.
    def mock_read(path):
        val = original_read(path)
        if val != 0.00:
            raise ValueError("Mocked post-replace failure")
        return val
        
    monkeypatch.setattr(lr_ai_exposure.apply_transaction, "read_exposure_2012", mock_read)
    
    evidence = execute_apply_transaction(xmp_path, 0.50, backup_dir, dry_run=False)
    
    assert evidence["status"] == "FAILED_AFTER_REPLACE_ROLLED_BACK"
    assert "Mocked post-replace failure" in evidence["message"]
    assert evidence["rollback_sha256"] == original_sha256
    
    # Verify file is restored to original
    assert hashlib.sha256(xmp_path.read_bytes()).hexdigest() == original_sha256
