# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.transfer_service import TransferService, TransferPlan


class TestTransferService(unittest.TestCase):
    def setUp(self):
        self.src_dir = Path(tempfile.mkdtemp())
        self.dst_dir = Path(tempfile.mkdtemp())

        # Create source files
        (self.src_dir / "report.pdf").write_bytes(b"PDF data 1")
        (self.src_dir / "data.csv").write_bytes(b"col1,col2\n1,2\n")

    def tearDown(self):
        shutil.rmtree(self.src_dir, ignore_errors=True)
        shutil.rmtree(self.dst_dir, ignore_errors=True)

    def test_batch_copy_auto_rename(self):
        # Pre-create conflicting file in destination
        (self.dst_dir / "report.pdf").write_bytes(b"Existing old report")

        sources = [self.src_dir / "report.pdf", self.src_dir / "data.csv"]
        plan = TransferService.generate_plan(sources, self.dst_dir, action_type="copy", collision_policy="rename")

        # The conflicting report.pdf should be renamed to report (1).pdf
        report_item = next(it for it in plan.items if it.source_path.name == "report.pdf")
        self.assertEqual(report_item.target_path.name, "report (1).pdf")

        success, skipped, failed = TransferService.execute_plan(plan)
        self.assertEqual(success, 2)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

        # Source files should still exist for copy
        self.assertTrue((self.src_dir / "report.pdf").exists())
        self.assertTrue((self.dst_dir / "report (1).pdf").exists())

    def test_batch_move(self):
        sources = [self.src_dir / "data.csv"]
        plan = TransferService.generate_plan(sources, self.dst_dir, action_type="move", collision_policy="rename")

        success, skipped, failed = TransferService.execute_plan(plan)
        self.assertEqual(success, 1)

        # Source file should no longer exist after move
        self.assertFalse((self.src_dir / "data.csv").exists())
        self.assertTrue((self.dst_dir / "data.csv").exists())


if __name__ == "__main__":
    unittest.main()
