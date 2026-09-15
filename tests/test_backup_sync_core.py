# -*- coding: utf-8 -*-
"""
Core Unit Tests for SINAX Backup & Sync Services.
"""

import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest

from app.services.backup_sync.models import (
    BackupJob,
    BackupProfile,
    BackupSnapshot,
    BackupType,
    ConflictResolution,
    IncrementalMode,
    RetentionPolicy,
    SyncMode,
    SyncPair,
    VerificationLevel,
)
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.copy_engine import CopyEngine
from app.services.backup_sync.incremental_detector import IncrementalDetector
from app.services.backup_sync.known_folders_service import KnownFoldersService
from app.services.backup_sync.physical_disk_service import PhysicalDiskService
from app.services.backup_sync.restore_drill_service import RestoreDrillService
from app.services.backup_sync.restore_service import RestoreService
from app.services.backup_sync.retention_service import RetentionService
from app.services.backup_sync.sync_engine import SyncEngine
from app.services.backup_sync.verification_service import VerificationService
from app.services.backup_sync.versioning_service import VersioningService
from app.services.backup_sync.backup_index_service import BackupIndexService
from app.services.backup_sync.backup_coordinator import BackupCoordinator


class TestBackupSyncCore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sinax_test_bs_")
        self.db_path = os.path.join(self.temp_dir, "test_bs.db")
        self.db = BackupDatabase(self.db_path)

        # Create source and destination directories
        self.src_dir = os.path.join(self.temp_dir, "source")
        self.dst_dir = os.path.join(self.temp_dir, "destination")
        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.dst_dir, exist_ok=True)

        # Create sample files
        self.file1 = os.path.join(self.src_dir, "doc1.txt")
        self.file2 = os.path.join(self.src_dir, "doc2.txt")
        with open(self.file1, "w", encoding="utf-8") as f:
            f.write("Hello World SINAX Backup Test")
        with open(self.file2, "w", encoding="utf-8") as f:
            f.write("Important Financial Records 2026")

    def tearDown(self):
        BackupDatabase._instances.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_known_folders_discovery(self):
        folders = KnownFoldersService.get_known_folders()
        self.assertGreaterEqual(len(folders), 5)
        keys = [f.key for f in folders]
        self.assertIn("desktop", keys)
        self.assertIn("documents", keys)
        self.assertIn("pictures", keys)

    def test_physical_disk_and_preflight(self):
        preflight = PhysicalDiskService.perform_preflight_check([self.src_dir], self.dst_dir)
        self.assertTrue(preflight.is_valid)
        # Check drive letters
        letter = PhysicalDiskService.get_drive_letter(self.src_dir)
        self.assertTrue(letter.endswith(":"))

    def test_streaming_copy_and_atomic_rename(self):
        dst_file = os.path.join(self.dst_dir, "doc1.txt")
        ok, err = CopyEngine.copy_file_safe(self.file1, dst_file)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(dst_file))
        with open(dst_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "Hello World SINAX Backup Test")
        # Ensure partial file does not exist
        partial = os.path.join(self.dst_dir, ".doc1.txt.sinaxpartial")
        self.assertFalse(os.path.exists(partial))

    def test_incremental_change_detection(self):
        scanned = IncrementalDetector.scan_directory(self.src_dir)
        self.assertEqual(len(scanned), 2)
        self.assertIn("doc1.txt", scanned)

        # Initial diff against empty versions -> both are new
        diff = IncrementalDetector.detect_changes(scanned, {})
        self.assertEqual(len(diff.new_files), 2)
        self.assertEqual(len(diff.modified_files), 0)

    def test_full_and_incremental_backup_pipeline(self):
        profile = BackupProfile(
            id="prof_test_1",
            name="Test Documents",
            sources=[self.src_dir],
            destination=self.dst_dir,
            backup_type=BackupType.INCREMENTAL,
            incremental_mode=IncrementalMode.FAST
        )
        self.db.save_profile(profile)

        coord = BackupCoordinator(self.db)
        # 1. Run Initial Backup
        job1 = coord.run_backup(profile)
        self.assertEqual(job1.status.value, "completed")
        self.assertEqual(job1.files_copied, 2)
        self.assertTrue(os.path.exists(os.path.join(self.dst_dir, "doc1.txt")))

        # 2. Modify one file and add a new file
        time.sleep(1.1)  # Ensure mtime diff
        with open(self.file1, "a", encoding="utf-8") as f:
            f.write("\nAppended modification line")
        new_file = os.path.join(self.src_dir, "doc3.txt")
        with open(new_file, "w", encoding="utf-8") as f:
            f.write("Third file content")

        # Run Incremental Backup
        job2 = coord.run_backup(profile)
        self.assertEqual(job2.status.value, "completed")
        self.assertEqual(job2.files_copied, 1)    # doc3.txt is new
        self.assertEqual(job2.files_updated, 1)   # doc1.txt was updated

        # Verify old version of doc1.txt was archived in .sinax_versions
        ver_dir = os.path.join(self.dst_dir, ".sinax_versions")
        self.assertTrue(os.path.exists(ver_dir))
        archived_files = os.listdir(ver_dir)
        self.assertGreaterEqual(len(archived_files), 1)

    def test_restore_and_collision_keep_both(self):
        # Setup backup
        dst_file = os.path.join(self.dst_dir, "doc1.txt")
        CopyEngine.copy_file_safe(self.file1, dst_file)

        # Attempt restore to src_dir where doc1.txt already exists
        restore_path = RestoreService.resolve_destination_path(self.src_dir, "doc1.txt", collision_policy="keep_both")
        self.assertNotEqual(restore_path, self.file1)
        self.assertIn("restored", restore_path)

    def test_restore_drill_sample(self):
        profile = BackupProfile(
            id="prof_drill",
            name="Drill Profile",
            sources=[self.src_dir],
            destination=self.dst_dir
        )
        self.db.save_profile(profile)
        coord = BackupCoordinator(self.db)
        coord.run_backup(profile)

        drill = RestoreDrillService(self.db)
        res = drill.run_drill(profile.id, sample_size=5)
        self.assertTrue(res.is_healthy)
        self.assertEqual(res.passed_count, 2)
        self.assertEqual(res.failed_count, 0)

    def test_two_way_sync_and_conflicts(self):
        side_a = os.path.join(self.temp_dir, "side_a")
        side_b = os.path.join(self.temp_dir, "side_b")
        os.makedirs(side_a, exist_ok=True)
        os.makedirs(side_b, exist_ok=True)

        file_a = os.path.join(side_a, "shared.txt")
        with open(file_a, "w", encoding="utf-8") as f:
            f.write("Original A")

        pair = SyncPair(
            id="pair_1",
            name="Sync Pair",
            side_a=side_a,
            side_b=side_b,
            mode=SyncMode.TWO_WAY
        )
        self.db.save_sync_pair(pair)

        engine = SyncEngine(self.db)
        ok, msg = engine.execute_sync(pair)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(os.path.join(side_b, "shared.txt")))

    def test_retention_never_destroy_last_good(self):
        profile = BackupProfile(
            id="prof_retention",
            name="Retention Profile",
            sources=[self.src_dir],
            destination=self.dst_dir,
            retention=RetentionPolicy(keep_last_n=1, keep_days=1)
        )
        self.db.save_profile(profile)

        coord = BackupCoordinator(self.db)
        coord.run_backup(profile)

        ret_service = RetentionService(self.db)
        preview = ret_service.evaluate_retention(profile)
        # Should keep the only good snapshot and not prune it
        self.assertEqual(len(preview.snapshots_to_prune), 0)

    def test_emergency_index_rebuild(self):
        # Run a backup
        profile = BackupProfile(
            id="prof_idx",
            name="Index Profile",
            sources=[self.src_dir],
            destination=self.dst_dir
        )
        self.db.save_profile(profile)
        coord = BackupCoordinator(self.db)
        coord.run_backup(profile)

        # Simulate fresh database without this profile
        new_db_path = os.path.join(self.temp_dir, "fresh.db")
        new_db = BackupDatabase(new_db_path)
        index_service = BackupIndexService(new_db)

        ok, count, msg = index_service.rebuild_index_from_destination(self.dst_dir)
        self.assertTrue(ok)
        self.assertGreaterEqual(count, 2)
        profiles = new_db.list_profiles()
        self.assertEqual(len(profiles), 1)


if __name__ == "__main__":
    unittest.main()
