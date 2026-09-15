# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.pages.maintenance_page import MaintenancePage
from app.ui.themes.theme_manager import theme_manager

class TestMaintenanceUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_maintenance_subpages(self):
        theme_manager.apply_theme("dark")
        page = MaintenancePage()
        page.show()
        self.assertEqual(page.stack.count(), 12)
        subpages = [
            "overview", "doctor", "cleanup", "windows_repair",
            "storage_disk", "updates", "startup", "network",
            "apps", "devices", "reliability", "advanced"
        ]
        for idx, key in enumerate(subpages):
            page.switch_subpage(key)
            self.assertEqual(page.stack.currentIndex(), idx)
            self.assertTrue(page._buttons[key].isChecked())
        page.close()
        page.deleteLater()

if __name__ == "__main__":
    unittest.main()
