# -*- coding: utf-8 -*-
"""
Security Badge Widget for SINAX Privacy & Security Center.
Renders high-contrast Fluent badges (e.g. 100% Local, Requires Admin, Online).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from app.ui.icons import get_icon


class ToolBadgeWidget(QFrame):
    """Clean pill badge with icon and label."""

    def __init__(self, text: str, bg_color: str, fg_color: str, icon_name: str = "", parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {fg_color}44;
                border-radius: 6px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        if icon_name:
            icon_lbl = QLabel(self)
            pix = get_icon(icon_name, color_hex=fg_color, size=12).pixmap(12, 12)
            icon_lbl.setPixmap(pix)
            layout.addWidget(icon_lbl)

        txt_lbl = QLabel(text, self)
        txt_lbl.setStyleSheet(f"color: {fg_color}; font-size: 11px; font-weight: bold;")
        layout.addWidget(txt_lbl)

    @classmethod
    def local_100(cls, parent=None) -> "ToolBadgeWidget":
        return cls("100% محلي", "#132E22", "#34D399", "shield", parent)

    @classmethod
    def online(cls, parent=None) -> "ToolBadgeWidget":
        return cls("أونلاين (Online)", "#1E3A5F", "#38BDF8", "globe", parent)

    @classmethod
    def requires_admin(cls, parent=None) -> "ToolBadgeWidget":
        return cls("يتطلب مسؤول (Admin)", "#451A03", "#FBBF24", "security", parent)

    @classmethod
    def modifies_files(cls, parent=None) -> "ToolBadgeWidget":
        return cls("يعدل ملفات", "#3B1C38", "#F472B6", "rename", parent)

