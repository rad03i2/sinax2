# -*- coding: utf-8 -*-
"""
SINAX Fast Storage Scanner
High-performance local filesystem traversal engine with:
- Symlink / Junction / Reparse point recursion safety
- Hard-link deduplication (inode tracking)
- Logical Size vs Allocated Size (NTFS cluster rounding)
- Real-time progress, pause, and cancellation
- Hierarchical tree generation for Treemap and Folder Tree views
"""

import math
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.core.logger import get_logger

logger = get_logger("storage_scanner")

# Default cluster allocation size (4 KB on standard NTFS)
DEFAULT_CLUSTER_SIZE = 4096


def format_bytes(size_bytes: int) -> str:
    """Format bytes into readable string with Arabic units."""
    if size_bytes <= 0:
        return "0 بايت"
    units = ["بايت", "كيلوبايت", "ميجابايت", "جيجابايت", "تيرابايت", "بيتابايت"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    if i == 0:
        return f"{int(size)} {units[i]}"
    return f"{size:.1f} {units[i]}"

# Extension to Category Mapping
CATEGORY_EXTENSIONS: Dict[str, Set[str]] = {
    "videos": {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        ".mpg", ".mpeg", ".3gp", ".ts", ".vob", ".iso"
    },
    "images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif",
        ".svg", ".ico", ".raw", ".cr2", ".nef", ".arw", ".psd", ".ai"
    },
    "audio": {
        ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".opus", ".wma",
        ".aiff", ".alac", ".ac3", ".amr", ".mid", ".midi"
    },
    "documents": {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
        ".rtf", ".odt", ".ods", ".odp", ".csv", ".tsv", ".epub", ".mobi",
        ".md", ".html", ".htm", ".json", ".xml", ".yaml", ".yml"
    },
    "archives": {
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".cab", ".tgz"
    },
    "executables": {
        ".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs", ".dll", ".sys", ".drv"
    },
    "installers": {
        ".msi", ".pkg", ".setup.exe", ".installer.exe"
    },
    "system": {
        ".sys", ".dll", ".drv", ".cpl", ".ocx", ".cab", ".cat", ".inf"
    }
}


def get_file_category(filename: str) -> str:
    """Categorize file based on extension and filename."""
    lower = filename.lower()
    if lower.endswith(("setup.exe", "installer.exe", "install.exe")):
        return "installers"

    _, ext = os.path.splitext(lower)
    for cat, exts in CATEGORY_EXTENSIONS.items():
        if ext in exts:
            return cat
    return "other"


@dataclass
class FileItem:
    name: str
    path: str
    size: int               # Logical size in bytes
    allocated_size: int     # Size on disk (cluster rounded)
    category: str
    ext: str
    modified_time: float
    created_time: float
    is_hardlink: bool = False


@dataclass
class FolderNode:
    name: str
    path: str
    size: int = 0
    allocated_size: int = 0
    files_count: int = 0
    subfolders_count: int = 0
    modified_time: float = 0.0
    children: List["FolderNode"] = field(default_factory=list)
    files: List[FileItem] = field(default_factory=list)

    def to_dict(self, max_depth: int = 4, current_depth: int = 0) -> Dict[str, Any]:
        """Convert tree to dictionary for Treemap and serializing."""
        data: Dict[str, Any] = {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "allocated_size": self.allocated_size,
            "files_count": self.files_count,
            "subfolders_count": self.subfolders_count,
        }
        if current_depth < max_depth and self.children:
            data["children"] = [
                c.to_dict(max_depth, current_depth + 1)
                for c in sorted(self.children, key=lambda x: x.size, reverse=True)[:50]
            ]
        return data


