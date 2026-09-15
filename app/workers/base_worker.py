# -*- coding: utf-8 -*-
"""
SINAX Base Worker
Base thread class providing cancellation and error signaling.
"""

from PySide6.QtCore import QThread, Signal

class BaseWorker(QThread):
    error_occurred = Signal(str)
    operation_canceled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_canceled = False

    def cancel(self):
        """Requests worker cancellation."""
        self._is_canceled = True

    def is_canceled(self) -> bool:
        return self._is_canceled
