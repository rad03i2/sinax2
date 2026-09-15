# -*- coding: utf-8 -*-
"""
SINAX Storage Worker
QThread executing directory storage and disk space analysis asynchronously.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import QThread, Signal

from app.services.storage_analysis_service import StorageAnalysisService, StorageReport
from app.core.logger import get_logger

logger = get_logger("storage_worker")


class StorageWorker(QThread):
    """Background worker for storage analytics."""

    progress_updated = Signal(int, int, str)  # file_count, total_dirs, current_name
    analysis_finished = Signal(object)        # StorageReport
    analysis_failed = Signal(str)

    def __init__(self, directory: Path, top_n: int = 50, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.top_n = top_n
        self._is_cancelled = False

    def cancel(self):
        """Signals worker to gracefully abort analysis."""
        self._is_cancelled = True

    def run(self):
        try:
            logger.info(f"Starting storage analysis for {self.directory}")
            report = StorageAnalysisService.analyze_directory(
                directory=self.directory,
                top_n=self.top_n,
                progress_callback=self._on_progress,
                is_cancelled=lambda: self._is_cancelled
            )
            if self._is_cancelled:
                logger.info("StorageWorker cancelled.")
            self.analysis_finished.emit(report)
        except Exception as e:
            logger.error(f"StorageWorker failed: {e}", exc_info=True)
            self.analysis_failed.emit(str(e))

    def _on_progress(self, scanned_files: int, total_dirs: int, current_name: str):
        if not self._is_cancelled:
            self.progress_updated.emit(scanned_files, total_dirs, current_name)
