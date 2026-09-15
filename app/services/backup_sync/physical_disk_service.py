# -*- coding: utf-8 -*-
"""
SINAX Physical Disk & Destination Analyzer.
Accurately discovers physical disk number (Disk #0, Disk #1) for drives, detects if
source and destination share the same physical drive (preventing false security),
inspects FAT32 file system limitations (files > 4GB), and verifies free space.
"""

import ctypes
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

import psutil
from app.core.logger import get_logger
from app.services.backup_sync.models import PreflightCheckResult

logger = get_logger("physical_disk_service")


class PhysicalDiskService:
    """Detects underlying physical disks and performs preflight filesystem checks."""

    _disk_map_cache: Optional[Dict[str, int]] = None

    @classmethod
    def get_drive_letter(cls, path: str) -> str:
        """Extracts upper-case drive letter like 'C:' from any path."""
        p = os.path.abspath(path)
        drive = os.path.splitdrive(p)[0].upper()
        return drive if drive else "C:"

    @classmethod
    def get_physical_disk_number(cls, path: str) -> Optional[int]:
        """Resolves drive letter to physical disk number (e.g. C: -> Disk 0)."""
        drive = cls.get_drive_letter(path).replace(":", "")
        if not drive:
            return None

        # Check cached mapping
        if cls._disk_map_cache and drive in cls._disk_map_cache:
            return cls._disk_map_cache[drive]

        cls._refresh_disk_mapping()
        if cls._disk_map_cache and drive in cls._disk_map_cache:
            return cls._disk_map_cache[drive]

        return None

    @classmethod
    def _refresh_disk_mapping(cls):
        """Builds drive letter -> disk number dictionary via PowerShell or WMI."""
        cls._disk_map_cache = {}
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-Partition | Select-Object DriveLetter, DiskNumber | ConvertTo-Json"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    letter = str(item.get("DriveLetter", "")).strip().upper()
                    disk_num = item.get("DiskNumber")
                    if letter and disk_num is not None:
                        cls._disk_map_cache[letter] = int(disk_num)
        except Exception as e:
            logger.debug(f"PowerShell partition lookup failed: {e}")

    @classmethod
    def is_same_physical_disk(cls, source_path: str, dest_path: str) -> Tuple[bool, Optional[int]]:
        """Checks if source and destination reside on the same physical drive."""
        src_drive = cls.get_drive_letter(source_path)
        dst_drive = cls.get_drive_letter(dest_path)

        if src_drive == dst_drive:
            disk_num = cls.get_physical_disk_number(source_path)
            return True, disk_num

        src_disk = cls.get_physical_disk_number(source_path)
        dst_disk = cls.get_physical_disk_number(dest_path)

        if src_disk is not None and dst_disk is not None and src_disk == dst_disk:
            return True, src_disk

        return False, None

    @classmethod
    def get_filesystem_type(cls, path: str) -> str:
        """Returns filesystem name e.g. 'NTFS', 'FAT32', 'exFAT'."""
        try:
            drive_root = cls.get_drive_letter(path) + "\\"
            vol_name = ctypes.create_unicode_buffer(1024)
            fs_name = ctypes.create_unicode_buffer(1024)
            serial = ctypes.c_ulong()
            max_len = ctypes.c_ulong()
            flags = ctypes.c_ulong()
            res = ctypes.windll.kernel32.GetVolumeInformationW(
                drive_root, vol_name, 1024, ctypes.byref(serial),
                ctypes.byref(max_len), ctypes.byref(flags), fs_name, 1024
            )
            return fs_name.value.upper() if res else "NTFS"
        except Exception:
            return "NTFS"

    @classmethod
    def check_fat32_file_limit(cls, source_paths: List[str], dest_path: str) -> Tuple[bool, List[str]]:
        """
        If destination is FAT32/FAT, scans sources for files > 4GB (4,294,967,295 bytes).
        Returns (has_violating_files, list_of_file_paths).
        """
        fs = cls.get_filesystem_type(dest_path)
        if "FAT" not in fs or "EXFAT" in fs:
            return False, []

        max_fat32_size = 4294967295  # 4 GiB - 1 byte
        violating_files: List[str] = []

        for src in source_paths:
            if os.path.isfile(src):
                try:
                    if os.path.getsize(src) > max_fat32_size:
                        violating_files.append(src)
                except OSError:
                    pass
            elif os.path.isdir(src):
                for root, _, files in os.walk(src):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            if os.path.getsize(fp) > max_fat32_size:
                                violating_files.append(fp)
                                if len(violating_files) >= 10:
                                    return True, violating_files
                        except OSError:
                            pass
        return len(violating_files) > 0, violating_files

    @classmethod
    def perform_preflight_check(
        cls,
        source_paths: List[str],
        destination_path: str,
        estimated_bytes: int = 0
    ) -> PreflightCheckResult:
        """Comprehensive preflight evaluation before running backup or sync."""
        res = PreflightCheckResult()

        # 1. Destination existence & write permission
        dest = Path(destination_path)
        try:
            dest.mkdir(parents=True, exist_ok=True)
            test_file = dest / ".sinax_write_test.tmp"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
        except Exception as e:
            res.is_valid = False
            res.errors.append(f"مسار الوجهة غير متاح أو لا توجد صلاحية كتابة: {e}")
            return res

        # 2. Check free space
        try:
            usage = shutil.disk_usage(destination_path)
            res.destination_free_bytes = usage.free
            if estimated_bytes > 0:
                res.source_bytes = estimated_bytes
                if usage.free < estimated_bytes:
                    res.is_valid = False
                    res.errors.append(
                        f"المساحة الفارغة على الوجهة ({usage.free / (1024**3):.1f} GB) غير كافية لحجم النسخة المطلوبة ({estimated_bytes / (1024**3):.1f} GB)."
                    )
                elif usage.free < (estimated_bytes * 1.05):
                    res.warnings.append("المساحة المتوفرة بالوجهة أوشكت على النفاد بعد النسخ.")
        except Exception as e:
            res.warnings.append(f"تعذر قياس المساحة الحرة للوجهة: {e}")

        # 3. Check same physical disk
        if source_paths:
            is_same, disk_num = cls.is_same_physical_disk(source_paths[0], destination_path)
            if is_same:
                res.is_same_physical_disk = True
                disk_label = f"Disk #{disk_num}" if disk_num is not None else "نفس القرص"
                res.warnings.append(
                    f"⚠ تحذير: المصدر والوجهة يقعان على نفس القرص الصلب الفيزيائي ({disk_label}). تعطل هذا القرص قد يؤدي لفقدان الأصل والنسخة معاً."
                )

        # 4. Check FAT32 limits
        has_fat32_viol, viol_files = cls.check_fat32_file_limit(source_paths, destination_path)
        if has_fat32_viol:
            res.is_fat32_over_4gb = True
            res.fat32_violating_files = viol_files
            res.is_valid = False
            res.errors.append(
                f"نظام ملفات الوجهة (FAT32) لا يدعم تخزين ملفات أكبر من 4GB. تم رصد {len(viol_files)} ملفات تتجاوز الحد."
            )

        # 5. Check recursive backup loop (e.g. C:\Docs\Backup inside C:\Docs)
        dest_abs = os.path.abspath(destination_path)
        for src in source_paths:
            src_abs = os.path.abspath(src)
            if dest_abs == src_abs or dest_abs.startswith(src_abs + os.sep):
                res.is_valid = False
                res.errors.append(
                    f"حلقة نسخ متداخلة محظورة: مجلد النسخة الاحتياطية ({dest_abs}) يقع داخل المجلد المصدري ({src_abs})."
                )

        return res
