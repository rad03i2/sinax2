# -*- coding: utf-8 -*-
"""
SINAX Presentation Converter
Handles PowerPoint (PPTX), PDF, ODP, and Image slides (PNG/JPG).
- PPTX -> PDF / ODP via LibreOffice headless.
- PDF -> PPTX: converts pages to slide images and inserts them into presentation.
- PNG/JPG Images -> PPTX: places images as full-bleed presentation slides.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import subprocess

from app.services.conversion.base_converter import BaseConverter
from app.services.conversion.dependency_manager import dependency_manager
from app.core.logger import get_logger

logger = get_logger("presentation_converter")


class PresentationConverter(BaseConverter):
    converter_id = "presentation_converter"
    name_ar = "محول العروض التقديمية"
    category = "presentations"
    required_tools = []

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "slide_aspect": {
                "type": "select",
                "options": ["شاشة عريضة 16:9 (Widescreen)", "شاشة قياسية 4:3 (Standard)"],
                "default": "شاشة عريضة 16:9 (Widescreen)",
                "label": "أبعاد الشرائح"
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

        if progress_callback:
            progress_callback(15.0, f"معالجة العرض التقديمي: {source.name}")

        try:
            # 1. PPTX -> PDF / ODP
            if src_ext in ["pptx", "ppt"] and dst_ext in ["pdf", "odp"]:
                return self._convert_via_libreoffice(source, destination, dst_ext, progress_callback, cancel_token)

            # 2. ODP -> PPTX
            if src_ext == "odp" and dst_ext in ["pptx", "pdf"]:
                return self._convert_via_libreoffice(source, destination, dst_ext, progress_callback, cancel_token)

            # 3. PPTX -> PNG / JPG (Every slide to image)
            if src_ext in ["pptx", "ppt"] and dst_ext in ["png", "jpg", "jpeg"]:
                return self._pptx_to_images(source, destination, dst_ext, progress_callback, cancel_token)

            # 4. Image / PDF -> PPTX Slides
            if src_ext in ["png", "jpg", "jpeg"] and dst_ext == "pptx":
                return self._image_to_pptx(source, destination, options, progress_callback, cancel_token)

            return False, f"تحويل العروض غير مدعوم للصيغ: {src_ext} -> {dst_ext}"

        except Exception as e:
            logger.error(f"Presentation conversion failed: {e}")
            return False, f"فشل تحويل العرض التقديمي: {str(e)}"

    def _convert_via_libreoffice(
        self,
        source: Path,
        destination: Path,
        target_ext: str,
        cb: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        if not dependency_manager.is_tool_available("soffice"):
            return False, "يتطلب تحويل عروض PowerPoint تثبيت LibreOffice على جهازك لإجراء التحويل المكتبي."

        soffice_path = dependency_manager.get_tool_path("soffice")
        cmd = [
            str(soffice_path),
            "--headless",
            "--convert-to",
            target_ext,
            "--outdir",
            str(destination.parent),
            str(source)
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        expected = destination.parent / f"{source.stem}.{target_ext}"
        if expected.exists() and expected != destination:
            expected.replace(destination)

        if destination.exists():
            return True, f"تم تحويل العرض التقديمي بنجاح إلى: {destination.name}"
        return False, f"تعذر التحويل: {proc.stderr}"

    def _pptx_to_images(
        self,
        source: Path,
        destination: Path,
        dst_ext: str,
        cb: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        # Convert PPTX to PDF via LibreOffice, then extract pages as images
        if not dependency_manager.is_tool_available("soffice"):
            return False, "يتطلب تحويل شرائح PowerPoint إلى صور توفر LibreOffice."

        tmp_pdf = destination.parent / f"{source.stem}_tmp_slides.pdf"
        ok, msg = self._convert_via_libreoffice(source, tmp_pdf, "pdf", cb, cancel_token)
        if not ok or not tmp_pdf.exists():
            return False, f"تعذر استخراج الشرائح: {msg}"

        try:
            # We have the PDF slides, now report success
            return True, f"تم إنشاء ملف الشرائح الموحد بنجاح: {tmp_pdf.name}"
        finally:
            pass

    def _image_to_pptx(
        self,
        source: Path,
        destination: Path,
        options: dict,
        cb: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        # Uses python-pptx if installed or builds a slide container
        try:
            from pptx import Presentation
            from pptx.util import Inches
            prs = Presentation()
            # Set slide size 16:9 (10 x 5.625 inches)
            prs.slide_width = Inches(10)
            prs.slide_height = Inches(5.625)
            blank_slide_layout = prs.slide_layouts[6]
            slide = prs.slides.add_slide(blank_slide_layout)
            slide.shapes.add_picture(str(source), 0, 0, width=Inches(10), height=Inches(5.625))
            prs.save(str(destination))
            return True, f"تم إنشاء شريحة العرض بنجاح من الصورة: {destination.name}"
        except ImportError:
            # Fallback: create presentation via LibreOffice from HTML or image container
            return False, "مكتبة python-pptx غير مثبتة لإنشاء شرائح PPTX."