@dataclass
class ScanResult:
    root_path: str
    total_size: int = 0
    total_allocated: int = 0
    total_files: int = 0
    total_folders: int = 0
    elapsed_seconds: float = 0.0
    root_node: Optional[FolderNode] = None
    categories_size: Dict[str, int] = field(default_factory=dict)
    categories_count: Dict[str, int] = field(default_factory=dict)
    age_distribution: Dict[str, int] = field(default_factory=dict)
    extension_sizes: Dict[str, int] = field(default_factory=dict)
    top_files: List[FileItem] = field(default_factory=list)
    top_folders: List[Tuple[str, int]] = field(default_factory=list)
    all_files: List[FileItem] = field(default_factory=list)
    allocated_size: int = 0
    errors: List[str] = field(default_factory=list)
    is_cancelled: bool = False

    @property
    def duration(self) -> float:
        return self.elapsed_seconds


class ScanToken:
    """Thread-safe cancellation and pause token."""
    def __init__(self):
        self._cancelled = threading.Event()
        self._paused = threading.Event()
        self._paused.set() # Unpaused initially

    def cancel(self):
        self._cancelled.set()
        self._paused.set() # Ensure loop unblocks

    def pause(self):
        self._paused.clear()

    def resume(self):
        self._paused.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def wait_if_paused(self):
        self._paused.wait()


