# -*- coding: utf-8 -*-
"""
Tests for System & Storage Services (Phase 10)
"""

import os
import tempfile
import unittest

from app.services.system_storage.cleanup_service import CleanupService
from app.services.system_storage.device_info_service import DeviceInfoService
from app.services.system_storage.disk_health_service import DiskHealthService
from app.services.system_storage.performance_service import PerformanceService
from app.services.system_storage.process_service import ProcessService
from app.services.system_storage.recommendation_engine import RecommendationEngine
from app.services.system_storage.snapshot_service import SnapshotService
from app.services.system_storage.storage_analyzer import StorageAnalyzer
from app.services.system_storage.storage_scanner import FastStorageScanner, format_bytes
from app.services.system_storage.startup_service import StartupService


class TestSystemStorageServices(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = self.temp_dir.name

        # Create test file structure
        self.img_dir = os.path.join(self.root_path, "Images")
        os.makedirs(self.img_dir, exist_ok=True)
        with open(os.path.join(self.img_dir, "pic1.png"), "wb") as f:
            f.write(b"0" * 1024 * 10)  # 10 KB

        self.doc_dir = os.path.join(self.root_path, "Docs")
        os.makedirs(self.doc_dir, exist_ok=True)
        with open(os.path.join(self.doc_dir, "doc1.pdf"), "wb") as f:
            f.write(b"0" * 1024 * 50)  # 50 KB

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fast_storage_scanner(self):
        scanner = FastStorageScanner(cluster_size=4096)
        result = scanner.scan(self.root_path)

        self.assertIsNotNone(result)
        self.assertEqual(result.total_files, 2)
        self.assertGreaterEqual(result.total_size, 60 * 1024)
        self.assertGreaterEqual(result.allocated_size, result.total_size)
        self.assertEqual(len(result.top_files), 2)
        self.assertEqual(result.top_files[0].name, "doc1.pdf")

    def test_storage_analyzer(self):
        scanner = FastStorageScanner(cluster_size=4096)
        result = scanner.scan(self.root_path)
        report = StorageAnalyzer.analyze_scan_result(result)

        self.assertEqual(report.total_files, 2)
        self.assertIn("images", report.categories)
        self.assertIn("documents", report.categories)
        self.assertGreater(report.categories["images"].size, 0)
        self.assertGreater(report.categories["documents"].size, 0)
        self.assertEqual(len(report.age_distribution), 4)

    def test_cleanup_service_protection_and_query(self):
        # Protected path check
        self.assertTrue(CleanupService.is_protected_path(r"C:\Windows\System32"))
        self.assertTrue(CleanupService.is_protected_path(r"C:\Program Files"))
        self.assertFalse(CleanupService.is_protected_path(self.root_path))

        # Recycle bin query shouldn't crash
        size, count = CleanupService.query_recycle_bin()
        self.assertIsInstance(size, int)
        self.assertIsInstance(count, int)

        # Simulation cleanup
        targets = CleanupService.get_cleanup_targets()
        self.assertGreater(len(targets), 0)

    def test_disk_health_and_logical_drives(self):
        drives = DiskHealthService.get_logical_drives()
        self.assertGreater(len(drives), 0)
        c_drive = next((d for d in drives if "C:" in d.drive_letter), None)
        self.assertIsNotNone(c_drive)
        self.assertGreater(c_drive.total_bytes, 0)

        # IO rate calculation
        rates = DiskHealthService.get_live_io_rates()
        self.assertIn("read_mb_s", rates)
        self.assertIn("write_mb_s", rates)

    def test_performance_service(self):
        perf = PerformanceService(history_len=10)
        snap = perf.sample()
        self.assertIsNotNone(snap)
        self.assertGreaterEqual(snap.cpu_percent, 0.0)
        self.assertGreater(snap.ram_total, 0)

        hist = perf.get_history()
        self.assertIn("cpu", hist)
        self.assertIn("ram", hist)
        self.assertEqual(len(hist["cpu"]), 1)

    def test_process_service_and_guard(self):
        procs = ProcessService.list_processes()
        self.assertGreater(len(procs), 0)

        # Guard critical processes
        ok, msg = ProcessService.terminate_process(0)
        self.assertFalse(ok)
        self.assertIn("محمية", msg)

        # Guard SINAX itself
        ok, msg = ProcessService.terminate_process(os.getpid())
        self.assertFalse(ok)

    def test_startup_service(self):
        items = StartupService.list_startup_items()
        self.assertIsInstance(items, list)
        for item in items:
            self.assertIsInstance(item.name, str)
            self.assertIsInstance(item.is_enabled, bool)

    def test_device_info_service(self):
        specs = DeviceInfoService.get_system_specs()
        self.assertIsNotNone(specs.os_name)
        self.assertIsNotNone(specs.cpu_name)
        self.assertGreater(specs.ram_total_bytes, 0)

    def test_snapshot_service(self):
        scanner = FastStorageScanner(cluster_size=4096)
        result = scanner.scan(self.root_path)
        report = StorageAnalyzer.analyze_scan_result(result)

        snap_id = SnapshotService.save_snapshot(report)
        self.assertGreater(snap_id, 0)

        snap = SnapshotService.get_snapshot(snap_id)
        self.assertIsNotNone(snap)
        self.assertEqual(snap["total_files"], 2)

    def test_recommendation_engine(self):
        cards = RecommendationEngine.evaluate_system()
        self.assertIsInstance(cards, list)


if __name__ == "__main__":
    unittest.main()
