# -*- coding: utf-8 -*-
"""
Unit tests for SIGNX UX, Theme, Sidebar, Search, Branding, and ScrollBar refinements.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QEvent, QCoreApplication

app = QApplication.instance() or QApplication(sys.argv)

from app.core.constants import APP_NAME, APP_TAGLINE_AR, DEVELOPER_NAME, APP_VERSION
from app.controllers.navigation_controller import NavigationController, navigation_controller
from app.ui.themes.theme_manager import theme_manager, detect_windows_theme
from app.controllers.theme_controller import theme_controller
from app.controllers.quick_about_controller import quick_about_controller
from app.controllers.command_palette_controller import command_palette_controller
from app.ui.dialogs.quick_about_dialog import QuickAboutDialog
from app.ui.dialogs.sidebar_flyout_dialog import SidebarFlyoutDialog
from app.ui.dialogs.command_palette_dialog import CommandPaletteDialog


class TestUXRefinements(unittest.TestCase):

    def setUp(self):
        self.nav = NavigationController()

    def test_branding_constants(self):
        """Verify visible branding requirements."""
        self.assertEqual(APP_NAME, "SINAX")
        self.assertEqual(APP_TAGLINE_AR, "نظام إدارة الحاسوب والملفات")
        self.assertEqual(DEVELOPER_NAME, "رضوان عبد الهادي")
        self.assertIsNotNone(APP_VERSION)

    def test_quick_about_controller(self):
        """Verify QuickAboutController metadata and state machine."""
        self.assertEqual(quick_about_controller.appName, "SINAX")
        self.assertEqual(quick_about_controller.appSubtitle, "نظام إدارة الحاسوب والملفات")
        self.assertEqual(quick_about_controller.developerName, "رضوان عبد الهادي")
        
        # Test toggle
        quick_about_controller.setOpen(False)
        self.assertFalse(quick_about_controller.isOpen)
        quick_about_controller.toggle()
        self.assertTrue(quick_about_controller.isOpen)
        quick_about_controller.toggle()
        self.assertFalse(quick_about_controller.isOpen)

    def test_quick_about_dialog_outside_click(self):
        """Verify QuickAboutDialog closes upon losing window activation."""
        dialog = QuickAboutDialog()
        quick_about_controller.setOpen(True)
        self.assertTrue(quick_about_controller.isOpen)

        # Simulate activation change when not active window
        act_event = QEvent(QEvent.ActivationChange)
        QCoreApplication.sendEvent(dialog, act_event)
        self.assertFalse(quick_about_controller.isOpen)
        dialog.close()

    def test_sidebar_accordion_single_source_of_truth(self):
        """Verify accordion state machine and openSectionId toggle logic."""
        # Initial state: expanded mode
        self.nav.setCollapsed(False)
        self.assertEqual(self.nav.openSectionId, "file_manager")

        # Toggle to multimedia
        self.nav.toggleSection("multimedia")
        self.assertEqual(self.nav.openSectionId, "multimedia")

        # Toggle multimedia again collapses it
        self.nav.toggleSection("multimedia")
        self.assertEqual(self.nav.openSectionId, "")

        # Reopen multimedia then closeSection()
        self.nav.toggleSection("multimedia")
        self.assertEqual(self.nav.openSectionId, "multimedia")
        self.nav.closeSection()
        self.assertEqual(self.nav.openSectionId, "")

    def test_collapsed_mode_accordion_and_routing(self):
        """Verify collapsed mode flyout opening, child selection, and no premature expansion."""
        # Set collapsed
        self.nav.setCollapsed(True)
        self.assertTrue(self.nav.isCollapsed)
        self.assertEqual(self.nav.openSectionId, "")

        # In collapsed mode, user clicks section icon: open flyout
        self.nav.toggleSection("multimedia")
        self.assertEqual(self.nav.openSectionId, "multimedia")

        # User selects child inside flyout: navigates, flyout closes, sidebar stays collapsed!
        self.nav.openRoute("video_center")
        self.assertEqual(self.nav.currentRoute, "video_center")
        self.assertEqual(self.nav.openSectionId, "")
        self.assertTrue(self.nav.isCollapsed)

        # Later, expanding sidebar restores parent accordion
        self.nav.setCollapsed(False)
        self.assertFalse(self.nav.isCollapsed)
        self.assertEqual(self.nav.openSectionId, "multimedia")

    def test_sidebar_flyout_dialog_outside_click(self):
        """Verify SidebarFlyoutDialog closes upon losing window activation."""
        dummy_parent = QWidget()
        dialog = SidebarFlyoutDialog(parent=dummy_parent, sidebar_widget=dummy_parent)
        navigation_controller.setCollapsed(True)
        navigation_controller.toggleSection("multimedia")
        self.assertEqual(navigation_controller.openSectionId, "multimedia")

        # Simulate activation change
        act_event = QEvent(QEvent.ActivationChange)
        QCoreApplication.sendEvent(dialog, act_event)
        self.assertEqual(navigation_controller.openSectionId, "")
        dialog.close()
        dummy_parent.close()

    def test_theme_system_3modes(self):
        """Verify 3-mode theme system (system / light / dark)."""
        # Test windows theme detection
        detected = detect_windows_theme()
        self.assertIn(detected, ("dark", "light"))

        # Test mode switching on theme_manager and theme_controller
        theme_manager.set_theme_mode("dark")
        self.assertEqual(theme_controller.themeMode, "dark")
        self.assertEqual(theme_controller.effectiveTheme, "dark")
        self.assertTrue(theme_controller.isDark)
        self.assertEqual(theme_controller.currentIcon, "moon")

        theme_manager.set_theme_mode("light")
        self.assertEqual(theme_controller.themeMode, "light")
        self.assertEqual(theme_controller.effectiveTheme, "light")
        self.assertFalse(theme_controller.isDark)
        self.assertEqual(theme_controller.currentIcon, "sun")

        theme_manager.set_theme_mode("system")
        self.assertEqual(theme_controller.themeMode, "system")
        self.assertEqual(theme_controller.effectiveTheme, detected)
        self.assertEqual(theme_controller.currentIcon, "monitor")

    def test_file_management_dark_mode_qss(self):
        """Verify dark.qss and light.qss contain all required File Management rules."""
        dark_qss_path = Path("app/ui/themes/dark.qss")
        light_qss_path = Path("app/ui/themes/light.qss")
        self.assertTrue(dark_qss_path.exists())
        self.assertTrue(light_qss_path.exists())

        dark_text = dark_qss_path.read_text(encoding="utf-8")
        light_text = light_qss_path.read_text(encoding="utf-8")

        for selector in ["QTreeView", "QTableView", "QListView", "QHeaderView::section", "QMenu", "QToolBar", "QToolButton"]:
            self.assertIn(selector, dark_text, f"Missing {selector} in dark.qss")
            self.assertIn(selector, light_text, f"Missing {selector} in light.qss")

        # Verify 10px scrollbars
        self.assertIn("width: 10px;", dark_text)
        self.assertIn("width: 10px;", light_text)

    def test_scrollbar_qml_anchoring(self):
        """Verify SinaxScrollBar.qml RTL left-anchoring and properties."""
        qml_path = Path("app/ui/qml/components/SinaxScrollBar.qml")
        self.assertTrue(qml_path.exists())
        content = qml_path.read_text(encoding="utf-8")

        self.assertIn("anchors.left: parent ? parent.left : undefined", content)
        self.assertIn("anchors.right: undefined", content)
        self.assertIn("width: 10", content)
        self.assertIn("policy: ScrollBar.AsNeeded", content)

    def test_command_palette_ux_and_outside_click(self):
        """Verify CommandPaletteController, CommandPaletteDialog outside click, and UX."""
        dialog = CommandPaletteDialog()
        command_palette_controller.setOpen(True)
        self.assertTrue(command_palette_controller.isOpen)

        # Simulate outside click dismissal
        act_event = QEvent(QEvent.ActivationChange)
        QCoreApplication.sendEvent(dialog, act_event)
        self.assertFalse(command_palette_controller.isOpen)

        # Selection navigates and closes
        command_palette_controller.setOpen(True)
        command_palette_controller.selectCommand("settings")
        self.assertFalse(command_palette_controller.isOpen)

        # Verify 350ms hover-leave timer in CommandPalette.qml
        palette_qml = Path("app/ui/qml/navigation/CommandPalette.qml").read_text(encoding="utf-8")
        self.assertIn("interval: 350", palette_qml)
        self.assertIn("hoverLeaveTimer", palette_qml)
        dialog.close()

    def test_tooltip_timing(self):
        """Verify SinaxTooltip timing constants."""
        tooltip_qml = Path("app/ui/qml/components/SinaxTooltip.qml").read_text(encoding="utf-8")
        self.assertIn("property int delay: 500", tooltip_qml)
        self.assertIn("property int timeout: 4000", tooltip_qml)


if __name__ == "__main__":
    unittest.main()
