# -*- coding: utf-8 -*-
"""
SINAX Universal Quick Batch Lab Engine
High-throughput, asynchronous batch processor running operations over thousands of files
or data records via QThreadPool, reporting progress, rate, ETA, and supporting clean cancellation.
"""

import time
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from app.services.quick_tools.models import BatchTaskItem, BatchTaskResult


class BatchWorkerSignals(QObject):
    """Signals for communicating batch execution events back to UI."""
    progress = Signal(int, int, str, float, str)  # (current, total, item_name, items_per_sec, eta_str)
    item_completed = Signal(int, str, bool, str)  # (index, item_path, is_success, result_summary)
    finished = Signal(object)                     # BatchTaskResult
    cancelled = Signal()
    error = Signal(str)


class BatchWorker(QRunnable):
    """Executes a list of items through a tool processor function."""

    def __init__(
        self,
        items: List[str],
        processor_fn: Callable[[str, Callable[[], bool]], Any],
        task_label: str = "Processing Batch"
    ):
        super().__init__()
        self.items = items
        self.processor_fn = processor_fn
        self.task_label = task_label
        self.signals = BatchWorkerSignals()
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total = len(self.items)
        if total == 0:
            res = BatchTaskResult(0, 0, 0, 0, 0.0, [])
            self.signals.finished.emit(res)
            return

        start_time = time.time()
        completed_items: List[BatchTaskItem] = []
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for idx, item in enumerate(self.items):
            if self._is_cancelled:
                self.signals.cancelled.emit()
                return

            item_start = time.time()
            task_item = BatchTaskItem(index=idx + 1, source_path=item)

            try:
                result = self.processor_fn(item, lambda: self._is_cancelled)
                task_item.status = "completed"
                task_item.result = result
                success_count += 1
                is_success = True
                summary = str(result)[:60]
            except InterruptedError:
                self.signals.cancelled.emit()
                return
            except Exception as e:
                task_item.status = "failed"
                task_item.error_message = str(e)
                failed_count += 1
                is_success = False
                summary = str(e)[:60]

            task_item.duration_ms = (time.time() - item_start) * 1000.0
            completed_items.append(task_item)

            # Metrics
            elapsed = time.time() - start_time
            rate = (idx + 1) / max(0.001, elapsed)
            remaining_items = total - (idx + 1)
            eta_sec = remaining_items / max(0.001, rate)
            eta_str = f"{int(eta_sec // 60):02d}:{int(eta_sec % 60):02d}"

            self.signals.item_completed.emit(idx + 1, item, is_success, summary)
            self.signals.progress.emit(idx + 1, total, item, round(rate, 1), eta_str)

        total_duration = time.time() - start_time
        final_result = BatchTaskResult(
            total_items=total,
            successful_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            total_duration_sec=total_duration,
            items=completed_items,
        )
        self.signals.finished.emit(final_result)


class BatchRunner:
    """Manager for starting and controlling asynchronous batch operations."""

    @staticmethod
    def run_batch(
        items: List[str],
        processor_fn: Callable[[str, Callable[[], bool]], Any],
        signals: Optional[BatchWorkerSignals] = None
    ) -> BatchWorker:
        """Starts batch operation on QThreadPool."""
        worker = BatchWorker(items, processor_fn)
        if signals:
            worker.signals = signals
        QThreadPool.globalInstance().start(worker)
        return worker
