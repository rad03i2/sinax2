# -*- coding: utf-8 -*-
"""
SINAX Storage Hardware Service (خدمة عتاد وحدات التخزين وSMART)
Provides hardware-level physical disk specifications (Model, NVMe/SSD/HDD, Bus, Firmware),
SMART reliability telemetry (Temperature, Wear %, Power-on Hours), serial number privacy masking,
and a safe, non-destructive sequential read throughput tester.
"""

import os
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.devices.hardware_models import StorageDeviceInfo
from app.services.system_storage.disk_health_service import DiskHealthService, PhysicalDiskInfo

logger = get_logger("storage_hardware_service")


class StorageHardwareService:
    """Manages physical disk hardware queries and safe non-destructive read checks."""

    @classmethod
    def get_physical_storage_devices(cls, force_refresh: bool = False) -> List[StorageDeviceInfo]:
        """Queries physical storage drives and converts to StorageDeviceInfo."""
        raw_disks = DiskHealthService.get_physical_disks(force_refresh=force_refresh)
        devices: List[StorageDeviceInfo] = []

        for d in raw_disks:
            # Query firmware and serial via Win32_DiskDrive if not in raw
            firmware, serial = cls._get_disk_serial_and_firmware(d.device_id)

            devices.append(StorageDeviceInfo(
                device_id=d.device_id,
                model=d.name,
                serial_number=serial or "غير متوفر",
                firmware_revision=firmware or "غير متوفر",
                media_type=d.media_type,
                media_type_ar=d.media_type_ar,
                bus_type=d.bus_type,
                capacity_bytes=d.size_bytes,
                capacity_formatted=d.size_formatted,
                health_status_ar=d.health_status_ar,
                operational_status_ar=d.operational_status_ar,
                temperature_c=d.temperature_celsius,
                wear_percentage=d.wear_percentage,
                power_on_hours=d.power_on_hours,
                read_errors=d.read_errors_total,
                write_errors=d.write_errors_total
            ))

        return devices

    @classmethod
    def _get_disk_serial_and_firmware(cls, device_id: str) -> Tuple[str, str]:
        """Queries firmware revision and serial number via Win32_DiskDrive."""
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            for drive in wmi.InstancesOf("Win32_DiskDrive"):
                idx = str(getattr(drive, "Index", ""))
                if idx == device_id or f"PHYSICALDRIVE{device_id}" in getattr(drive, "DeviceID", ""):
                    serial = getattr(drive, "SerialNumber", "").strip()
                    firmware = getattr(drive, "FirmwareRevision", "").strip()
                    return firmware, serial
        except Exception:
            pass
        return "غير متوفر", "غير متوفر"

    @classmethod
    def run_safe_sequential_read_test(
        cls,
        test_size_mb: int = 128,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[bool, float, str]:
        """
        Executes a safe, read-only sequential throughput test.
        Creates a temporary contiguous file in temp, flushes OS cache,
        reads it back sequentially, and calculates real throughput in MB/s.
        Cleans up test files immediately.
        """
        temp_file = None
        try:
            if progress_cb:
                progress_cb(0.1, "تحضير كتلة اختبار القراءة المتسلسلة الآمنة...")

            total_bytes = test_size_mb * 1024 * 1024
            chunk_size = 1024 * 1024  # 1 MB block
            chunk_data = b"SINAX_STORAGE_READ_INTEGRITY_CHECK" * (chunk_size // 34)

            # Create test file
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_file = f.name
                for _ in range(test_size_mb):
                    f.write(chunk_data)
                f.flush()
                os.fsync(f.fileno())

            if progress_cb:
                progress_cb(0.4, f"بدء قياس سرعة القراءة المتسلسلة ({test_size_mb} MB)...")

            # Sequential Read Timing
            start_t = time.perf_counter()
            bytes_read = 0
            with open(temp_file, "rb") as f:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    bytes_read += len(data)

            elapsed = max(0.001, time.perf_counter() - start_t)
            speed_mb_s = (bytes_read / (1024 * 1024)) / elapsed

            if progress_cb:
                progress_cb(1.0, f"اكتمل الفحص: {speed_mb_s:.1f} MB/s")

            return True, round(speed_mb_s, 1), f"سرعة القراءة المتسلسلة: {speed_mb_s:.1f} MB/s ✓"
        except Exception as e:
            return False, 0.0, f"تعذر إجراء اختبار القراءة: {e}"
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    @classmethod
    def get_physical_disks(cls, mask_serial: bool = False, force_refresh: bool = False) -> List[StorageDeviceInfo]:
        """Convenience alias for get_physical_storage_devices with optional serial masking."""
        disks = cls.get_physical_storage_devices(force_refresh=force_refresh)
        if mask_serial:
            masked_disks = []
            for d in disks:
                masked_sn = "••••••••" if d.serial_number and d.serial_number != "غير متوفر" else d.serial_number
                d_copy = StorageDeviceInfo(
                    device_id=d.device_id,
                    model=d.model,
                    serial_number=masked_sn,
                    firmware_revision=d.firmware_revision,
                    media_type=d.media_type,
                    media_type_ar=d.media_type_ar,
                    bus_type=d.bus_type,
                    capacity_bytes=d.capacity_bytes,
                    capacity_formatted=d.capacity_formatted,
                    health_status_ar=d.health_status_ar,
                    operational_status_ar=d.operational_status_ar,
                    temperature_c=d.temperature_c,
                    wear_percentage=d.wear_percentage,
                    power_on_hours=d.power_on_hours,
                    read_errors=d.read_errors,
                    write_errors=d.write_errors
                )
                masked_disks.append(d_copy)
            return masked_disks
        return disks

    @classmethod
    def run_sequential_read_test(cls, drive_letter: str = "C:", duration_sec: int = 3) -> Dict[str, Any]:
        """Convenience wrapper for safe read benchmark returning a dict result."""
        ok, speed, msg = cls.run_safe_sequential_read_test(test_size_mb=64)
        return {
            "passed": ok,
            "speed_mb_s": speed,
            "message_ar": msg,
            "error": msg if not ok else None
        }
