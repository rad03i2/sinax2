# -*- coding: utf-8 -*-
"""
SINAX Storage Analyzer
Processes raw storage scan results and generates deep insights:
- Category breakdowns (Images, Videos, Audio, Documents, Archives, etc.)
- Age distributions (<1 month, 1-6 months, 6-12 months, >1 year)
- Extension breakdowns
- Top N largest files and Top N largest folders
- System reserved space detection (pagefile.sys, hiberfil.sys, swapfile.sys, Windows.old)
- Specialized Downloads folder analysis
"""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger
from app.services.system_storage.storage_scanner import FileItem, FolderNode, ScanResult, format_bytes

logger = get_logger("storage_analyzer")


@dataclass
class CategoryStats:
    name: str
    label_ar: str
    size: int = 0
    count: int = 0
    percentage: float = 0.0
    color: str = "#4361EE"


@dataclass
class AgeStats:
    label_ar: str
    size: int = 0
    count: int = 0
    percentage: float = 0.0


@dataclass
class ExtensionStats:
    ext: str
    category: str
    size: int = 0
    count: int = 0
    percentage: float = 0.0


@dataclass
class SystemReservedInfo:
    pagefile_size: int = 0
    hiberfil_size: int = 0
    swapfile_size: int = 0
    windows_old_size: int = 0
    windows_old_path: Optional[str] = None
    total_reserved_size: int = 0


@dataclass
class DownloadsAnalysis:
    total_size: int = 0
    total_files: int = 0
    installers_size: int = 0
    installers_count: int = 0
    archives_size: int = 0
    archives_count: int = 0
    old_files_size: int = 0       # Not modified in > 90 days
    old_files_count: int = 0
    large_files: List[FileItem] = field(default_factory=list)


@dataclass
class StorageAnalysisReport:
    target_path: str
    total_size: int
    allocated_size: int
    total_files: int
    total_folders: int
    scan_duration: float
    categories: Dict[str, CategoryStats]
    age_distribution: List[AgeStats]
    top_extensions: List[ExtensionStats]
    top_files: List[FileItem]
    top_folders: List[Dict[str, Any]]
    system_reserved: SystemReservedInfo
    downloads_analysis: Optional[DownloadsAnalysis] = None


CATEGORY_CONFIG = {
    "videos": {"label_ar": "فيديو", "color": "#E63946"},
    "images": {"label_ar": "صور", "color": "#F4A261"},
    "audio": {"label_ar": "صوتيات", "color": "#2A9D8F"},
    "documents": {"label_ar": "مستندات", "color": "#457B9D"},
    "archives": {"label_ar": "أرشيف ومضغوطات", "color": "#9B5DE5"},
    "executables": {"label_ar": "برامج وتطبيقات", "color": "#00BBF9"},
    "installers": {"label_ar": "ملفات التثبيت", "color": "#F15BB5"},
    "system": {"label_ar": "ملفات النظام", "color": "#6C757D"},
    "other": {"label_ar": "أخرى", "color": "#8D99AE"},
}


