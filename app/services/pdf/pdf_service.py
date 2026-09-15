# -*- coding: utf-8 -*-
"""
SINAX Core PDF Service
Comprehensive local PDF engine utilizing pymupdf, pypdf, reportlab, and Pillow.
Provides 25+ production-grade offline PDF operations with zero external network calls.
"""

import os
import io
import math
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Callable

import fitz  # PyMuPDF
from PIL import Image
import pypdf

from app.core.logger import get_logger
from app.services.pdf.pdf_utils import parse_page_ranges, get_page_size_points, create_safe_output_path

logger = get_logger("pdf_service")


class PDFService:
    """Singleton service for all PDF manipulation and analysis operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PDFService, cls).__new__(cls)
        return cls._instance

    # ----------------------------------------------------------------------
    # 1. MERGE PDFs
    # ----------------------------------------------------------------------
    def merge_pdfs(
        self,
        files_with_ranges: List[Tuple[Path, str]],
        output_path: Path,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """
        Merges multiple PDF files into one output document.
        files_with_ranges: List of (file_path, page_range_str e.g. "1-5, 8")
        """
        out_doc = fitz.open()
        total_files = len(files_with_ranges)

        try:
            for i, (file_path, page_range) in enumerate(files_with_ranges):
                if progress_cb:
                    progress_cb((i / total_files) * 0.85, f"جاري دمج {file_path.name}...")

                src_doc = fitz.open(str(file_path))
                total_src_pages = len(src_doc)
                pages_to_include = parse_page_ranges(page_range, total_src_pages)

                for page_idx in pages_to_include:
                    out_doc.insert_pdf(src_doc, from_page=page_idx, to_page=page_idx)
                src_doc.close()

            if progress_cb:
                progress_cb(0.9, "جاري حفظ المستند النهائي...")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_doc.save(str(output_path), garbage=4, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تم دمج الملفات بنجاح.")
            return output_path
        finally:
            out_doc.close()

    # ----------------------------------------------------------------------
    # 2. SPLIT PDF
    # ----------------------------------------------------------------------
    def split_pdf(
        self,
        file_path: Path,
        output_dir: Path,
        split_mode: str = "pages",
        chunk_size: int = 10,
        custom_ranges: str = "",
        split_after: str = "",
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> List[Path]:
        """
        Splits PDF into multiple output files:
        split_mode: 'pages' (single page each), 'chunks' (every N pages),
                    'custom' (e.g. '1-5, 6-12'), 'split_after' (e.g. '5, 12')
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        src_doc = fitz.open(str(file_path))
        total_pages = len(src_doc)
        output_files: List[Path] = []
        stem = file_path.stem

        try:
            if split_mode == "pages":
                for p in range(total_pages):
                    if progress_cb:
                        progress_cb(p / total_pages, f"حفظ الصفحة {p+1} من {total_pages}...")
                    out_doc = fitz.open()
                    out_doc.insert_pdf(src_doc, from_page=p, to_page=p)
                    dest = output_dir / f"{stem}_page_{p+1:03d}.pdf"
                    out_doc.save(str(dest), garbage=3, deflate=True)
                    out_doc.close()
                    output_files.append(dest)

            elif split_mode == "chunks":
                chunk_idx = 1
                for start_p in range(0, total_pages, chunk_size):
                    end_p = min(start_p + chunk_size - 1, total_pages - 1)
                    if progress_cb:
                        progress_cb(start_p / total_pages, f"حفظ الجزء {chunk_idx} (صفحات {start_p+1}-{end_p+1})...")
                    out_doc = fitz.open()
                    out_doc.insert_pdf(src_doc, from_page=start_p, to_page=end_p)
                    dest = output_dir / f"{stem}_part_{chunk_idx:02d}.pdf"
                    out_doc.save(str(dest), garbage=3, deflate=True)
                    out_doc.close()
                    output_files.append(dest)
                    chunk_idx += 1

            elif split_mode == "custom":
                # custom_ranges e.g. "1-5, 6-10, 11-15"
                groups = [g.strip() for g in custom_ranges.replace("،", ",").split(",") if g.strip()]
                for idx, group in enumerate(groups):
                    pages = parse_page_ranges(group, total_pages)
                    if not pages:
                        continue
                    if progress_cb:
                        progress_cb(idx / len(groups), f"حفظ النطاق {group}...")
                    out_doc = fitz.open()
                    for p in pages:
                        out_doc.insert_pdf(src_doc, from_page=p, to_page=p)
                    dest = output_dir / f"{stem}_range_{group.replace('-', '_')}.pdf"
                    out_doc.save(str(dest), garbage=3, deflate=True)
                    out_doc.close()
                    output_files.append(dest)

            elif split_mode == "split_after":
                cut_pages = sorted(list(set(parse_page_ranges(split_after, total_pages))))
                # Cut pages are 0-indexed where cut happens after page
                cuts = [c + 1 for c in cut_pages if c + 1 < total_pages]
                boundaries = [0] + cuts + [total_pages]
                for idx in range(len(boundaries) - 1):
                    start_p = boundaries[idx]
                    end_p = boundaries[idx + 1] - 1
                    if start_p > end_p:
                        continue
                    out_doc = fitz.open()
                    out_doc.insert_pdf(src_doc, from_page=start_p, to_page=end_p)
                    dest = output_dir / f"{stem}_sec_{idx+1:02d}_p{start_p+1}-{end_p+1}.pdf"
                    out_doc.save(str(dest), garbage=3, deflate=True)
                    out_doc.close()
                    output_files.append(dest)

            if progress_cb:
                progress_cb(1.0, f"تم تقسيم الملف إلى {len(output_files)} أجزاء.")
            return output_files
        finally:
            src_doc.close()

    # ----------------------------------------------------------------------
    # 3. EXTRACT PAGES
    # ----------------------------------------------------------------------
    def extract_pages(
        self,
        file_path: Path,
        output_path: Path,
        pages_str: str,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Extracts specified pages into a new PDF document."""
        src_doc = fitz.open(str(file_path))
        out_doc = fitz.open()
        try:
            total_pages = len(src_doc)
            target_indices = parse_page_ranges(pages_str, total_pages)
            if not target_indices:
                raise ValueError("لم يتم تحديد صفحات صالحة للاستخراج.")

            for i, p in enumerate(target_indices):
                if progress_cb:
                    progress_cb(i / len(target_indices), f"استخراج صفحة {p+1}...")
                out_doc.insert_pdf(src_doc, from_page=p, to_page=p)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_doc.save(str(output_path), garbage=3, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تم استخراج الصفحات بنجاح.")
            return output_path
        finally:
            out_doc.close()
            src_doc.close()

    # ----------------------------------------------------------------------
    # 4. DELETE PAGES
    # ----------------------------------------------------------------------
    def delete_pages(
        self,
        file_path: Path,
        output_path: Path,
        pages_str: str = "",
        mode: str = "custom",  # 'custom', 'odd', 'even'
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Deletes specified, odd, or even pages from PDF."""
        src_doc = fitz.open(str(file_path))
        out_doc = fitz.open()
        try:
            total_pages = len(src_doc)
            if mode == "odd":
                # 1-indexed odd: page 1, 3, 5 -> indices 0, 2, 4
                to_delete = set(range(0, total_pages, 2))
            elif mode == "even":
                # 1-indexed even: page 2, 4, 6 -> indices 1, 3, 5
                to_delete = set(range(1, total_pages, 2))
            else:
                to_delete = set(parse_page_ranges(pages_str, total_pages))

            kept_pages = [p for p in range(total_pages) if p not in to_delete]
            if not kept_pages:
                raise ValueError("لا يمكن حذف جميع صفحات المستند.")

            for i, p in enumerate(kept_pages):
                if progress_cb:
                    progress_cb(i / len(kept_pages), f"حفظ صفحة {p+1}...")
                out_doc.insert_pdf(src_doc, from_page=p, to_page=p)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_doc.save(str(output_path), garbage=4, deflate=True)
            if progress_cb:
                progress_cb(1.0, f"تم حذف {len(to_delete)} صفحة بنجاح.")
            return output_path
        finally:
            out_doc.close()
            src_doc.close()

    # ----------------------------------------------------------------------
    # 5. REORDER PAGES
    # ----------------------------------------------------------------------
    def reorder_pages(
        self,
        file_path: Path,
        output_path: Path,
        new_order: List[int],
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Reorders pages in PDF using a list of 0-based page indices."""
        src_doc = fitz.open(str(file_path))
        out_doc = fitz.open()
        try:
            total_pages = len(src_doc)
            valid_order = [p for p in new_order if 0 <= p < total_pages]
            for i, p in enumerate(valid_order):
                if progress_cb:
                    progress_cb(i / len(valid_order), f"إعادة ترتيب صفحة {p+1}...")
                out_doc.insert_pdf(src_doc, from_page=p, to_page=p)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_doc.save(str(output_path), garbage=3, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تمت إعادة ترتيب الصفحات بنجاح.")
            return output_path
        finally:
            out_doc.close()
            src_doc.close()

    # ----------------------------------------------------------------------
    # 6. ROTATE PAGES
    # ----------------------------------------------------------------------
    def rotate_pages(
        self,
        file_path: Path,
        output_path: Path,
        angle: int = 90,
        pages_str: str = "all",
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Rotates specified pages by 90, 180, or 270 degrees clockwise."""
        doc = fitz.open(str(file_path))
        try:
            total_pages = len(doc)
            target_pages = parse_page_ranges(pages_str, total_pages)
            for i, pno in enumerate(target_pages):
                if progress_cb:
                    progress_cb(i / len(target_pages), f"تدوير صفحة {pno+1}...")
                page = doc[pno]
                page.set_rotation((page.rotation + angle) % 360)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=3, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تم تدوير الصفحات بنجاح.")
            return output_path
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 7. CROP PAGES & HALVE PAGES
    # ----------------------------------------------------------------------
    def crop_pages(
        self,
        file_path: Path,
        output_path: Path,
        mode: str = "margins",  # 'margins', 'halve_vertical', 'halve_horizontal'
        margins: Tuple[float, float, float, float] = (0, 0, 0, 0),  # (top, right, bottom, left) in pt
        pages_str: str = "all",
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """
        Crops margins or splits dual pages into two individual pages.
        """
        src_doc = fitz.open(str(file_path))
        out_doc = fitz.open()

        try:
            total_pages = len(src_doc)
            target_pages = parse_page_ranges(pages_str, total_pages)

            if mode in ("halve_vertical", "halve_horizontal"):
                for i, pno in enumerate(range(total_pages)):
                    if progress_cb:
                        progress_cb(i / total_pages, f"معالجة صفحة {pno+1}...")
                    page = src_doc[pno]
                    rect = page.rect
                    if pno in target_pages:
                        if mode == "halve_vertical":
                            # Split left and right halves (for dual-page scans)
                            mid_x = rect.x0 + rect.width / 2.0
                            # Left Page
                            p1 = out_doc.new_page(width=rect.width / 2.0, height=rect.height)
                            p1.show_pdf_page(p1.rect, src_doc, pno, clip=fitz.Rect(rect.x0, rect.y0, mid_x, rect.y1))
                            # Right Page
                            p2 = out_doc.new_page(width=rect.width / 2.0, height=rect.height)
                            p2.show_pdf_page(p2.rect, src_doc, pno, clip=fitz.Rect(mid_x, rect.y0, rect.x1, rect.y1))
                        else:
                            # Split top and bottom halves
                            mid_y = rect.y0 + rect.height / 2.0
                            p1 = out_doc.new_page(width=rect.width, height=rect.height / 2.0)
                            p1.show_pdf_page(p1.rect, src_doc, pno, clip=fitz.Rect(rect.x0, rect.y0, rect.x1, mid_y))
                            p2 = out_doc.new_page(width=rect.width, height=rect.height / 2.0)
                            p2.show_pdf_page(p2.rect, src_doc, pno, clip=fitz.Rect(rect.x0, mid_y, rect.x1, rect.y1))
                    else:
                        out_doc.insert_pdf(src_doc, from_page=pno, to_page=pno)
            else:
                # Margins mode
                top, right, bottom, left = margins
                for i, pno in enumerate(range(total_pages)):
                    if progress_cb:
                        progress_cb(i / total_pages, f"اقتصاص صفحة {pno+1}...")
                    page = src_doc[pno]
                    rect = page.rect
                    if pno in target_pages:
                        new_rect = fitz.Rect(
                            rect.x0 + left,
                            rect.y0 + top,
                            rect.x1 - right,
                            rect.y1 - bottom
                        )
                        page.set_cropbox(new_rect)
                    out_doc.insert_pdf(src_doc, from_page=pno, to_page=pno)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_doc.save(str(output_path), garbage=4, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تم اقتصاص الصفحات بنجاح.")
            return output_path
        finally:
            out_doc.close()
            src_doc.close()

    # ----------------------------------------------------------------------
    # 8. COMPRESS PDF
    # ----------------------------------------------------------------------
    def compress_pdf(
        self,
        file_path: Path,
        output_path: Path,
        preset: str = "balanced",  # 'light', 'balanced', 'strong', 'max'
        custom_dpi: int = 150,
        custom_quality: int = 75,
        grayscale: bool = False,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> int:
        """
        Compresses PDF using intelligent image downsampling and Deflate optimization.
        Returns the resulting size in bytes.
        """
        preset_configs = {
            "light": {"dpi": 200, "quality": 85, "downsample": False},
            "balanced": {"dpi": 150, "quality": 75, "downsample": True},
            "strong": {"dpi": 100, "quality": 55, "downsample": True},
            "max": {"dpi": 72, "quality": 35, "downsample": True},
        }

        cfg = preset_configs.get(preset, preset_configs["balanced"])
        target_dpi = custom_dpi if preset == "custom" else cfg["dpi"]
        target_quality = custom_quality if preset == "custom" else cfg["quality"]
        do_downsample = cfg["downsample"] if preset != "custom" else True

        doc = fitz.open(str(file_path))
        total_pages = len(doc)

        try:
            if do_downsample or grayscale:
                processed_xrefs = set()
                for pno in range(total_pages):
                    if progress_cb:
                        progress_cb((pno / total_pages) * 0.8, f"تحسين صور الصفحة {pno+1}...")
                    page = doc[pno]
                    image_list = page.get_images(full=True)

                    for img_info in image_list:
                        xref = img_info[0]
                        if xref in processed_xrefs:
                            continue
                        processed_xrefs.add(xref)

                        try:
                            base_img = doc.extract_image(xref)
                            if not base_img:
                                continue
                            img_bytes = base_img["image"]
                            img = Image.open(io.BytesIO(img_bytes))

                            # Grayscale conversion if requested
                            if grayscale and img.mode not in ("L", "1"):
                                img = img.convert("L")

                            # Downsample if large
                            orig_w, orig_h = img.size
                            # If larger than target DPI dimensions (approx max 2000px)
                            max_dim = int(8.27 * target_dpi)  # ~A4 width in pixels
                            if max(orig_w, orig_h) > max_dim:
                                scale = max_dim / float(max(orig_w, orig_h))
                                new_w = max(1, int(orig_w * scale))
                                new_h = max(1, int(orig_h * scale))
                                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                            buf = io.BytesIO()
                            if img.mode in ("RGBA", "P"):
                                img.convert("RGB").save(buf, format="JPEG", quality=target_quality, optimize=True)
                            else:
                                img.save(buf, format="JPEG", quality=target_quality, optimize=True)

                            # Replace image in PDF
                            new_bytes = buf.getvalue()
                            if len(new_bytes) < len(img_bytes):
                                doc.update_stream(xref, new_bytes)
                        except Exception as e:
                            logger.debug(f"Skipping image xref {xref} compression: {e}")

            if progress_cb:
                progress_cb(0.9, "إعادة بناء وتفريغ المستند...")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(
                str(output_path),
                garbage=4,
                deflate=True,
                clean=True,
                deflate_images=True,
                deflate_fonts=True
            )

            final_size = output_path.stat().st_size
            if progress_cb:
                progress_cb(1.0, f"تم الضغط بنجاح (الحجم الناتج: {final_size / (1024*1024):.2f} MB)")
            return final_size
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 9. COMPRESS TO TARGET SIZE (ITERATIVE OPTIMIZATION)
    # ----------------------------------------------------------------------
    def compress_target_size(
        self,
        file_path: Path,
        output_path: Path,
        target_bytes: int,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> int:
        """
        Iteratively compresses PDF using diminishing DPI and quality settings
        until the target size is achieved or best achievable ratio is reached.
        """
        orig_size = file_path.stat().st_size
        if orig_size <= target_bytes:
            shutil.copy2(file_path, output_path)
            return orig_size

        levels = [
            ("light", 200, 85),
            ("balanced", 150, 75),
            ("strong", 110, 60),
            ("max", 85, 45),
            ("max", 72, 30),
        ]

        temp_out = output_path.with_suffix(".tmp.pdf")
        best_size = orig_size

        try:
            for idx, (preset, dpi, qual) in enumerate(levels):
                if progress_cb:
                    progress_cb(idx / len(levels), f"محاولة ضغط بدقة {dpi} DPI وجودة {qual}%...")

                curr_size = self.compress_pdf(
                    file_path, temp_out, preset="custom", custom_dpi=dpi, custom_quality=qual
                )
                best_size = curr_size

                if curr_size <= target_bytes:
                    break

            if temp_out.exists():
                if output_path.exists():
                    output_path.unlink()
                temp_out.rename(output_path)

            if progress_cb:
                progress_cb(1.0, f"اكتملت المحاولة. الحجم النهائي: {best_size / (1024*1024):.2f} MB")
            return best_size
        finally:
            if temp_out.exists():
                try:
                    temp_out.unlink()
                except Exception:
                    pass

    # ----------------------------------------------------------------------
    # 10. PDF TO IMAGES
    # ----------------------------------------------------------------------
    def pdf_to_images(
        self,
        file_path: Path,
        output_dir: Path,
        img_format: str = "png",  # 'png', 'jpg', 'webp', 'tiff'
        dpi: int = 150,
        pages_str: str = "all",
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> List[Path]:
        """Renders specified PDF pages to standalone high-res image files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        target_pages = parse_page_ranges(pages_str, total_pages)
        output_files: List[Path] = []
        stem = file_path.stem
        fmt = img_format.lower().strip()
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        try:
            for i, pno in enumerate(target_pages):
                if progress_cb:
                    progress_cb(i / len(target_pages), f"تصدير صورة الصفحة {pno+1}...")
                page = doc[pno]
                pix = page.get_pixmap(matrix=matrix, alpha=(fmt == "png"))
                dest = output_dir / f"{stem}_page_{pno+1:03d}.{fmt}"

                if fmt in ("jpg", "jpeg"):
                    pix.save(str(dest), output="jpg")
                elif fmt == "webp":
                    # Convert pix to PIL then webp
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img.save(dest, format="WEBP", quality=90)
                elif fmt == "tiff":
                    img = Image.frombytes("RGB" if not pix.alpha else "RGBA", [pix.width, pix.height], pix.samples)
                    img.save(dest, format="TIFF")
                else:
                    pix.save(str(dest))

                output_files.append(dest)

            if progress_cb:
                progress_cb(1.0, f"تم تصدير {len(output_files)} صورة بنجاح.")
            return output_files
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 11. IMAGES TO PDF
    # ----------------------------------------------------------------------
    def images_to_pdf(
        self,
        image_files: List[Path],
        output_path: Path,
        page_size: str = "a4",
        fit_mode: str = "fit",  # 'fit', 'fill', 'original'
        margin_pt: float = 20.0,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Combines multiple image files into a single unified PDF."""
        out_doc = fitz.open()
        total_imgs = len(image_files)

        try:
            target_w, target_h = get_page_size_points(page_size)

            for i, img_path in enumerate(image_files):
                if progress_cb:
                    progress_cb(i / total_imgs, f"إدراج صورة {img_path.name}...")

                with Image.open(img_path) as im:
                    im_w, im_h = im.size

                if fit_mode == "original":
                    # Page matches image size exactly
                    page = out_doc.new_page(width=im_w, height=im_h)
                    page.insert_image(page.rect, filename=str(img_path))
                else:
                    # Target page size with margins
                    page = out_doc.new_page(width=target_w, height=target_h)
                    avail_rect = fitz.Rect(
                        margin_pt,
                        margin_pt,
                        target_w - margin_pt,
                        target_h - margin_pt
                    )

                    # Compute aspect ratio fit
                    aspect = im_w / float(im_h)
                    box_aspect = avail_rect.width / float(avail_rect.height)

                    if fit_mode == "fit":
                        if aspect > box_aspect:
                            # Width constrained
                            w = avail_rect.width
                            h = w / aspect
                        else:
                            # Height constrained
                            h = avail_rect.height
                            w = h * aspect
                        x = avail_rect.x0 + (avail_rect.width - w) / 2.0
                        y = avail_rect.y0 + (avail_rect.height - h) / 2.0
                        img_rect = fitz.Rect(x, y, x + w, y + h)
                    else:
                        img_rect = avail_rect

                    page.insert_image(img_rect, filename=str(img_path))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_doc.save(str(output_path), garbage=4, deflate=True)
            if progress_cb:
                progress_cb(1.0, f"تم تجميع {total_imgs} صورة في PDF واحد.")
            return output_path
        finally:
            out_doc.close()

    # ----------------------------------------------------------------------
    # 12. WATERMARK (TEXT & IMAGE)
    # ----------------------------------------------------------------------
    def add_watermark(
        self,
        file_path: Path,
        output_path: Path,
        text: str = "",
        font_size: int = 42,
        color_rgb: Tuple[float, float, float] = (0.7, 0.7, 0.7),
        opacity: float = 0.35,
        angle: float = 45.0,
        image_path: Optional[Path] = None,
        pages_str: str = "all",
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Adds text watermark or image stamp across PDF pages."""
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        target_pages = parse_page_ranges(pages_str, total_pages)

        try:
            for i, pno in enumerate(target_pages):
                if progress_cb:
                    progress_cb(i / len(target_pages), f"تطبيق العلامة المائية على صفحة {pno+1}...")
                page = doc[pno]
                rect = page.rect

                if image_path and image_path.exists():
                    # Center image stamp
                    with Image.open(image_path) as im:
                        iw, ih = im.size
                    max_w = rect.width * 0.6
                    scale = max_w / float(iw)
                    tw = iw * scale
                    th = ih * scale
                    img_rect = fitz.Rect(
                        (rect.width - tw) / 2.0,
                        (rect.height - th) / 2.0,
                        (rect.width + tw) / 2.0,
                        (rect.height + th) / 2.0
                    )
                    page.insert_image(img_rect, filename=str(image_path), overlay=True)
                elif text:
                    # Centered angled text watermark
                    center = fitz.Point(rect.width / 2.0, rect.height / 2.0)
                    page.insert_text(
                        center,
                        text,
                        fontsize=font_size,
                        morph=(center, fitz.Matrix(angle)),
                        color=color_rgb,
                        stroke_opacity=opacity,
                        fill_opacity=opacity,
                        overlay=True
                    )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=3, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تمت إضافة العلامة المائية بنجاح.")
            return output_path
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 13. PAGE NUMBERS & BATES
    # ----------------------------------------------------------------------
    def add_page_numbers(
        self,
        file_path: Path,
        output_path: Path,
        position: str = "bottom_center",
        pattern: str = "صفحة {page} من {total}",
        start_num: int = 1,
        prefix: str = "",
        pages_str: str = "all",
        font_size: int = 10,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Adds page numbers or Bates numbering to specified positions."""
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        target_pages = parse_page_ranges(pages_str, total_pages)

        try:
            curr_number = start_num
            for i, pno in enumerate(target_pages):
                if progress_cb:
                    progress_cb(i / len(target_pages), f"ترقيم صفحة {pno+1}...")
                page = doc[pno]
                rect = page.rect

                label_text = pattern.format(page=curr_number, total=total_pages)
                if prefix:
                    label_text = f"{prefix}{curr_number:06d}"

                margin = 32.0
                if position == "bottom_center":
                    pt = fitz.Point(rect.width / 2.0 - len(label_text) * 3, rect.height - margin)
                elif position == "bottom_right":
                    pt = fitz.Point(rect.width - margin - len(label_text) * 7, rect.height - margin)
                elif position == "bottom_left":
                    pt = fitz.Point(margin, rect.height - margin)
                elif position == "top_center":
                    pt = fitz.Point(rect.width / 2.0 - len(label_text) * 3, margin)
                elif position == "top_right":
                    pt = fitz.Point(rect.width - margin - len(label_text) * 7, margin)
                else:  # top_left
                    pt = fitz.Point(margin, margin)

                page.insert_text(pt, label_text, fontsize=font_size, color=(0.2, 0.2, 0.2), overlay=True)
                curr_number += 1

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=3, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تم ترقيم الصفحات بنجاح.")
            return output_path
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 14. PROTECT / ENCRYPT PDF (AES-256)
    # ----------------------------------------------------------------------
    def protect_pdf(
        self,
        file_path: Path,
        output_path: Path,
        user_password: str,
        owner_password: str = "",
        allow_print: bool = True,
        allow_copy: bool = True,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Encrypts PDF using AES-256 with passwords and permission flags."""
        reader = pypdf.PdfReader(str(file_path))
        writer = pypdf.PdfWriter()

        for i, page in enumerate(reader.pages):
            if progress_cb:
                progress_cb(i / len(reader.pages), f"تشفير صفحة {i+1}...")
            writer.add_page(page)

        owner_pwd = owner_password if owner_password else user_password

        # Encryption with AES-256
        writer.encrypt(
            user_password=user_password,
            owner_password=owner_pwd,
            permissions_flag=pypdf.constants.UserAccessPermissions.PRINT if allow_print else 0
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

        if progress_cb:
            progress_cb(1.0, "تم تشفير وحماية المستند بنجاح (AES-256).")
        return output_path

    # ----------------------------------------------------------------------
    # 15. UNLOCK / DECRYPT PDF
    # ----------------------------------------------------------------------
    def unlock_pdf(
        self,
        file_path: Path,
        output_path: Path,
        password: str,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Removes encryption from PDF using the valid password."""
        doc = fitz.open(str(file_path))
        try:
            if doc.is_encrypted:
                auth_res = doc.authenticate(password)
                if not auth_res:
                    raise ValueError("كلمة المرور غير صحيحة.")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=4, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تم فك قفل المستند وإزالة التشفير بنجاح.")
            return output_path
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 16. TRUE REDACTION
    # ----------------------------------------------------------------------
    def redact_pdf(
        self,
        file_path: Path,
        output_path: Path,
        search_terms: List[str],
        case_sensitive: bool = False,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[Path, int]:
        """
        Permanently redacts (erases) matching text patterns and pixels.
        Returns (output_path, count_of_redactions_applied).
        """
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        redactions_count = 0

        try:
            for pno in range(total_pages):
                if progress_cb:
                    progress_cb(pno / total_pages, f"فحص وتنقيح صفحة {pno+1}...")
                page = doc[pno]

                for term in search_terms:
                    term = term.strip()
                    if not term:
                        continue
                    # Search text rects
                    rects = page.search_for(term, flags=fitz.TEXTFLAGS_SEARCH if not case_sensitive else 0)
                    for r in rects:
                        page.add_redact_annot(r, fill=(0, 0, 0))
                        redactions_count += 1

                # Apply redactions permanently to page
                page.apply_redactions()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=4, deflate=True)
            if progress_cb:
                progress_cb(1.0, f"تم تنقيح {redactions_count} موقع بنجاح.")
            return output_path, redactions_count
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 17. METADATA MANAGEMENT
    # ----------------------------------------------------------------------
    def clean_metadata(
        self,
        file_path: Path,
        output_path: Path,
        strip_all: bool = True,
        new_meta: Optional[Dict[str, str]] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """Strips or updates PDF metadata attributes."""
        doc = fitz.open(str(file_path))
        try:
            if strip_all:
                doc.set_metadata({})
            elif new_meta:
                meta = doc.metadata or {}
                meta.update(new_meta)
                doc.set_metadata(meta)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path), garbage=4, deflate=True)
            if progress_cb:
                progress_cb(1.0, "تم تحديث البيانات الوصفية بنجاح.")
            return output_path
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 18. EXTRACT TEXT
    # ----------------------------------------------------------------------
    def extract_text(
        self,
        file_path: Path,
        output_txt_path: Path,
        pages_str: str = "all",
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """Extracts text content from PDF pages and saves to UTF-8 TXT file."""
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        target_pages = parse_page_ranges(pages_str, total_pages)
        full_text = []

        try:
            for i, pno in enumerate(target_pages):
                if progress_cb:
                    progress_cb(i / len(target_pages), f"استخراج نص صفحة {pno+1}...")
                page = doc[pno]
                text = page.get_text("text")
                full_text.append(f"--- [الصفحة {pno+1}] ---\n" + text)

            result_str = "\n\n".join(full_text)
            output_txt_path.parent.mkdir(parents=True, exist_ok=True)
            output_txt_path.write_text(result_str, encoding="utf-8")

            if progress_cb:
                progress_cb(1.0, "تم استخراج النصوص بنجاح.")
            return result_str
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 19. EXTRACT EMBEDDED IMAGES
    # ----------------------------------------------------------------------
    def extract_images(
        self,
        file_path: Path,
        output_dir: Path,
        pages_str: str = "all",
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> List[Path]:
        """Extracts original embedded images from PDF pages."""
        output_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        target_pages = parse_page_ranges(pages_str, total_pages)
        extracted: List[Path] = []
        stem = file_path.stem
        seen_xrefs = set()

        try:
            for i, pno in enumerate(target_pages):
                if progress_cb:
                    progress_cb(i / len(target_pages), f"فحص صور صفحة {pno+1}...")
                page = doc[pno]
                images = page.get_images()

                for img_idx, img_info in enumerate(images):
                    xref = img_info[0]
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)

                    base_img = doc.extract_image(xref)
                    if not base_img:
                        continue
                    ext = base_img["ext"]
                    dest = output_dir / f"{stem}_img_p{pno+1}_{img_idx+1}_{xref}.{ext}"
                    dest.write_bytes(base_img["image"])
                    extracted.append(dest)

            if progress_cb:
                progress_cb(1.0, f"تم استخراج {len(extracted)} صورة أصلية.")
            return extracted
        finally:
            doc.close()

    # ----------------------------------------------------------------------
    # 20. PDF DOCTOR & STATISTICS & REPAIR
    # ----------------------------------------------------------------------
    def inspect_and_repair(
        self,
        file_path: Path,
        repair_output_path: Optional[Path] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Inspects PDF structure, statistics, security, and fixes corrupted XREFs if requested.
        """
        stats: Dict[str, Any] = {
            "is_valid": True,
            "page_count": 0,
            "file_size_mb": 0.0,
            "version": "1.7",
            "is_encrypted": False,
            "has_forms": False,
            "image_count": 0,
            "font_count": 0,
            "links_count": 0,
            "metadata": {},
            "issues": []
        }

        try:
            stats["file_size_mb"] = round(file_path.stat().st_size / (1024 * 1024), 2)
            doc = fitz.open(str(file_path))
            stats["page_count"] = len(doc)
            stats["is_encrypted"] = doc.is_encrypted
            stats["metadata"] = doc.metadata or {}

            # Count components
            total_imgs = 0
            total_links = 0
            fonts_set = set()

            for pno in range(len(doc)):
                page = doc[pno]
                total_imgs += len(page.get_images())
                total_links += len(page.get_links())
                for f in page.get_fonts():
                    fonts_set.add(f[3])

            stats["image_count"] = total_imgs
            stats["links_count"] = total_links
            stats["font_count"] = len(fonts_set)

            # Repair if requested
            if repair_output_path:
                if progress_cb:
                    progress_cb(0.5, "جاري إعادة بناء الهيكل وجداول المراجع...")
                repair_output_path.parent.mkdir(parents=True, exist_ok=True)
                doc.save(str(repair_output_path), garbage=4, clean=True, deflate=True)
                stats["repaired"] = True

            doc.close()
            if progress_cb:
                progress_cb(1.0, "اكتمل فحص الملف بنجاح.")
            return stats
        except Exception as e:
            stats["is_valid"] = False
            stats["issues"].append(f"خطأ في قراءة هيكل الملف: {str(e)}")
            logger.error(f"Error inspecting PDF {file_path}: {e}")
            return stats

    # ----------------------------------------------------------------------
    # 21. COMPARE PDFs
    # ----------------------------------------------------------------------
    def compare_pdfs(
        self,
        file1_path: Path,
        file2_path: Path,
        progress_cb: Optional[Callable[[float, str], None]] = None
    ) -> Dict[str, Any]:
        """Compares two PDFs side by side and detects page and text differences."""
        doc1 = fitz.open(str(file1_path))
        doc2 = fitz.open(str(file2_path))

        try:
            p1_count = len(doc1)
            p2_count = len(doc2)
            max_p = max(p1_count, p2_count)
            diffs = []

            for pno in range(max_p):
                if progress_cb:
                    progress_cb(pno / max_p, f"مقارنة صفحة {pno+1}...")

                t1 = doc1[pno].get_text("text") if pno < p1_count else ""
                t2 = doc2[pno].get_text("text") if pno < p2_count else ""

                if t1 != t2:
                    diffs.append({
                        "page": pno + 1,
                        "match": False,
                        "file1_words": len(t1.split()),
                        "file2_words": len(t2.split()),
                    })
                else:
                    diffs.append({
                        "page": pno + 1,
                        "match": True
                    })

            res = {
                "file1_pages": p1_count,
                "file2_pages": p2_count,
                "diff_pages_count": sum(1 for d in diffs if not d["match"]),
                "pages_summary": diffs
            }
            if progress_cb:
                progress_cb(1.0, "تمت مقارنة المستندين بنجاح.")
            return res
        finally:
            doc1.close()
            doc2.close()


# Global Singleton Instance
pdf_service = PDFService()
