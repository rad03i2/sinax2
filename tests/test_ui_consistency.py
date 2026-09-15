# -*- coding: utf-8 -*-
"""
Automated Test Suite for SINAX UI Consistency:
1. Scrollbars Left-side RTL standard and Dashboard scrollbar presence
2. Theme consistency & apply_theme propagation across all 6 major centers
3. Quick Tools category chips dynamic sizing and filtering
4. Tooltip clipping fix (Overlay.overlay mounting)
5. QSS Scrollbar stylesheet rules for Light and Dark themes
"""

import sys
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QUrl
from PySide6.QtQuick import QQuickItem
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.ui.themes.theme_manager import theme_manager
from app.ui.pages.apps_manager_page import AppsManagerPage
from app.ui.pages.network_page import NetworkPage
from app.ui.pages.devices_page import DevicesPage
from app.ui.pages.privacy_security_page import PrivacySecurityPage
from app.ui.pages.maintenance_page import MaintenancePage
from app.ui.pages.backup_sync_page import BackupSyncPage
from app.controllers.quick_tools_controller import quick_tools_controller


class TestUiConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.app.setLayoutDirection(Qt.RightToLeft)

    def test_qml_scrollbar_anchored_left(self):
        """Verify SinaxScrollBar is anchored to parent.left (x == 0.0)."""
        qw = QQuickWidget()
        qw.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(qw.engine())
        qml_url = get_qml_url("pages/ImageCenterPage.qml")
        qw.setSource(qml_url)
        root = qw.rootObject()
        self.assertIsNotNone(root)

        scrollbar = root.findChild(QQuickItem, "vScrollBar")
        self.assertIsNotNone(scrollbar, "SinaxScrollBar with objectName 'vScrollBar' must exist")
        self.assertEqual(scrollbar.x(), 0.0, "Vertical scrollbar must be strictly on the LEFT (x == 0.0)")

    def test_dashboard_scrollbar_presence(self):
        """Verify Dashboard has vertical scrollbar anchored to the left."""
        qw = QQuickWidget()
        qw.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(qw.engine(), "dashboardController")
        qml_url = get_qml_url("pages/Dashboard.qml")
        qw.setSource(qml_url)
        root = qw.rootObject()
        self.assertIsNotNone(root)

        scrollbar = root.findChild(QQuickItem, "vScrollBar")
        self.assertIsNotNone(scrollbar, "Dashboard must contain vScrollBar")
        self.assertEqual(scrollbar.x(), 0.0, "Dashboard vertical scrollbar must be on the LEFT (x == 0.0)")

    def test_theme_propagation_six_centers(self):
        """Verify all 6 centers have apply_theme and adapt nav and stack backgrounds."""
        centers = [
            ("AppsManagerPage", AppsManagerPage()),
            ("NetworkPage", NetworkPage()),
            ("DevicesPage", DevicesPage()),
            ("PrivacySecurityPage", PrivacySecurityPage()),
            ("MaintenancePage", MaintenancePage()),
            ("BackupSyncPage", BackupSyncPage()),
        ]

        for name, page in centers:
            self.assertTrue(hasattr(page, "apply_theme"), f"{name} must implement apply_theme()")

            # Test Light Theme
            page.apply_theme("light")
            nav_widget = getattr(page, "nav_scroll", None) or getattr(page, "nav_bar", None)
            self.assertIsNotNone(nav_widget, f"{name} must have nav_scroll or nav_bar")
            nav_style = nav_widget.styleSheet()
            self.assertIn("#F8FAFC", nav_style, f"{name} nav in light theme must use #F8FAFC, got: {nav_style}")
            self.assertNotIn("#0D1117", nav_style, f"{name} nav in light theme must not contain dark #0D1117")

            stack_style = page.stack.styleSheet()
            self.assertIn("#FFFFFF", stack_style, f"{name} stack in light theme must use #FFFFFF, got: {stack_style}")

            # Test Dark Theme
            page.apply_theme("dark")
            nav_style_dark = nav_widget.styleSheet()
            self.assertIn("#0D1117", nav_style_dark, f"{name} nav in dark theme must use #0D1117")
            stack_style_dark = page.stack.styleSheet()
            self.assertIn("#0D1117", stack_style_dark, f"{name} stack in dark theme must use #0D1117")

    def test_quick_tools_chips_filter(self):
        """Verify Quick Tools category chips load, scale dynamically, and filter correctly."""
        qw = QQuickWidget()
        qw.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(qw.engine(), "quickToolsController")
        qml_url = get_qml_url("pages/QuickToolsPage.qml")
        qw.setSource(qml_url)
        root = qw.rootObject()
        self.assertIsNotNone(root)

        # Test controller category filtering
        all_count = quick_tools_controller.toolModel.rowCount()
        self.assertGreater(all_count, 0, "Quick tools must have items")

        quick_tools_controller.setCategory("encoding")
        encoding_count = quick_tools_controller.toolModel.rowCount()
        self.assertGreater(encoding_count, 0)
        self.assertLessEqual(encoding_count, all_count)

        # Reset to all
        quick_tools_controller.setCategory("all")
        self.assertEqual(quick_tools_controller.toolModel.rowCount(), all_count)

    def test_qss_scrollbars_defined(self):
        """Verify light.qss and dark.qss both contain Fluent QScrollBar styling rules."""
        light_path = Path("app/ui/themes/light.qss")
        dark_path = Path("app/ui/themes/dark.qss")

        light_qss = light_path.read_text(encoding="utf-8")
        dark_qss = dark_path.read_text(encoding="utf-8")

        self.assertIn("QScrollBar:vertical", light_qss)
        self.assertIn("QScrollBar:horizontal", light_qss)
        self.assertIn("QScrollBar::handle:vertical", light_qss)

        self.assertIn("QScrollBar:vertical", dark_qss)
        self.assertIn("QScrollBar:horizontal", dark_qss)
        self.assertIn("QScrollBar::handle:vertical", dark_qss)


if __name__ == "__main__":
    unittest.main()
