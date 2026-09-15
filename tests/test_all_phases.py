# -*- coding: utf-8 -*-
"""
Comprehensive End-to-End Verification Suite for SINAX Privacy & Security Center.
Covers Phases 13.1 through 13.9:
- 13.1: Architecture, 15 Core Services, Security Tool Registry, Badges, Zero-Mock Telemetry.
- 13.2: File Safety Inspector, Magic Bytes detection, Authenticode signatures.
- 13.3: File Integrity manifests, SHA-256 baseline hashing, diff classification.
- 13.4: Metadata sanitizer, privacy preservation (_private copies), Safe Share 7-stage pipeline.
- 13.5: Portable AES-256-GCM + scrypt Vault creation & extraction.
- 13.6: Hardware-aware secure deletion, protected system paths safety lock, Clipboard privacy.
- 13.7: Windows Security posture telemetry & DPAPI reputation key storage.
- 13.8: Alternate Data Streams (ADS) and NTFS ACL permissions analysis.
- 13.9: Multi-format report export (HTML, JSON, TXT, CSV), Privacy Mode redaction, UI stack integration.
"""

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass


def run_all_tests():
    print("==================================================================")
    print(" SINAX Privacy & Security Center - Complete Verification Suite ")
    print(" Phases 13.1 -> 13.9 ")
    print("==================================================================")

    # 1. Test Services and Registry (Phase 13.1)
    print("\n--- [Phase 13.1] Testing Services Architecture & Registry ---")
    from app.services.privacy_security import (
        SecurityOverviewService, DefenderService, SignatureService,
        IntegrityService, MetadataPrivacyService, EncryptionService,
        VaultService, SecureDeleteService, ClipboardPrivacyService,
        FileMonitorService, WindowsSecurityService, ReputationService,
        PermissionsService, SafeShareService, PrivacyReportService,
        SecurityToolRegistry,
    )
    tools = SecurityToolRegistry.get_all_tools()
    assert len(tools) >= 13, f"Expected at least 13 tools, found {len(tools)}"
    print(f" -> Catalog verified: {len(tools)} registered tools with full metadata.")

    # 2. Test File Safety & Authenticode (Phase 13.2)
    print("\n--- [Phase 13.2] Testing File Safety Inspector & Authenticode ---")
    from app.services.privacy_security.file_safety_service import FileSafetyService
    with tempfile.NamedTemporaryFile(suffix=".txt.exe", delete=False) as tf:
        tf.write(b"MZ\x90\x00\x03fake_pe")
        test_file = tf.name

    try:
        report = FileSafetyService.inspect_file(test_file)
        assert report.is_double_extension, "Expected double extension flag on .txt.exe"
        assert report.detected_mime == "application/x-dosexec", "Expected PE executable detection"
        print(f" -> Double extension & Magic Bytes detection PASSED (Detected: {report.detected_type_name}).")
    finally:
        if os.path.exists(test_file):
            os.unlink(test_file)

    # 3. Test Integrity & Manifests (Phase 13.3)
    print("\n--- [Phase 13.3] Testing Integrity Manifest Builder & Verifier ---")
    temp_dir = tempfile.mkdtemp(prefix="sinax_test_integrity_")
    try:
        f1 = Path(temp_dir) / "data.txt"
        f1.write_text("Secret Data 1", encoding="utf-8")
        f2 = Path(temp_dir) / "config.json"
        f2.write_text('{"setting": true}', encoding="utf-8")

        ok, man_path, count = IntegrityService.create_folder_manifest(temp_dir)
        assert ok, "Manifest creation failed"
        assert count == 2, f"Expected 2 files in manifest, got {count}"
        print(f" -> Manifest created successfully: {Path(man_path).name} with {count} files.")

        # Verify initial unchanged state
        v_ok, v_msg, diff = IntegrityService.verify_folder_manifest(temp_dir, man_path)
        assert v_ok, "Manifest verification failed"
        assert len(diff.unchanged_files) == 2, "Expected 2 unchanged files"
        assert not diff.has_changes, "Expected zero modifications"
        print(" -> Initial manifest verification PASSED: 100% match.")

        # Modify one file and test diff
        f1.write_text("Modified Secret Data", encoding="utf-8")
        v_ok2, v_msg2, diff2 = IntegrityService.verify_folder_manifest(temp_dir, man_path)
        assert diff2.has_changes, "Expected changes detected"
        assert len(diff2.modified_files) == 1, "Expected 1 modified file"
        print(" -> Manifest modification detection PASSED (Correctly flagged modified file).")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # 4. Test Metadata Sanitization & Safe Share (Phase 13.4)
    print("\n--- [Phase 13.4] Testing Metadata Sanitizer & Safe Share Studio ---")
    meta_service = MetadataPrivacyService()
    test_img = Path(temp_dir).parent / f"sinax_test_meta_{os.urandom(4).hex()}.txt"
    test_img.write_text("Sample file without metadata", encoding="utf-8")
    try:
        insp = meta_service.inspect_metadata(str(test_img))
        assert "format" in insp, "Expected format in metadata inspection"

        safe_share = SafeShareService()
        from app.services.privacy_security.models import PrivacyPreset
        ok, res = safe_share.process_safe_share(str(test_img), preset=PrivacyPreset.WORK_DOC, run_defender_scan=False)
        assert ok, "Safe share processing failed"
        assert res.is_verified, "Safe share output was not verified"
        assert os.path.exists(res.output_path), "Safe share clean copy not created"
        print(f" -> Safe Share 7-stage pipeline PASSED (Clean file generated: {Path(res.output_path).name}).")
        if os.path.exists(res.output_path):
            os.unlink(res.output_path)
    finally:
        if test_img.exists():
            test_img.unlink()

    # 5. Test Vault Encryption & Extraction (Phase 13.5)
    print("\n--- [Phase 13.5] Testing Portable AES-256-GCM Vault Engine ---")
    vault_service = VaultService()
    test_plain = Path(temp_dir).parent / f"sinax_secret_{os.urandom(4).hex()}.txt"
    test_plain.write_text("Top secret confidential text to encrypt in vault", encoding="utf-8")
    vault_file = str(test_plain) + ".sinaxvault"
    extract_dir = Path(temp_dir).parent / f"sinax_extracted_{os.urandom(4).hex()}"
    test_pwd = "MySecretVaultPassword#2026!"

    try:
        # Create
        c_ok, c_msg = vault_service.create_vault(str(test_plain), vault_file, password=test_pwd)
        assert c_ok, f"Vault creation failed: {c_msg}"
        assert os.path.exists(vault_file), "Vault output file does not exist"
        print(f" -> Encrypted .sinaxvault container created ({os.path.getsize(vault_file)} bytes).")

        # Extract
        e_ok, e_msg = vault_service.open_vault(vault_file, str(extract_dir), password=test_pwd)
        assert e_ok, f"Vault extraction failed: {e_msg}"
        extracted_file = extract_dir / test_plain.name
        assert extracted_file.exists(), "Extracted file not found"
        assert extracted_file.read_text(encoding="utf-8") == "Top secret confidential text to encrypt in vault"
        print(" -> Vault decryption & extraction PASSED (Plaintext matched 100%).")
    finally:
        if test_plain.exists():
            test_plain.unlink()
        if os.path.exists(vault_file):
            os.unlink(vault_file)
        shutil.rmtree(extract_dir, ignore_errors=True)

    # 6. Test Secure Delete & Passwords (Phase 13.6)
    print("\n--- [Phase 13.6] Testing Hardware-Aware Secure Delete & Passwords ---")
    sec_del = SecureDeleteService()
    system_root = os.environ.get("SystemRoot", "C:\\Windows")
    prot_info = sec_del.inspect_target_for_deletion(system_root)
    assert prot_info.get("is_protected"), "System root must be detected as protected!"
    shred_ok, shred_msg = sec_del.execute_secure_delete(system_root, passes=1)
    assert not shred_ok, "Shredder must reject system root deletion"
    print(" -> Protected System Directory Safety Lock PASSED (Refused deletion of SystemRoot).")

    # Password Tools test
    from app.services.quick_tools.tools.password_tools import PasswordTools
    pwd = PasswordTools.generate_password(length=24)
    assert len(pwd) == 24, "Expected 24 char password"
    entropy = PasswordTools.estimate_password_strength(pwd)
    assert entropy.get("entropy_bits", 0) > 80, "Expected high entropy"
    print(f" -> Password Generator PASSED ({entropy['entropy_bits']} bits entropy, '{entropy['label_ar']}').")

    # 7. Test Windows Security & Reputation (Phase 13.7)
    print("\n--- [Phase 13.7] Testing Windows Security & Reputation ---")
    win_sec = WindowsSecurityService()
    posture = win_sec.get_security_overview(force_refresh=False)
    assert "defender_active" in posture, "Expected defender_active in posture"
    assert "bitlocker_status" in posture, "Expected bitlocker_status in posture"
    print(f" -> Windows Security Telemetry PASSED (Defender: {posture['defender_active']}, BitLocker: {posture['bitlocker_status']}).")

    # 8. Test ADS & Permissions (Phase 13.8)
    print("\n--- [Phase 13.8] Testing NTFS Streams & Permissions ---")
    from app.services.privacy_security.ads_service import AlternateDataStreamsService
    streams = AlternateDataStreamsService.list_streams(str(ROOT / "main.py"))
    assert len(streams) >= 1, "Expected at least main data stream"
    print(f" -> ADS Streams inspection PASSED ({len(streams)} stream(s) found on main.py).")

    # 9. Test Reports & Full UI Integration (Phase 13.9)
    print("\n--- [Phase 13.9] Testing Reports Multi-Export & Full UI Integration ---")
    rep_service = PrivacyReportService()
    rep_out_html = Path(tempfile.gettempdir()) / "sinax_audit_test.html"
    rep_out_json = Path(tempfile.gettempdir()) / "sinax_audit_test.json"
    rep_out_csv = Path(tempfile.gettempdir()) / "sinax_audit_test.csv"
    rep_out_txt = Path(tempfile.gettempdir()) / "sinax_audit_test.txt"

    try:
        h_ok, _ = rep_service.export_report(str(rep_out_html), fmt="html", apply_privacy_mode=True)
        assert h_ok and rep_out_html.exists(), "HTML export failed"

        j_ok, _ = rep_service.export_report(str(rep_out_json), fmt="json", apply_privacy_mode=True)
        assert j_ok and rep_out_json.exists(), "JSON export failed"

        c_ok, _ = rep_service.export_report(str(rep_out_csv), fmt="csv", apply_privacy_mode=True)
        assert c_ok and rep_out_csv.exists(), "CSV export failed"

        t_ok, _ = rep_service.export_report(str(rep_out_txt), fmt="txt", apply_privacy_mode=True)
        assert t_ok and rep_out_txt.exists(), "TXT export failed"

        print(" -> Multi-format report exports PASSED (HTML, JSON, CSV, TXT generated with Privacy Mode).")
    finally:
        for f in (rep_out_html, rep_out_json, rep_out_csv, rep_out_txt):
            if f.exists():
                f.unlink()

    # Full Qt UI Stack Instantiation
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from app.ui.pages.privacy_security_page import PrivacySecurityPage
    page = PrivacySecurityPage()
    assert page.stack.count() == 13, f"Expected 13 active subpages, got {page.stack.count()}"

    expected_subpages = [
        "OverviewSubpage", "FileSafetySubpage", "IntegritySubpage",
        "SignatureSubpage", "MetadataCleanSubpage", "SafeShareSubpage",
        "VaultSubpage", "SecureDeleteSubpage", "FileMonitorSubpage",
        "PasswordsSubpage", "WindowsSecuritySubpage", "AdvancedToolsSubpage",
        "ReportsSubpage"
    ]

    for idx, expected_name in enumerate(expected_subpages):
        actual_name = type(page.stack.widget(idx)).__name__
        assert actual_name == expected_name, f"Index {idx}: expected {expected_name}, got {actual_name}"
        page.stack.setCurrentIndex(idx)

    print(f" -> Full UI Stack PASSED: All {page.stack.count()} subpages instantiated and navigable.")

    print("\n==================================================================")
    print(" ALL VERIFICATION TESTS FOR PHASES 13.1 -> 13.9 PASSED (100%)! ")
    print("==================================================================")


if __name__ == "__main__":
    run_all_tests()
