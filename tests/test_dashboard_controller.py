# -*- coding: utf-8 -*-
"""
SINAX Dashboard Controller Unit Tests
Tests:
- Telemetry metrics gathering (CPU, RAM, Disk C:)
- Background throttling and timer polling
- Lifecycle activation/deactivation (pausing telemetry when away from Dashboard)
- Backward compatibility properties
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.controllers.dashboard_controller import DashboardController


class TestDashboardController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.controller = DashboardController()

    def tearDown(self):
        self.controller.setActive(False)

    def test_metrics_initial_or_refreshed_values(self):
        """DashboardController must acquire realistic system metrics."""
        self.controller.refreshMetrics()
        self.app.processEvents()

        # Check values
        self.assertTrue(self.controller.cpuUsage.endswith("%"))
        self.assertTrue(self.controller.ramUsage.endswith("%"))
        self.assertTrue(self.controller.diskUsage.endswith("%"))
        self.assertGreater(len(self.controller.diskFree), 0)
        self.assertGreater(len(self.controller.statusMessage), 0)

    def test_lifecycle_pause_resume(self):
        """Deactivating controller must stop the timer; activating must resume it."""
        self.controller.setActive(False)
        self.assertFalse(self.controller.isActive)
        self.assertFalse(self.controller._timer.isActive())

        self.controller.setActive(True)
        self.assertTrue(self.controller.isActive)
        self.assertTrue(self.controller._timer.isActive())


if __name__ == "__main__":
    unittest.main()
