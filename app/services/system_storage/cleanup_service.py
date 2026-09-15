# -*- coding: utf-8 -*-
"""
SINAX Safe Cleanup Service
Performs safe, explainable disk space cleanup without fake boosters or registry tampering.
Adheres strictly to the philosophy:
Analyze First -> Explain -> Recommend -> User Confirms -> Execute.

Safety features:
- STRICT protected path blacklisting (Windows, System32, WinSxS, Program Files, etc.)
- Safety ratings: "safe" (green), "review" (yellow), "critical" (red)
- Graceful locked/in-use file skipping (no crashes)
- Simulation / dry-run support
- Windows Recycle Bin native query & empty via ctypes
- Browser cache isolation (caches only, never history, passwords, or cookies)
"""

import ctypes
import os
import shutil
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.core.logger import get_logger
from app.services.system_storage.storage_scanner import format_bytes

logger = get_logger("cleanup_service")

# Windows Protected Directories (Normalized lowercase)
PROTECTED_SYSTEM_DIRECTORIES = {
    r"c:\windows",
    r"c:\windows\system32",
    r"c:\windows\syswow64",
    r"c:\windows\winsxs",
    r"c:\windows\boot",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\programdata\microsoft",
    r"c:\system volume information",
    r"c:\recovery",
    r"c:\$recycle.bin",
}

# Recycle Bin Ctypes Structures
class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_int64),
        ("i64NumItems", ctypes.c_int64),
    ]


@dataclass
class CleanupItem:
    id: str
    name_ar: str
    description_ar: str
    safety_level: str           # "safe", "review", "critical"
    safety_label_ar: str
    size_bytes: int = 0
    files_count: int = 0
    target_paths: List[str] = field(default_factory=list)
    is_checked: bool = True
    is_recycle_bin: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CleanupResult:
    cleaned_bytes: int = 0
    cleaned_files: int = 0
    failed_files: int = 0
    skipped_locked_files: int = 0
    duration: float = 0.0
    errors: List[str] = field(default_factory=list)
    cleaned_items: List[str] = field(default_factory=list)


