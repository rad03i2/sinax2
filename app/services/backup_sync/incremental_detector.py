# -*- coding: utf-8 -*-
"""
SINAX Incremental Change Detector & Mass Changes Guard.
Supports Fast (size + mtime), Balanced (metadata), and Strict (hash) comparison.
Includes Ransomware-Awareness Safeguard: detects sudden massive changes (>60%)
before applying incremental modifications.
"""

from dataclasses import dataclass, field
import fnmatch
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from app.core.logger import get_logger
from app.services.backup_sync.models import FileVersion, IncrementalMode
from app.services.quick_tools.tools.hash_tools import HashTools

logger = get_logger("incremental_detector")


@dataclass
class FileScanItem:
    relative_path: str
    absolute_path: str
    size_bytes: int
    mtime: float
    is_new: bool = False
    is_modified: bool = False
    sha256: Optional[str] = None


@dataclass
class IncrementalDiffReport:
    new_files: List[FileScanItem] = field(default_factory=list)
    modified_files: List[FileScanItem] = field(default_factory=list)
    unchanged_files: List[FileScanItem] = field(default_factory=list)
    deleted_paths: List[str] = field(default_factory=list)
    total_scanned: int = 0
    total_bytes_to_copy: int = 0
    unusual_mass_changes: bool = False
    mass_change_reason: str = ""


class IncrementalDetector:
    """Calculates diffs between source directory and previous snapshot."""

    @classmethod
    def should_exclude(cls, relative_path: str, exclude_patterns: List[str]) -> bool:
        """Evaluates whether a relative path matches any exclusion pattern."""
        parts = relative_path.replace("\\", "/").split("/")
        for pattern in exclude_patterns:
            # Check pattern against whole path or each path segment
            if fnmatch.fnmatch(relative_path.replace("\\", "/"), pattern):
                return True
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False

    @classmethod
    def scan_directory(
        cls,
        source_root: str,
        exclude_patterns: Optional[List[str]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, FileScanItem]:
        """Recursively scans a source folder and returns {relative_path: FileScanItem}."""
        items: Dict[str, FileScanItem] = {}
        excludes = exclude_patterns or []
        root_path = Path(source_root).resolve()

        if not root_path.exists():
            return items

        if root_path.is_file():
            rel = root_path.name
            try:
                stat = root_path.stat()
                items[rel] = FileScanItem(
                    relative_path=rel,
                    absolute_path=str(root_path),
                    size_bytes=stat.st_size,
                    mtime=stat.st_mtime
                )
            except OSError:
                pass
            return items

        for dirpath, dirnames, filenames in os.walk(str(root_path)):
            if cancel_check and cancel_check():
                break

            # Filter directory exclusions in-place
            rel_dir = os.path.relpath(dirpath, str(root_path))
            if rel_dir != ".":
                if cls.should_exclude(rel_dir, excludes):
                    dirnames.clear()
                    continue

            for fname in filenames:
                full_p = os.path.join(dirpath, fname)
                rel_f = os.path.relpath(full_p, str(root_path)).replace("/", "\\")

                if cls.should_exclude(rel_f, excludes):
                    continue

                try:
                    stat = os.stat(full_p)
                    items[rel_f] = FileScanItem(
                        relative_path=rel_f,
                        absolute_path=full_p,
                        size_bytes=stat.st_size,
                        mtime=stat.st_mtime
                    )
                except (OSError, PermissionError):
                    continue

        return items

    @classmethod
    def detect_changes(
        cls,
        current_files: Dict[str, FileScanItem],
        previous_versions: Dict[str, FileVersion],
        mode: IncrementalMode = IncrementalMode.FAST,
        check_mass_changes: bool = True,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> IncrementalDiffReport:
        """Compares current scanned files against known previous snapshot versions."""
        report = IncrementalDiffReport()
        report.total_scanned = len(current_files)

        prev_paths = set(previous_versions.keys())
        curr_paths = set(current_files.keys())

        # 1. New files
        for p in curr_paths - prev_paths:
            item = current_files[p]
            item.is_new = True
            report.new_files.append(item)
            report.total_bytes_to_copy += item.size_bytes

        # 2. Deleted files (in backup, but gone from source)
        for p in prev_paths - curr_paths:
            report.deleted_paths.append(p)

        # 3. Existing files - Check modification
        for p in curr_paths & prev_paths:
            if cancel_check and cancel_check():
                break

            item = current_files[p]
            prev = previous_versions[p]
            modified = False

            if mode == IncrementalMode.FAST:
                # Size changed or mtime differs by > 1.5 seconds (FAT tolerance)
                if item.size_bytes != prev.size_bytes or abs(item.mtime - prev.mtime) > 1.5:
                    modified = True
            elif mode == IncrementalMode.BALANCED:
                if item.size_bytes != prev.size_bytes or abs(item.mtime - prev.mtime) > 1.0:
                    modified = True
            elif mode == IncrementalMode.STRICT:
                if item.size_bytes != prev.size_bytes:
                    modified = True
                else:
                    # Compare SHA-256
                    try:
                        curr_hash = HashTools.compute_file_hash(item.absolute_path, algorithm="SHA-256")
                        item.sha256 = curr_hash
                        if prev.sha256 and curr_hash.lower() != prev.sha256.lower():
                            modified = True
                    except Exception:
                        modified = True

            if modified:
                item.is_modified = True
                report.modified_files.append(item)
                report.total_bytes_to_copy += item.size_bytes
            else:
                report.unchanged_files.append(item)

        # 4. Ransomware-Awareness: Check for sudden mass changes
        if check_mass_changes and len(previous_versions) > 50:
            changed_count = len(report.modified_files) + len(report.deleted_paths)
            change_ratio = changed_count / len(previous_versions)
            if change_ratio >= 0.60 or changed_count > 1000:
                report.unusual_mass_changes = True
                report.mass_change_reason = (
                    f"تم رصد تغير أو حذف مفاجئ لـ ({changed_count}) ملفًا ({change_ratio * 100:.1f}%) "
                    f"من إجمالي ({len(previous_versions)}) ملفًا في النسخة السابقة. "
                    f"يرجى مراجعة التغييرات قبل المتابعة لمنع الكتابة فوق النسخ الصالحة."
                )

        return report
