# -*- coding: utf-8 -*-
"""
Unit tests for SINAX Maintenance & Repair Center.
Verifies core logic, models, parsers, recommendation engine,
privacy masking, and lock managers.
"""

import os
import unittest
from app.services.maintenance.models import (
    DiagnosticIssue,
    MaintenanceAction,
    RiskLevel,
    ScanMode,
    Severity,
)
from app.services.maintenance.maintenance_registry import MaintenanceRegistry
from app.services.maintenance.maintenance_lock import MaintenanceLockManager
from app.services.maintenance.reboot_state_service import RebootStateService
from app.services.maintenance.chkdsk_service import ChkdskService
from app.services.maintenance.windows_repair_service import WindowsRepairService
from app.services.maintenance.safe_cleanup_orchestrator import SafeCleanupOrchestrator
from app.services.maintenance.recommendation_engine import MaintenanceRecommendationEngine
from app.services.maintenance.diagnostic_package_service import DiagnosticPackageService


class TestMaintenanceCore(unittest.TestCase):
    """Test suite for maintenance services."""

    def test_reboot_state_service(self):
        is_pending, reasons = RebootStateService.check_pending_reboot()
        self.assertIsInstance(is_pending, bool)
        self.assertIsInstance(reasons, list)
        summary = RebootStateService.get_summary_ar()
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)

    def test_chkdsk_parser_healthy(self):
        sample_output = """
        The type of the file system is NTFS.
        Volume label is OS.
        Windows has scanned the file system and found no problems.
        No further action is required.
        0 KB in bad sectors.
        """
        parsed = ChkdskService.parse_chkdsk_output(sample_output)
        self.assertEqual(parsed["file_system"], "NTFS")
        self.assertFalse(parsed["has_errors"])
        self.assertTrue(parsed["is_clean"])
        self.assertEqual(parsed["bad_sectors_kb"], 0)

    def test_chkdsk_parser_corrupted(self):
        sample_output = """
        The type of the file system is NTFS.
        Windows found problems that each require chkdsk /f to fix.
        Corruption was found in index $I30.
        128 KB in bad sectors.
        """
        parsed = ChkdskService.parse_chkdsk_output(sample_output)
        self.assertEqual(parsed["file_system"], "NTFS")
        self.assertTrue(parsed["has_errors"])
        self.assertEqual(parsed["bad_sectors_kb"], 128)

    def test_safe_cleanup_byte_formatter(self):
        self.assertEqual(SafeCleanupOrchestrator.format_bytes(500), "500.0 B")
        self.assertEqual(SafeCleanupOrchestrator.format_bytes(1024), "1.0 KB")
        self.assertEqual(SafeCleanupOrchestrator.format_bytes(1024 * 1024 * 5), "5.0 MB")
        self.assertEqual(SafeCleanupOrchestrator.format_bytes(1024 * 1024 * 1024 * 3), "3.0 GB")

    def test_safe_cleanup_analyze(self):
        targets = SafeCleanupOrchestrator.analyze_cleanup_targets()
        self.assertIn("user_temp", targets)
        self.assertIn("windows_temp", targets)
        self.assertIn("thumbnail_cache", targets)
        self.assertIn("recycle_bin", targets)
        self.assertIn("total_reclaimable_bytes", targets)
        self.assertGreaterEqual(targets["total_reclaimable_bytes"], 0)

    def test_maintenance_lock(self):
        lock_mgr = MaintenanceLockManager()
        # Ensure clean state
        lock_mgr.release_job_lock("test_job_1")
        lock_mgr.release_job_lock("test_job_2")

        acquired1 = lock_mgr.acquire_job_lock("test_job_1", "فحص SFC التجريبي")
        self.assertTrue(acquired1)
        self.assertTrue(lock_mgr.is_busy())

        # Second acquisition should fail
        acquired2 = lock_mgr.acquire_job_lock("test_job_2", "فحص DISM المتزامن")
        self.assertFalse(acquired2)

        # Release first lock
        lock_mgr.release_job_lock("test_job_1")
        self.assertFalse(lock_mgr.is_busy())

        # Now second can acquire
        acquired3 = lock_mgr.acquire_job_lock("test_job_2", "فحص DISM المتزامن")
        self.assertTrue(acquired3)
        lock_mgr.release_job_lock("test_job_2")

    def test_recommendation_engine(self):
        issues = [
            DiagnosticIssue(
                id="issue_temp",
                title_ar="تراكم ملفات مؤقتة",
                title_en="Temp files",
                category="storage",
                severity=Severity.SUGGESTION,
                description_ar="الملفات المؤقتة بحجم 5 GB",
                description_en="5 GB Temp",
                evidence="5 GB found",
                suggested_action_id="clean_user_temp",
            ),
            DiagnosticIssue(
                id="issue_sfc",
                title_ar="ملفات نظام تالفة",
                title_en="Corrupted system files",
                category="windows_repair",
                severity=Severity.WARNING,
                description_ar="تلف في ملفات النظام",
                description_en="Corruption detected",
                evidence="CBS log reports error",
                suggested_action_id="sfc_scannow",
            ),
        ]
        plan = MaintenanceRecommendationEngine.generate_plan(issues, scan_mode=ScanMode.QUICK)
        self.assertEqual(len(plan.issues_found), 2)
        self.assertEqual(len(plan.recommended_actions), 2)
        # Verify sfc is flagged as requiring admin
        sfc_action = next(a for a in plan.recommended_actions if a.id == "sfc_scannow")
        self.assertTrue(sfc_action.requires_admin)

    def test_privacy_masking(self):
        raw_test_data = {
            "os_environment": {
                "computer_name": "DESKTOP-SECRET99",
                "username": "secret_developer",
                "userprofile": r"C:\Users\secret_developer",
            },
            "network": {
                "ip": "192.168.1.155",
                "mac": "00-14-22-01-23-45",
            }
        }
        masked = DiagnosticPackageService._apply_privacy_mask(raw_test_data)
        # Should not contain sensitive personal values
        self.assertNotIn("secret_developer", str(masked))
        self.assertNotIn("DESKTOP-SECRET99", str(masked))
        self.assertNotIn("192.168.1.155", str(masked))
        self.assertNotIn("00-14-22-01-23-45", str(masked))

    def test_registry_catalog(self):
        all_actions = MaintenanceRegistry.get_all_actions()
        self.assertGreaterEqual(len(all_actions), 8)
        categories = {a.category for a in all_actions}
        self.assertIn("cleanup", categories)
        self.assertIn("windows_repair", categories)
        self.assertIn("storage_disk", categories)
        self.assertIn("network", categories)


if __name__ == "__main__":
    unittest.main()
