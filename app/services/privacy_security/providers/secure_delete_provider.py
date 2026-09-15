# -*- coding: utf-8 -*-
"""
Secure Delete Provider for SINAX Privacy & Security.
Detects physical storage type (HDD, SSD, NVMe) using PowerShell / WMI,
applies appropriate scientific sanitization (1 or 3 passes on magnetic media),
enforces NIST flash storage wear-leveling warnings, and prevents deletion of system paths.
"""

import json
import os
from pathlib import Path
import subprocess
import time
from typing import Callable, Dict, List, Optional, Set, Tuple

from app.services.privacy_security.models import StorageType

PROTECTED_PATHS = {
    "c:\\windows",
    "c:\\windows\\system32",
    "c:\\windows\\syswow64",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\boot",
    "c:\\recovery",
    "c:\\",
    "d:\\",
}


class NativeOverwriteProvider:
    """Storage-aware file sanitization and deletion engine."""

    _storage_cache: Dict[str, Tuple[StorageType, str]] = {}

    @classmethod
    def get_drive_storage_type(cls, file_or_drive_path: str) -> Tuple[StorageType, str]:
        """
        Determines whether the drive hosting the path is HDD, SSD, or NVMe.
        Returns: (StorageType, friendly_description)
        """
        try:
            drive = os.path.splitdrive(os.path.abspath(file_or_drive_path))[0].upper()
            if not drive:
                drive = "C:"
            if drive in cls._storage_cache:
                return cls._storage_cache[drive]

            # Query PowerShell Get-PhysicalDisk
            cmd = [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                """
                Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType | ConvertTo-Json
                """
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=6,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            if res.returncode == 0 and res.stdout.strip():
                raw = json.loads(res.stdout)
                disks = raw if isinstance(raw, list) else [raw]

                for d in disks:
                    media = str(d.get("MediaType", "")).lower()
                    bus = str(d.get("BusType", "")).lower()
                    friendly = str(d.get("FriendlyName", "Storage"))

                    if "nvme" in bus or "nvme" in media:
                        result = (StorageType.NVME, f"{friendly} (NVMe SSD)")
                        cls._storage_cache[drive] = result
                        return result
                    elif "ssd" in media or "flash" in media or "solid" in media:
                        result = (StorageType.SSD, f"{friendly} (SATA/USB SSD)")
                        cls._storage_cache[drive] = result
                        return result
                    elif "hdd" in media or "magnetic" in media:
                        result = (StorageType.HDD, f"{friendly} (Magnetic HDD)")
                        cls._storage_cache[drive] = result
                        return result

            # Default fallback for Windows modern drives if unable to query
            result = (StorageType.SSD, "قرص تخزين صلب (SSD / Flash Media)")
            cls._storage_cache[drive] = result
            return result

        except Exception:
            return StorageType.UNKNOWN, "وسيط تخزين غير محدد"

    @staticmethod
    def is_path_protected(path: str) -> bool:
        """Checks if a target file or folder is within critical Windows system directories."""
        p_lower = str(Path(path).resolve()).lower()
        for prot in PROTECTED_PATHS:
            if p_lower == prot or p_lower.startswith(prot + "\\"):
                # Allow subfiles in ProgramData or user folders if not system
                if prot in ("c:\\windows", "c:\\program files", "c:\\program files (x86)", "c:\\boot", "c:\\recovery"):
                    return True
                if p_lower in ("c:\\", "d:\\", "e:\\"):
                    return True
        return False

    @classmethod
    def secure_delete_file(
        cls,
        file_path: str,
        passes: int = 1,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[bool, str]:
        """
        Overwrites file data with zeros/random bytes before deletion.
        On SSD/NVMe, explicitly records that flash wear-leveling prevents guaranteed physical wiping.
        """
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            return False, f"الملف غير موجود: {file_path}"

        if cls.is_path_protected(str(p)):
            return False, f"ممنوع: المسار المالي يقع ضمن ملفات النظام المحمية: {p}"

        storage_type, media_desc = cls.get_drive_storage_type(str(p))

        try:
            file_size = p.stat().st_size

            # Perform overwrite passes
            chunk_size = 1024 * 1024  # 1 MB
            with open(p, "r+b") as f:
                for pass_idx in range(passes):
                    f.seek(0)
                    bytes_written = 0

                    # Pass pattern: pass 0 = zeros, pass 1 = 0xFF, pass 2 = random
                    if pass_idx == 0:
                        pattern = b"\x00" * chunk_size
                    elif pass_idx == 1:
                        pattern = b"\xFF" * chunk_size
                    else:
                        pattern = os.urandom(chunk_size)

                    while bytes_written < file_size:
                        write_len = min(chunk_size, file_size - bytes_written)
                        f.write(pattern[:write_len])
                        bytes_written += write_len

                    f.flush()
                    os.fsync(f.fileno())

                    if progress_cb:
                        progress = (pass_idx + 1) / passes
                        progress_cb(progress, f"اكتمل التمرير {pass_idx + 1} من {passes}")

            # Obfuscate filename before deletion to clear directory metadata
            rand_name = p.parent / f"del_{os.urandom(8).hex()}.tmp"
            p.rename(rand_name)
            rand_name.unlink()

            if storage_type in (StorageType.SSD, StorageType.NVME):
                return True, (
                    f"تم حذف الملف بنجاح على قرص ({media_desc}).\n"
                    "ملاحظة علمية: نظراً لأن القرص من نوع Flash/SSD، فإن نظام Wear-Leveling "
                    "يمنع الجزم بمحو جميع النسخ الفيزيائية الموزعة داخلياً."
                )
            else:
                return True, f"تم الحذف الآمن للملف بنجاح بعد {passes} دورات كتابة على ({media_desc})."

        except Exception as e:
            return False, f"فشل الحذف الآمن: {str(e)}"

    @classmethod
    def secure_delete_folder(
        cls,
        folder_path: str,
        passes: int = 1,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str, int]:
        """Recursively sanitizes and deletes all files within a folder."""
        f_dir = Path(folder_path).resolve()
        if not f_dir.exists() or not f_dir.is_dir():
            return False, f"المجلد غير موجود: {folder_path}", 0

        if cls.is_path_protected(str(f_dir)):
            return False, f"ممنوع: لا يمكن حذف مجلد نظام محمي: {f_dir}", 0

        # Collect files
        all_files = [f for f in f_dir.rglob("*") if f.is_file()]
        total_files = len(all_files)
        deleted_count = 0

        for idx, f in enumerate(all_files):
            if cancel_check and cancel_check():
                return False, "تم إيقاف عملية الحذف بواسطة المستخدم.", deleted_count

            ok, _ = cls.secure_delete_file(str(f), passes=passes)
            if ok:
                deleted_count += 1

            if progress_cb and total_files > 0:
                progress_cb((idx + 1) / total_files, f"حذف الملف {idx + 1} من {total_files}")

        # Remove remaining empty directories
        for d in sorted(list(f_dir.rglob("*")), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()
                except Exception:
                    pass

        try:
            f_dir.rmdir()
        except Exception:
            pass

        return True, f"تم حذف {deleted_count} ملفاً من أصل {total_files} بنجاح.", deleted_count
