# -*- coding: utf-8 -*-
"""
SINAX Conflict Service.
Assists users with resolving file conflicts between two sync points, providing
file metadata inspection, side-by-side comparison, and automated resolution.
"""

import difflib
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple

from app.core.logger import get_logger
from app.services.backup_sync.copy_engine import CopyEngine
from app.services.backup_sync.models import ConflictResolution

logger = get_logger("conflict_service")


class ConflictService:
    """Manages comparison and resolution of sync conflicts."""

    @classmethod
    def get_conflict_diff_summary(cls, path_a: str, path_b: str) -> Dict[str, Any]:
        """Provides side-by-side metadata and optional text diff."""
        pa = Path(path_a)
        pb = Path(path_b)

        info = {
            "path_a": path_a,
            "path_b": path_b,
            "exists_a": pa.exists(),
            "exists_b": pb.exists(),
            "size_a": pa.stat().st_size if pa.exists() else 0,
            "size_b": pb.stat().st_size if pb.exists() else 0,
            "mtime_a": pa.stat().st_mtime if pa.exists() else 0,
            "mtime_b": pb.stat().st_mtime if pb.exists() else 0,
            "is_text": False,
            "text_diff_sample": ""
        }

        # Check if text file for diff
        text_extensions = {".txt", ".py", ".md", ".json", ".csv", ".xml", ".ini", ".cfg", ".log", ".html"}
        if pa.suffix.lower() in text_extensions and pa.exists() and pb.exists():
            try:
                if info["size_a"] < 1024 * 1024 and info["size_b"] < 1024 * 1024:
                    with open(pa, "r", encoding="utf-8", errors="ignore") as fa, open(pb, "r", encoding="utf-8", errors="ignore") as fb:
                        lines_a = fa.readlines()[:100]
                        lines_b = fb.readlines()[:100]
                    diff = list(difflib.unified_diff(lines_a, lines_b, fromfile="الطرف A", tofile="الطرف B", n=2))
                    info["is_text"] = True
                    info["text_diff_sample"] = "".join(diff[:30])
            except Exception:
                pass

        return info

    @classmethod
    def apply_resolution(
        cls,
        path_a: str,
        path_b: str,
        resolution: ConflictResolution
    ) -> Tuple[bool, str]:
        """Applies resolution choice to a specific conflicting pair."""
        pa = Path(path_a)
        pb = Path(path_b)

        try:
            if resolution == ConflictResolution.KEEP_A:
                ok, err = CopyEngine.copy_file_safe(str(pa), str(pb))
                return ok, "تم اعتماد النسخة (A) وتحديث (B) بنجاح." if ok else err

            elif resolution == ConflictResolution.KEEP_B:
                ok, err = CopyEngine.copy_file_safe(str(pb), str(pa))
                return ok, "تم اعتماد النسخة (B) وتحديث (A) بنجاح." if ok else err

            elif resolution == ConflictResolution.KEEP_BOTH:
                # Keep both: create conflict copy on Side B
                t_str = time.strftime("%Y-%m-%d_%H%M%S")
                sidecar = pb.parent / f"{pb.stem} (conflict {t_str}){pb.suffix}"
                ok, err = CopyEngine.copy_file_safe(str(pa), str(sidecar))
                return ok, f"تم الاحتفاظ بالاثنين وحفظ النسخة في: {sidecar.name}" if ok else err

            elif resolution == ConflictResolution.SKIP:
                return True, "تم تخطي التعارض دون تعديل."

            return False, "خيار غير معروف."
        except Exception as e:
            return False, str(e)
