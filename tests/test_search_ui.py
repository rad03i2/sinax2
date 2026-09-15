# -*- coding: utf-8 -*-
import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

app = QApplication.instance() or QApplication(sys.argv)

from app.ui.pages.search_analysis_page import SearchAnalysisPage
from app.ui.main_window import MainWindow
from app.services.search_service import SearchFilter, SearchService
from app.services.storage_analysis_service import StorageAnalysisService


class TestSearchUI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base = Path(self.test_dir)

        # Create dummy directory structure
        (self.base / "sub").mkdir(parents=True, exist_ok=True)
        (self.base / "doc1.pdf").write_bytes(b"%PDF dummy 1")
        (self.base / "sub" / "code.py").write_text("print('hello world')", encoding="utf-8")
        (self.base / "photo.png").write_bytes(b"PNG image bytes")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_search_page_init(self):
        page = SearchAnalysisPage()
        self.assertIsNotNone(page)
        self.assertEqual(page.tabs.count(), 2)
        self.assertIsNotNone(page.search_table)
        self.assertIsNotNone(page.top_table)

    def test_search_execution_synchronous(self):
        page = SearchAnalysisPage()
        page.set_directory(self.base)
        self.assertEqual(page.current_folder, self.base)

        # Directly run search service and populate UI
        filt = SearchFilter(query="*.py", recursive=True)
        results = SearchService.search(self.base, filt)
        self.assertEqual(len(results), 1)

        page._populate_search_table(results)
        self.assertEqual(page.search_table.rowCount(), 1)
        self.assertEqual(page.search_table.item(0, 1).text(), "code.py")

    def test_storage_analysis_synchronous(self):
        page = SearchAnalysisPage()
        page.set_directory(self.base)

        report = StorageAnalysisService.analyze_directory(self.base)
        self.assertEqual(report.total_files, 3)

        page._on_storage_finished(report)
        # Check that top table has 3 rows
        self.assertEqual(page.top_table.rowCount(), 3)
        # Check KPI cards updated
        val = page.card_total_files.findChild(QLabel := page.card_total_files.findChildren(object)[-1].__class__, "kpiValue").text()
        self.assertIn("3", val)

    def test_main_window_navigation_to_search(self):
        main_win = MainWindow()
        self.assertIsNotNone(main_win.search_page)
        main_win.navigate_to("search_analysis")
        self.assertEqual(main_win.stack.currentIndex(), 5)


if __name__ == "__main__":
    unittest.main()
