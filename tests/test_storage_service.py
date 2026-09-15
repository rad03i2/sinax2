# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.storage_analysis_service import StorageAnalysisService


class TestStorageAnalysisService(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base = Path(self.test_dir)

        (self.base / "sub1").mkdir()
        (self.base / "sub2").mkdir()

        # Create files with specified sizes
        (self.base / "sub1" / "large_file.bin").write_bytes(b"X" * 10000)
        (self.base / "sub2" / "small_doc.docx").write_bytes(b"Y" * 2000)
        (self.base / "image.png").write_bytes(b"Z" * 3000)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_analyze_directory(self):
        report = StorageAnalysisService.analyze_directory(self.base)
        self.assertEqual(report.total_files, 3)
        self.assertEqual(report.total_size_bytes, 15000)
        self.assertGreater(report.total_dirs, 0)

        # Check largest file
        self.assertEqual(len(report.top_largest_files), 3)
        self.assertEqual(report.top_largest_files[0].filename, "large_file.bin")
        self.assertEqual(report.top_largest_files[0].size_bytes, 10000)

        # Check category breakdown
        self.assertIn("word", report.categories)
        self.assertEqual(report.categories["word"].file_count, 1)
        self.assertEqual(report.categories["word"].total_bytes, 2000)

        self.assertIn("images", report.categories)
        self.assertEqual(report.categories["images"].file_count, 1)
        self.assertEqual(report.categories["images"].total_bytes, 3000)


if __name__ == "__main__":
    unittest.main()
