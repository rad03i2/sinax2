# -*- coding: utf-8 -*-
"""
SINAX Folder Quick Tools
Folder size and statistics, directory tree generator (ASCII/Unicode/Markdown/JSON),
file name extraction, folder comparison, empty folder finder, and path issue inspectors.
"""

from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}


class FolderTools:
    """Operations on directory trees, inventories, and path structure analysis."""

    @staticmethod
    def calculate_folder_stats(
        folder_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """Scans a directory tree, computing total size, counts, and extension breakdown."""
        root = Path(folder_path)
        if not root.is_dir():
            raise NotADirectoryError(f"Directory not found: {folder_path}")

        total_files = 0
        total_folders = 0
        total_bytes = 0
        ext_counter = Counter()

        largest_file: Optional[Tuple[str, int]] = None
        newest_file: Optional[Tuple[str, float]] = None

        for dirpath, dirnames, filenames in os.walk(folder_path):
            if cancel_check and cancel_check():
                raise InterruptedError("Folder scan cancelled.")

            total_folders += len(dirnames)

            for f in filenames:
                total_files += 1
                fp = os.path.join(dirpath, f)
                try:
                    st = os.stat(fp)
                    sz = st.st_size
                    total_bytes += sz

                    ext = os.path.splitext(f)[1].lower() or "(بدون امتداد)"
                    ext_counter[ext] += 1

                    if not largest_file or sz > largest_file[1]:
                        largest_file = (f, sz)
                    if not newest_file or st.st_mtime > newest_file[1]:
                        newest_file = (f, st.st_mtime)
                except Exception:
                    pass

                if progress_callback and total_files % 100 == 0:
                    progress_callback(total_files, total_bytes, f)

        from app.services.quick_tools.tools.file_tools import FileTools
        newest_str = datetime.fromtimestamp(newest_file[1]).strftime("%Y-%m-%d %H:%M") if newest_file else "غير متوفر"

        return {
            "folder_name": root.name,
            "total_files": total_files,
            "total_folders": total_folders,
            "total_bytes": total_bytes,
            "size_human": FileTools.format_size(total_bytes),
            "top_extensions": ext_counter.most_common(8),
            "largest_file": largest_file[0] if largest_file else "لا يوجد",
            "largest_file_size": FileTools.format_size(largest_file[1]) if largest_file else "0 B",
            "newest_file": newest_file[0] if newest_file else "لا يوجد",
            "newest_date": newest_str,
        }

    @staticmethod
    def extract_file_names(
        folder_path: str,
        recursive: bool = True,
        output_format: str = "TXT", # 'TXT', 'CSV', 'JSON'
        include_paths: bool = False,
        relative_paths: bool = True
    ) -> str:
        """Extracts listing of all files in folder and serializes to requested format."""
        root = Path(folder_path)
        items = []

        if recursive:
            generator = root.rglob("*")
        else:
            generator = root.glob("*")

        for p in generator:
            if p.is_file():
                if include_paths:
                    val = p.relative_to(root).as_posix() if relative_paths else str(p.resolve())
                else:
                    val = p.name
                items.append(val)

        items.sort()

        if output_format == "JSON":
            return json.dumps(items, indent=2, ensure_ascii=False)
        elif output_format == "CSV":
            return "Name\n" + "\n".join(f'"{i}"' for i in items)
        return "\n".join(items)

    @staticmethod
    def generate_directory_tree(
        folder_path: str,
        max_depth: int = 3,
        show_files: bool = True,
        style: str = "unicode" # 'unicode', 'ascii', 'markdown'
    ) -> str:
        """Generates visual hierarchy tree of directory."""
        root = Path(folder_path)
        if not root.is_dir():
            return "المجلد غير موجود"

        branch = "├── " if style == "unicode" else "|-- "
        tee = "└── " if style == "unicode" else "`-- "
        pipe = "│   " if style == "unicode" else "|   "
        space = "    "

        lines = [f"{root.name}/" if style != "markdown" else f"# {root.name}"]

        def _walk(dir_path: Path, prefix: str, depth: int):
            if depth > max_depth:
                return

            try:
                entries = sorted(list(dir_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return

            if not show_files:
                entries = [e for e in entries if e.is_dir()]

            count = len(entries)
            for idx, entry in enumerate(entries):
                is_last = (idx == count - 1)
                connector = tee if is_last else branch

                if style == "markdown":
                    indent = "  " * depth
                    if entry.is_dir():
                        lines.append(f"{indent}- 📁 **{entry.name}/**")
                    else:
                        lines.append(f"{indent}- 📄 {entry.name}")
                else:
                    lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")

                if entry.is_dir():
                    extension = space if is_last else pipe
                    _walk(entry, prefix + extension, depth + 1)

        _walk(root, "", 1)
        return "\n".join(lines)

    @staticmethod
    def compare_folder_listings(dir_a: str, dir_b: str) -> Dict[str, Any]:
        """Compares metadata listings between two directories."""
        root_a = Path(dir_a)
        root_b = Path(dir_b)

        files_a = {p.relative_to(root_a).as_posix(): p.stat() for p in root_a.rglob("*") if p.is_file()}
        files_b = {p.relative_to(root_b).as_posix(): p.stat() for p in root_b.rglob("*") if p.is_file()}

        only_a = [k for k in files_a if k not in files_b]
        only_b = [k for k in files_b if k not in files_a]

        common = [k for k in files_a if k in files_b]
        diff_size = [k for k in common if files_a[k].st_size != files_b[k].st_size]
        diff_date = [k for k in common if int(files_a[k].st_mtime) != int(files_b[k].st_mtime)]
        identical = [k for k in common if k not in diff_size and k not in diff_date]

        return {
            "total_in_a": len(files_a),
            "total_in_b": len(files_b),
            "only_in_a_count": len(only_a),
            "only_in_b_count": len(only_b),
            "different_size_count": len(diff_size),
            "different_date_count": len(diff_date),
            "identical_count": len(identical),
            "only_in_a": sorted(only_a),
            "only_in_b": sorted(only_b),
            "different_size": sorted(diff_size),
            "different_date": sorted(diff_date),
        }

    @staticmethod
    def find_empty_folders(folder_path: str) -> List[str]:
        """Returns list of directories that contain no files or only empty subdirectories."""
        empty = []
        for dirpath, dirnames, filenames in os.walk(folder_path, topdown=False):
            # If no files and no subdirectories left
            if not filenames and not dirnames:
                empty.append(dirpath)
        return empty

    @staticmethod
    def find_long_paths(folder_path: str, threshold: int = 240) -> List[Tuple[str, int]]:
        """Finds items exceeding Windows path limit length threshold."""
        long_paths = []
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for name in dirnames + filenames:
                full = os.path.join(dirpath, name)
                if len(full) >= threshold:
                    long_paths.append((full, len(full)))
        long_paths.sort(key=lambda x: x[1], reverse=True)
        return long_paths

    @staticmethod
    def inspect_problematic_names(folder_path: str) -> List[Dict[str, str]]:
        """Detects files with problematic or reserved Windows characters."""
        issues = []
        illegal_chars = set('<>:"/\\|?*')

        for dirpath, dirnames, filenames in os.walk(folder_path):
            for name in dirnames + filenames:
                reasons = []
                stem = Path(name).stem.upper()
                if stem in WINDOWS_RESERVED_NAMES:
                    reasons.append(f"اسم DOS محجوز لـ Windows ({stem})")
                if any(c in illegal_chars for c in name):
                    reasons.append("يحتوي على رموز ممنوعة (< > : \" / \\ | ? *)")
                if name.endswith(" ") or name.endswith("."):
                    reasons.append("ينتهي بمسافة أو نقطة")

                if reasons:
                    issues.append({
                        "name": name,
                        "path": os.path.join(dirpath, name),
                        "issues": ", ".join(reasons),
                    })
        return issues
