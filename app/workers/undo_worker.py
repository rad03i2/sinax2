# -*- coding: utf-8 -*-
"""
SINAX UndoWorker
Executes rollback operations in the background.
"""

from PySide6.QtCore import Signal
from app.workers.base_worker import BaseWorker
from app.services.rename_service import RenameService
from app.core.undo_manager import HistoryRecord
from app.core.logger import get_logger

logger = get_logger("undo_worker")

class UndoWorker(BaseWorker):
    progress = Signal(int, int, str, int, int)
    finished = Signal(int, int, list)

    def __init__(self, record: HistoryRecord, parent=None):
        super().__init__(parent)
        self.record = record

    def run(self):
        logger.info(f"Starting UndoWorker for record {self.record.record_id}")
        
        def progress_cb(cur, tot, fname, succ, fail):
            self.progress.emit(cur, tot, fname, succ, fail)

        success, failed, errors = RenameService.undo_operation(
            self.record,
            progress_callback=progress_cb
        )
        self.finished.emit(success, failed, errors)