class CleanupService:
    """Scans and safely cleans temporary, cache, and junk files."""

    @staticmethod
    def is_protected_path(path_str: str) -> bool:
        """Check if a path or any of its critical parent directories is protected."""
        try:
            norm = os.path.normpath(os.path.abspath(path_str)).lower()
            for protected in PROTECTED_SYSTEM_DIRECTORIES:
                # Direct match or protected is parent of norm without being an explicitly allowed safe subfolder
                if norm == protected or (norm.startswith(protected + "\\") and "temp" not in norm and "cache" not in norm):
                    return True
            return False
        except Exception:
            return True

    @staticmethod
    def query_recycle_bin(drive_letter: Optional[str] = None) -> Tuple[int, int]:
        """Query recycle bin for size in bytes and number of items using Windows API."""
        try:
            rb_info = SHQUERYRBINFO()
            rb_info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
            root_path = f"{drive_letter.upper()[:2]}\\" if drive_letter else None
            res = ctypes.windll.shell32.SHQueryRecycleBinW(root_path, ctypes.byref(rb_info))
            if res == 0:
                return rb_info.i64Size, rb_info.i64NumItems
        except Exception as e:
            logger.debug(f"Failed to query recycle bin: {e}")
        return 0, 0

    @staticmethod
    def empty_recycle_bin(drive_letter: Optional[str] = None) -> bool:
        """Empty recycle bin silently without confirmation dialogs."""
        try:
            root_path = f"{drive_letter.upper()[:2]}\\" if drive_letter else None
            # SHERB_NOCONFIRMATION = 0x00000001
            # SHERB_NOPROGRESSUI   = 0x00000002
            # SHERB_NOSOUND        = 0x00000004
            flags = 1 | 2 | 4
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, root_path, flags)
            return res == 0
        except Exception as e:
            logger.error(f"Failed to empty recycle bin: {e}")
            return False

    @classmethod
    def get_cleanup_targets(cls) -> List[CleanupItem]:
        """Define standard verifiable cleanup targets."""
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        appdata = os.environ.get("APPDATA", "")
        user_temp = os.environ.get("TEMP", "")
        win_dir = os.environ.get("WINDIR", "C:\\Windows")

        targets = [
            # 1. User Temp Files
            CleanupItem(
                id="user_temp",
                name_ar="ملفات النظام المؤقتة للمستخدم",
                description_ar="الملفات المؤقتة المنشأة بواسطة التطبيقات والبرامج في مجلد %TEMP%",
                safety_level="safe",
                safety_label_ar="آمن غالباً",
                target_paths=[user_temp] if user_temp and os.path.exists(user_temp) else [],
                is_checked=True
            ),
            # 2. Windows Temp Files
            CleanupItem(
                id="win_temp",
                name_ar="ملفات ويندوز المؤقتة العامة",
                description_ar="ملفات مؤقتة يتركها نظام التشغيل والتحديثات في مجلد Windows\\Temp",
                safety_level="safe",
                safety_label_ar="آمن غالباً",
                target_paths=[os.path.join(win_dir, "Temp")] if os.path.exists(os.path.join(win_dir, "Temp")) else [],
                is_checked=True
            ),
            # 3. Windows Recycle Bin
            CleanupItem(
                id="recycle_bin",
                name_ar="سلة المحذوفات",
                description_ar="الملفات التي قام المستخدم بحذفها وتنتظر التفريغ النهائي",
                safety_level="safe",
                safety_label_ar="آمن غالباً",
                is_recycle_bin=True,
                is_checked=True
            ),
            # 4. Windows Thumbnails Cache
            CleanupItem(
                id="thumb_cache",
                name_ar="كاش معاينات الصور والمصغرات",
                description_ar="ملفات كاش المعاينات المصغرة thumbcache لنظام ويندوز",
                safety_level="safe",
                safety_label_ar="آمن غالباً",
                target_paths=[
                    os.path.join(local_appdata, "Microsoft", "Windows", "Explorer")
                ] if local_appdata else [],
                is_checked=True
            ),
            # 5. Web Browsers Cache (Isolated cache directories only)
            CleanupItem(
                id="browser_cache",
                name_ar="كاش متصفحات الويب (ذاكرة مؤقتة فقط)",
                description_ar="ملفات الكاش للمتصفحات (Chrome, Edge, Brave, Firefox) - لا يتم مسح كلمات السر أو السجل أو المفضلة أبداً",
                safety_level="safe",
                safety_label_ar="آمن غالباً",
                target_paths=[
                    p for p in [
                        os.path.join(local_appdata, "Google", "Chrome", "User Data", "Default", "Cache"),
                        os.path.join(local_appdata, "Microsoft", "Edge", "User Data", "Default", "Cache"),
                        os.path.join(local_appdata, "BraveSoftware", "Brave-Browser", "User Data", "Default", "Cache"),
                        os.path.join(local_appdata, "Mozilla", "Firefox", "Profiles"),
                    ] if os.path.exists(p)
                ],
                is_checked=True
            ),
            # 6. Windows Error Reporting / Crash Dumps
            CleanupItem(
                id="crash_dumps",
                name_ar="سجلات تقارير الأخطاء ومقالب الانهيار (Crash Dumps)",
                description_ar="ملفات تفريغ الذاكرة عند انهيار البرامج وسجلات تقارير أخطاء ويندوز",
                safety_level="review",
                safety_label_ar="يتطلب مراجعة",
                target_paths=[
                    p for p in [
                        os.path.join(local_appdata, "CrashDumps"),
                        os.path.join(win_dir, "Minidump"),
                        os.path.join(local_appdata, "Microsoft", "Windows", "WER"),
                    ] if os.path.exists(p)
                ],
                is_checked=False
            ),
            # 7. Delivery Optimization Cache
            CleanupItem(
                id="delivery_opt",
                name_ar="كاش تحسين تسليم التحديثات (Delivery Optimization)",
                description_ar="ملفات كاش تحديثات ويندوز المخزنة للمشاركة عبر الشبكة المحلية",
                safety_level="safe",
                safety_label_ar="آمن غالباً",
                target_paths=[
                    os.path.join(win_dir, "SoftwareDistribution", "DeliveryOptimization")
                ] if os.path.exists(os.path.join(win_dir, "SoftwareDistribution", "DeliveryOptimization")) else [],
                is_checked=False
            ),
            # 8. Temporary Log Files
            CleanupItem(
                id="stale_logs",
                name_ar="ملفات السجلات القديمة المؤقتة (*.log)",
                description_ar="سجلات نصية قديمة تركها مثبتو البرامج داخل مجلدات التثبيت المؤقتة",
                safety_level="review",
                safety_label_ar="يتطلب مراجعة",
                target_paths=[user_temp] if user_temp and os.path.exists(user_temp) else [],
                is_checked=False,
                details={"ext_filter": [".log", ".tmp", ".bak"]}
            ),
        ]
        return targets

    @classmethod
    def scan_all_targets(
        cls,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[CleanupItem]:
        """Scan all cleanup targets and calculate real cleanable size and file counts."""
        targets = cls.get_cleanup_targets()
        total = len(targets)

        for idx, item in enumerate(targets):
            if progress_callback:
                progress_callback(item.name_ar, idx, total)

            # Special case: Recycle bin
            if item.is_recycle_bin:
                size, count = cls.query_recycle_bin()
                item.size_bytes = size
                item.files_count = count
                continue

            # Target paths scanning
            item_size = 0
            item_count = 0
            is_thumb = item.id == "thumb_cache"
            is_logs = item.id == "stale_logs"

            for target_path in item.target_paths:
                if not os.path.exists(target_path):
                    continue

                try:
                    for root, dirs, files in os.walk(target_path):
                        for f in files:
                            # Thumbnail cache specific filtering
                            if is_thumb and not f.lower().startswith("thumbcache_"):
                                continue

                            # Log files specific filtering
                            if is_logs and not f.lower().endswith((".log", ".tmp", ".bak")):
                                continue

                            fp = os.path.join(root, f)
                            try:
                                item_size += os.path.getsize(fp)
                                item_count += 1
                            except (OSError, PermissionError):
                                pass
                except Exception as e:
                    logger.debug(f"Error scanning {target_path}: {e}")

            item.size_bytes = item_size
            item.files_count = item_count

        if progress_callback:
            progress_callback("اكتمل الفحص", total, total)

        return targets

    @classmethod
    def execute_cleanup(
        cls,
        selected_items: List[CleanupItem],
        simulation: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> CleanupResult:
        """Execute cleanup on selected targets. Gracefully skips locked files."""
        result = CleanupResult()
        start_time = time.time()
        total_items = len(selected_items)

        for idx, item in enumerate(selected_items):
            if not item.is_checked:
                continue

            if progress_callback:
                progress_callback(item.name_ar, idx, total_items)

            # 1. Recycle Bin
            if item.is_recycle_bin:
                if not simulation:
                    success = cls.empty_recycle_bin()
                    if success:
                        result.cleaned_bytes += item.size_bytes
                        result.cleaned_files += item.files_count
                        result.cleaned_items.append(item.name_ar)
                    else:
                        result.errors.append("تعذر تفريغ سلة المحذوفات بالكامل.")
                else:
                    result.cleaned_bytes += item.size_bytes
                    result.cleaned_files += item.files_count
                    result.cleaned_items.append(item.name_ar)
                continue

            # 2. File and Directory Deletions
            is_thumb = item.id == "thumb_cache"
            is_logs = item.id == "stale_logs"
            item_cleaned_bytes = 0
            item_cleaned_count = 0

            for target_path in item.target_paths:
                if not os.path.exists(target_path):
                    continue

                # STRICT Protection check: Never delete the root directory itself if protected
                if cls.is_protected_path(target_path):
                    logger.warning(f"Prevented attempted deletion inside protected path: {target_path}")
                    continue

                for root, dirs, files in os.walk(target_path, topdown=False):
                    for f in files:
                        if is_thumb and not f.lower().startswith("thumbcache_"):
                            continue
                        if is_logs and not f.lower().endswith((".log", ".tmp", ".bak")):
                            continue

                        file_path = os.path.join(root, f)

                        # Check protected file path
                        if cls.is_protected_path(file_path):
                            continue

                        try:
                            f_size = os.path.getsize(file_path)
                            if not simulation:
                                os.remove(file_path)
                            item_cleaned_bytes += f_size
                            item_cleaned_count += 1
                        except (PermissionError, OSError):
                            # File is in use/locked by running program or access denied
                            result.skipped_locked_files += 1
                        except Exception as e:
                            result.failed_files += 1
                            logger.debug(f"Failed to delete {file_path}: {e}")

                    # Remove empty subdirectories if safe
                    if not simulation and root != target_path:
                        try:
                            os.rmdir(root)
                        except (OSError, PermissionError):
                            pass

            result.cleaned_bytes += item_cleaned_bytes
            result.cleaned_files += item_cleaned_count
            if item_cleaned_count > 0:
                result.cleaned_items.append(item.name_ar)

        result.duration = time.time() - start_time
        if progress_callback:
            progress_callback("اكتملت عملية التنظيف", total_items, total_items)

        return result
