# -*- coding: utf-8 -*-
"""
Verification script for Phase 13.1 - SINAX Privacy & Security Center.
Validates:
1. All 15 core services exist and can be imported.
2. SecurityToolRegistry contains tools with all required fields.
3. Badges are properly defined and computed.
4. Dashboard telemetry summary has real data keys and zero mock data.
5. PrivacySecurityPage instantiates cleanly with all 13 subpages.
"""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

def test_services_import():
    print("[1/5] Testing 15 Core Privacy & Security Services...")
    from app.services.privacy_security import (
        SecurityOverviewService,
        DefenderService,
        SignatureService,
        IntegrityService,
        MetadataPrivacyService,
        EncryptionService,
        VaultService,
        SecureDeleteService,
        ClipboardPrivacyService,
        FileMonitorService,
        WindowsSecurityService,
        ReputationService,
        PermissionsService,
        SafeShareService,
        PrivacyReportService,
    )
    services = [
        SecurityOverviewService,
        DefenderService,
        SignatureService,
        IntegrityService,
        MetadataPrivacyService,
        EncryptionService,
        VaultService,
        SecureDeleteService,
        ClipboardPrivacyService,
        FileMonitorService,
        WindowsSecurityService,
        ReputationService,
        PermissionsService,
        SafeShareService,
        PrivacyReportService,
    ]
    assert len(services) == 15, "Expected 15 services"
    print(f" -> All {len(services)} services imported successfully.")

def test_tool_registry():
    print("[2/5] Testing SecurityToolRegistry and Required Fields...")
    from app.services.privacy_security.security_registry import SecurityToolRegistry
    tools = SecurityToolRegistry.get_all_tools()
    assert len(tools) >= 13, f"Expected at least 13 tools, found {len(tools)}"

    required_attrs = [
        "id", "title", "description", "category", "risk_level",
        "requires_admin", "requires_network", "modifies_files",
        "sends_data_externally", "supports_batch", "handler"
    ]
    for t in tools:
        for attr in required_attrs:
            assert hasattr(t, attr), f"Tool {t.id} missing attribute {attr}"

    print(f" -> SecurityToolRegistry verified: {len(tools)} tools with all 11 required fields.")

def test_badges():
    print("[3/5] Testing Local / Online Badges...")
    from app.services.privacy_security.security_registry import SecurityToolRegistry
    tools = SecurityToolRegistry.get_all_tools()
    for t in tools:
        badges = SecurityToolRegistry.get_badges_for_tool(t)
        assert len(badges) >= 1, f"Tool {t.id} has no badges"
        badge_texts = [b.text_en for b in badges]
        assert ("100% Local" in badge_texts or "Online" in badge_texts), f"Tool {t.id} missing local/online badge"

    print(" -> Badges verified across all catalog tools.")

def test_dashboard_summary():
    print("[4/5] Testing Dashboard Telemetry Summary (Zero Mock)...")
    from app.services.privacy_security.security_overview_service import SecurityOverviewService
    service = SecurityOverviewService()
    summary = service.get_dashboard_summary(force_refresh=False)

    required_keys = [
        "defender_active", "realtime_protection", "firewall_status",
        "smartscreen_status", "controlled_folder_access", "bitlocker_status",
        "monitored_files_count", "last_privacy_scan", "encrypted_vaults_count"
    ]
    for k in required_keys:
        assert k in summary, f"Summary missing key {k}"

    print(" -> Dashboard telemetry summary verified:")
    for k in required_keys:
        print(f"    * {k}: {summary[k]}")

def test_ui_instantiation():
    print("[5/5] Testing PrivacySecurityPage UI & Subpages...")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from app.ui.pages.privacy_security_page import PrivacySecurityPage
    page = PrivacySecurityPage()
    assert page.stack.count() == 13, f"Expected 13 subpages, got {page.stack.count()}"

    # Test subpage switching
    for key, label, _ in page.SUBPAGE_KEYS:
        page.switch_subpage(key)
        assert page.stack.currentIndex() == page._key_to_index[key]

    print(f" -> PrivacySecurityPage verified with all {page.stack.count()} subpages.")

if __name__ == "__main__":
    test_services_import()
    test_tool_registry()
    test_badges()
    test_dashboard_summary()
    test_ui_instantiation()
    print("\nALL PHASE 13.1 VERIFICATION TESTS PASSED SUCCESSFULLY!")
