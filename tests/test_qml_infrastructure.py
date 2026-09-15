# -*- coding: utf-8 -*-
"""
SINAX QML Infrastructure & Component Library Unit Tests
Tests:
- Vector SinaxIconProvider rendering and caching
- QML Theme singleton palette and typography
- Component instantiation (SinaxButton, SinaxBadge, SinaxCard, SinaxTextField)
- configure_qml_engine and resource URL resolution
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPixmap

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.ui.qml_icon_provider import SinaxIconProvider
from app.controllers.theme_controller import theme_controller


class TestQmlInfrastructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_icon_provider_vector_generation(self):
        """SinaxIconProvider must generate sharp QPixmap for arbitrary icons and sizes."""
        provider = SinaxIconProvider()
        # Request a standard icon: name/color/size
        requested_size = QSize(32, 32)
        pixmap = provider.requestPixmap("folder/#60CDFF/32", requested_size)
        self.assertIsInstance(pixmap, QPixmap)
        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 32)
        self.assertEqual(pixmap.height(), 32)

        # Request default color fallback
        pixmap2 = provider.requestPixmap("settings", requested_size)
        self.assertFalse(pixmap2.isNull())

        # Test requestImage
        image = provider.requestImage("dashboard/#FFFFFF/24", requested_size)
        self.assertIsInstance(image, QImage)
        self.assertFalse(image.isNull())

    def test_qml_url_resolution(self):
        """get_qml_url must resolve valid URLs for registered QML files."""
        url = get_qml_url("navigation/Sidebar.qml")
        self.assertTrue(url.isValid())
        self.assertTrue(url.toString().endswith("Sidebar.qml"))

        top_url = get_qml_url("navigation/TopBar.qml")
        self.assertTrue(top_url.isValid())

        dash_url = get_qml_url("pages/Dashboard.qml")
        self.assertTrue(dash_url.isValid())

    def test_qml_theme_and_components_loading(self):
        """Verify core QML components compile and instantiate cleanly in QtQuick engine."""
        qw = QQuickWidget()
        qw.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(qw.engine())

        # Load TopBar.qml which exercises Theme, SinaxIconButton, SinaxBadge
        qw.setSource(get_qml_url("navigation/TopBar.qml"))
        self.assertEqual(qw.status(), QQuickWidget.Status.Ready, f"Errors: {qw.errors()}")
        self.assertIsNotNone(qw.rootObject())

    def test_theme_controller_toggle(self):
        """ThemeController must toggle theme mode and notify QML layer."""
        initial_dark = theme_controller.isDark
        theme_controller.toggleTheme()
        self.assertNotEqual(theme_controller.isDark, initial_dark)

        # Toggle back to maintain test environment consistency
        theme_controller.toggleTheme()
        self.assertEqual(theme_controller.isDark, initial_dark)


if __name__ == "__main__":
    unittest.main()
