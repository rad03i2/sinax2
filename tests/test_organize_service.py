# -*- coding: utf-8 -*-
"""
SINAX Smart Organize Automated Tests
Tests classification modes, plan generation, move/copy execution, collision handling, and Undo.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.organize_service import OrganizeService, OrganizePlan

class TestOrganizeService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="sinax_organize_test_"))
        self.source_dir = self.test_dir / "source"
        self.source_dir.mkdir()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_classification_modes(self):
        # 1. Category
        pdf = self.source_dir / "test.pdf"
        pdf.touch()
        self.assertEqual(OrganizeService.classify_file(pdf, "category"), "ملفات PDF")

        # 2. Extension
        docx = self.source_dir / "document.docx"
        docx.touch()
        self.assertEqual(OrganizeService.classify_file(docx, "extension"), "DOCX")

        # 3. Size
        big_file = self.source_dir / "big.dat"
        with open(big_file, "wb") as f:
            f.write(b"0" * 15 * 1024 * 1024)  # 15 MB
        self.assertIn("10 - 100 ميجابايت", OrganizeService.classify_file(big_file, "size"))

        # 4. Academic Keywords
        lec = self.source_dir / "Lecture_01_AI.pdf"
        hw = self.source_dir / "Homework_Assignment_2.docx"
        exam = self.source_dir / "Final_Exam_2024.pdf"
        self.assertEqual(OrganizeService.classify_file(lec, "academic"), "محاضرات ودروس")
        self.assertEqual(OrganizeService.classify_file(hw, "academic"), "واجبات وتكاليف")
        self.assertEqual(OrganizeService.classify_file(exam, "academic"), "امتحانات واختبارات")

    def test_execute_move_and_undo(self):
        f1 = self.source_dir / "doc1.pdf"
        f2 = self.source_dir / "img1.png"
        f1.write_text("content1", encoding="utf-8")
        f2.write_text("content2", encoding="utf-8")

        plan = OrganizeService.generate_plan(
            files=[f1, f2],
            source_dir=self.source_dir,
            target_base_dir=self.source_dir,
            mode="extension",
            action_type="move",
            collision_strategy="rename"
        )

        self.assertEqual(len(plan.items), 2)
        self.assertEqual(plan.folders_summary.get("PDF", 0), 1)
        self.assertEqual(plan.folders_summary.get("PNG", 0), 1)

        # Execute Move
        success, fail, errors, record = OrganizeService.execute_plan(plan)
        self.assertEqual(success, 2)
        self.assertEqual(fail, 0)
        self.assertFalse(f1.exists())
        self.assertFalse(f2.exists())
        self.assertTrue((self.source_dir / "PDF" / "doc1.pdf").exists())
        self.assertTrue((self.source_dir / "PNG" / "img1.png").exists())

        # Test Undo
        self.assertIsNotNone(record)
        u_success, u_fail, u_errors = OrganizeService.undo_operation(record)
        self.assertEqual(u_success, 2)
        self.assertTrue(f1.exists())
        self.assertTrue(f2.exists())
        # Empty subfolders should be removed
        self.assertFalse((self.source_dir / "PDF").exists())
        self.assertFalse((self.source_dir / "PNG").exists())

    def test_collision_handling_auto_rename(self):
        # Target already has doc1.pdf
        target_dir = self.source_dir / "PDF"
        target_dir.mkdir()
        existing_pdf = target_dir / "doc1.pdf"
        existing_pdf.write_text("existing content", encoding="utf-8")

        new_pdf = self.source_dir / "doc1.pdf"
        new_pdf.write_text("new content", encoding="utf-8")

        plan = OrganizeService.generate_plan(
            files=[new_pdf],
            source_dir=self.source_dir,
            target_base_dir=self.source_dir,
            mode="extension",
            action_type="move",
            collision_strategy="rename"
        )

        success, fail, errors, record = OrganizeService.execute_plan(plan)
        self.assertEqual(success, 1)
        self.assertEqual(fail, 0)
        # Original remains
        self.assertEqual(existing_pdf.read_text(encoding="utf-8"), "existing content")
        # New file renamed to doc1 (1).pdf
        renamed_pdf = target_dir / "doc1 (1).pdf"
        self.assertTrue(renamed_pdf.exists())
        self.assertEqual(renamed_pdf.read_text(encoding="utf-8"), "new content")

if __name__ == "__main__":
    unittest.main()