class StorageAnalyzer:
    """Analyzes ScanResult or raw files and compiles comprehensive storage breakdown."""

    @staticmethod
    def detect_system_reserved(drive_letter: str = "C:") -> SystemReservedInfo:
        """Detect presence and size of Windows system-reserved files (pagefile, hiberfil, Windows.old)."""
        info = SystemReservedInfo()
        drive = drive_letter.rstrip("\\/").upper()
        if not drive.endswith(":"):
            drive += ":"
        root = Path(f"{drive}\\")

        # System root files
        pagefile = root / "pagefile.sys"
        hiberfil = root / "hiberfil.sys"
        swapfile = root / "swapfile.sys"
        win_old = root / "Windows.old"

        try:
            if pagefile.exists():
                info.pagefile_size = pagefile.stat().st_size
        except Exception as e:
            logger.debug(f"Could not read pagefile.sys: {e}")

        try:
            if hiberfil.exists():
                info.hiberfil_size = hiberfil.stat().st_size
        except Exception as e:
            logger.debug(f"Could not read hiberfil.sys: {e}")

        try:
            if swapfile.exists():
                info.swapfile_size = swapfile.stat().st_size
        except Exception as e:
            logger.debug(f"Could not read swapfile.sys: {e}")

        try:
            if win_old.exists() and win_old.is_dir():
                info.windows_old_path = str(win_old)
                # Quick shallow or bounded size calculation for Windows.old
                total_win_old = 0
                for dirpath, _, filenames in os.walk(win_old):
                    for f in filenames:
                        try:
                            fp = os.path.join(dirpath, f)
                            total_win_old += os.path.getsize(fp)
                        except (OSError, PermissionError):
                            continue
                info.windows_old_size = total_win_old
        except Exception as e:
            logger.debug(f"Could not check Windows.old: {e}")

        info.total_reserved_size = (
            info.pagefile_size + info.hiberfil_size + info.swapfile_size + info.windows_old_size
        )
        return info

    @staticmethod
    def analyze_scan_result(scan_result: ScanResult, is_drive_root: bool = False) -> StorageAnalysisReport:
        """Generate a complete StorageAnalysisReport from a ScanResult."""
        total_size = scan_result.total_size
        now = time.time()

        # 1. Categories
        categories: Dict[str, CategoryStats] = {}
        for cat_key, conf in CATEGORY_CONFIG.items():
            categories[cat_key] = CategoryStats(
                name=cat_key,
                label_ar=conf["label_ar"],
                color=conf["color"]
            )

        # 2. Age Distribution Buckets:
        # < 1 month (30 days), 1-6 months (180 days), 6-12 months (365 days), > 1 year
        age_buckets = [
            {"label_ar": "أقل من شهر", "max_days": 30, "size": 0, "count": 0},
            {"label_ar": "1 - 6 أشهر", "max_days": 180, "size": 0, "count": 0},
            {"label_ar": "6 - 12 شهر", "max_days": 365, "size": 0, "count": 0},
            {"label_ar": "أكثر من سنة", "max_days": float("inf"), "size": 0, "count": 0},
        ]

        # 3. Extensions Tracker
        ext_map: Dict[str, Dict[str, Any]] = {}

        for item in scan_result.all_files:
            # Category
            cat = item.category if item.category in categories else "other"
            categories[cat].size += item.size
            categories[cat].count += 1

            # Age
            age_days = max(0.0, (now - item.modified_time) / 86400.0)
            if age_days <= 30:
                age_buckets[0]["size"] += item.size
                age_buckets[0]["count"] += 1
            elif age_days <= 180:
                age_buckets[1]["size"] += item.size
                age_buckets[1]["count"] += 1
            elif age_days <= 365:
                age_buckets[2]["size"] += item.size
                age_buckets[2]["count"] += 1
            else:
                age_buckets[3]["size"] += item.size
                age_buckets[3]["count"] += 1

            # Extension
            ext_clean = item.ext.lower() if item.ext else "بدون امتداد"
            if ext_clean not in ext_map:
                ext_map[ext_clean] = {"size": 0, "count": 0, "cat": cat}
            ext_map[ext_clean]["size"] += item.size
            ext_map[ext_clean]["count"] += 1

        # Calculate percentages for categories
        for cat in categories.values():
            cat.percentage = (cat.size / total_size * 100.0) if total_size > 0 else 0.0

        # Calculate age stats
        age_stats_list: List[AgeStats] = []
        for b in age_buckets:
            pct = (b["size"] / total_size * 100.0) if total_size > 0 else 0.0
            age_stats_list.append(AgeStats(
                label_ar=b["label_ar"],
                size=b["size"],
                count=b["count"],
                percentage=pct
            ))

        # Sort and limit top extensions
        sorted_exts = sorted(ext_map.items(), key=lambda x: x[1]["size"], reverse=True)
        top_exts: List[ExtensionStats] = []
        for ext_name, data in sorted_exts[:30]:
            pct = (data["size"] / total_size * 100.0) if total_size > 0 else 0.0
            top_exts.append(ExtensionStats(
                ext=ext_name,
                category=data["cat"],
                size=data["size"],
                count=data["count"],
                percentage=pct
            ))

        # Check system reserved if scanning a drive root
        system_reserved = SystemReservedInfo()
        if is_drive_root or (len(scan_result.root_node.path) <= 3 and ":" in scan_result.root_node.path):
            drive_letter = scan_result.root_node.path[:2]
            system_reserved = StorageAnalyzer.detect_system_reserved(drive_letter)

        # Downloads analysis if target is downloads folder
        downloads_analysis = None
        target_lower = scan_result.root_node.path.lower()
        if "download" in target_lower or "تنزيل" in target_lower:
            downloads_analysis = StorageAnalyzer.analyze_downloads_files(scan_result.all_files)

        return StorageAnalysisReport(
            target_path=scan_result.root_node.path,
            total_size=scan_result.total_size,
            allocated_size=scan_result.allocated_size,
            total_files=scan_result.total_files,
            total_folders=scan_result.total_folders,
            scan_duration=scan_result.duration,
            categories=categories,
            age_distribution=age_stats_list,
            top_extensions=top_exts,
            top_files=scan_result.top_files,
            top_folders=scan_result.top_folders,
            system_reserved=system_reserved,
            downloads_analysis=downloads_analysis
        )

    @staticmethod
    def analyze_downloads_files(files: List[FileItem]) -> DownloadsAnalysis:
        """Analyze files in Downloads folder for installers, archives, stale downloads."""
        analysis = DownloadsAnalysis()
        analysis.total_files = len(files)
        now = time.time()

        for item in files:
            analysis.total_size += item.size

            # Installers
            if item.category == "installers" or item.name.lower().endswith((".exe", ".msi", ".iso")):
                analysis.installers_size += item.size
                analysis.installers_count += 1

            # Archives
            if item.category == "archives":
                analysis.archives_size += item.size
                analysis.archives_count += 1

            # Old files (> 90 days)
            age_days = (now - item.modified_time) / 86400.0
            if age_days > 90:
                analysis.old_files_size += item.size
                analysis.old_files_count += 1

        # Sort top large downloads
        analysis.large_files = sorted(files, key=lambda x: x.size, reverse=True)[:50]
        return analysis
