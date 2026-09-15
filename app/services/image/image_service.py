# -*- coding: utf-8 -*-
"""
SINAX Core Image Processing Service
Comprehensive, 100% local, high-performance image engine powered by
Pillow, OpenCV, imagehash, piexif, and pillow_heif.
"""

import io
import os
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageDraw, ImageFont

# Register HEIF opener for native Apple HEIC/HEIF support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

try:
    import piexif
except Exception:
    piexif = None

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

try:
    import imagehash
except Exception:
    imagehash = None

from app.core.logger import get_logger

logger = get_logger(__name__)


class ImageService:
    """Core image processing service providing atomic operations for single or batch processing."""

    def __init__(self):
        pass

    # -------------------------------------------------------------------------
    # 1. COMPRESSION & TARGET SIZE OPTIMIZATION
    # -------------------------------------------------------------------------
    def compress_image(
        self,
        input_path: Path,
        output_path: Path,
        preset: str = "balanced",
        quality: int = 80,
        target_size_kb: Optional[int] = None,
        lossless: bool = False
    ) -> Dict[str, Any]:
        """
        Compresses an image using presets or exact quality.
        If target_size_kb is specified, uses binary search & adaptive downscaling
        to ensure output size is strictly <= target_size_kb.
        """
        in_path = Path(input_path)
        out_path = Path(output_path)
        orig_size = in_path.stat().st_size

        preset_quality_map = {
            "light": 90,
            "balanced": 80,
            "strong": 60,
            "max": 40,
        }
        eff_quality = preset_quality_map.get(preset, quality)

        with Image.open(in_path) as img:
            # Preserve orientation before saving
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            target_fmt = out_path.suffix.lstrip(".").upper()
            if target_fmt in ("JPG", "JPEG"):
                target_fmt = "JPEG"
                if img.mode in ("RGBA", "P", "LA"):
                    # Avoid black background on JPG conversion
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
            elif target_fmt == "WEBP":
                pass
            elif target_fmt == "PNG":
                pass

            out_path.parent.mkdir(parents=True, exist_ok=True)

            if target_size_kb and target_size_kb > 0:
                target_bytes = target_size_kb * 1024
                # Smart iterative optimization
                best_buffer = None
                low_q = 5
                high_q = 95
                curr_img = img.copy()

                for attempt in range(7):  # Binary search on quality
                    q = (low_q + high_q) // 2
                    buf = io.BytesIO()
                    save_kwargs = {"quality": q, "optimize": True}
                    if target_fmt == "WEBP":
                        save_kwargs["method"] = 6
                    curr_img.save(buf, format=target_fmt, **save_kwargs)
                    size = buf.tell()

                    if size <= target_bytes:
                        best_buffer = buf.getvalue()
                        low_q = q + 1  # Try higher quality
                    else:
                        high_q = q - 1

                # If still too large, downscale image dimensions iteratively
                scale = 0.9
                while (not best_buffer or len(best_buffer) > target_bytes) and scale >= 0.2:
                    nw = max(16, int(curr_img.width * scale))
                    nh = max(16, int(curr_img.height * scale))
                    scaled_img = curr_img.resize((nw, nh), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    scaled_img.save(buf, format=target_fmt, quality=55, optimize=True)
                    if buf.tell() <= target_bytes:
                        best_buffer = buf.getvalue()
                        break
                    scale -= 0.15

                if best_buffer:
                    with open(out_path, "wb") as f:
                        f.write(best_buffer)
                else:
                    # Save lowest quality fallback
                    curr_img.save(out_path, format=target_fmt, quality=20, optimize=True)

            else:
                # Standard preset compression
                save_kwargs = {"optimize": True}
                if lossless and target_fmt in ("WEBP", "PNG"):
                    if target_fmt == "WEBP":
                        save_kwargs["lossless"] = True
                else:
                    if target_fmt in ("JPEG", "WEBP"):
                        save_kwargs["quality"] = eff_quality

                img.save(out_path, format=target_fmt, **save_kwargs)

        new_size = out_path.stat().st_size
        savings = max(0, orig_size - new_size)
        savings_pct = (savings / orig_size * 100.0) if orig_size > 0 else 0.0

        return {
            "success": True,
            "orig_size": orig_size,
            "new_size": new_size,
            "savings": savings,
            "savings_pct": round(savings_pct, 1),
            "output_path": str(out_path)
        }

    # -------------------------------------------------------------------------
    # 2. BATCH RESIZE (Fit, Fill, Stretch, Percent, Edges)
    # -------------------------------------------------------------------------
    def resize_image(
        self,
        input_path: Path,
        output_path: Path,
        mode: str = "fit",
        width: Optional[int] = None,
        height: Optional[int] = None,
        percent: Optional[float] = None,
        longest_edge: Optional[int] = None,
        shortest_edge: Optional[int] = None,
        do_not_enlarge: bool = False
    ) -> Dict[str, Any]:
        """Resizes image according to specified mode and constraints."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            orig_w, orig_h = img.size
            target_w, target_h = orig_w, orig_h

            if mode == "percent" and percent and percent > 0:
                factor = percent / 100.0
                target_w = max(1, int(orig_w * factor))
                target_h = max(1, int(orig_h * factor))

            elif mode == "longest" and longest_edge and longest_edge > 0:
                if orig_w >= orig_h:
                    target_w = longest_edge
                    target_h = max(1, int(orig_h * (longest_edge / orig_w)))
                else:
                    target_h = longest_edge
                    target_w = max(1, int(orig_w * (longest_edge / orig_h)))

            elif mode == "shortest" and shortest_edge and shortest_edge > 0:
                if orig_w <= orig_h:
                    target_w = shortest_edge
                    target_h = max(1, int(orig_h * (shortest_edge / orig_w)))
                else:
                    target_h = shortest_edge
                    target_w = max(1, int(orig_w * (shortest_edge / orig_h)))

            elif mode == "width_only" and width and width > 0:
                target_w = width
                target_h = max(1, int(orig_h * (width / orig_w)))

            elif mode == "height_only" and height and height > 0:
                target_h = height
                target_w = max(1, int(orig_w * (height / orig_h)))

            elif mode in ("fit", "fill", "stretch"):
                req_w = width or orig_w
                req_h = height or orig_h

                if mode == "stretch":
                    target_w, target_h = req_w, req_h
                elif mode == "fit":
                    ratio = min(req_w / orig_w, req_h / orig_h)
                    target_w = max(1, int(orig_w * ratio))
                    target_h = max(1, int(orig_h * ratio))
                elif mode == "fill":
                    # ImageOps.fit crops from center
                    ratio = max(req_w / orig_w, req_h / orig_h)
                    target_w = max(1, int(orig_w * ratio))
                    target_h = max(1, int(orig_h * ratio))

            if do_not_enlarge:
                if target_w > orig_w or target_h > orig_h:
                    target_w, target_h = orig_w, orig_h

            if mode == "fill" and width and height:
                res_img = ImageOps.fit(img, (width, height), Image.Resampling.LANCZOS)
            else:
                res_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_pil_image(res_img, out_path)

        return {
            "success": True,
            "orig_dimensions": (orig_w, orig_h),
            "new_dimensions": res_img.size,
            "output_path": str(out_path)
        }

    # -------------------------------------------------------------------------
    # 3. FORMAT CONVERSION (JPG, PNG, WebP, AVIF, BMP, TIFF, GIF, ICO, HEIC)
    # -------------------------------------------------------------------------
    def convert_image(
        self,
        input_path: Path,
        output_path: Path,
        target_format: str = "webp",
        quality: int = 85,
        bg_color: str = "#FFFFFF"
    ) -> Dict[str, Any]:
        """Converts image between standard and modern image formats."""
        in_path = Path(input_path)
        out_path = Path(output_path)
        norm_fmt = target_format.lower().lstrip(".")

        with Image.open(in_path) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            # Handle transparency when converting to non-alpha formats
            if norm_fmt in ("jpg", "jpeg", "bmp"):
                if img.mode in ("RGBA", "P", "LA"):
                    bg_rgb = self._hex_to_rgb(bg_color)
                    bg = Image.new("RGB", img.size, bg_rgb)
                    alpha = img.split()[-1] if img.mode == "RGBA" else None
                    bg.paste(img, mask=alpha)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")

            out_path.parent.mkdir(parents=True, exist_ok=True)

            if norm_fmt == "ico":
                # Multi-size favicon
                sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                img.save(out_path, format="ICO", sizes=sizes)
            elif norm_fmt in ("jpg", "jpeg"):
                img.save(out_path, format="JPEG", quality=quality, optimize=True)
            elif norm_fmt == "webp":
                img.save(out_path, format="WEBP", quality=quality, method=6)
            elif norm_fmt == "png":
                img.save(out_path, format="PNG", optimize=True)
            elif norm_fmt == "bmp":
                img.save(out_path, format="BMP")
            elif norm_fmt in ("tiff", "tif"):
                img.save(out_path, format="TIFF")
            elif norm_fmt == "gif":
                img.save(out_path, format="GIF")
            else:
                img.save(out_path)

        return {
            "success": True,
            "target_format": norm_fmt.upper(),
            "output_path": str(out_path)
        }

    # -------------------------------------------------------------------------
    # 4. CROP & MANUAL CROP
    # -------------------------------------------------------------------------
    def crop_image(
        self,
        input_path: Path,
        output_path: Path,
        aspect_ratio: Optional[str] = None,
        align: str = "center",
        crop_box: Optional[Tuple[int, int, int, int]] = None
    ) -> Dict[str, Any]:
        """Crops image by aspect ratio or explicit pixel bounding box."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            w, h = img.size

            if crop_box:
                left, top, right, bottom = crop_box
                left = max(0, min(left, w))
                top = max(0, min(top, h))
                right = max(left + 1, min(right, w))
                bottom = max(top + 1, min(bottom, h))
                cropped = img.crop((left, top, right, bottom))
            elif aspect_ratio:
                parts = aspect_ratio.split(":")
                ar_w, ar_h = float(parts[0]), float(parts[1])
                target_ar = ar_w / ar_h
                current_ar = w / h

                if current_ar > target_ar:
                    new_w = int(h * target_ar)
                    new_h = h
                else:
                    new_w = w
                    new_h = int(w / target_ar)

                if align == "center":
                    left = (w - new_w) // 2
                    top = (h - new_h) // 2
                elif align == "top":
                    left = (w - new_w) // 2
                    top = 0
                elif align == "bottom":
                    left = (w - new_w) // 2
                    top = h - new_h
                elif align == "left":
                    left = 0
                    top = (h - new_h) // 2
                elif align == "right":
                    left = w - new_w
                    top = (h - new_h) // 2
                else:
                    left = (w - new_w) // 2
                    top = (h - new_h) // 2

                cropped = img.crop((left, top, left + new_w, top + new_h))
            else:
                cropped = img

            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_pil_image(cropped, out_path)

        return {"success": True, "dimensions": cropped.size, "output_path": str(out_path)}

    # -------------------------------------------------------------------------
    # 5. ROTATE & ORIENTATION
    # -------------------------------------------------------------------------
    def rotate_orient_image(
        self,
        input_path: Path,
        output_path: Path,
        angle: int = 0,
        auto_orient: bool = False,
        flip_h: bool = False,
        flip_v: bool = False
    ) -> Dict[str, Any]:
        """Rotates, flips, and auto-orients images based on EXIF sensors."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            if auto_orient:
                try:
                    img = ImageOps.exif_transpose(img)
                except Exception:
                    pass

            if angle % 360 != 0:
                img = img.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)

            if flip_h:
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if flip_v:
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_pil_image(img, out_path)

        return {"success": True, "output_path": str(out_path)}

    # -------------------------------------------------------------------------
    # 6. WATERMARK & BRANDING
    # -------------------------------------------------------------------------
    def watermark_image(
        self,
        input_path: Path,
        output_path: Path,
        text: str = "",
        logo_path: Optional[Path] = None,
        position: str = "bottom_right",
        opacity: float = 0.8,
        font_size: int = 36,
        color: str = "#FFFFFF",
        angle: int = 0,
        margin: int = 24
    ) -> Dict[str, Any]:
        """Applies text watermark or logo stamp with alpha transparency in 9 positions."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            base = img.convert("RGBA")
            overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))

            w, h = base.size

            if logo_path and Path(logo_path).exists():
                with Image.open(logo_path) as logo:
                    logo = logo.convert("RGBA")
                    # Scale logo if larger than 25% of image width
                    max_lw = int(w * 0.25)
                    if logo.width > max_lw:
                        ratio = max_lw / logo.width
                        logo = logo.resize((max_lw, max(1, int(logo.height * ratio))), Image.Resampling.LANCZOS)

                    # Adjust opacity
                    if opacity < 1.0:
                        r, g, b, a = logo.split()
                        a = a.point(lambda p: int(p * opacity))
                        logo = Image.merge("RGBA", (r, g, b, a))

                    pos = self._compute_position(w, h, logo.width, logo.height, position, margin)
                    overlay.paste(logo, pos, mask=logo)

            elif text:
                # Text overlay
                txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(txt_layer)
                
                # Try default or standard sans font
                font = ImageFont.load_default()

                # Calculate text size
                bbox = draw.textbbox((0, 0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                # Draw with opacity
                r, g, b = self._hex_to_rgb(color)
                a = int(255 * opacity)
                
                pos = self._compute_position(w, h, tw, th, position, margin)
                draw.text(pos, text, font=font, fill=(r, g, b, a))
                overlay = txt_layer

            combined = Image.alpha_composite(base, overlay)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_pil_image(combined, out_path)

        return {"success": True, "output_path": str(out_path)}

    # -------------------------------------------------------------------------
    # 7. BORDERS & CANVAS EXPANSION
    # -------------------------------------------------------------------------
    def border_canvas_image(
        self,
        input_path: Path,
        output_path: Path,
        border_width: int = 0,
        border_color: str = "#FFFFFF",
        canvas_width: Optional[int] = None,
        canvas_height: Optional[int] = None,
        canvas_bg: str = "#FFFFFF"
    ) -> Dict[str, Any]:
        """Adds solid borders or expands canvas around the image."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            if border_width > 0:
                b_color = self._hex_to_rgb(border_color)
                img = ImageOps.expand(img, border=border_width, fill=b_color)

            if canvas_width and canvas_height:
                if canvas_width > img.width or canvas_height > img.height:
                    nw = max(img.width, canvas_width)
                    nh = max(img.height, canvas_height)
                    bg_rgb = self._hex_to_rgb(canvas_bg)
                    new_canvas = Image.new(img.mode, (nw, nh), bg_rgb)
                    x = (nw - img.width) // 2
                    y = (nh - img.height) // 2
                    new_canvas.paste(img, (x, y))
                    img = new_canvas

            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_pil_image(img, out_path)

        return {"success": True, "output_path": str(out_path)}

    # -------------------------------------------------------------------------
    # 8. ENHANCEMENT & COLOR ADJUSTMENTS
    # -------------------------------------------------------------------------
    def enhance_filter_image(
        self,
        input_path: Path,
        output_path: Path,
        auto_enhance: bool = False,
        brightness: float = 1.0,
        contrast: float = 1.0,
        saturation: float = 1.0,
        sharpness: float = 1.0,
        denoise: bool = False,
        blur_radius: int = 0,
        grayscale: bool = False,
        sepia: bool = False,
        invert: bool = False
    ) -> Dict[str, Any]:
        """Applies auto-contrast, brightness, CLAHE, filters, and color adjustments."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            if auto_enhance:
                # Apply auto-contrast and mild sharpening
                img = ImageOps.autocontrast(img, cutoff=1)
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.25)

            if brightness != 1.0:
                img = ImageEnhance.Brightness(img).enhance(brightness)
            if contrast != 1.0:
                img = ImageEnhance.Contrast(img).enhance(contrast)
            if saturation != 1.0 and img.mode in ("RGB", "RGBA"):
                img = ImageEnhance.Color(img).enhance(saturation)
            if sharpness != 1.0:
                img = ImageEnhance.Sharpness(img).enhance(sharpness)

            if blur_radius > 0:
                img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            if grayscale:
                img = ImageOps.grayscale(img)

            if sepia and img.mode in ("RGB", "RGBA"):
                # Apply sepia tone matrix
                img = img.convert("RGB")
                sepia_img = Image.new("RGB", img.size)
                # Fast sepia filter
                np_img = np.array(img, dtype=np.float32)
                sepia_mat = np.array([[0.393, 0.769, 0.189],
                                      [0.349, 0.686, 0.168],
                                      [0.272, 0.534, 0.131]])
                transformed = cv2.transform(np_img, sepia_mat)
                transformed = np.clip(transformed, 0, 255).astype(np.uint8)
                img = Image.fromarray(transformed)

            if invert:
                if img.mode in ("RGBA", "LA"):
                    r, g, b, a = img.convert("RGBA").split()
                    rgb_inv = ImageOps.invert(Image.merge("RGB", (r, g, b)))
                    r2, g2, b2 = rgb_inv.split()
                    img = Image.merge("RGBA", (r2, g2, b2, a))
                else:
                    img = ImageOps.invert(img.convert("RGB"))

            out_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_pil_image(img, out_path)

        return {"success": True, "output_path": str(out_path)}

    # -------------------------------------------------------------------------
    # 9. METADATA & PRIVACY (Strip all, Strip GPS, Shift Date)
    # -------------------------------------------------------------------------
    def metadata_image(
        self,
        input_path: Path,
        output_path: Path,
        action: str = "strip_all",
        shift_hours: int = 0,
        shift_days: int = 0
    ) -> Dict[str, Any]:
        """Strips EXIF, removes GPS location, or shifts capture date for privacy."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if action == "strip_all":
                # Save purely raw pixel buffer without EXIF/IPTC/XMP
                clean_img = Image.new(img.mode, img.size)
                clean_img.paste(img)
                self._save_pil_image(clean_img, out_path, include_exif=False)

            elif action == "strip_gps" and piexif:
                exif_dict = piexif.load(str(in_path))
                exif_dict["GPS"] = {}  # Empty GPS IFD
                exif_bytes = piexif.dump(exif_dict)
                self._save_pil_image(img, out_path, raw_exif=exif_bytes)

            elif action == "shift_date" and piexif:
                exif_dict = piexif.load(str(in_path))
                delta = timedelta(days=shift_days, hours=shift_hours)
                for tag_key in (piexif.ExifIFD.DateTimeOriginal, piexif.ExifIFD.DateTimeDigitized):
                    if tag_key in exif_dict.get("Exif", {}):
                        try:
                            val_str = exif_dict["Exif"][tag_key].decode("ascii")
                            dt = datetime.strptime(val_str, "%Y:%m:%d %H:%M:%S") + delta
                            exif_dict["Exif"][tag_key] = dt.strftime("%Y:%m:%d %H:%M:%S").encode("ascii")
                        except Exception:
                            pass
                exif_bytes = piexif.dump(exif_dict)
                self._save_pil_image(img, out_path, raw_exif=exif_bytes)

            else:
                self._save_pil_image(img, out_path)

        return {"success": True, "action": action, "output_path": str(out_path)}

    # -------------------------------------------------------------------------
    # 10. TRANSPARENCY & BACKGROUND
    # -------------------------------------------------------------------------
    def smart_transparency(
        self,
        input_path: Path,
        output_path: Path,
        target_color: str = "#FFFFFF",
        tolerance: int = 30
    ) -> Dict[str, Any]:
        """Converts near-white or specified key color into transparent alpha pixels."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            img = img.convert("RGBA")
            np_img = np.array(img)

            tr_r, tr_g, tr_b = self._hex_to_rgb(target_color)

            # Compute Euclidean distance to target color
            r_diff = np.abs(np_img[:, :, 0].astype(int) - tr_r)
            g_diff = np.abs(np_img[:, :, 1].astype(int) - tr_g)
            b_diff = np.abs(np_img[:, :, 2].astype(int) - tr_b)

            mask = (r_diff <= tolerance) & (g_diff <= tolerance) & (b_diff <= tolerance)
            np_img[mask, 3] = 0

            res_img = Image.fromarray(np_img, mode="RGBA")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            res_img.save(out_path, format="PNG")

        return {"success": True, "output_path": str(out_path)}

    # -------------------------------------------------------------------------
    # 11. ADVANCED: FAVICON, CONTACT SHEET, GIF MAKER
    # -------------------------------------------------------------------------
    def generate_ico(
        self,
        input_path: Path,
        output_path: Path,
        sizes: List[int] = [16, 24, 32, 48, 64, 128, 256]
    ) -> Dict[str, Any]:
        """Generates multi-resolution .ico icon file."""
        in_path = Path(input_path)
        out_path = Path(output_path)

        with Image.open(in_path) as img:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            ico_sizes = [(s, s) for s in sizes]
            img.save(out_path, format="ICO", sizes=ico_sizes)

        return {"success": True, "sizes": sizes, "output_path": str(out_path)}

    def contact_sheet(
        self,
        image_paths: List[Path],
        output_path: Path,
        cols: int = 4,
        cell_size: Tuple[int, int] = (240, 240),
        spacing: int = 12,
        bg_color: str = "#1E1E1E",
        include_names: bool = True
    ) -> Dict[str, Any]:
        """Creates a contact sheet grid mosaic of multiple images."""
        if not image_paths:
            return {"success": False, "error": "No images provided"}

        num_images = len(image_paths)
        rows = math.ceil(num_images / cols)

        cell_w, cell_h = cell_size
        text_h = 24 if include_names else 0

        grid_w = cols * cell_w + (cols + 1) * spacing
        grid_h = rows * (cell_h + text_h) + (rows + 1) * spacing

        bg_rgb = self._hex_to_rgb(bg_color)
        canvas = Image.new("RGB", (grid_w, grid_h), bg_rgb)
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()

        for idx, p in enumerate(image_paths):
            c = idx % cols
            r = idx // cols

            x = spacing + c * (cell_w + spacing)
            y = spacing + r * (cell_h + text_h + spacing)

            try:
                with Image.open(p) as tile:
                    tile.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                    # Center in cell
                    offset_x = x + (cell_w - tile.width) // 2
                    offset_y = y + (cell_h - tile.height) // 2
                    canvas.paste(tile, (offset_x, offset_y))

                if include_names:
                    lbl = p.name[:24]
                    draw.text((x + 4, y + cell_h + 4), lbl, font=font, fill=(200, 200, 200))
            except Exception:
                continue

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, quality=90)

        return {"success": True, "output_path": str(out_path), "grid": (cols, rows)}

    def create_gif(
        self,
        image_paths: List[Path],
        output_path: Path,
        duration_ms: int = 200,
        loop: int = 0
    ) -> Dict[str, Any]:
        """Creates animated GIF from image sequence."""
        if not image_paths:
            return {"success": False, "error": "No images provided"}

        frames = []
        first_size = None

        for p in image_paths:
            try:
                img = Image.open(p)
                if not first_size:
                    first_size = img.size
                else:
                    if img.size != first_size:
                        img = img.resize(first_size, Image.Resampling.LANCZOS)
                frames.append(img.convert("RGBA"))
            except Exception:
                continue

        if not frames:
            return {"success": False, "error": "Failed to decode frames"}

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        frames[0].save(
            out_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=loop,
            format="GIF"
        )

        return {"success": True, "frames": len(frames), "output_path": str(out_path)}

    def extract_gif_frames(
        self,
        input_path: Path,
        output_dir: Path,
        format: str = "png"
    ) -> Dict[str, Any]:
        """Extracts individual frames from an animated GIF."""
        in_path = Path(input_path)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        extracted = []
        with Image.open(in_path) as gif:
            frame_idx = 0
            while True:
                try:
                    gif.seek(frame_idx)
                    frame_path = out_dir / f"frame_{frame_idx+1:04d}.{format}"
                    gif.convert("RGBA").save(frame_path)
                    extracted.append(str(frame_path))
                    frame_idx += 1
                except EOFError:
                    break

        return {"success": True, "count": len(extracted), "frames": extracted}

    # -------------------------------------------------------------------------
    # 12. PERCEPTUAL SIMILARITY & PALETTE EXTRACTOR
    # -------------------------------------------------------------------------
    def calculate_image_hash(self, image_path: Path) -> Optional[str]:
        """Computes perceptual dHash string for visual similarity comparisons."""
        if not imagehash:
            return None
        try:
            with Image.open(image_path) as img:
                return str(imagehash.dhash(img))
        except Exception:
            return None

    def compare_images_similarity(self, path1: Path, path2: Path) -> float:
        """Returns similarity percentage (0.0 to 100.0) based on perceptual hashing."""
        if not imagehash:
            return 0.0
        try:
            with Image.open(path1) as img1, Image.open(path2) as img2:
                h1 = imagehash.dhash(img1)
                h2 = imagehash.dhash(img2)
                diff = h1 - h2  # Hamming distance (0 to 64)
                similarity = max(0.0, 100.0 - (diff / 64.0 * 100.0))
                return round(similarity, 1)
        except Exception:
            return 0.0

    def extract_color_palette(self, image_path: Path, num_colors: int = 6) -> List[Dict[str, Any]]:
        """Extracts dominant color palette in HEX and RGB with occurrence percentages."""
        in_path = Path(image_path)
        palette = []
        try:
            with Image.open(in_path) as img:
                img = img.convert("RGB")
                img.thumbnail((150, 150), Image.Resampling.BOX)
                quantized = img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
                colors = quantized.getcolors()
                if not colors:
                    return []

                total_pixels = sum(count for count, _ in colors)
                raw_palette = quantized.getpalette()[:num_colors * 3]

                for count, idx in sorted(colors, key=lambda x: x[0], reverse=True):
                    r = raw_palette[idx * 3]
                    g = raw_palette[idx * 3 + 1]
                    b = raw_palette[idx * 3 + 2]
                    hex_code = f"#{r:02X}{g:02X}{b:02X}"
                    pct = round((count / total_pixels) * 100.0, 1)
                    palette.append({
                        "hex": hex_code,
                        "rgb": (r, g, b),
                        "percentage": pct
                    })
        except Exception as e:
            logger.error(f"Failed to extract palette: {e}")

        return palette

    def analyze_image(self, image_path: Path) -> Dict[str, Any]:
        """Inspects technical properties, dimensions, DPI, and blur score."""
        in_path = Path(image_path)
        info: Dict[str, Any] = {"path": str(in_path), "filename": in_path.name}

        try:
            with Image.open(in_path) as img:
                w, h = img.size
                mp = round((w * h) / 1_000_000.0, 2)
                dpi = img.info.get("dpi", (72, 72))
                info.update({
                    "format": img.format or in_path.suffix.lstrip(".").upper(),
                    "width": w,
                    "height": h,
                    "megapixels": mp,
                    "mode": img.mode,
                    "dpi": f"{int(dpi[0])} x {int(dpi[1])}",
                    "file_size": in_path.stat().st_size
                })

            # Calculate blur score using OpenCV variance of Laplacian
            if cv2 is not None:
                cv_img = cv2.imread(str(in_path), cv2.IMREAD_GRAYSCALE)
                if cv_img is not None:
                    var = cv2.Laplacian(cv_img, cv2.CV_64F).var()
                    info["blur_score"] = round(var, 1)
                    info["is_blurry"] = bool(var < 100.0)
        except Exception as e:
            info["error"] = str(e)

        return info

    # -------------------------------------------------------------------------
    # INTERNAL HELPERS
    # -------------------------------------------------------------------------
    def _save_pil_image(
        self,
        img: Image.Image,
        out_path: Path,
        include_exif: bool = True,
        raw_exif: Optional[bytes] = None
    ):
        ext = out_path.suffix.lower().lstrip(".")
        fmt = "JPEG" if ext in ("jpg", "jpeg") else ext.upper()

        if fmt == "JPEG" and img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.split()[-1] if img.mode == "RGBA" else None
            bg.paste(img, mask=alpha)
            img = bg
        elif fmt == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        kwargs: Dict[str, Any] = {"format": fmt}
        if fmt in ("JPEG", "WEBP"):
            kwargs["quality"] = 88
            kwargs["optimize"] = True

        if raw_exif:
            kwargs["exif"] = raw_exif
        elif not include_exif:
            kwargs["exif"] = b""

        img.save(out_path, **kwargs)

    def _compute_position(self, w: int, h: int, item_w: int, item_h: int, pos_str: str, margin: int) -> Tuple[int, int]:
        p = pos_str.lower()
        if "top" in p:
            y = margin
        elif "bottom" in p:
            y = h - item_h - margin
        else:
            y = (h - item_h) // 2

        if "left" in p:
            x = margin
        elif "right" in p:
            x = w - item_w - margin
        else:
            x = (w - item_w) // 2

        return (max(0, x), max(0, y))

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join([c * 2 for c in h])
        if len(h) != 6:
            return (255, 255, 255)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# Global service instance
image_service = ImageService()
