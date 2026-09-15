# -*- coding: utf-8 -*-
"""
SINAX Naming & Slug Tools
Sanitizes filenames for Windows, generates URL slugs, and formats sequential numbers/templates.
"""

from pathlib import Path
import re
from typing import List, Optional


WINDOWS_ILLEGAL_CHAR_REGEX = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}


class NamingTools:
    """Utilities for cleaning and generating safe file names, slugs, and numbering sequences."""

    @staticmethod
    def sanitize_filename(
        name: str,
        replacement: str = "_",
        max_length: int = 240
    ) -> str:
        """Converts arbitrary string into a safe, valid Windows filename."""
        clean = WINDOWS_ILLEGAL_CHAR_REGEX.sub(replacement, name)
        # Strip trailing dots and spaces (forbidden in Windows)
        clean = clean.strip(". ")

        if not clean:
            clean = "untitled"

        # Check reserved DOS names
        stem = Path(clean).stem.upper()
        if stem in WINDOWS_RESERVED:
            clean = f"_{clean}"

        # Bound length
        if len(clean) > max_length:
            ext = Path(clean).suffix
            stem_allowed = max_length - len(ext)
            clean = clean[:stem_allowed] + ext

        return clean

    @staticmethod
    def generate_slug(text: str, separator: str = "-") -> str:
        """Converts text into clean, URL/file friendly slug."""
        clean = text.strip().lower()
        # Replace non-alphanumeric (allowing Arabic letters \u0600-\u06FF)
        clean = re.sub(r"[^\w\s\u0600-\u06FF-]", "", clean)
        clean = re.sub(r"[\s_]+", separator, clean)
        clean = clean.strip(separator)
        return clean or "slug"

    @staticmethod
    def generate_sequence(
        count: int = 20,
        start: int = 1,
        step: int = 1,
        padding: int = 3,
        prefix: str = "",
        suffix: str = ""
    ) -> List[str]:
        """Generates formatted sequential numbers."""
        results = []
        cur = start
        for _ in range(count):
            num_str = str(cur).zfill(padding)
            results.append(f"{prefix}{num_str}{suffix}")
            cur += step
        return results
