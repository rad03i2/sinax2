# -*- coding: utf-8 -*-
"""
SINAX Duplicate Worker
QThread executing multi-pass duplicate scanning asynchronously in background.
"""

from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import QThread, Signal

from app.services.duplicate_service import DuplicateService, DuplicateGroup
from app.core.logger import get_logger

logger = get_logger("duplicate_worker")


class DuplicateWorker(QThread):
    """Background worker for duplicate and image similarity scanning."""

    progress_updated = Signal(int, int, str)  # pass_number (1,2,3), processed_count, current_action
    duplicates_found = Signal(list)           # List[DuplicateGroup]
    scan_failed = Signal(str)

    def __init__(
        self,
        directory: Path,
        recursive: bool = True,
        min_size_bytes: int = 1,
        category_filter: str = "all",
        use_perceptual_hash: bool = False,
        similarity_threshold: int = 5,
        parent=None
    ):
        super().__init__(parent)
        self.directory = directory
        self.recursive = recursive
        self.min_size_bytes = min_size_bytes
        self.category_filter = category_filter
        self.use_perceptual_hash = use_perceptual_hash
        self.similarity_threshold = similarity_threshold
        self._is_cancelled = False

    def cancel(self):
        """Gracefully signals worker to stop scanning."""
        self._is_cancelled = True

    def run(self):
        try:
            logger.info(f"Starting duplicate scan on {self.directory} (perceptual={self.use_perceptual_hash})")
            groups = DuplicateService.find_duplicates(
                directory=self.directory,
                recursive=self.recursive,
                min_size_bytes=self.min_size_bytes,
                category_filter=self.category_filter,
                use_perceptual_hash=self.use_perceptual_hash,
                similarity_threshold=self.similarity_threshold,
                progress_callback=self._on_progress,
                is_cancelled=lambda: self._is_cancelled
            )
            if self._is_cancelled:
                logger.info("DuplicateWorker cancelled.")
            self.duplicates_found.emit(groups)
        except Exception as e:
            logger.error(f"DuplicateWorker error: {e}", exc_info=True)
            self.scan_failed.emit(str(e))

    def _on_progress(self, pass_num: int, count: int, text: str):
        if not self._is_cancelled:
            self.progress_updated.emit(pass_num, count, text)
