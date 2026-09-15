# -*- coding: utf-8 -*-
"""
SINAX Organize Worker
Executes smart file moving, copying, and directory creation
in a background QThread to ensure fluid, non-blocking UI interactions.
"""

from PySide6.QtCore import Signal
from app.workers.base_worker import BaseWorker
from app.services.organize_service import OrganizeService, OrganizePlan
from app.core.logger import get_logger

logger = get_logger("organize_worker")


class OrganizeWorker(BaseWorker):
    organize_started = Signal(int)  # total count
    progress_updated = Signal(int, int, str, int)  # current, total, filename, percentage
    organize_finished = Signal(int, int, list, object)  # success_count, fail_count, errors, record
    organize_failed = Signal(str)  # error_message

    def __init__(self, plan: OrganizePlan, parent=None):
        super().__init__(parent)
        self.plan = plan

    def run(self):
        total = len(self.plan.selected_items)
        self.organize_started.emit(total)

        def progress_cb(current_idx: int, total_count: int, filename: str):
            if self.is_canceled():
                raise InterruptedError("تم إلغاء عملية التنظيم بواسطة المستخدم.")
            pct = int((current_idx / max(total_count, 1)) * 100)
            self.progress_updated.emit(current_idx, total_count, filename, pct)

        try:
            success, fail, errors, record = OrganizeService.execute_plan(
                self.plan,
                progress_callback=progress_cb
            )
            self.organize_finished.emit(success, fail, errors, record)
            logger.info(f"OrganizeWorker completed: {success} succeeded, {fail} failed")

        except InterruptedError as ie:
            logger.warning(f"Organize canceled: {ie}")
            self.operation_canceled.emit()

        except Exception as e:
            logger.error(f"Organize worker error: {e}")
            self.organize_failed.emit(str(e))
