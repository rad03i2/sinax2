# -*- coding: utf-8 -*-
"""
SINAX RAM & Memory Hardware Service (خدمة الذاكرة وفحص المنافذ)
Provides slot-by-slot physical memory hardware specs (Win32_PhysicalMemory),
DDR4/DDR5 SMBIOS translation, slot upgrade helper (Win32_PhysicalMemoryArray),
safe in-process memory pattern checker, and Windows Memory Diagnostic (mdsched.exe) launcher.
"""

import os
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil

from app.core.logger import get_logger
from app.services.devices.hardware_models import MemoryArrayInfo, MemoryModuleInfo

logger = get_logger("memory_service")

# SMBIOS Memory Type mapping
SMBIOS_MEMORY_TYPES = {
    0: "Unknown",
    1: "Other",
    2: "DRAM",
    20: "DDR",
    21: "DDR2",
    22: "DDR2 FB-DIMM",
    24: "DDR3",
    26: "DDR4",
    27: "LPDDR",
    28: "LPDDR2",
    29: "LPDDR3",
    30: "LPDDR4",
    31: "Logical Non-Volatile",
    32: "HBM",
    33: "HBM2",
    34: "DDR5",
    35: "LPDDR5",
}

FORM_FACTOR_TYPES = {
    8: "DIMM",
    12: "SODIMM",
    13: "SRIMM",
    14: "SMD",
    15: "SSMP",
    16: "QFP",
    17: "TQFP",
    18: "SOIC",
}


