# -*- coding: utf-8 -*-
"""
SINAX RenameWorker
Executes batch renaming asynchronously in a background QThread with real-time progress feedback.
"""

from typing import List, Optional
from PySide6.QtCore import Signal

from app.workers.base_worker import BaseWorker
from app.services.rename_service import RenameService, RenamePlan
from app.core.undo_manager import HistoryRecord
from app.core.logger import get_logger

logger = get_logger("rename_worker")

class RenameWorker(BaseWorker):
    progress = Signal(int, int, str, int, int)  # current, total, filename, success_count, fail_count
    finished = Signal(int, int, list, object)  # success_count, fail_count, errors, history_record

    def __init__(self, plan: RenamePlan, parent=None):
        super().__init__(parent)
        self.plan = plan

    def run(self):
        logger.info(f"Starting RenameWorker with {len(self.plan.rename_map)} files to rename.")

        def progress_cb(cur, tot, fname, succ, fail):
            self.progress.emit(cur, tot, fname, succ, fail)

        def cancel_cb():
            return self.is_canceled()

        success, fail, errors, record = RenameService.execute_plan(
            self.plan,
            progress_callback=progress_cb,
            cancel_check=cancel_cb
        )

        if self.is_canceled():
            self.operation_canceled.emit()
        else:
            self.finished.emit(success, fail, errors, record)
