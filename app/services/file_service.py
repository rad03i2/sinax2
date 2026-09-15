# -*- coding: utf-8 -*-
"""
SINAX File Service
Core file operations, system path protection, explorer integration, and natural sorting.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import send2trash

from app.core.constants import (
    SYSTEM_PATHS, WINDOWS_RESERVED_CHARS, WINDOWS_RESERVED_NAMES,
    FILE_CATEGORIES, EXTENSION_TO_CATEGORY
)
from app.models.file_item import FileItem
from app.core.logger import get_logger

logger = get_logger("file_service")

class FileService:
    @staticmethod
    def is_system_path(path: Path) -> Tuple[bool, str]:
        """Checks if directory is a protected Windows system path."""
        try:
            resolved = Path(path).resolve()
            for sys_p in SYSTEM_PATHS:
                if resolved == sys_p or sys_p in resolved.parents:
                    return True, f"هذا المجلد يقع ضمن ملفات النظام المحمية ({sys_p})"
            if str(resolved).lower().endswith("system32") or "windows" in str(resolved).lower():
                return True, "هذا المسار يتبع مجلدات نظام التشغيل ويندوز"
        except Exception as e:
            logger.warning(f"Error checking system path: {e}")
        return False, ""

    @staticmethod
    def natural_sort_key(s: str) -> List[Any]:
        """Key for natural/smart numeric sorting (e.g., 'file 2' before 'file 10')."""
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

    @staticmethod
    def scan_directory(
        directory: Path,
        recursive: bool = False,
        category_filter: str = "all",
        custom_extension: Optional[str] = None
    ) -> Tuple[List[FileItem], Dict[str, int], int]:
        """
        Scans a directory for files.
        Returns:
            (file_items, category_counts, total_bytes)
        """
        items: List[FileItem] = []
        counts: Dict[str, int] = {k: 0 for k in FILE_CATEGORIES.keys()}
        total_bytes = 0

        if not directory.exists() or not directory.is_dir():
            return items, counts, 0

        try:
            iterator = directory.rglob('*') if recursive else directory.glob('*')
            for path in iterator:
                try:
                    if not path.is_file():
                        continue
                    
                    item = FileItem.from_path(path)
                    counts['all'] += 1
                    counts[item.category_key] = counts.get(item.category_key, 0) + 1
                    total_bytes += item.size_bytes

                    # Apply filter
                    if category_filter and category_filter != "all":
                        if item.category_key != category_filter:
                            continue
                    
                    if custom_extension:
                        clean_ext = custom_extension.lower().strip()
                        if not clean_ext.startswith('.'):
                            clean_ext = '.' + clean_ext
                        if item.extension.lower() != clean_ext:
                            continue

                    items.append(item)
                except (PermissionError, FileNotFoundError):
                    continue
        except Exception as e:
            logger.error(f"Failed scanning directory {directory}: {e}")

        return items, counts, total_bytes

    @staticmethod
    def validate_filename(name: str) -> Tuple[bool, str]:
        """Checks if a filename is valid on Windows."""
        if not name or not name.strip():
            return False, "اسم الملف لا يمكن أن يكون فارغاً"
        
        # Check invalid chars
        invalid_present = [c for c in name if c in WINDOWS_RESERVED_CHARS]
        if invalid_present:
            return False, f"يحتوي الاسم على أحرف ممنوعة في ويندوز: {' '.join(set(invalid_present))}"
        
        # Check reserved DOS names (CON, PRN, etc.)
        base = name.split('.')[0].upper()
        if base in WINDOWS_RESERVED_NAMES:
            return False, f"هذا الاسم محجوز لنظام ويندوز ({base})"

        # Check ending with dot or space
        if name.endswith(' ') or name.endswith('.'):
            return False, "لا يمكن أن ينتهي اسم الملف بمسافة أو نقطة في ويندوز"

        if len(name) > 255:
            return False, "اسم الملف طويل جداً (يتجاوز 255 حرفاً)"

        return True, ""

    @staticmethod
    def send_to_recycle_bin(path: Path) -> bool:
        """Safely sends file to Windows Recycle Bin."""
        try:
            send2trash.send2trash(str(path))
            return True
        except Exception as e:
            logger.error(f"Failed to recycle {path}: {e}")
            return False

    @staticmethod
    def open_in_explorer(path: Path) -> None:
        """Opens Windows Explorer with the file or directory highlighted."""
        try:
            resolved = Path(path).resolve()
            if resolved.is_file():
                subprocess.Popen(f'explorer /select,"{resolved}"')
            elif resolved.is_dir():
                subprocess.Popen(f'explorer "{resolved}"')
        except Exception as e:
            logger.error(f"Failed to open in Explorer: {e}")

    @staticmethod
    def open_file(path: Path) -> None:
        """Opens file with the default associated application."""
        try:
            resolved = Path(path).resolve()
            os.startfile(str(resolved))
        except Exception as e:
            logger.error(f"Failed to open file: {e}")

    @staticmethod
    def open_terminal(path: Path, terminal_type: str = "powershell") -> None:
        """Opens CMD or PowerShell at the directory."""
        try:
            folder = path if path.is_dir() else path.parent
            if terminal_type.lower() == "cmd":
                subprocess.Popen(f'start cmd /K "cd /d {folder}"', shell=True)
            else:
                subprocess.Popen(f'start powershell -NoExit -Command "Set-Location \'{folder}\'"', shell=True)
        except Exception as e:
            logger.error(f"Failed to open terminal: {e}")