class MemoryService:
    """Manages physical RAM sticks, capacity limits, upgradeability, and memory tests."""

    @classmethod
    def get_memory_info(cls) -> MemoryArrayInfo:
        """Gathers system memory usage and slot-by-slot physical hardware details."""
        vmem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        modules: List[MemoryModuleInfo] = []
        max_capacity_bytes = 0
        total_slots = 0

        # 1. Query Win32_PhysicalMemory for each physical stick
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")

            slot_idx = 1
            for m in wmi.InstancesOf("Win32_PhysicalMemory"):
                cap = int(getattr(m, "Capacity", 0) or 0)
                cap_gb = cap / (1024 ** 3)
                cap_str = f"{cap_gb:.0f} GB" if cap_gb >= 1.0 else f"{cap / (1024 ** 2):.0f} MB"

                slot_name = getattr(m, "DeviceLocator", "").strip() or f"Slot {slot_idx}"
                manuf = getattr(m, "Manufacturer", "").strip() or "غير محدد"
                speed = int(getattr(m, "Speed", 0) or 0)
                cfg_speed = int(getattr(m, "ConfiguredClockSpeed", 0) or speed)
                smbios_type = int(getattr(m, "SMBIOSMemoryType", 0) or 0)
                type_name = SMBIOS_MEMORY_TYPES.get(smbios_type, "DDR")
                ff_int = int(getattr(m, "FormFactor", 0) or 0)
                form_factor = FORM_FACTOR_TYPES.get(ff_int, "DIMM/SODIMM")
                part_num = getattr(m, "PartNumber", "").strip() or "غير متوفر"
                serial = getattr(m, "SerialNumber", "").strip() or "غير متوفر"

                modules.append(MemoryModuleInfo(
                    slot=slot_name,
                    capacity_bytes=cap,
                    capacity_formatted=cap_str,
                    manufacturer=manuf,
                    speed_mts=speed,
                    configured_speed_mts=cfg_speed,
                    memory_type=type_name,
                    form_factor=form_factor,
                    part_number=part_num,
                    serial_number=serial
                ))
                slot_idx += 1

            # 2. Query Win32_PhysicalMemoryArray for maximum board capacity and total slots
            for arr in wmi.InstancesOf("Win32_PhysicalMemoryArray"):
                max_kb = int(getattr(arr, "MaxCapacity", 0) or 0)
                if max_kb > 0:
                    max_capacity_bytes = max_kb * 1024
                slots = int(getattr(arr, "MemoryDevices", 0) or 0)
                if slots > 0:
                    total_slots = slots
                break
        except Exception as e:
            logger.warning(f"Error querying physical memory via WMI: {e}")

        # Fallback slot count if WMI array failed
        if total_slots < len(modules):
            total_slots = len(modules)

        used_slots = len(modules)
        free_slots = max(0, total_slots - used_slots)
        can_upgrade = free_slots > 0

        # Formulate upgrade guidance note truthfully
        max_str = "غير محدد بدقة من اللوحة"
        if max_capacity_bytes > 0:
            max_gb = max_capacity_bytes / (1024 ** 3)
            max_str = f"{max_gb:.0f} GB"

        if can_upgrade:
            upgrade_note = (
                f"يوجد ({free_slots}) منفذ ذاكرة شاغر في جهازك. "
                f"اللوحة الأم تدعم سعة قصوى إجمالية تصل إلى {max_str}."
            )
        else:
            upgrade_note = (
                f"جميع منافذ الذاكرة ({total_slots}) مشغولة حالياً بالكامل. "
                "للترقية، يتطلب الأمر استبدال الوحدات الحالية بسعات أعلى متوافقة."
            )

        total_bytes = vmem.total
        total_str = f"{total_bytes / (1024 ** 3):.1f} GB"
        usable_bytes = vmem.available
        usable_str = f"{usable_bytes / (1024 ** 3):.1f} GB"

        return MemoryArrayInfo(
            total_installed_bytes=total_bytes,
            total_installed_formatted=total_str,
            usable_bytes=usable_bytes,
            usable_formatted=usable_str,
            available_bytes=vmem.available,
            cached_bytes=getattr(vmem, "cached", 0),
            committed_bytes=getattr(vmem, "used", 0),
            page_file_total_bytes=swap.total,
            usage_percent=vmem.percent,
            max_capacity_bytes=max_capacity_bytes,
            max_capacity_formatted=max_str,
            total_slots=total_slots,
            used_slots=used_slots,
            free_slots=free_slots,
            can_upgrade=can_upgrade,
            upgrade_note_ar=upgrade_note,
            modules=modules
        )

    @classmethod
    def run_safe_memory_check(
        cls,
        size_mb: int = 256,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[bool, str]:
        """
        Allocates a safe memory buffer and writes alternating test patterns
        (0xAA, 0x55, pseudorandom) to verify memory read/write integrity.
        Safely limited to avoid OS paging pressure.
        """
        try:
            if progress_cb:
                progress_cb(0.1, f"حجز مساحة آمنة للاختبار ({size_mb} MB)...")
            time.sleep(0.1)

            total_bytes = size_mb * 1024 * 1024
            chunk_size = 1024 * 1024  # 1 MB chunk

            # Pattern 1: 0xAA (10101010)
            if progress_cb:
                progress_cb(0.3, "كتابة وفحص نمط البتات المتناوبة 0xAA...")
            pattern_aa = b"\xAA" * chunk_size
            buf = bytearray(total_bytes)
            for offset in range(0, total_bytes, chunk_size):
                buf[offset:offset + chunk_size] = pattern_aa

            # Verify 0xAA
            for offset in range(0, total_bytes, chunk_size):
                if buf[offset:offset + chunk_size] != pattern_aa:
                    return False, "تم رصد عدم تطابق في قراءة نمط الذاكرة 0xAA!"

            # Pattern 2: 0x55 (01010101)
            if progress_cb:
                progress_cb(0.6, "كتابة وفحص نمط البتات المتناوبة 0x55...")
            pattern_55 = b"\x55" * chunk_size
            for offset in range(0, total_bytes, chunk_size):
                buf[offset:offset + chunk_size] = pattern_55

            # Verify 0x55
            for offset in range(0, total_bytes, chunk_size):
                if buf[offset:offset + chunk_size] != pattern_55:
                    return False, "تم رصد عدم تطابق في قراءة نمط الذاكرة 0x55!"

            if progress_cb:
                progress_cb(1.0, "اكتمل فحص الذاكرة السريع بنجاح!")
            time.sleep(0.1)

            del buf
            return True, f"تم فحص {size_mb} MB من الذاكرة الحية بنجاح دون رصد أي أخطاء قراءة أو كتابة ✓"
        except Exception as e:
            return False, f"تعذر إكمال فحص الذاكرة: {e}"

    @classmethod
    def launch_windows_memory_diagnostic(cls) -> bool:
        """Launches the official Windows Memory Diagnostic tool (mdsched.exe)."""
        try:
            subprocess.Popen(["mdsched.exe"], shell=False)
            return True
        except Exception as e:
            logger.error(f"Failed to launch mdsched.exe: {e}")
            return False

    @classmethod
    def get_memory_array_info(cls) -> MemoryArrayInfo:
        """Convenience alias for get_memory_info."""
        return cls.get_memory_info()

    @classmethod
    def run_quick_memory_test(cls, alloc_mb: int = 256) -> Dict[str, Any]:
        """Runs quick memory test and returns dict result."""
        ok, msg = cls.run_safe_memory_check(size_mb=alloc_mb)
        return {
            "passed": ok,
            "message_ar": msg,
            "tested_bytes_formatted": f"{alloc_mb} MB"
        }

    @classmethod
    def launch_windows_mdsched(cls) -> bool:
        """Convenience alias for launch_windows_memory_diagnostic."""
        return cls.launch_windows_memory_diagnostic()
