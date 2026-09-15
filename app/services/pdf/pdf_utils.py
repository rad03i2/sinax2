# -*- coding: utf-8 -*-
"""
SINAX PDF Utilities
Helper functions for page range parsing, size conversions, coordinates, and safe atomic files.
"""

import re
import shutil
import tempfile
from pathlib import Path
from typing import List, Set, Tuple, Optional

# Standard Page Sizes in points (72 points per inch)
PAGE_SIZES = {
    "a4": (595.28, 841.89),
    "a3": (841.89, 1190.55),
    "a5": (419.53, 595.28),
    "letter": (612.0, 792.0),
    "legal": (612.0, 1008.0),
    "tabloid": (792.0, 1224.0),
}

def parse_page_ranges(range_str: str, total_pages: int) -> List[int]:
    """
    Parses a page range string (e.g. '1, 3-5, 8, 10-12') into 0-based page indices.
    If range_str is empty or 'all', returns all pages [0, 1, ..., total_pages - 1].
    Invalid or out-of-range pages are safely clamped and filtered.
    """
    if not range_str or range_str.strip().lower() in ("all", "الكل", "*"):
        return list(range(total_pages))

    result: List[int] = []
    seen: Set[int] = set()

    # Normalize separators (Arabic comma, western comma, semicolon)
    normalized = range_str.replace("،", ",").replace(";", ",")
    parts = normalized.split(",")

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) == 2 and bounds[0].strip().isdigit() and bounds[1].strip().isdigit():
                start = max(1, int(bounds[0].strip()))
                end = min(total_pages, int(bounds[1].strip()))
                if start <= end:
                    for p in range(start, end + 1):
                        idx = p - 1
                        if idx not in seen and 0 <= idx < total_pages:
                            seen.add(idx)
                            result.append(idx)
                else:
                    # Reverse range
                    for p in range(start, end - 1, -1):
                        idx = p - 1
                        if idx not in seen and 0 <= idx < total_pages:
                            seen.add(idx)
                            result.append(idx)
        elif part.isdigit():
            p = int(part)
            idx = p - 1
            if idx not in seen and 0 <= idx < total_pages:
                seen.add(idx)
                result.append(idx)

    return result

def format_page_list(page_indices: List[int]) -> str:
    """Formats a list of 0-based page indices into human-readable 1-based ranges."""
    if not page_indices:
        return ""
    sorted_pages = sorted(list(set(p + 1 for p in page_indices)))
    ranges = []
    start = end = sorted_pages[0]

    for p in sorted_pages[1:]:
        if p == end + 1:
            end = p
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = end = p

    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)

def get_page_size_points(size_name: str, orientation: str = "portrait") -> Tuple[float, float]:
    """Returns width and height in points for standard page names."""
    w, h = PAGE_SIZES.get(size_name.lower().strip(), PAGE_SIZES["a4"])
    if orientation.lower() == "landscape" and w < h:
        return h, w
    elif orientation.lower() == "portrait" and w > h:
        return h, w
    return w, h

def create_safe_output_path(source_path: Path, output_dir: Optional[Path] = None, suffix: str = "_sinax", ext: str = ".pdf") -> Path:
    """
    Generates a collision-safe destination path that never overwrites the original file
    unless explicitly requested.
    """
    target_dir = output_dir if output_dir else source_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    stem = source_path.stem
    candidate = target_dir / f"{stem}{suffix}{ext}"
    counter = 1
    while candidate.exists():
        candidate = target_dir / f"{stem}{suffix}_{counter}{ext}"
        counter += 1
    return candidate
