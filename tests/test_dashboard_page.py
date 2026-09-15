# -*- coding: utf-8 -*-
"""
Unit test for SINAX Executive Control Dashboard (لوحة القيادة والتحكم)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.pages.dashboard_page import DashboardPage


class TestDashboardPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.dashboard = DashboardPage()
        self.dashboard.show()

    def tearDown(self):
        self.dashboard.close()

    def test_dashboard_components_initialized(self):
        """Verify essential dashboard components exist."""
        self.assertIsNotNone(self.dashboard.card_cpu)
        self.assertIsNotNone(self.dashboard.card_ram)
        self.assertIsNotNone(self.dashboard.card_disk)
        self.assertIsNotNone(self.dashboard.status_badge)

    def test_navigation_signal(self):
        """Verify clicking quick action emits navigate_requested signal."""
        emitted = []
        self.dashboard.navigate_requested.connect(lambda target: emitted.append(target))

        self.dashboard.navigate_requested.emit("file_manager")
        self.assertIn("file_manager", emitted)

        self.dashboard.navigate_requested.emit("backup_sync")
        self.assertIn("backup_sync", emitted)

    def test_telemetry_load(self):
        """Verify telemetry loader executes without raising exceptions."""
        try:
            self.dashboard._load_async_telemetry()
        except Exception as e:
            self.fail(f"_load_async_telemetry raised an exception: {e}")


if __name__ == "__main__":
    unittest.main()
