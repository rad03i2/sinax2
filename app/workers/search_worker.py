# -*- coding: utf-8 -*-
"""
SINAX Search Worker
QThread executing multi-criteria file search asynchronously in background.
"""

from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import QThread, Signal

from app.services.search_service import SearchService, SearchFilter, SearchResultItem
from app.core.logger import get_logger

logger = get_logger("search_worker")


class SearchWorker(QThread):
    """Background worker for multi-criteria search."""

    progress_updated = Signal(int, int, str)  # found_count, scanned_count, current_filename
    search_finished = Signal(list)            # List[SearchResultItem]
    search_failed = Signal(str)

    def __init__(self, directory: Path, search_filter: SearchFilter, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.search_filter = search_filter
        self._is_cancelled = False

    def cancel(self):
        """Signals worker to gracefully abort search."""
        self._is_cancelled = True

    def run(self):
        try:
            logger.info(f"Starting search in {self.directory} with query='{self.search_filter.query}'")
            results = SearchService.search(
                directory=self.directory,
                search_filter=self.search_filter,
                progress_callback=self._on_progress,
                is_cancelled=lambda: self._is_cancelled
            )
            if self._is_cancelled:
                logger.info("SearchWorker cancelled.")
                self.search_finished.emit(results)
            else:
                logger.info(f"Search completed: found {len(results)} matches.")
                self.search_finished.emit(results)
        except Exception as e:
            logger.error(f"SearchWorker failed: {e}", exc_info=True)
            self.search_failed.emit(str(e))

    def _on_progress(self, found: int, scanned: int, current_file: str):
        if not self._is_cancelled:
            self.progress_updated.emit(found, scanned, current_file)
