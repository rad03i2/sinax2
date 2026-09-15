# -*- coding: utf-8 -*-
"""
Unit test for SINAX Lazy Loading Architecture (معمارية التحميل الكسول)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.ui.pages.dashboard_page import DashboardPage


class TestLazyLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()

    def test_initial_lazy_state(self):
        """Page 0 (Dashboard) should be eagerly loaded; other pages should remain unloaded placeholders."""
        self.assertGreaterEqual(self.window.stack.count(), 22)
        self.assertTrue(self.window.is_page_loaded(0))
        self.assertIsInstance(self.window.get_page(0), DashboardPage)

        # Pages 1 to 21 must NOT be loaded at initial launch
        self.assertFalse(self.window.is_page_loaded(1))
        self.assertFalse(self.window.is_page_loaded(2))
        self.assertFalse(self.window.is_page_loaded(8))
        self.assertFalse(self.window.is_page_loaded(14))

    def test_navigation_triggers_lazy_load(self):
        """Navigating to an unloaded page should instantiate and cache it seamlessly."""
        self.assertFalse(self.window.is_page_loaded(2))

        # Navigate to Batch Rename (Index 2)
        self.window.navigate_to("batch_rename")

        self.assertTrue(self.window.is_page_loaded(2))
        page2 = self.window.get_page(2)
        self.assertIsNotNone(page2)
        self.assertEqual(self.window.stack.currentIndex(), 2)

    def test_attribute_access_triggers_lazy_load(self):
        """Accessing window.<page_attribute> directly should load the page transparently for backwards compatibility."""
        self.assertFalse(self.window.is_page_loaded(8))  # Settings page

        # Access attribute
        settings = self.window.settings_page
        self.assertIsNotNone(settings)
        self.assertTrue(self.window.is_page_loaded(8))

    def test_repeated_access_returns_cached_instance(self):
        """Loading a page once must cache it so subsequent accesses do not re-instantiate."""
        p1_first = self.window.get_page(1)
        p1_second = self.window.get_page(1)
        self.assertIs(p1_first, p1_second)


if __name__ == "__main__":
    unittest.main()
