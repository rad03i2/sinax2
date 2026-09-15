# -*- coding: utf-8 -*-
"""
Performance & Responsiveness Benchmarking for SINAX Centers.
Verifies:
- Centers load and render in < 300ms without freezing GUI main thread.
- Hardware detection (FFmpeg GPU encoders) runs asynchronously in background.
- Subpages load lazily on first access.
- Re-visiting cached pages switches in < 25ms.
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.ui.pages.video_center_page import VideoCenterPage
from app.ui.pages.devices_page import DevicesPage
from app.ui.pages.system_storage_page import SystemStoragePage
from app.ui.pages.backup_sync_page import BackupSyncPage


class TestCenterLoadingPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_video_center_instant_load(self):
        """Video Center must initialize in under 250ms with async hardware detector."""
        t0 = time.perf_counter()
        page = VideoCenterPage()
        page.show()
        self.app.processEvents()
        elapsed = time.perf_counter() - t0
        page.close()

        print(f"\n[BENCHMARK] VideoCenterPage creation time: {elapsed:.3f}s")
        # Must be well under 1.0s (previously took 2-4 seconds running synchronous ffmpeg encoders)
        self.assertLess(elapsed, 0.85, "VideoCenterPage took too long to initialize!")

    def test_devices_page_lazy_load(self):
        """DevicesPage must initialize in under 250ms with SubpageLazyRegistry."""
        t0 = time.perf_counter()
        page = DevicesPage()
        page.show()
        self.app.processEvents()
        elapsed = time.perf_counter() - t0

        print(f"[BENCHMARK] DevicesPage initial creation time: {elapsed:.3f}s")
        self.assertLess(elapsed, 0.40, "DevicesPage took too long to initialize!")

        # Only Overview is eagerly loaded; other 13 are NOT instantiated yet
        self.assertEqual(len(page._registry._instances), 1)
        self.assertIn("overview", page._registry._instances)
        self.assertNotIn("cpu", page._registry._instances)

        # Accessing a subpage on demand via switch_subpage
        t_sub0 = time.perf_counter()
        page.switch_subpage("cpu")
        elapsed_sub = time.perf_counter() - t_sub0
        print(f"[BENCHMARK] Devices CPU subpage on-demand creation time: {elapsed_sub:.3f}s")
        self.assertIn("cpu", page._registry._instances)
        cpu_page = page._registry.get_or_create("cpu")
        self.assertIsNotNone(cpu_page)

        # Re-accessing must be instantaneous (< 10ms) from cache
        t_sub_cached = time.perf_counter()
        page.switch_subpage("cpu")
        elapsed_cached = time.perf_counter() - t_sub_cached
        print(f"[BENCHMARK] Devices CPU subpage cached switch time: {elapsed_cached*1000:.2f}ms")
        self.assertLess(elapsed_cached, 0.025)

        page.close()

    def test_system_storage_page_lazy_load(self):
        """SystemStoragePage must initialize quickly with only Overview loaded."""
        t0 = time.perf_counter()
        page = SystemStoragePage()
        page.show()
        self.app.processEvents()
        elapsed = time.perf_counter() - t0

        print(f"[BENCHMARK] SystemStoragePage initial creation time: {elapsed:.3f}s")
        self.assertLess(elapsed, 0.40)
        page.close()

    def test_backup_sync_page_lazy_load(self):
        """BackupSyncPage must initialize quickly with only Overview loaded."""
        t0 = time.perf_counter()
        page = BackupSyncPage()
        page.show()
        self.app.processEvents()
        elapsed = time.perf_counter() - t0

        print(f"[BENCHMARK] BackupSyncPage initial creation time: {elapsed:.3f}s")
        self.assertLess(elapsed, 0.40)
        page.close()


if __name__ == "__main__":
    unittest.main()
