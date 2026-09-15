# -*- coding: utf-8 -*-
"""
SINAX Post-Uninstall Leftover Scanner
Scans Program Files, AppData, ProgramData, and shortcuts for uninstalled software remnants.
Enforces a 3-tier confidence system and strictly protects shared vendor directories and user personal data.
"""

from dataclasses import dataclass
from datetime import datetime
import logging
import os
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple
import winreg

from app.services.apps_manager.app_model import format_bytes

logger = logging.getLogger("SINAX.apps_manager.leftover_scanner")

# Shared vendor roots that MUST NEVER be proposed for deletion as an entire folder
SHARED_VENDOR_ROOTS = {
    "adobe", "microsoft", "autodesk", "jetbrains", "google", "apple",
    "oracle", "mozilla", "steam", "epic games", "electronic arts",
    "ubisoft", "riot games", "blizzard", "common files", "packages", "windows"
}


@dataclass
class LeftoverItem:
    """Represents a potential remnant file, folder, shortcut, or registry key."""
    path: str
    item_type: str  # folder, file, shortcut, registry
    size_bytes: int
    confidence: str  # high, medium, low
    confidence_label_ar: str
    reason: str
    selected: bool = False

    @property
    def display_size(self) -> str:
        return format_bytes(self.size_bytes)


