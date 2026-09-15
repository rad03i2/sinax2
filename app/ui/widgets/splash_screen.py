# -*- coding: utf-8 -*-
"""
SINAX Professional Fast Splash Screen
Features:
- Frameless modern window with glowing tech border
- Real-time animated initialization checklist
- Auto-progress without blocking main thread
"""

from typing import List, Optional
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSplashScreen,
    QVBoxLayout,
    QWidget,
)
from app.core.constants import APP_NAME, APP_NAME_AR, APP_VERSION
from app.ui.design_system.tokens import ThemeTokens
from app.ui.icons import create_sinax_logo


class SinaxSplashScreen(QSplashScreen):
    """
    Modern high-DPI splash screen displaying sequential loading status ticks
    before seamlessly handing over to MainWindow.
    """

    def __init__(self):
        pixmap = QPixmap(480, 290)
        pixmap.fill(Qt.transparent)
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setLayoutDirection(Qt.RightToLeft)
        self._step_index = 0
        self._steps = [
            "تحميل النواة وقاعدة البيانات",
            "تحميل الإعدادات والمظهر الداكن",
            "تجهيز الواجهة وقمرة القيادة",
        ]
        self._render_splash()

    def advance_step(self, step_name: Optional[str] = None):
        """Advances to the next checklist milestone and redraws."""
        self._step_index += 1
        self._render_splash()
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.processEvents()

    def _render_splash(self):
        pixmap = QPixmap(480, 290)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background rounded card
        painter.setBrush(QColor("#161B22"))
        painter.setPen(QColor("#30363D"))
        painter.drawRoundedRect(2, 2, 476, 286, 12, 12)

        # Top Accent line
        painter.setPen(QColor("#38BDF8"))
        painter.drawLine(30, 2, 450, 2)

        # Draw Logo
        logo_pix = create_sinax_logo(54).pixmap(54, 54)
        painter.drawPixmap(213, 24, logo_pix)

        # Title
        painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
        painter.setPen(QColor("#F0F6FC"))
        painter.drawText(0, 92, 480, 26, Qt.AlignCenter, f"{APP_NAME}  •  {APP_NAME_AR}")

        # Subtitle
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#8B949E"))
        painter.drawText(0, 118, 480, 20, Qt.AlignCenter, "نظام إدارة الحاسوب والملفات الذكي")

        # Checklist container
        y_start = 152
        painter.setFont(QFont("Segoe UI", 10))

        for idx, step_text in enumerate(self._steps):
            y_pos = y_start + (idx * 26)
            if idx < self._step_index:
                # Completed
                painter.setPen(QColor("#34D399"))
                painter.drawText(120, y_pos, 220, 20, Qt.AlignRight | Qt.AlignVCenter, f"✓ {step_text}")
            elif idx == self._step_index:
                # In progress
                painter.setPen(QColor("#38BDF8"))
                painter.drawText(120, y_pos, 220, 20, Qt.AlignRight | Qt.AlignVCenter, f"• {step_text}...")
            else:
                # Pending
                painter.setPen(QColor("#484F58"))
                painter.drawText(120, y_pos, 220, 20, Qt.AlignRight | Qt.AlignVCenter, f"○ {step_text}")

        # Footer version
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#57606A"))
        painter.drawText(0, 258, 480, 16, Qt.AlignCenter, f"v{APP_VERSION} • محمي بنظام التحميل الذكي")

        painter.end()
        self.setPixmap(pixmap)
