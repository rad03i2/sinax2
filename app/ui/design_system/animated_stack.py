# -*- coding: utf-8 -*-
"""
SINAX Animated Stacked Widget
Provides a subtle, snappy (~120ms) fade-in page transition when navigating between
sections, replacing harsh instantaneous page cuts while preserving responsiveness.
"""

from typing import Optional
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


class AnimatedStackedWidget(QStackedWidget):
    """
    Drop-in replacement for QStackedWidget with lightweight opacity transition.
    Cleans up graphics effects after animation to maintain crisp high-DPI rendering.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim: Optional[QPropertyAnimation] = None
        self._effect: Optional[QGraphicsOpacityEffect] = None
        self.transitions_enabled = True

    def setCurrentIndex(self, index: int, animate: bool = True):
        if not self.transitions_enabled or not animate or self.currentIndex() == index or not self.isVisible():
            super().setCurrentIndex(index)
            return

        next_widget = self.widget(index)
        if not next_widget:
            super().setCurrentIndex(index)
            return

        super().setCurrentIndex(index)

        # Apply snappy fade-in
        self._effect = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(120)
        self._anim.setStartValue(0.2)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            if next_widget:
                next_widget.setGraphicsEffect(None)
            self._effect = None
            self._anim = None

        self._anim.finished.connect(_cleanup)
        self._anim.start()
