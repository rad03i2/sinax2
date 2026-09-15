# -*- coding: utf-8 -*-
"""
SINAX FileItem Model
Data structure representing an individual file in lists and table models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.core.constants import EXTENSION_TO_CATEGORY, FILE_CATEGORIES

def format_file_size(size_bytes: int) -> str:
    """Formats bytes into human-readable Arabic/metric size."""
    if size_bytes < 1024:
        return f"{size_bytes} بايت"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} ك.ب"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} م.ب"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} ج.ب"

@dataclass
class FileItem:
    path: Path
    original_name: str
    new_name: str = ""
    size_bytes: int = 0
    formatted_size: str = ""
    extension: str = ""
    category_key: str = "other"
    category_label: str = "ملفات أخرى"
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None
    is_selected: bool = True
    status: str = "normal"  # normal, changed, conflict, success, error
    conflict_reason: str = ""
    error_message: str = ""
    
    @classmethod
    def from_path(cls, path: Path) -> "FileItem":
        name = path.name
        ext = path.suffix.lower()
        cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
        cat_info = FILE_CATEGORIES.get(cat_key, FILE_CATEGORIES["other"])
        
        try:
            stat = path.stat()
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            ctime = datetime.fromtimestamp(stat.st_ctime)
        except Exception:
            size = 0
            mtime = None
            ctime = None

        return cls(
            path=path,
            original_name=name,
            new_name=name,
            size_bytes=size,
            formatted_size=format_file_size(size),
            extension=ext,
            category_key=cat_key,
            category_label=cat_info['label_ar'],
            created_time=ctime,
            modified_time=mtime,
            is_selected=True,
            status="normal"
        )

    @property
    def parent_dir(self) -> Path:
        return self.path.parent

    @property
    def is_changed(self) -> bool:
        return bool(self.new_name and self.new_name != self.original_name)

    @property
    def has_conflict(self) -> bool:
        return bool(self.conflict_reason)
