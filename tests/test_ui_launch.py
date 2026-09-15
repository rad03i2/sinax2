# -*- coding: utf-8 -*-
"""
Headless UI Launch & Navigation Test
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.ui.themes.theme_manager import theme_manager

class TestUILaunch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_window_launch_and_navigation(self):
        theme_manager.apply_theme("dark")
        window = MainWindow()
        window.show()

        self.assertGreaterEqual(window.stack.count(), 8)

        # Batch Rename navigation
        window.navigate_to("batch_rename")
        self.assertEqual(window.stack.currentIndex(), 2)

        # Settings navigation
        window.navigate_to("settings")
        self.assertEqual(window.stack.currentIndex(), 8)

        # History navigation
        window.navigate_to("history")
        self.assertEqual(window.stack.currentIndex(), 7)

        # Converter navigation
        window.navigate_to("converter")
        self.assertEqual(window.stack.currentIndex(), 9)

        # Audio Center navigation (Phase 9)
        window.navigate_to("audio_center")
        self.assertEqual(window.stack.currentIndex(), 13)

        # System & Storage navigation (Phase 10)
        window.navigate_to("system_storage")
        self.assertEqual(window.stack.currentIndex(), 14)
        window.navigate_to("system_storage_analyzer")
        self.assertEqual(window.stack.currentIndex(), 14)
        self.assertEqual(window.system_storage_page.stack.currentIndex(), 1)
        window.navigate_to("system_storage_cleanup")
        self.assertEqual(window.system_storage_page.stack.currentIndex(), 2)

        # Apps & Programs Manager navigation (Phase 11)
        window.navigate_to("apps_manager")
        self.assertEqual(window.stack.currentIndex(), 15)
        window.navigate_to("apps_inventory")
        self.assertEqual(window.stack.currentIndex(), 15)
        self.assertEqual(window.apps_manager_page.stack.currentIndex(), 1)
        window.navigate_to("apps_updates")
        self.assertEqual(window.apps_manager_page.stack.currentIndex(), 2)
        window.navigate_to("apps_before_format")
        self.assertEqual(window.apps_manager_page.stack.currentIndex(), 7)
        window.navigate_to("apps_restore")
        self.assertEqual(window.apps_manager_page.stack.currentIndex(), 8)

        # Maintenance & Repair Center navigation (Phase 15 / Maintenance)
        window.navigate_to("maintenance")
        self.assertEqual(window.stack.currentIndex(), 20)
        self.assertEqual(window.maintenance_page.stack.currentIndex(), 0)
        
        maintenance_subpages = [
            ("maintenance_doctor", 1),
            ("maintenance_cleanup", 2),
            ("maintenance_windows_repair", 3),
            ("maintenance_storage_disk", 4),
            ("maintenance_updates", 5),
            ("maintenance_startup", 6),
            ("maintenance_network", 7),
            ("maintenance_apps", 8),
            ("maintenance_devices", 9),
            ("maintenance_reliability", 10),
            ("maintenance_advanced", 11),
            ("maintenance_overview", 0),
        ]
        for page_id, expected_sub_idx in maintenance_subpages:
            window.navigate_to(page_id)
            self.assertEqual(window.stack.currentIndex(), 20)
            self.assertEqual(window.maintenance_page.stack.currentIndex(), expected_sub_idx)

        # Backup & Sync Center navigation (Phase 16 / Backup & Sync)
        window.navigate_to("backup_sync")
        self.assertEqual(window.stack.currentIndex(), 21)
        self.assertEqual(window.backup_sync_page.stack.currentIndex(), 0)

        backup_sync_subpages = [
            ("backup_sync_wizard", 1),
            ("backup_sync_quick_backup", 2),
            ("backup_sync_before_format", 3),
            ("backup_sync_sync", 4),
            ("backup_sync_restore", 5),
            ("backup_sync_versions", 6),
            ("backup_sync_health_drill", 7),
            ("backup_sync_destinations", 8),
            ("backup_sync_schedules", 9),
            ("backup_sync_history_reports", 10),
            ("backup_sync_overview", 0),
        ]
        for page_id, expected_sub_idx in backup_sync_subpages:
            window.navigate_to(page_id)
            self.assertEqual(window.stack.currentIndex(), 21)
            self.assertEqual(window.backup_sync_page.stack.currentIndex(), expected_sub_idx)

        # Theme toggle
        new_t = theme_manager.toggle_theme()
        self.assertEqual(new_t, "light")
        new_t2 = theme_manager.toggle_theme()
        self.assertEqual(new_t2, "dark")
        window.close()
        window.deleteLater()

if __name__ == "__main__":
    unittest.main()
