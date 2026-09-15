# -*- coding: utf-8 -*-
"""
SINAX Merge Worker
Executes file merging, document concatenation, and archiving operations
in a background QThread to ensure the UI remains fully responsive.
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtCore import Signal

from app.workers.base_worker import BaseWorker
from app.services.merge_service import MergeService
from app.core.logger import get_logger

logger = get_logger("merge_worker")


class MergeWorker(BaseWorker):
    merge_started = Signal(int)  # total files count
    progress_updated = Signal(int, int, str, int)  # current, total, filename, percentage
    merge_finished = Signal(str, float)  # output_path_str, elapsed_seconds
    merge_failed = Signal(str)  # error_message

    def __init__(
        self,
        mode: str,
        input_paths: List[Path],
        output_path: Path,
        extra_params: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.mode = mode
        self.input_paths = [Path(p) for p in input_paths]
        self.output_path = Path(output_path)
        self.extra_params = extra_params or {}

    def run(self):
        total = len(self.input_paths)
        self.merge_started.emit(total)
        start_time = time.time()

        def progress_cb(current_idx: int, total_count: int, filename: str):
            if self.is_canceled():
                raise InterruptedError("تم إلغاء عملية الدمج بواسطة المستخدم.")
            pct = int((current_idx / max(total_count, 1)) * 100)
            self.progress_updated.emit(current_idx, total_count, filename, pct)

        try:
            if not self.input_paths:
                raise ValueError("لا توجد ملفات محددة للدمج.")

            if self.mode == "pdf":
                MergeService.merge_pdfs(
                    self.input_paths,
                    self.output_path,
                    progress_callback=progress_cb
                )

            elif self.mode == "docx":
                add_breaks = self.extra_params.get("docx_page_breaks", True)
                MergeService.merge_docx(
                    self.input_paths,
                    self.output_path,
                    add_page_breaks=add_breaks,
                    progress_callback=progress_cb
                )

            elif self.mode == "excel":
                excel_mode = self.extra_params.get("excel_mode", "sheets")
                MergeService.merge_excel_sheets(
                    self.input_paths,
                    self.output_path,
                    mode=excel_mode,
                    progress_callback=progress_cb
                )

            elif self.mode == "images_pdf":
                MergeService.images_to_pdf(
                    self.input_paths,
                    self.output_path,
                    progress_callback=progress_cb
                )

            elif self.mode == "images_stitch":
                direction = self.extra_params.get("stitch_direction", "vertical")
                MergeService.stitch_images(
                    self.input_paths,
                    self.output_path,
                    direction=direction,
                    progress_callback=progress_cb
                )

            elif self.mode in ["zip", "videos_zip"]:
                MergeService.create_zip_archive(
                    self.input_paths,
                    self.output_path,
                    progress_callback=progress_cb
                )

            else:
                # Default fallback is ZIP
                MergeService.create_zip_archive(
                    self.input_paths,
                    self.output_path,
                    progress_callback=progress_cb
                )

            elapsed = round(time.time() - start_time, 2)
            self.merge_finished.emit(str(self.output_path), elapsed)
            logger.info(f"Merge operation [{self.mode}] finished successfully in {elapsed}s")

        except InterruptedError as ie:
            logger.warning(f"Merge canceled: {ie}")
            self.operation_canceled.emit()

        except Exception as e:
            logger.error(f"Merge failed: {e}")
            self.merge_failed.emit(str(e))
