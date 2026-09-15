# -*- coding: utf-8 -*-
"""
Tests for Universal File Converter UI & Workspace.
Verifies page launch, search filter, category chips, workspace opening, and return navigation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.pages.universal_converter_page import UniversalConverterPage
from app.services.conversion.registry import conversion_registry

class TestConverterUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.page = UniversalConverterPage()
        self.page.resize(1280, 800)

    def tearDown(self):
        self.page.close()

    def test_initial_state(self):
        self.assertEqual(self.page.stack.currentIndex(), 0)
        self.assertGreaterEqual(len(self.page._card_widgets), 50)

    def test_search_filter(self):
        # Search for PDF
        self.page.search_edit.setText("PDF")
        pdf_count = len(self.page._card_widgets)
        self.assertGreater(pdf_count, 0)
        self.assertLess(pdf_count, 50)

        # Clear search
        self.page.search_edit.clear()
        self.assertGreaterEqual(len(self.page._card_widgets), 50)

    def test_category_filter(self):
        self.page._on_category_clicked("images")
        img_count = len(self.page._card_widgets)
        self.assertGreater(img_count, 0)
        self.assertLess(img_count, 50)

        # Back to all
        self.page._on_category_clicked("all")
        self.assertGreaterEqual(len(self.page._card_widgets), 50)

    def test_open_workspace_and_return(self):
        card_widget = self.page._card_widgets[0]
        direction = card_widget.card_def.forward_dir
        card_id = card_widget.card_def.card_id

        # Open workspace
        self.page._open_workspace(direction, card_id)
        self.assertEqual(self.page.stack.currentIndex(), 1)
        self.assertTrue(self.page.is_in_workspace())
        self.assertIsNotNone(self.page.current_workspace)

        # Close workspace
        self.page.close_workspace()
        self.assertEqual(self.page.stack.currentIndex(), 0)
        self.assertFalse(self.page.is_in_workspace())
        self.assertIsNone(self.page.current_workspace)

if __name__ == "__main__":
    unittest.main()
