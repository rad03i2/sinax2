# -*- coding: utf-8 -*-
"""
SINAX Center Async Loading Overlay Widget
A lightweight, non-blocking Fluent checklist overlay displayed while background services prepare.
"""

from typing import List, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.design_system.tokens import ThemeTokens
from app.ui.icons import get_icon


class CenterLoadingWidget(QFrame):
    """
    Non-blocking feedback card showing sequential checklist progress
    without locking the main thread or preventing navigation.
    """

    def __init__(self, center_name: str, parent=None):
        super().__init__(parent)
        self.center_name = center_name
        self.setLayoutDirection(Qt.RightToLeft)
        self.setObjectName("CenterLoadingCard")
        self.setStyleSheet(f"""
            QFrame#CenterLoadingCard {{
                background-color: {ThemeTokens.BG_SURFACE};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_LG};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header with spinner/clock icon
        hdr_layout = QHBoxLayout()
        hdr_layout.setSpacing(10)

        ic_lbl = QLabel()
        ic_lbl.setPixmap(get_icon("clock", ThemeTokens.ACCENT_LIGHT, 20).pixmap(20, 20))
        hdr_layout.addWidget(ic_lbl)

        title_lbl = QLabel(f"جاري تجهيز {center_name}...")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY};")
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch()
        layout.addLayout(hdr_layout)

        # Checklist rows
        self._steps = [
            ("load_ui", "تحميل الواجهة"),
            ("prep_tools", "تجهيز الأدوات"),
            ("ready", "جاهز للاستخدام"),
        ]
        self._step_labels = {}

        for step_id, step_text in self._steps:
            row = QHBoxLayout()
            row.setSpacing(8)

            check_icon = QLabel("○")
            check_icon.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED}; font-size: 13px; font-weight: bold;")
            row.addWidget(check_icon)

            lbl = QLabel(step_text)
            lbl.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; font-size: 12px;")
            row.addWidget(lbl)
            row.addStretch()

            layout.addLayout(row)
            self._step_labels[step_id] = (check_icon, lbl)

    def mark_step_done(self, step_id: str):
        """Marks a checklist step as completed with a green checkmark."""
        if step_id in self._step_labels:
            ic, lbl = self._step_labels[step_id]
            ic.setText("✓")
            ic.setStyleSheet(f"color: {ThemeTokens.SUCCESS}; font-size: 14px; font-weight: bold;")
            lbl.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY}; font-size: 12px; font-weight: 500;")

    def simulate_quick_ready(self, on_finish=None):
        """Sequential quick progression for smooth visual handoff."""
        QTimer.singleShot(60, lambda: self.mark_step_done("load_ui"))
        QTimer.singleShot(140, lambda: self.mark_step_done("prep_tools"))
        QTimer.singleShot(220, lambda: self.mark_step_done("ready"))
        if on_finish:
            QTimer.singleShot(260, on_finish)