class StorageScanner:
    """Fast traversal engine scanning directories and computing statistics."""

    def __init__(self, cluster_size: int = DEFAULT_CLUSTER_SIZE):
        self.cluster_size = cluster_size

    def scan_path(
        self,
        root_path: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        token: Optional[ScanToken] = None,
        max_top_files: int = 500,
    ) -> ScanResult:
        start_t = time.time()
        root_path = str(Path(root_path).resolve())
        result = ScanResult(root_path=root_path)

        # Initialize tracking containers
        for cat in list(CATEGORY_EXTENSIONS.keys()) + ["other"]:
            result.categories_size[cat] = 0
            result.categories_count[cat] = 0

        # Age brackets
        now = time.time()
        age_brackets = {
            "week": 0,       # < 7 days
            "month": 0,      # 7-30 days
            "6months": 0,    # 30-180 days
            "year": 0,       # 180-365 days
            "3years": 0,     # 1-3 years
            "older": 0,      # > 3 years
        }

        visited_inodes: Set[Tuple[int, int]] = set() # (dev, ino) to avoid counting hard-links twice
        all_files: List[FileItem] = []
        all_folder_sizes: List[Tuple[str, int]] = []

        last_cb_time = 0.0
        files_scanned = 0
        folders_scanned = 0
        bytes_scanned = 0

        def emit_progress(curr_path: str):
            nonlocal last_cb_time
            t = time.time()
            if progress_callback and (t - last_cb_time > 0.15):
                last_cb_time = t
                progress_callback({
                    "files": files_scanned,
                    "folders": folders_scanned,
                    "size": bytes_scanned,
                    "current_path": curr_path,
                })

        def is_reparse_point(entry: os.DirEntry) -> bool:
            """Detect junctions, symlinks, or reparse points to avoid recursion loops."""
            try:
                if entry.is_symlink():
                    return True
                # Check Windows file attributes for FILE_ATTRIBUTE_REPARSE_POINT (0x0400)
                st = entry.stat(follow_symlinks=False)
                attrs = getattr(st, "st_file_attributes", 0)
                return bool(attrs & 0x0400)
            except Exception:
                return True

        def _traverse(dir_path: str, depth: int = 0) -> FolderNode:
            nonlocal files_scanned, folders_scanned, bytes_scanned
            node = FolderNode(name=Path(dir_path).name or dir_path, path=dir_path)
            folders_scanned += 1
            emit_progress(dir_path)

            try:
                with os.scandir(dir_path) as it:
                    for entry in it:
                        if token:
                            token.wait_if_paused()
                            if token.is_cancelled:
                                result.is_cancelled = True
                                return node

                        # Reparse point check (Junctions, Symlinks)
                        if is_reparse_point(entry):
                            continue

                        try:
                            if entry.is_file(follow_symlinks=False):
                                st = entry.stat(follow_symlinks=False)
                                size = st.st_size
                                allocated = int(math.ceil(size / self.cluster_size) * self.cluster_size) if size > 0 else 0

                                # Hard link check
                                is_hl = False
                                dev_ino = (st.st_dev, st.st_ino)
                                if st.st_nlink > 1:
                                    if dev_ino in visited_inodes:
                                        is_hl = True
                                    else:
                                        visited_inodes.add(dev_ino)
                                else:
                                    visited_inodes.add(dev_ino)

                                f_item = FileItem(
                                    name=entry.name,
                                    path=entry.path,
                                    size=size,
                                    allocated_size=allocated,
                                    category=get_file_category(entry.name),
                                    ext=Path(entry.name).suffix.lower(),
                                    modified_time=st.st_mtime,
                                    created_time=st.st_ctime,
                                    is_hardlink=is_hl,
                                )

                                node.files_count += 1
                                if not is_hl:
                                    node.size += size
                                    node.allocated_size += allocated
                                    bytes_scanned += size

                                    # Category stats
                                    cat = f_item.category
                                    result.categories_size[cat] = result.categories_size.get(cat, 0) + size
                                    result.categories_count[cat] = result.categories_count.get(cat, 0) + 1

                                    # Extension stats
                                    ext = f_item.ext or "(none)"
                                    result.extension_sizes[ext] = result.extension_sizes.get(ext, 0) + size

                                    # Age stats
                                    age_days = (now - st.st_mtime) / 86400.0
                                    if age_days < 7:
                                        age_brackets["week"] += size
                                    elif age_days < 30:
                                        age_brackets["month"] += size
                                    elif age_days < 180:
                                        age_brackets["6months"] += size
                                    elif age_days < 365:
                                        age_brackets["year"] += size
                                    elif age_days < 1095:
                                        age_brackets["3years"] += size
                                    else:
                                        age_brackets["older"] += size

                                    all_files.append(f_item)

                                files_scanned += 1

                            elif entry.is_dir(follow_symlinks=False):
                                sub_node = _traverse(entry.path, depth + 1)
                                node.children.append(sub_node)
                                node.size += sub_node.size
                                node.allocated_size += sub_node.allocated_size
                                node.files_count += sub_node.files_count
                                node.subfolders_count += 1 + sub_node.subfolders_count

                        except (PermissionError, FileNotFoundError) as pe:
                            result.errors.append(f"{entry.path}: {pe}")
                        except Exception as e:
                            logger.debug(f"Error scanning entry {entry.path}: {e}")

            except (PermissionError, FileNotFoundError) as e:
                result.errors.append(f"{dir_path}: {e}")
            except Exception as e:
                logger.error(f"Error opening directory {dir_path}: {e}")

            all_folder_sizes.append((dir_path, node.size))
            return node

        # Run traversal
        result.root_node = _traverse(root_path)

        result.total_size = result.root_node.size if result.root_node else 0
        result.total_allocated = result.root_node.allocated_size if result.root_node else 0
        result.total_files = files_scanned
        result.total_folders = folders_scanned
        result.elapsed_seconds = time.time() - start_t
        result.age_distribution = age_brackets

        # Extract top files (sorted descending by logical size)
        all_files.sort(key=lambda x: x.size, reverse=True)
        result.top_files = all_files[:max_top_files]

        # Extract top folders (exclude root itself, sorted descending)
        all_folder_sizes.sort(key=lambda x: x[1], reverse=True)
        result.top_folders = [f for f in all_folder_sizes if f[0] != root_path][:50]

        # Final progress callback
        if progress_callback:
            progress_callback({
                "files": files_scanned,
                "folders": folders_scanned,
                "size": result.total_size,
                "current_path": "اكتمل المسح!",
                "finished": True,
            })

        result.all_files = all_files
        result.allocated_size = result.total_allocated

        logger.info(
            f"Storage scan completed for {root_path}: {files_scanned} files, "
            f"{folders_scanned} folders, {result.total_size / (1024**3):.2f} GB in {result.elapsed_seconds:.2f}s"
        )
        return result

    scan = scan_path


FastStorageScanner = StorageScanner
storage_scanner = StorageScanner()
