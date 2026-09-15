# -*- coding: utf-8 -*-
"""
Unit test suite for SINAX Devices & Hardware Center (Phase 13).
Tests all 12 backend services, data models, persistence, and reporting.
"""

import os
import tempfile
import unittest

from app.services.devices.battery_service import BatteryService
from app.services.devices.cpu_service import CpuService
from app.services.devices.display_service import DisplayService
from app.services.devices.driver_service import DriverService
from app.services.devices.gpu_service import GpuService
from app.services.devices.hardware_models import (
    BatteryDetails,
    BiosInfo,
    CpuInfo,
    GpuInfo,
    MemoryArrayInfo,
    MotherboardInfo,
    PnpDeviceInfo,
    StorageDeviceInfo,
    SystemSummary,
    UsbDeviceInfo,
    WindowsDetails,
)
from app.services.devices.hardware_report_service import HardwareReportService
from app.services.devices.hardware_test_service import HardwareTestService
from app.services.devices.memory_service import MemoryService
from app.services.devices.motherboard_bios_service import MotherboardBiosService
from app.services.devices.sensor_service import SensorService
from app.services.devices.storage_hardware_service import StorageHardwareService
from app.services.devices.usb_service import UsbService
from app.services.devices.windows_info_service import WindowsInfoService


class TestDevicesCore(unittest.TestCase):
    """Verifies core hardware services and truthful non-fake outputs."""

    def test_01_cpu_service(self):
        cpu = CpuService.get_cpu_info()
        self.assertIsInstance(cpu, CpuInfo)
        self.assertTrue(len(cpu.name) > 0)
        self.assertGreaterEqual(cpu.cores_physical, 1)
        self.assertGreaterEqual(cpu.cores_logical, 1)

        # History buffer
        history = CpuService.get_cpu_history()
        self.assertIsInstance(history, list)
        self.assertGreaterEqual(len(history), 1)

    def test_02_gpu_service(self):
        gpus = GpuService.get_gpu_list()
        self.assertIsInstance(gpus, list)
        self.assertGreater(len(gpus), 0)
        primary = gpus[0]
        self.assertIsInstance(primary, GpuInfo)
        self.assertTrue(len(primary.name) > 0)

        # Live metrics
        live = GpuService.get_gpu_live_metrics(primary.id)
        self.assertIsInstance(live, dict)

    def test_03_memory_service(self):
        ram = MemoryService.get_memory_array_info()
        self.assertIsInstance(ram, MemoryArrayInfo)
        self.assertGreater(ram.total_installed_bytes, 0)
        self.assertGreater(ram.total_slots, 0)
        self.assertGreaterEqual(ram.used_slots, 1)
        self.assertIsInstance(ram.modules, list)

        # Quick in-process pattern check
        quick_res = MemoryService.run_quick_memory_test(alloc_mb=32)
        self.assertIn("passed", quick_res)
        self.assertTrue(quick_res["passed"])

    def test_04_motherboard_bios_service(self):
        mb = MotherboardBiosService.get_motherboard_info()
        self.assertIsInstance(mb, MotherboardInfo)
        self.assertTrue(len(mb.manufacturer) > 0)

        bios = MotherboardBiosService.get_bios_info()
        self.assertIsInstance(bios, BiosInfo)
        self.assertIn(bios.bios_mode, ["UEFI", "Legacy"])

    def test_05_storage_hardware_service(self):
        disks = StorageHardwareService.get_physical_disks(mask_serial=False)
        self.assertIsInstance(disks, list)
        self.assertGreater(len(disks), 0)
        disk = disks[0]
        self.assertIsInstance(disk, StorageDeviceInfo)
        self.assertGreater(disk.capacity_bytes, 0)

        # Mask serial check
        disks_masked = StorageHardwareService.get_physical_disks(mask_serial=True)
        if disks[0].serial_number and disks[0].serial_number != "غير متوفر":
            self.assertTrue("•" in disks_masked[0].serial_number or "*" in disks_masked[0].serial_number)

    def test_06_battery_service(self):
        bat = BatteryService.get_battery_details()
        self.assertIsInstance(bat, BatteryDetails)
        # Should gracefully return present=True or False without raising
        if bat.present:
            self.assertGreaterEqual(bat.charge_percent, 0)
            self.assertLessEqual(bat.charge_percent, 100)

    def test_07_display_service(self):
        monitors = DisplayService.get_monitors()
        self.assertIsInstance(monitors, list)
        self.assertGreater(len(monitors), 0)
        mon = monitors[0]
        self.assertGreater(mon.width_pixels, 0)
        self.assertGreater(mon.height_pixels, 0)

    def test_08_usb_service(self):
        devs = UsbService.get_usb_devices(only_connected=True)
        self.assertIsInstance(devs, list)
        # Safe eject test with non-existent instance returns safe failure
        eject_res = UsbService.eject_usb_device("NON_EXISTENT_INSTANCE_ID")
        self.assertFalse(eject_res["success"])

    def test_09_driver_service(self):
        tree = DriverService.get_pnp_tree()
        self.assertIsInstance(tree, dict)
        self.assertGreater(len(tree), 0)

        probs = DriverService.get_problem_devices()
        self.assertIsInstance(probs, list)

    def test_10_sensor_service(self):
        sensors = SensorService.get_all_sensors()
        self.assertIsInstance(sensors, list)
        self.assertGreater(len(sensors), 0)
        provider = SensorService.get_active_provider_name()
        self.assertTrue(len(provider) > 0)

    def test_11_windows_info_service(self):
        win = WindowsInfoService.get_windows_details()
        self.assertIsInstance(win, WindowsDetails)
        self.assertTrue("Windows" in win.edition)
        self.assertTrue(len(win.build) > 0)

    def test_12_hardware_test_service(self):
        stages_visited = []
        def on_prog(name, pct):
            stages_visited.append((name, pct))

        results = HardwareTestService.run_full_check(progress_cb=on_prog)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 9)
        self.assertGreaterEqual(len(stages_visited), 9)

    def test_13_hardware_report_and_snapshots(self):
        summary = HardwareReportService.get_system_summary()
        self.assertIsInstance(summary, SystemSummary)

        # Snapshot
        snap = HardwareReportService.save_snapshot(name="Unit Test Snapshot")
        self.assertIsNotNone(snap)
        snapshots = HardwareReportService.list_snapshots()
        self.assertGreater(len(snapshots), 0)

        # Export test
        with tempfile.TemporaryDirectory() as td:
            out_html = os.path.join(td, "report.html")
            ok_html = HardwareReportService.export_report(fmt="html", destination_path=out_html)
            self.assertTrue(ok_html)
            self.assertTrue(os.path.exists(out_html))
            self.assertGreater(os.path.getsize(out_html), 100)

            out_json = os.path.join(td, "report.json")
            ok_json = HardwareReportService.export_report(fmt="json", destination_path=out_json)
            self.assertTrue(ok_json)
            self.assertTrue(os.path.exists(out_json))


if __name__ == "__main__":
    unittest.main()
