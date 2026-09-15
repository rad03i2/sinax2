# -*- coding: utf-8 -*-
"""
Tests for DuplicateCopyPage UI and MainWindow Tool 5 integration.
"""

import sys
import shutil
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from app.ui.pages.duplicate_copy_page import DuplicateCopyPage
from app.ui.main_window import MainWindow
from app.services.duplicate_service import DuplicateService


class TestDuplicateUI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base = Path(self.test_dir)

        # Create test duplicates
        self.f1 = self.base / "file1.txt"
        self.f2 = self.base / "file2.txt"
        self.f3 = self.base / "unique.txt"

        self.f1.write_bytes(b"HELLO DUPLICATE CONTENT" * 100)
        self.f2.write_bytes(b"HELLO DUPLICATE CONTENT" * 100)
        self.f3.write_bytes(b"UNIQUE NON DUPLICATE CONTENT")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_duplicate_page_init(self):
        page = DuplicateCopyPage()
        self.assertIsNotNone(page)
        self.assertEqual(page.tabs.count(), 2)
        self.assertIsNotNone(page.dup_table)
        self.assertIsNotNone(page.transfer_table)

    def test_duplicate_detection_and_table_population(self):
        page = DuplicateCopyPage()
        page.set_directory(self.base)
        self.assertEqual(page.current_folder, self.base)

        # Find duplicates synchronously
        groups = DuplicateService.find_duplicates(self.base, recursive=True)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].files), 2)

        # Populate UI table
        page.duplicate_groups = groups
        page._populate_dup_table()
        self.assertEqual(page.dup_table.rowCount(), 2)

        # Test smart selection: keep first, select rest
        page._apply_auto_select("all_except_first")
        checked_count = sum(1 for r in range(page.dup_table.rowCount()) if page.dup_table.item(r, 0).checkState() == Qt.Checked)
        self.assertEqual(checked_count, 1)

        # Deselect all
        page._apply_auto_select("deselect_all")
        for r in range(page.dup_table.rowCount()):
            it = page.dup_table.item(r, 0)
            self.assertEqual(it.checkState(), Qt.Unchecked)

        # Select all except oldest
        page._apply_auto_select("all_except_oldest")
        checked_count = sum(1 for r in range(page.dup_table.rowCount()) if page.dup_table.item(r, 0).checkState() == Qt.Checked)
        self.assertEqual(checked_count, 1)

    def test_transfer_tab_population(self):
        page = DuplicateCopyPage()
        page.tabs.setCurrentIndex(1)

        # Add files to transfer
        page.transfer_source_files = [self.f1, self.f3]
        page._populate_transfer_table()
        self.assertEqual(page.transfer_table.rowCount(), 2)
        self.assertEqual(len(page.transfer_source_files), 2)

        # Clear files
        page._on_clear_source_files()
        self.assertEqual(page.transfer_table.rowCount(), 0)
        self.assertEqual(len(page.transfer_source_files), 0)

    def test_main_window_integration(self):
        main_win = MainWindow()
        self.assertIsNotNone(main_win.duplicate_page)

        # Direct navigation
        main_win.navigate_to("duplicate_copy")
        self.assertEqual(main_win.stack.currentIndex(), 6)

        # Hub card activation
        hub = main_win.file_manager_page
        self.assertIsNotNone(hub)


if __name__ == "__main__":
    unittest.main()
