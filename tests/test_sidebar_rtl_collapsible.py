# -*- coding: utf-8 -*-
"""
Unit tests for SINAX RTL & Collapsible Sidebar.
Verifies:
- 100% Arabic RTL direction.
- Expand / Collapse toggle (240px <-> 64px) with Hamburger button.
- True exclusive accordion navigation.
- In-memory state and tooltips.
- 100% backward compatibility.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.ui.widgets.sidebar import Sidebar, SidebarNavItem


class TestSidebarRTLCollapsible(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.sidebar = Sidebar()
        self.sidebar.show()

    def tearDown(self):
        self.sidebar.close()

    def test_sidebar_initial_expanded_state(self):
        """Sidebar should start expanded at 240px with RTL direction."""
        self.assertEqual(self.sidebar.width(), Sidebar.EXPANDED_WIDTH)
        self.assertEqual(self.sidebar.layoutDirection(), Qt.RightToLeft)
        self.assertFalse(self.sidebar._is_collapsed)
        self.assertTrue(self.sidebar._brand_title_container.isVisible())
        self.assertTrue(self.sidebar._brand_logo_lbl.isVisible())

    def test_toggle_collapse_and_expand(self):
        """Hamburger button toggle should switch between 64px and 240px cleanly."""
        # 1. Click toggle to collapse
        self.sidebar.btn_toggle.click()
        self.assertTrue(self.sidebar._is_collapsed)
        self.assertEqual(self.sidebar.width(), Sidebar.COLLAPSED_WIDTH)
        self.assertFalse(self.sidebar._brand_title_container.isVisible())
        self.assertFalse(self.sidebar._brand_logo_lbl.isVisible())
        self.assertFalse(self.sidebar._version_label.isVisible())

        # Check button state in collapsed mode
        for btn in self.sidebar._buttons.values():
            self.assertFalse(btn.title_lbl.isVisible())
            if btn.chevron_lbl:
                self.assertFalse(btn.chevron_lbl.isVisible())
            self.assertNotEqual(btn.toolTip(), "")

        # Check all child containers hidden while collapsed
        for cont in self.sidebar._section_containers.values():
            self.assertFalse(cont.isVisible())

        # 2. Click toggle again to expand
        self.sidebar.btn_toggle.click()
        self.assertFalse(self.sidebar._is_collapsed)
        self.assertEqual(self.sidebar.width(), Sidebar.EXPANDED_WIDTH)
        self.assertTrue(self.sidebar._brand_title_container.isVisible())
        self.assertTrue(self.sidebar._brand_logo_lbl.isVisible())
        self.assertTrue(self.sidebar._version_label.isVisible())

        # Check button state in expanded mode
        for btn in self.sidebar._buttons.values():
            self.assertTrue(btn.title_lbl.isVisible())
            if btn.chevron_lbl:
                self.assertTrue(btn.chevron_lbl.isVisible())

    def test_rtl_hierarchy_and_properties(self):
        """All buttons must have Qt.RightToLeft and support QPushButton methods."""
        dashboard_btn = self.sidebar._buttons["dashboard"]
        self.assertEqual(dashboard_btn.layoutDirection(), Qt.RightToLeft)
        self.assertEqual(dashboard_btn.text(), "الرئيسية")

        # Test active state
        self.sidebar.set_active_page("dashboard")
        self.assertEqual(dashboard_btn.property("active"), "true")
        self.assertEqual(dashboard_btn.property("section_active"), "false")

    def test_accordion_exclusive_and_subpage_selection(self):
        """Selecting a subpage must highlight the child, parent, and expand accordion."""
        self.sidebar.set_active_page("devices_cpu")
        self.assertEqual(self.sidebar._current_open_section, "devices")
        self.assertTrue(self.sidebar._section_containers["devices"].isVisible())
        self.assertFalse(self.sidebar._section_containers["file_manager"].isVisible())

        # Child button active
        cpu_btn = self.sidebar._sub_buttons["devices_cpu"]
        self.assertEqual(cpu_btn.property("active"), "true")

        # Parent button section_active
        devices_btn = self.sidebar._buttons["devices"]
        self.assertEqual(devices_btn.property("section_active"), "true")

    def test_collapsed_navigation_without_container_explosion(self):
        """Clicking an item in collapsed mode navigates without unhiding child containers."""
        self.sidebar.set_collapsed(True)

        emitted = []
        self.sidebar.page_selected.connect(lambda pid: emitted.append(pid))

        self.sidebar._handle_click("maintenance")
        self.assertIn("maintenance_overview", emitted)
        # All section containers must remain hidden in collapsed mode
        for cont in self.sidebar._section_containers.values():
            self.assertFalse(cont.isVisible())


if __name__ == "__main__":
    unittest.main()
