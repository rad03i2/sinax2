# -*- coding: utf-8 -*-
"""
SINAX Ebook Converter
Handles EPUB <-> PDF conversion via Calibre's ebook-convert tool.
Includes clear user warnings regarding scanned or complex PDF structures.
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

from app.services.conversion.base_converter import BaseConverter
from app.services.conversion.dependency_manager import dependency_manager
from app.core.logger import get_logger

logger = get_logger("ebook_converter")


class EbookConverter(BaseConverter):
    converter_id = "ebook_converter"
    name_ar = "محول الكتب الإلكترونية"
    category = "ebooks"
    required_tools = ["ebook-convert"]

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "font_size": {
                "type": "int",
                "min": 8,
                "max": 24,
                "default": 12,
                "label": "حجم الخط الأساسي في الكتاب"
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

        if not self.is_available():
            return False, "يتطلب تحويل الكتب الإلكترونية توفر أداة Calibre (ebook-convert) على حاسوبك."

        calibre_path = dependency_manager.get_tool_path("ebook-convert")
        if not calibre_path:
            return False, "تعذر العثور على أداة Calibre."

        if cancel_token and cancel_token():
            return False, "تم إلغاء العملية."

        src_ext = source.suffix.lower().lstrip('.')
        dst_ext = destination.suffix.lower().lstrip('.')
        destination.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(15.0, f"بدء معالجة الكتاب الإلكتروني: {source.name}")

        cmd = [str(calibre_path), str(source), str(destination)]

        # Add warning for PDF -> EPUB
        warning = ""
        if src_ext == "pdf" and dst_ext == "epub":
            warning = "\n(تنبيه: قد تختلف دقة تنسيق الكتاب إذا كان ملف PDF ممسوحاً ضوئياً أو بتخطيط متعدد الأعمدة)."

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            while proc.poll() is None:
                if cancel_token and cancel_token():
                    proc.kill()
                    if destination.exists():
                        try:
                            destination.unlink()
                        except Exception:
                            pass
                    return False, "تم إلغاء تحويل الكتاب بأمان."
                try:
                    proc.wait(timeout=0.3)
                except subprocess.TimeoutExpired:
                    pass

            if destination.exists() and destination.stat().st_size > 0:
                if progress_callback:
                    progress_callback(100.0, f"اكتمل تحويل الكتاب: {destination.name}")
                return True, f"تم تحويل الكتاب الإلكتروني بنجاح: {destination.name}{warning}"

            stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
            return False, f"فشل تحويل Calibre: {stderr[-200:]}"

        except Exception as e:
            logger.error(f"Ebook conversion error: {e}")
            return False, f"خطأ أثناء تحويل الكتاب: {str(e)}"
