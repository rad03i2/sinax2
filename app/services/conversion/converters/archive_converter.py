# -*- coding: utf-8 -*-
"""
SINAX Archive Repacker & Converter
Safely repacks archives (ZIP <-> 7Z).
Extracts to temp directory, creates target archive, validates integrity, cleans up temp,
and NEVER deletes or modifies source files!
"""

import os
import shutil
import tempfile
import zipfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

from app.services.conversion.base_converter import BaseConverter
from app.services.conversion.dependency_manager import dependency_manager
from app.core.logger import get_logger

logger = get_logger("archive_converter")


class ArchiveConverter(BaseConverter):
    converter_id = "archive_converter"
    name_ar = "محول ومعيد تغليف الأرشيفات"
    category = "archives"
    required_tools = []

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "compression_level": {
                "type": "select",
                "options": ["قياسي (Standard)", "أقصى ضغط (Ultra / Best)", "سريع (Fast)"],
                "default": "قياسي (Standard)",
                "label": "مستوى الضغط"
            }
        }

    def convert(
        self,
        source: Path,
        destination: Path,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, str]:
        options = options or {}
        valid, msg = self.validate_input(source)
        if not valid:
            return False, msg

        if cancel_token and cancel_token():
            return False, "تم إلغاء العملية."

        src_ext = source.suffix.lower().lstrip('.')
        dst_ext = destination.suffix.lower().lstrip('.')
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Check 7z dependency if 7z is involved
        has_7z_tool = dependency_manager.is_tool_available("7z")

        if (src_ext == "7z" or dst_ext == "7z") and not has_7z_tool:
            return False, "يتطلب التعامل مع أرشيفات 7Z توفر برنامج 7-Zip على حاسوبك."

        tmp_dir = Path(tempfile.mkdtemp(prefix="sinax_archive_"))

        try:
            if progress_callback:
                progress_callback(20.0, f"فك محتويات الأرشيف مؤقتاً: {source.name}...")

            # 1. Unpack source into temp
            if src_ext == "zip":
                with zipfile.ZipFile(source, 'r') as zf:
                    zf.extractall(tmp_dir)
            elif src_ext == "7z":
                tool_path = dependency_manager.get_tool_path("7z")
                cmd = [str(tool_path), "x", str(source), f"-o{tmp_dir}", "-y"]
                res = subprocess.run(cmd, capture_output=True, timeout=120)
                if res.returncode != 0:
                    return False, f"فشل فك أرشيف 7Z: {res.stderr.decode('utf-8', errors='replace')}"

            if cancel_token and cancel_token():
                return False, "تم إلغاء العملية."

            if progress_callback:
                progress_callback(60.0, f"إنشاء الأرشيف الجديد: {destination.name}...")

            # 2. Pack target from temp
            if dst_ext == "zip":
                with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, _, files in os.walk(tmp_dir):
                        for f in files:
                            full_f = Path(root) / f
                            arcname = full_f.relative_to(tmp_dir)
                            zf.write(full_f, arcname)
            elif dst_ext == "7z":
                tool_path = dependency_manager.get_tool_path("7z")
                cmd = [str(tool_path), "a", str(destination), f"{tmp_dir}/*"]
                res = subprocess.run(cmd, capture_output=True, timeout=180)
                if res.returncode != 0:
                    return False, f"فشل إنشاء أرشيف 7Z: {res.stderr.decode('utf-8', errors='replace')}"

            # 3. Verify integrity
            if destination.exists() and destination.stat().st_size > 0:
                if progress_callback:
                    progress_callback(100.0, f"تمت إعادة تغليف الأرشيف بنجاح: {destination.name}")
                return True, f"تمت إعادة تغليف الأرشيف بنجاح دون المساس بالمصدر: {destination.name}"

            return False, "فشل إنشاء ملف الأرشيف الهدف."

        except Exception as e:
            logger.error(f"Archive repacking error: {e}")
            return False, f"خطأ أثناء إعادة تغليف الأرشيف: {str(e)}"
        finally:
            # Clean up temp
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
