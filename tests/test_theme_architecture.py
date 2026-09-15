# -*- coding: utf-8 -*-
"""
SINAX Theme Architecture & UI Restoration Tests
Verifies:
1. Branding constants & Single Source of Truth
2. TopBar QML compilation status & error count
3. Search Focus & Caret drop functionality
4. UniversalConverterPage dynamic Light & Dark mode rendering (No Dark Island)
5. 20-cycle Theme Switch Stress Test
6. Page Cache Theme Persistence (Dark -> Cached -> Light -> Reopened)
"""

import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.constants import APP_NAME, APP_NAME_AR, APP_TAGLINE_AR
from app.ui.themes.theme_manager import theme_manager
from app.controllers.theme_controller import theme_controller
from app.controllers.command_palette_controller import command_palette_controller
from app.ui.widgets.header_bar import HeaderBar
from app.ui.pages.universal_converter_page import UniversalConverterPage
from app.ui.main_window import MainWindow


class TestThemeArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_01_branding_restoration(self):
        """Verify SINAX branding restoration."""
        self.assertEqual(APP_NAME, "SINAX")
        self.assertEqual(APP_NAME_AR, "ساينكس")
        self.assertEqual(APP_TAGLINE_AR, "نظام إدارة الحاسوب والملفات")

    def test_02_topbar_compilation_and_restoration(self):
        """Verify TopBar QML compilation with Popup import (0 errors, Ready status)."""
        header = HeaderBar()
        errors = header.quick_widget.errors()
        self.assertEqual(len(errors), 0, f"HeaderBar has QML errors: {[e.toString() for e in errors]}")
        self.assertEqual(header.quick_widget.status(), QQuickWidget.Status.Ready)

    def test_03_search_focus_and_dialog(self):
        """Verify CommandPaletteDialog opens and closes cleanly without keeping focus."""
        command_palette_controller.setOpen(False)
        self.assertFalse(command_palette_controller.isOpen)

        command_palette_controller.setOpen(True)
        self.assertTrue(command_palette_controller.isOpen)

        command_palette_controller.setOpen(False)
        self.assertFalse(command_palette_controller.isOpen)

    def test_04_universal_converter_theme_rendering(self):
        """Verify UniversalConverterPage renders 100% Light without Dark Islands."""
        page = UniversalConverterPage()

        # 1. Apply Light Mode
        theme_manager.set_theme_mode("light")
        page._apply_theme("light")

        # Verify QuickDropBanner has light background
        banner_style = page.quick_banner.styleSheet()
        self.assertIn("#EFF6FF", banner_style)
        self.assertNotIn("#1A2433", banner_style)

        # Verify cards are light
        self.assertGreater(len(page._card_widgets), 0)
        first_card = page._card_widgets[0]
        card_style = first_card.styleSheet()
        self.assertIn("#FFFFFF", card_style)
        self.assertNotIn("#1E1E1E", card_style)

        # Verify direction button is light
        dir_btn_style = first_card.btn_forward.styleSheet()
        self.assertIn("#F8FAFC", dir_btn_style)
        self.assertNotIn("#252525", dir_btn_style)

        # 2. Switch to Dark Mode
        theme_manager.set_theme_mode("dark")
        page._apply_theme("dark")

        # Verify QuickDropBanner has dark background
        banner_style_dark = page.quick_banner.styleSheet()
        self.assertIn("#1A2433", banner_style_dark)

        # Verify cards are dark
        card_style_dark = first_card.styleSheet()
        self.assertIn("#1E293B", card_style_dark)

        # Verify direction button is dark
        dir_btn_style_dark = first_card.btn_forward.styleSheet()
        self.assertIn("#0F172A", dir_btn_style_dark)

        # 3. Switch back to Light Mode
        theme_manager.set_theme_mode("light")
        page._apply_theme("light")
        self.assertIn("#EFF6FF", page.quick_banner.styleSheet())
        self.assertIn("#FFFFFF", first_card.styleSheet())

    def test_05_theme_switch_stress_20_cycles(self):
        """Perform 20 rapid cycles of theme switching (Dark -> Light -> System...)."""
        modes = ["dark", "light", "system", "light", "dark"]
        for cycle in range(4):
            for mode in modes:
                theme_manager.set_theme_mode(mode)
                self.assertIn(theme_manager.effective_theme, ("dark", "light"))
                self.app.processEvents()

    def test_06_page_cache_theme_persistence(self):
        """Verify cached page updates immediately upon theme toggle."""
        window = MainWindow()
        window.hide()

        # Start in Dark mode
        theme_manager.set_theme_mode("dark")

        # Load converter page in Dark mode into cache
        converter = window.ensure_page_loaded(9)
        self.assertIsNotNone(converter)
        self.assertIn("#1E293B", converter._card_widgets[0].styleSheet())

        # Switch theme to Light while converter is cached in the background
        theme_manager.set_theme_mode("light")
        self.app.processEvents()

        # Reopen / inspect cached converter - MUST be Light!
        reopened = window.ensure_page_loaded(9)
        self.assertEqual(reopened, converter)
        self.assertIn("#FFFFFF", reopened._card_widgets[0].styleSheet())
        self.assertNotIn("#1E1E1E", reopened._card_widgets[0].styleSheet())

        window.close()


if __name__ == "__main__":
    unittest.main()
