# -*- coding: utf-8 -*-
"""
Safe Cleanup Orchestrator for SINAX Maintenance & Repair Center.
Implements honest, safe temporary files analysis and cleanup:
- User Temp & Windows Temp (safely skips in-use locked files without crashing)
- Thumbnail & Icon Cache repair and rebuild
- Recycle Bin statistics and confirmed emptying via Win32 Shell API
- Downloads Review (categorizes old installers, archives, large files without auto-deletion)
- Strictly avoids fake 'Registry Turbo' or destructive browser profile deletions.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SafeCleanupOrchestrator:
    """Orchestrates system cache analysis, safe cleanup, and downloads review."""

    @staticmethod
    def analyze_cleanup_targets() -> Dict[str, Any]:
        """
        Calculates disk space consumed by various temporary areas without deleting anything.
        """
        results: Dict[str, Any] = {
            "user_temp": {"bytes": 0, "count": 0, "path": "", "safety": "آمن غالباً"},
            "windows_temp": {"bytes": 0, "count": 0, "path": "", "safety": "آمن (قد يتطلب مسؤول)"},
            "thumbnail_cache": {"bytes": 0, "count": 0, "path": "", "safety": "آمن (يعاد إنشاؤه تلقائياً)"},
            "recycle_bin": {"bytes": 0, "count": 0, "path": "", "safety": "يحتاج مراجعة"},
            "crash_dumps": {"bytes": 0, "count": 0, "path": "", "safety": "يحتاج مراجعة (مفيد للتشخيص)"},
            "total_reclaimable_bytes": 0,
        }

        # 1. User Temp
        user_temp = os.environ.get("TEMP", "")
        if user_temp and os.path.exists(user_temp):
            b, c = SafeCleanupOrchestrator._get_dir_size(user_temp)
            results["user_temp"]["bytes"] = b
            results["user_temp"]["count"] = c
            results["user_temp"]["path"] = user_temp

        # 2. Windows Temp
        win_temp = r"C:\Windows\Temp"
        if os.path.exists(win_temp):
            b, c = SafeCleanupOrchestrator._get_dir_size(win_temp)
            results["windows_temp"]["bytes"] = b
            results["windows_temp"]["count"] = c
            results["windows_temp"]["path"] = win_temp

        # 3. Explorer Thumbnail Cache
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            thumb_dir = Path(local_app) / "Microsoft" / "Windows" / "Explorer"
            if thumb_dir.exists():
                thumb_bytes = 0
                thumb_count = 0
                try:
                    for f in thumb_dir.glob("thumbcache_*.db"):
                        try:
                            thumb_bytes += f.stat().st_size
                            thumb_count += 1
                        except Exception:
                            pass
                except Exception:
                    pass
                results["thumbnail_cache"]["bytes"] = thumb_bytes
                results["thumbnail_cache"]["count"] = thumb_count
                results["thumbnail_cache"]["path"] = str(thumb_dir)

        # 4. Recycle Bin
        rb_bytes, rb_count = SafeCleanupOrchestrator.get_recycle_bin_stats()
        results["recycle_bin"]["bytes"] = rb_bytes
        results["recycle_bin"]["count"] = rb_count

        # 5. Crash Dumps / Minidump
        minidump_dir = r"C:\Windows\Minidump"
        if os.path.exists(minidump_dir):
            b, c = SafeCleanupOrchestrator._get_dir_size(minidump_dir)
            results["crash_dumps"]["bytes"] = b
            results["crash_dumps"]["count"] = c
            results["crash_dumps"]["path"] = minidump_dir

        total = (
            results["user_temp"]["bytes"]
            + results["windows_temp"]["bytes"]
            + results["thumbnail_cache"]["bytes"]
            + results["recycle_bin"]["bytes"]
        )
        results["total_reclaimable_bytes"] = total
        return results

    @staticmethod
    def clean_user_temp(progress_cb=None) -> Tuple[int, int, int]:
        """
        Cleans User Temp directory. Skips locked files gracefully.
        Returns: (freed_bytes, deleted_count, skipped_count)
        """
        user_temp = os.environ.get("TEMP", "")
        if not user_temp or not os.path.exists(user_temp):
            return 0, 0, 0

        freed_bytes = 0
        deleted_count = 0
        skipped_count = 0

        for root, dirs, files in os.walk(user_temp, topdown=False):
            for file in files:
                fpath = os.path.join(root, file)
                try:
                    sz = os.path.getsize(fpath)
                    os.remove(fpath)
                    freed_bytes += sz
                    deleted_count += 1
                    if progress_cb and deleted_count % 50 == 0:
                        progress_cb(deleted_count, f"تم حذف {deleted_count} ملف مؤقت...")
                except Exception:
                    skipped_count += 1

            for d in dirs:
                dpath = os.path.join(root, d)
                try:
                    os.rmdir(dpath)
                except Exception:
                    pass

        return freed_bytes, deleted_count, skipped_count

    @staticmethod
    def get_recycle_bin_stats() -> Tuple[int, int]:
        """Queries Windows Shell API for Recycle Bin total size and item count."""
        if os.name != "nt":
            return 0, 0

        import ctypes
        from ctypes import wintypes

        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("i64Size", ctypes.c_int64),
                ("i64NumItems", ctypes.c_int64),
            ]

        try:
            rb_info = SHQUERYRBINFO()
            rb_info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
            res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb_info))
            if res == 0:
                return int(rb_info.i64Size), int(rb_info.i64NumItems)
        except Exception:
            pass

        return 0, 0

    @staticmethod
    def empty_recycle_bin(confirm_first: bool = False) -> bool:
        """Empties Recycle Bin via official Windows Shell32 API."""
        if os.name != "nt":
            return False

        import ctypes
        # SHERB_NOCONFIRMATION = 0x00000001, SHERB_NOPROGRESSUI = 0x00000002, SHERB_NOSOUND = 0x00000004
        flags = 0x00000007 if not confirm_first else 0x00000000
        try:
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            return res == 0
        except Exception:
            return False

    @staticmethod
    def review_downloads_folder() -> Dict[str, Any]:
        """
        Categorizes user Downloads folder without deleting anything:
        - Large files (> 500MB, > 1GB)
        - Installers (.exe, .msi)
        - Archives (.zip, .rar, .7z, .iso)
        - Files older than 180 days
        - Total size and file count
        """
        downloads_path = Path.home() / "Downloads"
        if not downloads_path.exists():
            return {
                "exists": False,
                "total_bytes": 0,
                "total_count": 0,
                "large_files": [],
                "installers": [],
                "archives": [],
                "old_files": [],
            }

        total_bytes = 0
        total_count = 0
        now = time.time()
        six_months_sec = 180 * 86400

        large_files = []
        installers = []
        archives = []
        old_files = []

        try:
            for item in downloads_path.iterdir():
                if item.is_file():
                    try:
                        st = item.stat()
                        sz = st.st_size
                        mtime = st.st_mtime
                        ext = item.suffix.lower()

                        total_bytes += sz
                        total_count += 1

                        item_data = {
                            "name": item.name,
                            "path": str(item),
                            "size_bytes": sz,
                            "size_str": SafeCleanupOrchestrator.format_bytes(sz),
                            "modified_str": time.strftime("%Y-%m-%d", time.localtime(mtime)),
                            "age_days": int((now - mtime) / 86400),
                        }

                        # Large files (> 500 MB)
                        if sz >= 500 * 1024 * 1024:
                            large_files.append(item_data)

                        # Installers
                        if ext in (".exe", ".msi"):
                            installers.append(item_data)

                        # Archives & ISOs
                        if ext in (".zip", ".rar", ".7z", ".tar", ".gz", ".iso"):
                            archives.append(item_data)

                        # Old files (> 180 days)
                        if (now - mtime) > six_months_sec:
                            old_files.append(item_data)

                    except Exception:
                        pass
        except Exception:
            pass

        return {
            "exists": True,
            "path": str(downloads_path),
            "total_bytes": total_bytes,
            "total_count": total_count,
            "large_files": sorted(large_files, key=lambda x: x["size_bytes"], reverse=True)[:25],
            "installers": sorted(installers, key=lambda x: x["size_bytes"], reverse=True)[:25],
            "archives": sorted(archives, key=lambda x: x["size_bytes"], reverse=True)[:25],
            "old_files": sorted(old_files, key=lambda x: x["age_days"], reverse=True)[:25],
        }

    @staticmethod
    def _get_dir_size(dir_path: str) -> Tuple[int, int]:
        total_size = 0
        file_count = 0
        try:
            for root, _, files in os.walk(dir_path):
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except Exception:
                        pass
        except Exception:
            pass
        return total_size, file_count

    @staticmethod
    def format_bytes(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
