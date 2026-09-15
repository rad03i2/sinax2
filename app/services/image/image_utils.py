# -*- coding: utf-8 -*-
"""
SINAX Image Utilities
Helper utilities for image file scanning, directory tree preservation,
proxy thumbnail generation, and metadata helpers.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Set, Tuple, Generator
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

# Recognized image extensions
SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp",
    ".tiff", ".tif", ".gif", ".ico", ".heic", ".heif"
}

# In-memory LRU-like thumbnail cache
_THUMBNAIL_CACHE: dict = {}
_MAX_CACHE_ENTRIES = 500


def scan_images(sources: List[Path], recursive: bool = True) -> List[Path]:
    """
    Scans a list of paths (files or directories) and returns all valid image files.
    Ensures no duplicate paths and sorts naturally.
    """
    found_files: List[Path] = []
    seen: Set[str] = set()

    for src in sources:
        try:
            p = Path(src).resolve()
            if not p.exists():
                continue

            if p.is_file():
                if p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                    p_str = str(p)
                    if p_str not in seen:
                        seen.add(p_str)
                        found_files.append(p)
            elif p.is_dir():
                pattern = "**/*" if recursive else "*"
                for entry in p.glob(pattern):
                    if entry.is_file() and entry.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                        entry_str = str(entry)
                        if entry_str not in seen:
                            seen.add(entry_str)
                            found_files.append(entry)
        except Exception:
            continue

    return found_files


def get_relative_output_path(
    source_file: Path,
    base_folder: Optional[Path],
    output_folder: Path,
    suffix: str = "",
    new_ext: Optional[str] = None
) -> Path:
    """
    Computes output path while preserving folder hierarchy if base_folder is provided.
    
    Example:
      source_file = /photos/2024/summer/pic.jpg
      base_folder = /photos
      output_folder = /compressed
      Result: /compressed/2024/summer/pic_compressed.jpg
    """
    src = Path(source_file).resolve()
    out = Path(output_folder).resolve()

    stem = src.stem + suffix
    ext = (new_ext if new_ext else src.suffix).lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    target_filename = f"{stem}{ext}"

    if base_folder:
        try:
            base = Path(base_folder).resolve()
            rel_dir = src.parent.relative_to(base)
            target_dir = out / rel_dir
        except (ValueError, Exception):
            target_dir = out
    else:
        target_dir = out

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / target_filename


def get_proxy_thumbnail(image_path: Path, size: Tuple[int, int] = (64, 64)) -> Optional[QPixmap]:
    """
    Generates or retrieves a lightweight proxy thumbnail for display in tables or lists.
    Uses memory cache to avoid repeatedly decoding full resolution images.
    """
    cache_key = (str(image_path), size)
    if cache_key in _THUMBNAIL_CACHE:
        return _THUMBNAIL_CACHE[cache_key]

    try:
        from PIL import Image, ImageOps
        with Image.open(image_path) as img:
            # Handle orientation for thumbnail
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            img.thumbnail(size, Image.Resampling.BOX)
            
            # Convert PIL image to QPixmap
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            data = img.tobytes("raw", "RGBA")
            qim = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qim)

            if len(_THUMBNAIL_CACHE) >= _MAX_CACHE_ENTRIES:
                # Discard oldest 100 entries
                for k in list(_THUMBNAIL_CACHE.keys())[:100]:
                    del _THUMBNAIL_CACHE[k]

            _THUMBNAIL_CACHE[cache_key] = pixmap
            return pixmap
    except Exception:
        return None


def format_size(size_bytes: int) -> str:
    """Formats byte count into human readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024.0:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024.0 * 1024.0):.2f} MB"
    else:
        return f"{size_bytes / (1024.0 * 1024.0 * 1024.0):.2f} GB"
