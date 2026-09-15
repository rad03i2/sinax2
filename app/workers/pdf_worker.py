# -*- coding: utf-8 -*-
"""
SINAX PDF Background Worker
Handles async processing of PDF operations with progress reporting, cancellation,
speed metrics, and operation history integration.
"""

import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from PySide6.QtCore import QThread, Signal

from app.workers.base_worker import BaseWorker
from app.services.pdf.pdf_service import pdf_service
from app.services.pdf.pdf_utils import create_safe_output_path
from app.core.undo_manager import undo_manager
from app.core.logger import get_logger

logger = get_logger("pdf_worker")


class PDFWorker(BaseWorker):
    """Background worker for all PDF Center operations."""

    # Signals
    overall_progress = Signal(int, int, float)               # (current_file_idx, total_files, overall_pct)
    file_progress = Signal(float, str)                       # (file_pct, message)
    file_status = Signal(int, str, str, str)                 # (row_index, status_text, output_path, error_msg)
    stats_updated = Signal(float, str)                       # (speed_mb_s, eta_str)
    finished_all = Signal(int, int, int, list)               # (success_count, fail_count, skipped_count, failed_files)

    def __init__(
        self,
        tool_id: str,
        files: List[Path],
        output_dir: Path,
        options: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.tool_id = tool_id
        self.files = files
        self.output_dir = output_dir
        self.options = options or {}
        self._start_time = 0.0

    def run(self):
        self._start_time = time.time()
        success_count = 0
        fail_count = 0
        skipped_count = 0
        failed_files: List[Tuple[Path, str]] = []

        total_files = len(self.files)
        total_bytes_processed = 0

        logger.info(f"Starting PDFWorker for tool '{self.tool_id}' on {total_files} file(s)...")

        # -------------------------------------------------------------
        # SPECIAL CASE: MERGE (combines all input files into one output)
        # -------------------------------------------------------------
        if self.tool_id == "merge":
            try:
                if self.is_canceled():
                    self.operation_canceled.emit()
                    return

                out_name = self.options.get("output_filename", "merged_document.pdf")
                if not out_name.lower().endswith(".pdf"):
                    out_name += ".pdf"
                dest_path = self.output_dir / out_name

                # files with ranges
                ranges_map = self.options.get("page_ranges", {})
                files_with_ranges = [(f, ranges_map.get(str(f), "all")) for f in self.files]

                def progress_bridge(pct: float, msg: str):
                    if self.is_canceled():
                        return
                    self.overall_progress.emit(1, 1, pct * 100.0)
                    self.file_progress.emit(pct * 100.0, msg)

                res = pdf_service.merge_pdfs(files_with_ranges, dest_path, progress_cb=progress_bridge)
                success_count = 1

                undo_manager.record_operation(
                    op_type="pdf_merge",
                    affected_items=[str(f) for f in self.files],
                    details=f"Merged {len(self.files)} files into {dest_path.name}"
                )

                self.file_status.emit(0, "نجحت العملية", str(res), "")
            except Exception as e:
                fail_count = 1
                failed_files.append((self.files[0] if self.files else Path("merged"), str(e)))
                logger.error(f"Merge error: {e}", exc_info=True)
                self.file_status.emit(0, "فشلت العملية", "", str(e))

            self.finished_all.emit(success_count, fail_count, skipped_count, failed_files)
            return

        # -------------------------------------------------------------
        # SPECIAL CASE: IMAGES TO PDF (combines multiple images into one PDF)
        # -------------------------------------------------------------
        if self.tool_id == "images_to_pdf":
            try:
                if self.is_canceled():
                    self.operation_canceled.emit()
                    return

                out_name = self.options.get("output_filename", "images_album.pdf")
                if not out_name.lower().endswith(".pdf"):
                    out_name += ".pdf"
                dest_path = self.output_dir / out_name

                def progress_bridge(pct: float, msg: str):
                    if self.is_canceled():
                        return
                    self.overall_progress.emit(1, 1, pct * 100.0)
                    self.file_progress.emit(pct * 100.0, msg)

                page_size = self.options.get("page_size", "a4")
                fit_mode = self.options.get("fit_mode", "fit")

                res = pdf_service.images_to_pdf(
                    self.files,
                    dest_path,
                    page_size=page_size,
                    fit_mode=fit_mode,
                    progress_cb=progress_bridge
                )
                success_count = 1

                undo_manager.record_operation(
                    op_type="images_to_pdf",
                    affected_items=[str(f) for f in self.files],
                    details=f"Combined {len(self.files)} images into {dest_path.name}"
                )

                self.file_status.emit(0, "نجحت العملية", str(res), "")
            except Exception as e:
                fail_count = 1
                failed_files.append((self.files[0] if self.files else Path("images"), str(e)))
                logger.error(f"Images to PDF error: {e}", exc_info=True)
                self.file_status.emit(0, "فشلت العملية", "", str(e))

            self.finished_all.emit(success_count, fail_count, skipped_count, failed_files)
            return

        # -------------------------------------------------------------
        # GENERAL BATCH OR SINGLE-FILE OPERATIONS
        # -------------------------------------------------------------
        for idx, src_file in enumerate(self.files):
            if self.is_canceled():
                logger.info("PDFWorker cancellation detected.")
                self.operation_canceled.emit()
                return

            # Compute Speed & ETA
            elapsed = max(0.1, time.time() - self._start_time)
            file_sz = src_file.stat().st_size if src_file.exists() else 0
            total_bytes_processed += file_sz
            speed_mb = (total_bytes_processed / (1024.0 * 1024.0)) / elapsed

            remaining_files = total_files - idx
            eta_sec = int(remaining_files * (elapsed / max(1, idx))) if idx > 0 else 0
            eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}"

            self.stats_updated.emit(speed_mb, eta_str)

            overall_pct = (idx / float(total_files)) * 100.0
            self.overall_progress.emit(idx + 1, total_files, overall_pct)

            def make_file_cb(row_idx):
                def cb(pct: float, msg: str):
                    if self.is_canceled():
                        return
                    self.file_progress.emit(pct * 100.0, msg)
                return cb

            cb = make_file_cb(idx)

            try:
                out_path = self._process_single_file(src_file, cb)
                success_count += 1
                self.file_status.emit(idx, "نجحت العملية", str(out_path), "")

                undo_manager.record_operation(
                    op_type=f"pdf_{self.tool_id}",
                    affected_items=[str(src_file)],
                    details=f"Processed {src_file.name} with {self.tool_id}"
                )
            except Exception as e:
                fail_count += 1
                failed_files.append((src_file, str(e)))
                logger.error(f"Error processing {src_file.name} with {self.tool_id}: {e}", exc_info=True)
                self.file_status.emit(idx, "فشلت العملية", "", str(e))

        self.overall_progress.emit(total_files, total_files, 100.0)
        self.finished_all.emit(success_count, fail_count, skipped_count, failed_files)

    def _process_single_file(self, src: Path, cb) -> Path:
        """Dispatches single file processing according to tool_id."""
        tid = self.tool_id
        opts = self.options

        # 1. SPLIT
        if tid == "split":
            mode = opts.get("split_mode", "pages")
            chunk = opts.get("chunk_size", 10)
            ranges = opts.get("custom_ranges", "")
            split_after = opts.get("split_after", "")
            out_files = pdf_service.split_pdf(
                src, self.output_dir, split_mode=mode, chunk_size=chunk,
                custom_ranges=ranges, split_after=split_after, progress_cb=cb
            )
            return out_files[0] if out_files else self.output_dir

        # 2. EXTRACT PAGES
        elif tid == "extract_pages":
            pages_str = opts.get("pages_str", "1")
            dest = create_safe_output_path(src, self.output_dir, suffix="_extracted")
            return pdf_service.extract_pages(src, dest, pages_str=pages_str, progress_cb=cb)

        # 3. DELETE PAGES
        elif tid == "delete_pages":
            pages_str = opts.get("pages_str", "")
            mode = opts.get("delete_mode", "custom")
            dest = create_safe_output_path(src, self.output_dir, suffix="_trimmed")
            return pdf_service.delete_pages(src, dest, pages_str=pages_str, mode=mode, progress_cb=cb)

        # 4. REORDER PAGES
        elif tid == "reorder":
            order = opts.get("page_order", [])
            dest = create_safe_output_path(src, self.output_dir, suffix="_reordered")
            return pdf_service.reorder_pages(src, dest, new_order=order, progress_cb=cb)

        # 5. ROTATE
        elif tid == "rotate":
            angle = opts.get("angle", 90)
            pages = opts.get("pages_str", "all")
            dest = create_safe_output_path(src, self.output_dir, suffix=f"_rot{angle}")
            return pdf_service.rotate_pages(src, dest, angle=angle, pages_str=pages, progress_cb=cb)

        # 6. CROP & HALVE
        elif tid in ("crop", "halve_pages", "add_margins"):
            mode = opts.get("crop_mode", "margins")
            if tid == "halve_pages":
                mode = opts.get("halve_dir", "halve_vertical")
            margins = opts.get("margins", (0, 0, 0, 0))
            pages = opts.get("pages_str", "all")
            dest = create_safe_output_path(src, self.output_dir, suffix="_cropped")
            return pdf_service.crop_pages(src, dest, mode=mode, margins=margins, pages_str=pages, progress_cb=cb)

        # 7. COMPRESS
        elif tid == "compress":
            preset = opts.get("preset", "balanced")
            dest = create_safe_output_path(src, self.output_dir, suffix="_compressed")
            pdf_service.compress_pdf(src, dest, preset=preset, progress_cb=cb)
            return dest

        # 8. COMPRESS TARGET SIZE
        elif tid == "compress_target":
            target_mb = opts.get("target_mb", 2.0)
            target_bytes = int(target_mb * 1024 * 1024)
            dest = create_safe_output_path(src, self.output_dir, suffix=f"_{target_mb}MB")
            pdf_service.compress_target_size(src, dest, target_bytes=target_bytes, progress_cb=cb)
            return dest

        # 9. PDF TO IMAGES
        elif tid == "pdf_to_images":
            fmt = opts.get("img_format", "png")
            dpi = opts.get("dpi", 150)
            pages = opts.get("pages_str", "all")
            sub_dir = self.output_dir / f"{src.stem}_images"
            out_imgs = pdf_service.pdf_to_images(src, sub_dir, img_format=fmt, dpi=dpi, pages_str=pages, progress_cb=cb)
            return out_imgs[0] if out_imgs else sub_dir

        # 10. WATERMARK
        elif tid == "watermark":
            text = opts.get("text", "")
            img_p = opts.get("image_path")
            fsize = opts.get("font_size", 42)
            opacity = opts.get("opacity", 0.35)
            angle = opts.get("angle", 45.0)
            dest = create_safe_output_path(src, self.output_dir, suffix="_watermarked")
            return pdf_service.add_watermark(
                src, dest, text=text, font_size=fsize, opacity=opacity, angle=angle,
                image_path=img_p, progress_cb=cb
            )

        # 11. PAGE NUMBERS
        elif tid == "page_numbers":
            pos = opts.get("position", "bottom_center")
            pattern = opts.get("pattern", "صفحة {page} من {total}")
            start_num = opts.get("start_num", 1)
            prefix = opts.get("prefix", "")
            dest = create_safe_output_path(src, self.output_dir, suffix="_numbered")
            return pdf_service.add_page_numbers(
                src, dest, position=pos, pattern=pattern, start_num=start_num,
                prefix=prefix, progress_cb=cb
            )

        # 12. PROTECT
        elif tid == "protect":
            user_pwd = opts.get("user_password", "")
            owner_pwd = opts.get("owner_password", "")
            allow_print = opts.get("allow_print", True)
            allow_copy = opts.get("allow_copy", True)
            dest = create_safe_output_path(src, self.output_dir, suffix="_protected")
            return pdf_service.protect_pdf(
                src, dest, user_password=user_pwd, owner_password=owner_pwd,
                allow_print=allow_print, allow_copy=allow_copy, progress_cb=cb
            )

        # 13. UNLOCK
        elif tid == "unlock":
            pwd = opts.get("password", "")
            dest = create_safe_output_path(src, self.output_dir, suffix="_unlocked")
            return pdf_service.unlock_pdf(src, dest, password=pwd, progress_cb=cb)

        # 14. REDACT
        elif tid == "redact":
            terms = opts.get("search_terms", [])
            case_s = opts.get("case_sensitive", False)
            dest = create_safe_output_path(src, self.output_dir, suffix="_redacted")
            res_p, _ = pdf_service.redact_pdf(src, dest, search_terms=terms, case_sensitive=case_s, progress_cb=cb)
            return res_p

        # 15. METADATA
        elif tid == "metadata":
            strip = opts.get("strip_all", True)
            new_m = opts.get("new_metadata")
            dest = create_safe_output_path(src, self.output_dir, suffix="_cleaned")
            return pdf_service.clean_metadata(src, dest, strip_all=strip, new_meta=new_m, progress_cb=cb)

        # 16. EXTRACT TEXT
        elif tid == "extract_text":
            pages = opts.get("pages_str", "all")
            dest = create_safe_output_path(src, self.output_dir, suffix="_text", ext=".txt")
            pdf_service.extract_text(src, dest, pages_str=pages, progress_cb=cb)
            return dest

        # 17. EXTRACT IMAGES
        elif tid == "extract_images":
            pages = opts.get("pages_str", "all")
            sub_dir = self.output_dir / f"{src.stem}_extracted_images"
            imgs = pdf_service.extract_images(src, sub_dir, pages_str=pages, progress_cb=cb)
            return imgs[0] if imgs else sub_dir

        # 18. GRAYSCALE & FLATTEN
        elif tid in ("grayscale", "flatten"):
            gray = (tid == "grayscale")
            dest = create_safe_output_path(src, self.output_dir, suffix=f"_{tid}")
            pdf_service.compress_pdf(src, dest, preset="light", grayscale=gray, progress_cb=cb)
            return dest

        # 19. DOCTOR & REPAIR
        elif tid == "pdf_doctor":
            dest = create_safe_output_path(src, self.output_dir, suffix="_repaired")
            pdf_service.inspect_and_repair(src, repair_output_path=dest, progress_cb=cb)
            return dest

        # Fallback
        dest = create_safe_output_path(src, self.output_dir, suffix="_processed")
        shutil.copy2(src, dest)
        return dest
