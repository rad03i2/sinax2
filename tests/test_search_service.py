# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta

from app.services.search_service import SearchService, SearchFilter, SearchResultItem


class TestSearchService(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base = Path(self.test_dir)

        # Create dummy directory structure and files
        (self.base / "docs").mkdir(parents=True, exist_ok=True)
        (self.base / "media").mkdir(parents=True, exist_ok=True)

        # File 1: Python script with specific text
        (self.base / "script_math.py").write_text("def calculate_total():\n    return 42\n", encoding="utf-8")

        # File 2: PDF dummy
        (self.base / "docs" / "Report_2025.pdf").write_bytes(b"%PDF-1.4 dummy data 123456789")

        # File 3: Image dummy
        (self.base / "media" / "photo_summer.png").write_bytes(b"PNG fake data")

        # File 4: Text log with specific keyword
        (self.base / "docs" / "server_error.log").write_text("2026-01-01 ERROR: Database connection failed!\nOK\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_search_all_files(self):
        filt = SearchFilter(query="", recursive=True)
        results = SearchService.search(self.base, filt)
        self.assertEqual(len(results), 4)

    def test_search_by_wildcard_name(self):
        filt = SearchFilter(query="*.pdf", recursive=True)
        results = SearchService.search(self.base, filt)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].filename, "Report_2025.pdf")

    def test_search_by_regex(self):
        filt = SearchFilter(query=r"\d{4}", use_regex=True, recursive=True)
        results = SearchService.search(self.base, filt)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].filename, "Report_2025.pdf")

    def test_search_by_category(self):
        filt = SearchFilter(category="images", recursive=True)
        results = SearchService.search(self.base, filt)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].filename, "photo_summer.png")

    def test_search_by_content_query(self):
        filt = SearchFilter(content_query="Database connection", recursive=True)
        results = SearchService.search(self.base, filt)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].filename, "server_error.log")
        self.assertIn("Database connection failed", results[0].match_snippet)
        self.assertEqual(results[0].match_line_num, 1)

    def test_search_non_recursive(self):
        filt = SearchFilter(query="", recursive=False)
        results = SearchService.search(self.base, filt)
        # Only script_math.py is in root
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].filename, "script_math.py")


if __name__ == "__main__":
    unittest.main()
