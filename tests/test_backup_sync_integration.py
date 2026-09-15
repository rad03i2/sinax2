# -*- coding: utf-8 -*-
"""
Direct MainWindow + Backup & Sync Integration Test
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow

class TestBackupSyncIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_backup_sync_wiring(self):
        window = MainWindow()
        window.show()

        # Check stack index 21
        self.assertGreaterEqual(window.stack.count(), 22)

        # Check navigate to backup_sync
        window.navigate_to("backup_sync")
        self.assertEqual(window.stack.currentIndex(), 21)
        self.assertEqual(window.backup_sync_page.stack.currentIndex(), 0)

        # Test all 11 subpages
        subpages = [
            ("backup_sync_overview", 0),
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
        ]
        for pid, expected_idx in subpages:
            window.navigate_to(pid)
            self.assertEqual(window.stack.currentIndex(), 21)
            self.assertEqual(window.backup_sync_page.stack.currentIndex(), expected_idx)

        # Test back navigation from subpage returns to overview
        window.navigate_to("backup_sync_wizard")
        self.assertEqual(window.backup_sync_page.stack.currentIndex(), 1)
        window._go_back()
        self.assertEqual(window.backup_sync_page.stack.currentIndex(), 0)

        window.close()

if __name__ == "__main__":
    unittest.main()
