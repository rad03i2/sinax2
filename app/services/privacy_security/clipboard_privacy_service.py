# -*- coding: utf-8 -*-
"""
Clipboard Privacy Service for SINAX Privacy & Security.
Cleans system clipboard, manages auto-clear timers for sensitive credentials,
and inspects clipboard types without logging or leaking private contents.
"""

import time
from typing import Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QClipboard, QGuiApplication


class ClipboardPrivacyService(QObject):
    """Manages clipboard sanitation and sensitive data timeouts."""

    clipboard_cleared = Signal()
    timer_ticked = Signal(int)  # Remaining seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._auto_clear_timer = QTimer(self)
        self._auto_clear_timer.setInterval(1000)
        self._auto_clear_timer.timeout.connect(self._on_tick)
        self._remaining_seconds = 0

    def clear_now(self) -> bool:
        """Immediately wipes all clipboard contents."""
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.clear(mode=QClipboard.Clipboard)
            self.stop_timer()
            self.clipboard_cleared.emit()
            return True
        return False

    def schedule_clear(self, seconds: int):
        """Schedules clipboard auto-clearing after the specified duration."""
        self._remaining_seconds = max(1, seconds)
        self._auto_clear_timer.start()
        self.timer_ticked.emit(self._remaining_seconds)

    def stop_timer(self):
        """Cancels any active auto-clear countdown."""
        self._auto_clear_timer.stop()
        self._remaining_seconds = 0

    def get_clipboard_summary(self) -> Dict[str, bool]:
        """
        Inspects the types present in the clipboard without exposing the content.
        """
        clipboard = QGuiApplication.clipboard()
        if not clipboard:
            return {"has_text": False, "has_image": False, "has_urls": False}

        mime_data = clipboard.mimeData()
        if not mime_data:
            return {"has_text": False, "has_image": False, "has_urls": False}

        return {
            "has_text": mime_data.hasText(),
            "has_image": mime_data.hasImage(),
            "has_urls": mime_data.hasUrls(),
        }

    def _on_tick(self):
        self._remaining_seconds -= 1
        self.timer_ticked.emit(self._remaining_seconds)
        if self._remaining_seconds <= 0:
            self.clear_now()
