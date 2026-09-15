# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta

from app.services.duplicate_service import DuplicateService, DuplicateGroup, DuplicateItem


class TestDuplicateService(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base = Path(self.test_dir)

        # Create identical files (group 1: 500 bytes)
        data_a = b"A" * 500
        (self.base / "file1.txt").write_bytes(data_a)
        (self.base / "copy_of_file1.txt").write_bytes(data_a)

        # Create another copy in a subfolder with different modified time
        (self.base / "sub").mkdir(parents=True, exist_ok=True)
        sub_copy = self.base / "sub" / "file1_deep.txt"
        sub_copy.write_bytes(data_a)

        # Create unique file (500 bytes but different content to test partial/full hash separation!)
        data_b = b"B" * 500
        (self.base / "different_content_same_size.txt").write_bytes(data_b)

        # Create unique file with different size
        (self.base / "unique_size.pdf").write_bytes(b"C" * 1200)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_exact_duplicates_3pass(self):
        groups = DuplicateService.find_duplicates(self.base, recursive=True)
        # Should find exactly 1 group of 3 identical files
        self.assertEqual(len(groups), 1)
        grp = groups[0]
        self.assertEqual(len(grp.files), 3)
        self.assertEqual(grp.size_bytes, 500)
        # Wasted size should be 500 * 2 = 1000 bytes
        self.assertEqual(grp.wasted_size_bytes, 1000)

    def test_smart_auto_select_rules(self):
        groups = DuplicateService.find_duplicates(self.base, recursive=True)
        self.assertEqual(len(groups), 1)
        grp = groups[0]

        # Rule 1: all_except_first
        DuplicateService.apply_auto_select(groups, "all_except_first")
        self.assertFalse(grp.files[0].is_selected)
        self.assertTrue(grp.files[1].is_selected)
        self.assertTrue(grp.files[2].is_selected)

        # Rule 2: all_except_shortest (sub_copy should be selected because it has the longest path)
        DuplicateService.apply_auto_select(groups, "all_except_shortest")
        deep_item = next(it for it in grp.files if "sub" in str(it.path))
        self.assertTrue(deep_item.is_selected)

        # Rule 3: deselect_all
        DuplicateService.apply_auto_select(groups, "deselect_all")
        self.assertTrue(all(not it.is_selected for it in grp.files))

    def test_quarantine_items(self):
        groups = DuplicateService.find_duplicates(self.base, recursive=True)
        DuplicateService.apply_auto_select(groups, "all_except_first")

        selected_items = [it for it in groups[0].files if it.is_selected]
        self.assertEqual(len(selected_items), 2)

        q_parent = Path(tempfile.mkdtemp())
        success, failed, q_dir = DuplicateService.quarantine_items(selected_items, q_parent)
        self.assertEqual(success, 2)
        self.assertEqual(failed, 0)
        self.assertTrue(q_dir.exists())

        # Cleanup quarantine
        shutil.rmtree(q_parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
