# -*- coding: utf-8 -*-
"""
SINAX Navigation Controller & Navigation Model Unit Tests
Tests:
- NavigationModel roles, data retrieval, and hierarchy
- Exclusive accordion expansion and single-section state
- Real-time search filter and auto-expansion of matching children
- NavigationController routing, history (goBack / goForward), and breadcrumbs
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.models.navigation_model import NavigationModel
from app.controllers.navigation_controller import NavigationController


class TestNavigationControllerModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.controller = NavigationController()
        self.model = self.controller.navModel

    def test_model_initialization(self):
        """Model must load items from NAVIGATION_SECTIONS and expose correct count."""
        self.assertGreater(self.model.rowCount(), 10)
        # Verify first item is dashboard
        idx0 = self.model.index(0, 0)
        item_id = self.model.data(idx0, NavigationModel.ItemIdRole)
        title = self.model.data(idx0, NavigationModel.TitleRole)
        self.assertEqual(item_id, "dashboard")
        self.assertEqual(title, "الرئيسية")

    def test_accordion_exclusive_toggle(self):
        """Toggling a section must collapse any other open section (exclusive accordion)."""
        # Initially file_manager is open
        self.assertEqual(self.model._current_open_section, "file_manager")

        # Toggle multimedia
        self.model.toggle_section("multimedia")
        self.assertEqual(self.model._current_open_section, "multimedia")

        # Children of file_manager must now be hidden, multimedia visible
        for item in self.model._items:
            if item.parent_id == "file_manager":
                self.assertFalse(item.is_visible)
            elif item.parent_id == "multimedia":
                self.assertTrue(item.is_visible)

        # Toggle multimedia again collapses it to None
        self.model.toggle_section("multimedia")
        self.assertIsNone(self.model._current_open_section)

    def test_search_filtering(self):
        """Search query must filter items and auto-reveal matching children."""
        self.controller.setSearchQuery("فيديو")
        # Ensure only matching items or their parent sections are visible
        visible_items = [item for item in self.model._items if item.is_visible]
        self.assertTrue(any("فيديو" in item.title for item in visible_items))

        # Clear search
        self.controller.setSearchQuery("")
        # Model should revert to normal accordion view
        self.assertEqual(self.controller.searchQuery, "")

    def test_routing_and_breadcrumbs(self):
        """Routing must update currentRoute, currentBreadcrumb, and trigger routeRequested."""
        emitted_routes = []
        self.controller.routeRequested.connect(lambda r: emitted_routes.append(r))

        self.controller.openRoute("video_center")
        self.assertEqual(self.controller.currentRoute, "video_center")
        self.assertIn("فيديو", self.controller.currentTitle)
        self.assertIn("›", self.controller.currentBreadcrumb)
        self.assertIn("video_center", emitted_routes)

    def test_history_navigation_back_and_forward(self):
        """Navigating multiple routes must support goBack and goForward cleanly."""
        self.controller.openRoute("dashboard")
        self.controller.openRoute("file_manager")
        self.controller.openRoute("converter")

        self.assertTrue(self.controller.canGoBack)
        self.assertFalse(self.controller.canGoForward)

        # Go back to file_manager
        self.controller.goBack()
        self.assertEqual(self.controller.currentRoute, "file_manager")
        self.assertTrue(self.controller.canGoForward)

        # Go forward to converter
        self.controller.goForward()
        self.assertEqual(self.controller.currentRoute, "converter")


if __name__ == "__main__":
    unittest.main()
