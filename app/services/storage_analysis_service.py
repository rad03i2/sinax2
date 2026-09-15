# -*- coding: utf-8 -*-
"""
SINAX Storage & Space Analysis Service
Scans folder trees to compute disk space distribution, category breakdown,
top space hogs, and age distribution metrics.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any

from app.core.constants import FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.models.file_item import format_file_size
from app.core.logger import get_logger

logger = get_logger("storage_analysis_service")


@dataclass
class StorageItemInfo:
    """Represents a file tracked in storage analysis."""
    path: Path
    filename: str
    size_bytes: int
    formatted_size: str
    category_key: str
    category_label: str
    modified_time: Optional[datetime]
    formatted_date: str


@dataclass
class CategorySpaceInfo:
    """Storage stats for a single file category."""
    key: str
    label_ar: str
    color: str
    total_bytes: int = 0
    formatted_size: str = "0 بايت"
    file_count: int = 0
    percentage: float = 0.0


@dataclass
class StorageReport:
    """Complete analysis report of a directory tree."""
    directory: Path
    total_files: int = 0
    total_dirs: int = 0
    total_size_bytes: int = 0
    formatted_total_size: str = "0 بايت"
    categories: Dict[str, CategorySpaceInfo] = field(default_factory=dict)
    top_largest_files: List[StorageItemInfo] = field(default_factory=list)
    inactive_files: List[StorageItemInfo] = field(default_factory=list)  # > 180 days old
    subfolder_sizes: List[Dict[str, Any]] = field(default_factory=list)


class StorageAnalysisService:
    """Analyzes folder sizes, category distribution and largest files."""

    @staticmethod
    def analyze_directory(
        directory: Path,
        top_n: int = 50,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> StorageReport:
        """Performs full storage analytics on a directory tree."""
        report = StorageReport(directory=directory)
        if not directory or not directory.exists() or not directory.is_dir():
            return report

        # Initialize category map
        cat_map: Dict[str, CategorySpaceInfo] = {}
        for k, v in FILE_CATEGORIES.items():
            if k != "all":
                cat_map[k] = CategorySpaceInfo(
                    key=k,
                    label_ar=v.get("label_ar", k),
                    color=v.get("color", "#757575"),
                    total_bytes=0,
                    file_count=0
                )

        all_items: List[StorageItemInfo] = []
        dir_count = 0
        file_count = 0
        total_size = 0
        subfolder_totals: Dict[str, int] = {}
        now = datetime.now()
        six_months_ago = now - timedelta(days=180)

        for root, dirs, files in os.walk(directory):
            if is_cancelled and is_cancelled():
                logger.info("Storage analysis cancelled by user.")
                break

            dir_count += len(dirs)
            rel_root = Path(root).relative_to(directory)
            top_subfolder = rel_root.parts[0] if rel_root.parts else ""

            for fname in files:
                if is_cancelled and is_cancelled():
                    break

                fpath = Path(root) / fname
                try:
                    stat = fpath.stat()
                    sz = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                except (OSError, PermissionError):
                    continue

                file_count += 1
                total_size += sz

                if top_subfolder:
                    subfolder_totals[top_subfolder] = subfolder_totals.get(top_subfolder, 0) + sz

                ext = fpath.suffix.lower()
                cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
                if cat_key not in cat_map:
                    cat_key = "other"

                cat_info = cat_map[cat_key]
                cat_info.total_bytes += sz
                cat_info.file_count += 1

                item_info = StorageItemInfo(
                    path=fpath,
                    filename=fname,
                    size_bytes=sz,
                    formatted_size=format_file_size(sz),
                    category_key=cat_key,
                    category_label=cat_info.label_ar,
                    modified_time=mtime,
                    formatted_date=mtime.strftime("%Y-%m-%d")
                )
                all_items.append(item_info)

                if progress_callback and (file_count % 150 == 0):
                    progress_callback(file_count, 0, fname)

        # Compute percentages & formatted sizes
        for c in cat_map.values():
            c.formatted_size = format_file_size(c.total_bytes)
            c.percentage = (c.total_bytes / total_size * 100.0) if total_size > 0 else 0.0

        # Sort largest files
        all_items.sort(key=lambda x: x.size_bytes, reverse=True)
        top_files = all_items[:top_n]

        # Inactive files (> 180 days)
        old_items = [it for it in all_items if it.modified_time and it.modified_time < six_months_ago]
        old_items.sort(key=lambda x: x.size_bytes, reverse=True)

        # Top subfolders
        sorted_subfolders = [
            {"name": k, "size_bytes": v, "formatted_size": format_file_size(v)}
            for k, v in sorted(subfolder_totals.items(), key=lambda item: item[1], reverse=True)
        ]

        report.total_files = file_count
        report.total_dirs = dir_count
        report.total_size_bytes = total_size
        report.formatted_total_size = format_file_size(total_size)
        report.categories = cat_map
        report.top_largest_files = top_files
        report.inactive_files = old_items[:50]
        report.subfolder_sizes = sorted_subfolders[:20]

        return report
