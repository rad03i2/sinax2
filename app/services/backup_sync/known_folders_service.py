# -*- coding: utf-8 -*-
"""
SINAX Known Folders Service.
Resolves Windows Special / Known Folders (Desktop, Documents, Pictures, Videos,
Music, Downloads) using Windows Registry User Shell Folders and standard APIs,
honoring customized user relocations without hardcoded paths.
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Dict, List, Optional
import winreg

from app.core.logger import get_logger

logger = get_logger("known_folders_service")


@dataclass
class KnownFolderInfo:
    key: str
    name_ar: str
    name_en: str
    path: str
    exists: bool = False
    file_count: int = 0
    size_bytes: int = 0
    icon_name: str = "folder"


class KnownFoldersService:
    """Service to discover and query Windows Known Folders."""

    REG_MAPPINGS = {
        "desktop": ("Desktop", "سطح المكتب", "Desktop", "desktop"),
        "documents": ("Personal", "المستندات", "Documents", "document"),
        "pictures": ("My Pictures", "الصور", "Pictures", "image"),
        "videos": ("My Video", "الفيديوهات", "Videos", "video"),
        "music": ("My Music", "الموسيقى والصوتيات", "Music", "music"),
        "downloads": ("{374DE290-123F-4565-9164-39C4925E467B}", "التنزيلات", "Downloads", "download"),
    }

    @classmethod
    def get_known_folders(cls, calculate_sizes: bool = False) -> List[KnownFolderInfo]:
        """Returns all 6 major known folders with verified system paths."""
        results: List[KnownFolderInfo] = []
        user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))

        reg_paths = cls._read_user_shell_folders()

        for key, (reg_key, name_ar, name_en, icon) in cls.REG_MAPPINGS.items():
            raw_path = reg_paths.get(reg_key)
            if raw_path:
                expanded = os.path.expandvars(raw_path)
            else:
                # Standard fallback
                fallback_names = {
                    "desktop": "Desktop",
                    "documents": "Documents",
                    "pictures": "Pictures",
                    "videos": "Videos",
                    "music": "Music",
                    "downloads": "Downloads",
                }
                expanded = os.path.join(user_profile, fallback_names[key])

            exists = os.path.exists(expanded) and os.path.isdir(expanded)
            file_count = 0
            size_bytes = 0

            if exists and calculate_sizes:
                file_count, size_bytes = cls._quick_scan_stats(expanded)

            results.append(KnownFolderInfo(
                key=key,
                name_ar=name_ar,
                name_en=name_en,
                path=expanded,
                exists=exists,
                file_count=file_count,
                size_bytes=size_bytes,
                icon_name=icon
            ))

        return results

    @classmethod
    def get_important_folders_paths(cls) -> List[str]:
        """Returns list of the top essential user folders (Desktop, Documents, Pictures)."""
        all_f = cls.get_known_folders(calculate_sizes=False)
        return [f.path for f in all_f if f.key in ("desktop", "documents", "pictures") and f.exists]

    @classmethod
    def _read_user_shell_folders(cls) -> Dict[str, str]:
        paths = {}
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                num_values = winreg.QueryInfoKey(key)[1]
                for i in range(num_values):
                    name, val, _ = winreg.EnumValue(key, i)
                    paths[name] = str(val)
        except Exception as e:
            logger.warning(f"Failed to read User Shell Folders registry: {e}")
        return paths

    @classmethod
    def _quick_scan_stats(cls, folder: str, max_files: int = 50000) -> (int, int):
        count = 0
        total_size = 0
        try:
            for root, _, files in os.walk(folder):
                for f in files:
                    count += 1
                    try:
                        p = os.path.join(root, f)
                        total_size += os.path.getsize(p)
                    except (OSError, PermissionError):
                        pass
                    if count >= max_files:
                        break
                if count >= max_files:
                    break
        except Exception:
            pass
        return count, total_size