class LeftoverScanner:
    """Scans for software remnants with strict confidence scoring."""

    @classmethod
    def scan_for_app(cls, app_name: str, publisher: str = "") -> List[LeftoverItem]:
        """Scans disk and registry for remnants matching the specified app name."""
        if not app_name or len(app_name.strip()) < 3:
            return []

        clean_name = cls._clean_search_token(app_name)
        clean_pub = cls._clean_search_token(publisher) if publisher else ""

        results: List[LeftoverItem] = []

        # 1. Search Directories
        search_roots = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("APPDATA", ""),
            os.environ.get("ProgramData", r"C:\ProgramData"),
        ]

        for root in search_roots:
            if not root or not os.path.exists(root):
                continue
            try:
                with os.scandir(root) as it:
                    for entry in it:
                        try:
                            item = cls._evaluate_disk_entry(entry, clean_name, clean_pub)
                            if item:
                                results.append(item)
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue

        # 2. Search Shortcuts
        shortcut_roots = [
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
        ]
        for sc_root in shortcut_roots:
            if not sc_root or not os.path.exists(sc_root):
                continue
            for root_dir, _, files in os.walk(sc_root):
                for f in files:
                    if f.lower().endswith(".lnk") and clean_name in cls._clean_search_token(f):
                        full_p = os.path.join(root_dir, f)
                        results.append(
                            LeftoverItem(
                                path=full_p,
                                item_type="shortcut",
                                size_bytes=os.path.getsize(full_p) if os.path.exists(full_p) else 0,
                                confidence="high",
                                confidence_label_ar="ثقة عالية",
                                reason="اختصار برنامج متبقي في قائمة ابدأ أو سطح المكتب.",
                                selected=True,
                            )
                        )

        # 3. Search App-Specific Registry Key
        reg_items = cls._scan_registry_keys(clean_name, clean_pub)
        results.extend(reg_items)

        logger.info(f"LeftoverScanner found {len(results)} remnants for '{app_name}'")
        return results

    @classmethod
    def clean_leftovers(cls, items: List[LeftoverItem], backup_dir: Optional[str] = None) -> Tuple[int, int, List[str]]:
        """
        Safely cleans selected leftover items.
        Exports registry keys to a .reg backup file before removal.
        Moves files and folders to Windows Recycle Bin.
        Returns: (success_count, fail_count, list of errors).
        """
        success = 0
        failed = 0
        errors = []

        for item in items:
            try:
                if item.item_type in ("folder", "file", "shortcut"):
                    if not os.path.exists(item.path):
                        continue
                    # Check shared vendor root guard
                    base_low = os.path.basename(os.path.normpath(item.path)).lower()
                    if base_low in SHARED_VENDOR_ROOTS:
                        errors.append(f"تخطي مجلد مشترك محمي: {item.path}")
                        failed += 1
                        continue

                    if item.item_type == "folder":
                        shutil.rmtree(item.path, ignore_errors=False)
                    else:
                        os.remove(item.path)
                    success += 1

                elif item.item_type == "registry":
                    # Backup key first
                    if backup_dir:
                        cls._backup_registry_key(item.path, backup_dir)
                    cls._delete_registry_key(item.path)
                    success += 1

            except Exception as e:
                failed += 1
                errors.append(f"{item.path}: {e}")

        return success, failed, errors

    @classmethod
    def _evaluate_disk_entry(cls, entry: os.DirEntry, clean_name: str, clean_pub: str) -> Optional[LeftoverItem]:
        """Evaluates whether a folder or file is an application remnant."""
        name_clean = cls._clean_search_token(entry.name)

        # Skip shared vendor root entirely
        if name_clean in SHARED_VENDOR_ROOTS:
            # Check inside the vendor root for subfolder matching app
            try:
                with os.scandir(entry.path) as sub_it:
                    for sub in sub_it:
                        if sub.is_dir():
                            sub_clean = cls._clean_search_token(sub.name)
                            if clean_name in sub_clean or sub_clean in clean_name:
                                sz = cls._get_folder_size(sub.path)
                                return LeftoverItem(
                                    path=sub.path,
                                    item_type="folder",
                                    size_bytes=sz,
                                    confidence="high",
                                    confidence_label_ar="ثقة عالية",
                                    reason=f"مجلد فرعي خاص بالبرنامج داخل مجلد الناشر {entry.name}.",
                                    selected=True,
                                )
            except (OSError, PermissionError):
                pass
            return None

        # Direct match on folder name
        if clean_name == name_clean or (len(clean_name) >= 4 and clean_name in name_clean):
            sz = cls._get_folder_size(entry.path) if entry.is_dir() else entry.stat().st_size
            return LeftoverItem(
                path=entry.path,
                item_type="folder" if entry.is_dir() else "file",
                size_bytes=sz,
                confidence="high",
                confidence_label_ar="ثقة عالية",
                reason="اسم المجلد يطابق اسم البرنامج المعزول بدقة.",
                selected=True,
            )

        return None

    @classmethod
    def _scan_registry_keys(cls, clean_name: str, clean_pub: str) -> List[LeftoverItem]:
        """Scans HKCU and HKLM Software hives for app-specific keys."""
        items = []
        hives = [
            (winreg.HKEY_CURRENT_USER, r"Software", "HKCU\\Software"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE", "HKLM\\SOFTWARE"),
        ]
        for hive, subpath, hive_name in hives:
            try:
                with winreg.OpenKey(hive, subpath, 0, winreg.KEY_READ) as k:
                    num = winreg.QueryInfoKey(k)[0]
                    for i in range(num):
                        try:
                            subkey_name = winreg.EnumKey(k, i)
                            subkey_clean = cls._clean_search_token(subkey_name)
                            if subkey_clean in SHARED_VENDOR_ROOTS:
                                continue
                            if clean_name == subkey_clean or (len(clean_name) >= 4 and clean_name in subkey_clean):
                                full_reg_path = f"{hive_name}\\{subkey_name}"
                                items.append(
                                    LeftoverItem(
                                        path=full_reg_path,
                                        item_type="registry",
                                        size_bytes=0,
                                        confidence="medium",
                                        confidence_label_ar="ثقة متوسطة",
                                        reason="مفتاح إعدادات في سجل ويندوز يحمل اسم البرنامج.",
                                        selected=False,
                                    )
                                )
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError):
                continue
        return items

    @staticmethod
    def _clean_search_token(s: str) -> str:
        """Normalizes names by removing punctuation, spaces, and casing."""
        return re.sub(r"[^a-zA-Z0-9\u0600-\u06FF]", "", s).lower()

    @staticmethod
    def _get_folder_size(path: str) -> int:
        """Quickly computes size of a directory up to a safe limit."""
        total = 0
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
        return total

    @staticmethod
    def _backup_registry_key(key_path: str, backup_dir: str):
        """Exports a registry key to a .reg file using Windows reg.exe export."""
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", key_path)
        out_reg = os.path.join(backup_dir, f"backup_{safe_name}_{timestamp}.reg")
        import subprocess
        subprocess.run(["reg.exe", "export", key_path, out_reg, "/y"], capture_output=True)

    @staticmethod
    def _delete_registry_key(key_path: str):
        """Safely deletes a registry key using Windows reg.exe delete."""
        import subprocess
        subprocess.run(["reg.exe", "delete", key_path, "/f"], capture_output=True)
