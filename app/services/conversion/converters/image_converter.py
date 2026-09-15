# -*- coding: utf-8 -*-
"""
SINAX Image Converter
High-performance local image converter supporting JPG, PNG, WebP, BMP, TIFF, ICO, SVG, AVIF, HEIC.
Handles transparency compositing, quality, resizing, and multi-resolution ICO icons.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from PIL import Image

from app.services.conversion.base_converter import BaseConverter
from app.core.logger import get_logger

logger = get_logger("image_converter")


class ImageConverter(BaseConverter):
    converter_id = "image_converter"
    name_ar = "محول الصور والرسوميات"
    category = "images"
    required_tools = []  # Core conversions run via Pillow / QtSvg

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "quality": {
                "type": "int",
                "min": 1,
                "max": 100,
                "default": 90,
                "label": "جودة الصورة (Quality)"
            },
            "resize_mode": {
                "type": "select",
                "options": ["الأصلية (Original)", "1920x1080 (FHD)", "1280x720 (HD)", "800x600", "50% (نصف الحجم)", "25% (ربع الحجم)"],
                "default": "الأصلية (Original)",
                "label": "أبعاد الصورة"
            },
            "alpha_bg": {
                "type": "select",
                "options": ["أبيض (White)", "أسود (Black)", "رمادي (Gray)"],
                "default": "أبيض (White)",
                "label": "لون خلفية الشفافية (عند التحويل لـ JPG)"
            },
            "ico_sizes": {
                "type": "select",
                "options": ["متعدد الأحجام (16, 32, 48, 64, 128, 256)", "أيقونة قياسية (32x32)", "أيقونة كبيرة (256x256)"],
                "default": "متعدد الأحجام (16, 32, 48, 64, 128, 256)",
                "label": "أحجام ملف الأيقونة ICO"
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

        target_ext = destination.suffix.lower().lstrip('.')
        source_ext = source.suffix.lower().lstrip('.')

        if progress_callback:
            progress_callback(10.0, f"قراءة الصورة: {source.name}")

        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Special Case: SVG -> PNG using PySide6 QtSvg for highest vector rendering accuracy
            if source_ext == "svg" and target_ext in ["png", "jpg", "jpeg", "webp"]:
                return self._convert_svg(source, destination, target_ext, options, progress_callback, cancel_token)

            # Standard Raster Conversions using Pillow
            with Image.open(source) as img:
                if cancel_token and cancel_token():
                    return False, "تم إلغاء العملية."

                if progress_callback:
                    progress_callback(35.0, "معالجة الأبعاد والألوان...")

                # Apply Resizing if requested
                img = self._apply_resize(img, options.get("resize_mode", "الأصلية (Original)"))

                # Handle Transparency / Alpha when saving to non-alpha formats (like JPEG/BMP)
                if target_ext in ["jpg", "jpeg", "bmp"]:
                    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                        bg_choice = options.get("alpha_bg", "أبيض (White)")
                        bg_color = (255, 255, 255)
                        if "أسود" in bg_choice:
                            bg_color = (0, 0, 0)
                        elif "رمادي" in bg_choice:
                            bg_color = (128, 128, 128)

                        # Create clean solid background
                        background = Image.new("RGB", img.size, bg_color)
                        alpha_img = img.convert("RGBA")
                        background.paste(alpha_img, mask=alpha_img.split()[3])
                        img = background
                    elif img.mode != "RGB":
                        img = img.convert("RGB")

                # Handle ICO Multi-resolution Output
                if target_ext == "ico":
                    if progress_callback:
                        progress_callback(60.0, "توليد أحجام الأيقونات المتعددة...")
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")

                    ico_choice = options.get("ico_sizes", "")
                    if "32x32" in ico_choice:
                        sizes = [(32, 32)]
                    elif "256x256" in ico_choice:
                        sizes = [(256, 256)]
                    else:
                        sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

                    img.save(destination, format="ICO", sizes=sizes)
                else:
                    # Save standard format
                    quality = int(options.get("quality", 90))
                    save_kwargs = {}

                    if target_ext in ["jpg", "jpeg"]:
                        save_kwargs["quality"] = quality
                        save_kwargs["optimize"] = True
                    elif target_ext == "webp":
                        save_kwargs["quality"] = quality
                        save_kwargs["method"] = 6
                    elif target_ext == "png":
                        save_kwargs["optimize"] = True

                    fmt = "JPEG" if target_ext in ["jpg", "jpeg"] else target_ext.upper()
                    img.save(destination, format=fmt, **save_kwargs)

            if progress_callback:
                progress_callback(100.0, f"تم حفظ الصورة بنجاح: {destination.name}")

            return True, f"تم التحويل بنجاح: {destination.name}"

        except Exception as e:
            logger.error(f"Image conversion failed for {source.name}: {e}")
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False, f"فشل تحويل الصورة: {str(e)}"

    def _apply_resize(self, img: Image.Image, resize_mode: str) -> Image.Image:
        """Applies requested proportional resizing."""
        if "الأصلية" in resize_mode:
            return img

        w, h = img.size
        if "50%" in resize_mode:
            new_w, new_h = max(1, int(w * 0.5)), max(1, int(h * 0.5))
        elif "25%" in resize_mode:
            new_w, new_h = max(1, int(w * 0.25)), max(1, int(h * 0.25))
        elif "1920x1080" in resize_mode:
            img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            return img
        elif "1280x720" in resize_mode:
            img.thumbnail((1280, 720), Image.Resampling.LANCZOS)
            return img
        elif "800x600" in resize_mode:
            img.thumbnail((800, 600), Image.Resampling.LANCZOS)
            return img
        else:
            return img

        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def _convert_svg(
        self,
        source: Path,
        destination: Path,
        target_ext: str,
        options: Dict[str, Any],
        progress_callback: Optional[Callable],
        cancel_token: Optional[Callable]
    ) -> Tuple[bool, str]:
        """Renders vector SVG to raster image using QtSvg."""
        try:
            from PySide6.QtSvg import QSvgRenderer
            from PySide6.QtGui import QImage, QPainter, QColor
            from PySide6.QtCore import QSize

            renderer = QSvgRenderer(str(source))
            if not renderer.isValid():
                return False, "ملف SVG غير صالح أو تالف."

            default_sz = renderer.defaultSize()
            w = max(default_sz.width(), 800)
            h = max(default_sz.height(), 800)

            # High-resolution rendering
            img = QImage(w, h, QImage.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))  # Transparent

            painter = QPainter(img)
            renderer.render(painter)
            painter.end()

            # Save temporary PNG
            temp_png = destination.with_suffix(".tmp_svg.png")
            img.save(str(temp_png), "PNG")

            # Convert with Pillow to target format
            with Image.open(temp_png) as pil_img:
                if target_ext in ["jpg", "jpeg", "bmp"]:
                    bg_color = (255, 255, 255)
                    bg = Image.new("RGB", pil_img.size, bg_color)
                    bg.paste(pil_img, mask=pil_img.split()[3])
                    bg.save(destination, format="JPEG" if target_ext in ["jpg", "jpeg"] else "BMP")
                else:
                    pil_img.save(destination, format=target_ext.upper())

            if temp_png.exists():
                temp_png.unlink()

            return True, f"تم تحويل SVG بنجاح إلى {destination.name}"
        except Exception as e:
            return False, f"فشل تحويل SVG: {e}"
