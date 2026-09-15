# -*- coding: utf-8 -*-
"""
Test SINAX Backup & Sync Center UI Page & Subpages.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.pages.backup_sync_page import BackupSyncPage
from app.ui.themes.theme_manager import theme_manager


class TestBackupSyncUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_backup_sync_subpages(self):
        theme_manager.apply_theme("dark")
        page = BackupSyncPage()
        page.show()

        # Check that all 11 subpages exist in stack
        self.assertEqual(page.stack.count(), 11)

        subpages = [
            "overview",
            "wizard",
            "quick_backup",
            "before_format",
            "sync",
            "restore",
            "versions",
            "health_drill",
            "destinations",
            "schedules",
            "history_reports",
        ]

        for idx, key in enumerate(subpages):
            page.switch_subpage(key)
            self.assertEqual(page.stack.currentIndex(), idx)
            self.assertTrue(page._buttons[key].isChecked())

        page.close()
        page.deleteLater()

    def test_backup_sync_dialogs(self):
        from app.ui.pages.backup_sync.dialogs.backup_progress_dialog import BackupProgressDialog
        from app.ui.pages.backup_sync.dialogs.dry_run_preview_dialog import DryRunPreviewDialog
        from app.ui.pages.backup_sync.dialogs.conflict_resolution_dialog import ConflictResolutionDialog
        from app.ui.pages.backup_sync.dialogs.restore_collision_dialog import RestoreCollisionDialog
        from app.services.backup_sync.models import ConflictResolution, SyncConflict
        from app.services.backup_sync.sync_engine import SyncDryRunReport

        # 1. Progress dialog
        prog = BackupProgressDialog(title="نسخ تجريبي")
        prog.update_progress("فحص الملفات", 5, 10, "ملف_تجريبي.txt")
        self.assertEqual(prog.lbl_stage.text(), "فحص الملفات")
        prog.close()

        # 2. Dry run preview
        from app.services.backup_sync.models import SyncMode
        from app.services.backup_sync.sync_engine import SyncActionItem
        rep = SyncDryRunReport(
            pair_id="pair_1",
            mode=SyncMode.TWO_WAY,
            to_copy_a_to_b=[SyncActionItem(action="copy_a_to_b", relative_path="a.txt", size_bytes=100, reason="New file")],
            to_copy_b_to_a=[],
            to_delete=[SyncActionItem(action="delete_b", relative_path="b.txt", size_bytes=200, reason="Deleted from source")],
            conflicts=[]
        )
        dry = DryRunPreviewDialog(rep)
        self.assertIsNotNone(dry)
        dry.close()

        # 3. Conflict resolution dialog
        conf_dlg = ConflictResolutionDialog("c:/source/doc.txt", "d:/dest/doc.txt")
        self.assertIsNotNone(conf_dlg)
        self.assertEqual(conf_dlg.selected_resolution, ConflictResolution.KEEP_BOTH)
        conf_dlg.close()

        # 4. Restore collision dialog
        coll_dlg = RestoreCollisionDialog("restored.txt", "c:/data/restored.txt")
        self.assertIsNotNone(coll_dlg)
        self.assertEqual(coll_dlg.selected_policy, "keep_both")
        coll_dlg.close()


if __name__ == "__main__":
    unittest.main()
