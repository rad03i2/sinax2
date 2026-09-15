# -*- coding: utf-8 -*-
import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure QApplication exists for GUI tests
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from app.ui.pages.smart_organize_page import SmartOrganizePage
from app.ui.main_window import MainWindow
from app.services.organize_service import OrganizeService


class TestOrganizeUI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_path = Path(self.test_dir)

        # Create dummy files
        (self.base_path / "Lecture1_Math.pdf").write_text("dummy pdf", encoding="utf-8")
        (self.base_path / "Assignment2_Code.py").write_text("print('test')", encoding="utf-8")
        (self.base_path / "photo.jpg").write_text("dummy image", encoding="utf-8")
        (self.base_path / "report_2025.docx").write_text("dummy docx", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_smart_organize_page_init(self):
        page = SmartOrganizePage()
        self.assertIsNotNone(page)
        self.assertIsNotNone(page.preview_table)
        self.assertIsNotNone(page.mode_combo)
        self.assertEqual(page.mode_combo.count(), 6)

    def test_smart_organize_scan_and_plan(self):
        page = SmartOrganizePage()
        page.set_directory(self.base_path)

        self.assertEqual(len(page.scanned_files), 4)
        self.assertIsNotNone(page.current_plan)
        self.assertEqual(len(page.current_plan.items), 4)

        # Preview table should have 4 rows
        self.assertEqual(page.preview_table.rowCount(), 4)

        # Distribution summary label should have entries
        self.assertIn("المجلدات التي سيتم إنشاؤها", page.folders_summary_lbl.text())

    def test_change_organization_mode(self):
        page = SmartOrganizePage()
        page.set_directory(self.base_path)

        # Change to extension mode (index 1)
        page.mode_combo.setCurrentIndex(1)
        self.assertEqual(page.current_plan.mode, "extension")

        # Change to academic mode
        academic_idx = page.mode_combo.findData("academic")
        page.mode_combo.setCurrentIndex(academic_idx)
        self.assertEqual(page.current_plan.mode, "academic")
        
        # Check Lecture1_Math.pdf suggested folder
        lecture_item = next((it for it in page.current_plan.items if "Lecture" in it.source_path.name), None)
        self.assertIsNotNone(lecture_item)
        self.assertIn("محاضرات", lecture_item.suggested_folder)

    def test_table_folder_editing(self):
        page = SmartOrganizePage()
        page.set_directory(self.base_path)

        # Column 4 is the suggested folder (editable)
        item = page.preview_table.item(0, 4)
        self.assertIsNotNone(item)
        
        # Manually edit the folder cell
        item.setText("مجلد_مخصص")
        
        # Plan item 0 should be updated
        self.assertEqual(page.current_plan.items[0].suggested_folder, "مجلد_مخصص")

    def test_main_window_navigation_to_organize(self):
        main_win = MainWindow()
        self.assertIsNotNone(main_win.organize_page)

        # Trigger navigation to smart_organize
        main_win.navigate_to("smart_organize")
        self.assertEqual(main_win.stack.currentIndex(), 4)


if __name__ == "__main__":
    unittest.main()
