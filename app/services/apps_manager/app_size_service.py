# -*- coding: utf-8 -*-
"""
SINAX Application True Disk Size Service
Calculates real allocated disk space for installed application folders without blocking the UI.
Skips reparse points and symbolic links.
"""

import logging
import os
from typing import Dict, Optional

logger = logging.getLogger("SINAX.apps_manager.app_size_service")


class AppSizeService:
    """Calculates physical disk usage of installed software directories."""

    _size_cache: Dict[str, int] = {}

    @classmethod
    def calculate_folder_size(cls, folder_path: Optional[str]) -> int:
        """Recursively sums file sizes within folder_path, avoiding symlinks."""
        if not folder_path or not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return 0

        norm_path = os.path.normpath(folder_path)
        if norm_path in cls._size_cache:
            return cls._size_cache[norm_path]

        total = 0
        try:
            for root, dirs, files in os.walk(norm_path, followlinks=False):
                # Filter out symlink directories
                dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        if not os.path.islink(fp):
                            total += os.path.getsize(fp)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError) as e:
            logger.debug(f"Error calculating size for {norm_path}: {e}")

        cls._size_cache[norm_path] = total
        return total
