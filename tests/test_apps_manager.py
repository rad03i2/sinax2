# -*- coding: utf-8 -*-
"""
SINAX Apps & Programs Manager Unit Test Suite
"""

import os
import shutil
import tempfile
import unittest

from app.services.apps_manager.app_model import InstalledApp, format_bytes
from app.services.apps_manager.app_snapshot_service import AppSnapshotService
from app.services.apps_manager.backup_restore_service import BackupRestoreService
from app.services.apps_manager.broken_entries_service import BrokenEntriesService
from app.services.apps_manager.inventory_service import InventoryService
from app.services.apps_manager.leftover_scanner import LeftoverScanner, SHARED_VENDOR_ROOTS
from app.services.apps_manager.providers.registry_provider import RegistryProvider
from app.services.apps_manager.providers.winget_provider import WingetProvider
from app.services.apps_manager.uninstall_service import UninstallService


class TestAppsManager(unittest.TestCase):
    """Unit tests for Phase 11 Apps Manager Services."""

    def test_app_model(self):
        app = InstalledApp(
            id="test_id_123",
            name="VLC media player",
            version="3.0.21",
            publisher="VideoLAN",
            installed_size=150 * 1024 * 1024,
            install_date="20260315",
            date_reliable=True,
            package_id="VideoLAN.VLC",
        )
        self.assertEqual(app.display_size, "150.0 MB")
        self.assertEqual(app.formatted_install_date, "2026-03-15")
        self.assertEqual(app.effective_size_bytes, 150 * 1024 * 1024)

        d = app.to_dict()
        app2 = InstalledApp.from_dict(d)
        self.assertEqual(app2.name, "VLC media player")
        self.assertEqual(app2.package_id, "VideoLAN.VLC")

    def test_registry_provider(self):
        apps = RegistryProvider.get_installed_apps()
        self.assertIsInstance(apps, list)
        self.assertGreater(len(apps), 0)
        # Check that basic fields are populated
        first = apps[0]
        self.assertTrue(bool(first.id))
        self.assertTrue(bool(first.name))

    def test_tokenize_command(self):
        # Quoted string with args
        exe, args = UninstallService.tokenize_command(r'"C:\Program Files\App\uninstall.exe" /S /x')
        self.assertEqual(exe, r"C:\Program Files\App\uninstall.exe")
        self.assertEqual(args, ["/S", "/x"])

        # msiexec call
        exe_msi, args_msi = UninstallService.tokenize_command("MsiExec.exe /I{12345678-ABCD-1234-ABCD-1234567890AB}")
        self.assertEqual(exe_msi, "MsiExec.exe")
        self.assertIn("/I{12345678-ABCD-1234-ABCD-1234567890AB}", args_msi)

    def test_system_protection_guard(self):
        sys_app = InstalledApp(
            id="sys_1",
            name="Windows Security Core",
            is_system_component=True,
        )
        res = UninstallService.uninstall_app(sys_app)
        self.assertFalse(res.success)
        self.assertIn("مرفوض", res.message)

        runtime_app = InstalledApp(
            id="run_1",
            name="Microsoft Visual C++ 2015-2022 Redistributable",
            is_runtime_or_driver=True,
        )
        res2 = UninstallService.uninstall_app(runtime_app)
        self.assertFalse(res2.success)
        self.assertIn("مرفوض", res2.message)

    def test_inventory_filter_and_stats(self):
        sample_apps = [
            InstalledApp(id="1", name="Chrome", publisher="Google", installed_size=500 * 1024 * 1024, source="exe"),
            InstalledApp(id="2", name="VLC", publisher="VideoLAN", installed_size=200 * 1024 * 1024, update_available=True, source="winget"),
            InstalledApp(id="3", name="Visual Studio", publisher="Microsoft", installed_size=3 * 1024 * 1024 * 1024, is_startup=True),
        ]
        stats = InventoryService.get_summary_stats(sample_apps)
        self.assertEqual(stats["total_apps"], 3)
        self.assertEqual(stats["updates_count"], 1)
        self.assertEqual(stats["large_count"], 1)
        self.assertEqual(stats["startup_count"], 1)

        # Filter by search
        search_res = InventoryService.filter_apps(sample_apps, query="vlc")
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0].name, "VLC")

        # Filter by updates
        up_res = InventoryService.filter_apps(sample_apps, category="updates")
        self.assertEqual(len(up_res), 1)
        self.assertEqual(up_res[0].name, "VLC")

        # Filter by large
        large_res = InventoryService.filter_apps(sample_apps, category="large")
        self.assertEqual(len(large_res), 1)
        self.assertEqual(large_res[0].name, "Visual Studio")

    def test_backup_and_restore_bundle(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            sample_apps = [
                InstalledApp(id="1", name="7-Zip", publisher="Igor Pavlov", version="24.08", package_id="7zip.7zip"),
                InstalledApp(id="2", name="Custom App", publisher="Vendor", version="1.0"),
            ]
            bundle = BackupRestoreService.export_backup_bundle(sample_apps, tmp_dir)
            self.assertIn("json", bundle)
            self.assertTrue(os.path.exists(bundle["json"]))
            self.assertIn("html", bundle)
            self.assertTrue(os.path.exists(bundle["html"]))
            self.assertIn("csv", bundle)
            self.assertTrue(os.path.exists(bundle["csv"]))

            # Inspect
            inspection = BackupRestoreService.inspect_backup_file(bundle["json"])
            self.assertEqual(inspection["total_count"], 2)
            self.assertEqual(inspection["installable_count"], 1)
            self.assertEqual(inspection["manual_count"], 1)
            self.assertEqual(inspection["installable_items"][0]["package_id"], "7zip.7zip")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_leftover_shared_roots(self):
        self.assertIn("adobe", SHARED_VENDOR_ROOTS)
        self.assertIn("microsoft", SHARED_VENDOR_ROOTS)
        self.assertIn("autodesk", SHARED_VENDOR_ROOTS)

    def test_snapshot_service(self):
        sample_apps1 = [
            InstalledApp(id="1", name="App A", version="1.0", publisher="Pub A"),
            InstalledApp(id="2", name="App B", version="1.0", publisher="Pub B"),
        ]
        id1 = AppSnapshotService.save_snapshot("Snap 1", sample_apps1)
        self.assertIsInstance(id1, int)

        sample_apps2 = [
            InstalledApp(id="1", name="App A", version="2.0", publisher="Pub A"),  # updated
            InstalledApp(id="3", name="App C", version="1.0", publisher="Pub C"),  # added, App B removed
        ]
        id2 = AppSnapshotService.save_snapshot("Snap 2", sample_apps2)

        diff = AppSnapshotService.compare_snapshots(id1, id2)
        self.assertEqual(diff["added_count"], 1)
        self.assertEqual(diff["removed_count"], 1)
        self.assertEqual(diff["updated_count"], 1)
        self.assertEqual(diff["updated"][0]["new_version"], "2.0")


if __name__ == "__main__":
    unittest.main()
