# -*- coding: utf-8 -*-
"""
SINAX Core Rename Engine Automated Tests
Tests numbering systems, conflict prevention, circular collision handling, and rollback.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.models.file_item import FileItem
from app.models.rename_rule import RenameConfig
from app.services.file_service import FileService
from app.services.rename_service import RenameService, RenamePlan

class TestRenameEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="sinax_test_"))

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_number_formatting(self):
        # Western with padding
        self.assertEqual(RenameService.format_index(1, "western", padding=1), "1")
        self.assertEqual(RenameService.format_index(5, "western", padding=3), "005")

        # Arabic Indic
        self.assertEqual(RenameService.format_index(1, "arabic_indic", padding=1), "١")
        self.assertEqual(RenameService.format_index(12, "arabic_indic", padding=3), "٠١٢")

        # Arabic Alphabet
        self.assertEqual(RenameService.format_index(1, "arabic_alpha"), "أ")
        self.assertEqual(RenameService.format_index(2, "arabic_alpha"), "ب")

        # Arabic Words
        self.assertEqual(RenameService.format_index(1, "arabic_words"), "الأول")
        self.assertEqual(RenameService.format_index(2, "arabic_words"), "الثاني")
        self.assertEqual(RenameService.format_index(10, "arabic_words"), "العاشر")

        # English Upper
        self.assertEqual(RenameService.format_index(1, "english_upper"), "A")
        self.assertEqual(RenameService.format_index(2, "english_upper"), "B")

        # English Words
        self.assertEqual(RenameService.format_index(1, "english_words"), "First")
        self.assertEqual(RenameService.format_index(2, "english_words"), "Second")

    def test_smart_numeric_sort(self):
        names = ["Lecture 10.pdf", "Lecture 1.pdf", "Lecture 2.pdf", "Lecture 20.pdf"]
        items = []
        for n in names:
            p = self.test_dir / n
            p.touch()
            items.append(FileItem.from_path(p))

        sorted_items = RenameService.sort_items(items, "smart_numeric")
        sorted_names = [i.original_name for i in sorted_items]
        self.assertEqual(sorted_names, ["Lecture 1.pdf", "Lecture 2.pdf", "Lecture 10.pdf", "Lecture 20.pdf"])

    def test_preset_generation_and_execution(self):
        files = ["doc_a.pdf", "doc_b.pdf", "doc_c.pdf"]
        items = []
        for f in files:
            p = self.test_dir / f
            p.touch()
            items.append(FileItem.from_path(p))

        cfg = RenameConfig(
            mode="custom",
            pattern="محاضرة {n}",
            start_number=1,
            padding=2,
            number_system="western",
            keep_extension=True
        )

        plan = RenameService.generate_preview(items, cfg)
        self.assertTrue(plan.valid)
        self.assertEqual(plan.conflicts_count, 0)
        self.assertEqual(plan.items[0].new_name, "محاضرة 01.pdf")
        self.assertEqual(plan.items[1].new_name, "محاضرة 02.pdf")
        self.assertEqual(plan.items[2].new_name, "محاضرة 03.pdf")

        # Execute
        success, fail, errors, record = RenameService.execute_plan(plan)
        self.assertEqual(success, 3)
        self.assertEqual(fail, 0)
        self.assertTrue((self.test_dir / "محاضرة 01.pdf").exists())
        self.assertTrue((self.test_dir / "محاضرة 02.pdf").exists())
        self.assertTrue((self.test_dir / "محاضرة 03.pdf").exists())

        # Test Undo
        self.assertIsNotNone(record)
        u_success, u_fail, u_errors = RenameService.undo_operation(record)
        self.assertEqual(u_success, 3)
        self.assertTrue((self.test_dir / "doc_a.pdf").exists())
        self.assertTrue((self.test_dir / "doc_b.pdf").exists())
        self.assertTrue((self.test_dir / "doc_c.pdf").exists())

    def test_circular_collision_safe_swap(self):
        # A.pdf -> B.pdf and B.pdf -> A.pdf
        p1 = self.test_dir / "A.pdf"
        p2 = self.test_dir / "B.pdf"
        p1.write_text("content A", encoding="utf-8")
        p2.write_text("content B", encoding="utf-8")

        item1 = FileItem.from_path(p1)
        item2 = FileItem.from_path(p2)

        # Manually create circular swap plan
        plan = RenamePlan()
        plan.items = [item1, item2]
        item1.new_name = "B.pdf"
        item2.new_name = "A.pdf"
        plan.rename_map = [(p1, p2), (p2, p1)]

        success, fail, errors, record = RenameService.execute_plan(plan)
        self.assertEqual(success, 2)
        self.assertEqual(fail, 0)
        self.assertEqual((self.test_dir / "B.pdf").read_text(encoding="utf-8"), "content A")
        self.assertEqual((self.test_dir / "A.pdf").read_text(encoding="utf-8"), "content B")

    def test_windows_illegal_char_detection(self):
        p = self.test_dir / "valid.txt"
        p.touch()
        item = FileItem.from_path(p)

        cfg = RenameConfig(
            pattern="invalid<?>file",
            keep_extension=True
        )
        plan = RenameService.generate_preview([item], cfg)
        self.assertFalse(plan.valid)
        self.assertEqual(plan.conflicts_count, 1)
        self.assertIn("أحرف ممنوعة", item.conflict_reason)

if __name__ == "__main__":
    unittest.main()
