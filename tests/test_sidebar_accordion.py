# -*- coding: utf-8 -*-
"""
Unit test for SINAX Sidebar Accordion Navigation (شريط التنقل المتطوي Fluent Accordion)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.widgets.sidebar import Sidebar


class TestSidebarAccordion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.sidebar = Sidebar()
        self.sidebar.show()

    def tearDown(self):
        self.sidebar.close()

    def test_sidebar_initial_sections(self):
        """Verify section containers exist for major categories."""
        self.assertIn("file_manager", self.sidebar._section_containers)
        self.assertIn("multimedia", self.sidebar._section_containers)
        self.assertIn("system_storage", self.sidebar._section_containers)
        self.assertIn("maintenance", self.sidebar._section_containers)
        self.assertIn("backup_sync", self.sidebar._section_containers)

    def test_true_accordion_behavior(self):
        """Opening one section must automatically collapse all other sections."""
        # Open multimedia section
        self.sidebar._toggle_accordion("multimedia")
        self.assertTrue(self.sidebar._section_containers["multimedia"].isVisible())
        self.assertFalse(self.sidebar._section_containers["system_storage"].isVisible())
        self.assertFalse(self.sidebar._section_containers["file_manager"].isVisible())

        # Now open system_storage
        self.sidebar._toggle_accordion("system_storage")
        self.assertTrue(self.sidebar._section_containers["system_storage"].isVisible())
        self.assertFalse(self.sidebar._section_containers["multimedia"].isVisible())
        self.assertFalse(self.sidebar._section_containers["file_manager"].isVisible())

    def test_set_active_page_auto_expands_parent(self):
        """Setting an active sub-page should auto-expand its parent accordion group."""
        self.sidebar.set_active_page("system_storage_analyzer")

        self.assertTrue(self.sidebar._section_containers["system_storage"].isVisible())
        self.assertFalse(self.sidebar._section_containers["multimedia"].isVisible())
        self.assertEqual(self.sidebar._current_open_section, "system_storage")

    def test_signal_emission_on_navigation(self):
        """Selecting a section or child should emit page_selected signal with proper page ID."""
        emitted_pages = []
        self.sidebar.page_selected.connect(lambda pid: emitted_pages.append(pid))

        self.sidebar._handle_click("quick_tools")
        self.assertIn("quick_tools", emitted_pages)

        self.sidebar._handle_click("history")
        self.assertIn("history", emitted_pages)


if __name__ == "__main__":
    unittest.main()
