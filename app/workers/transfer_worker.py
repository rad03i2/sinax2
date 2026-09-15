# -*- coding: utf-8 -*-
"""
SINAX Transfer Worker
QThread executing batch copy/move operations asynchronously in background with speed measurement.
"""

import time
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QThread, Signal

from app.services.transfer_service import TransferService, TransferPlan
from app.models.file_item import format_file_size
from app.core.logger import get_logger

logger = get_logger("transfer_worker")


class TransferWorker(QThread):
    """Background worker for batch safe copy/move execution."""

    progress_updated = Signal(int, int, str, float, str)  # current, total, filename, pct, speed_str
    transfer_finished = Signal(int, int, int)             # success, skipped, failed
    transfer_failed = Signal(str)

    def __init__(self, plan: TransferPlan, parent=None):
        super().__init__(parent)
        self.plan = plan
        self._is_cancelled = False
        self._start_time = 0.0
        self._transferred_bytes = 0

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self._start_time = time.time()
            self._transferred_bytes = 0

            def on_progress(curr: int, tot: int, fname: str, pct: float):
                if self._is_cancelled:
                    return

                elapsed = time.time() - self._start_time
                if elapsed > 0 and curr < len(self.plan.items):
                    # compute approximate speed
                    chunk_sz = self.plan.items[curr - 1].size_bytes if curr > 0 else 0
                    self._transferred_bytes += chunk_sz
                    speed_bps = self._transferred_bytes / elapsed
                    speed_str = f"{format_file_size(int(speed_bps))}/ث"
                else:
                    speed_str = "--"

                self.progress_updated.emit(curr, tot, fname, pct, speed_str)

            success, skipped, failed = TransferService.execute_plan(
                plan=self.plan,
                progress_callback=on_progress,
                is_cancelled=lambda: self._is_cancelled
            )

            if self._is_cancelled:
                logger.info("TransferWorker cancelled.")
            self.transfer_finished.emit(success, skipped, failed)

        except Exception as e:
            logger.error(f"TransferWorker failed: {e}", exc_info=True)
            self.transfer_failed.emit(str(e))
