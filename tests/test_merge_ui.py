# -*- coding: utf-8 -*-
"""
SINAX Merge Files UI Automated Test
Verifies UI controls, table interactions, ordering, sorting, and mode detection.
"""

import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.ui.pages.merge_files_page import MergeFilesPage


class TestMergeUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.window = MainWindow()
        cls.window.navigate_to("merge_files")
        cls.page = cls.window.merge_page

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="sinax_merge_ui_"))

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        self.page._clear_files()

    def test_navigation_to_merge_page(self):
        self.assertIsInstance(self.page, MergeFilesPage)
        self.assertEqual(self.window.stack.currentIndex(), 3)

    def test_add_files_and_mode_detection(self):
        # Create dummy PDFs
        p1 = self.test_dir / "Chapter 1.pdf"
        p2 = self.test_dir / "Chapter 2.pdf"
        p1.touch()
        p2.touch()

        self.page.add_paths([p1, p2])
        self.assertEqual(len(self.page.files_list), 2)
        self.assertEqual(self.page.table.rowCount(), 2)

        # Check detected mode
        self.assertEqual(self.page.current_detected_mode["mode"], "pdf")
        self.assertIn("PDF", self.page.mode_title.text())
        self.assertTrue(self.page.merge_btn.isEnabled())

    def test_reorder_and_sort(self):
        files = [
            self.test_dir / "File 10.docx",
            self.test_dir / "File 1.docx",
            self.test_dir / "File 2.docx"
        ]
        for f in files:
            f.touch()

        self.page.add_paths(files)
        self.assertEqual(self.page.files_list[0].name, "File 10.docx")

        # Smart Numeric Sort
        self.page.sort_combo.setCurrentIndex(0)  # numeric
        self.page._apply_sorting()

        self.assertEqual(self.page.files_list[0].name, "File 1.docx")
        self.assertEqual(self.page.files_list[1].name, "File 2.docx")
        self.assertEqual(self.page.files_list[2].name, "File 10.docx")

        # Move last item up
        self.page.table.selectRow(2)
        self.page._move_up()
        self.assertEqual(self.page.files_list[1].name, "File 10.docx")

        # Move to top
        self.page.table.selectRow(1)
        self.page._move_to_top()
        self.assertEqual(self.page.files_list[0].name, "File 10.docx")

if __name__ == "__main__":
    unittest.main()
