# -*- coding: utf-8 -*-
"""
SINAX Modern Cards & Visual Primitives
Eliminates ugly tables, harsh bordered lines, and cluttered fields in favor of
clean, spacious, Windows 11 Fluent-inspired cards and badges.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from app.ui.design_system.tokens import ThemeTokens
from app.ui.icons import get_icon


class ModernCard(QFrame):
    """
    Standard clean card container with subtle 1px border, soft 10px radius,
    and comfortable padding. Replaces cluttered bordered frames.
    """

    def __init__(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        parent=None,
        elevated: bool = False,
        hoverable: bool = False,
    ):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        bg = ThemeTokens.BG_ELEVATED if elevated else ThemeTokens.BG_SURFACE
        hover_style = f"QFrame:hover {{ border-color: {ThemeTokens.BORDER_HOVER}; }}" if hoverable else ""
        self.setStyleSheet(f"""
            ModernCard, QFrame#{self.objectName()} {{
                background-color: {bg};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_LG};
            }}
            {hover_style}
        """)

        self.title_lbl: Optional[QLabel] = None
        self.subtitle_lbl: Optional[QLabel] = None

        if title or subtitle:
            layout = self._ensure_layout()
            if title:
                self.title_lbl = QLabel(title)
                self.title_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
                self.title_lbl.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY}; background: transparent;")
                layout.addWidget(self.title_lbl)
            if subtitle:
                self.subtitle_lbl = QLabel(subtitle)
                self.subtitle_lbl.setStyleSheet(f"font-size: 11px; color: {ThemeTokens.TEXT_MUTED}; background: transparent; margin-bottom: 4px;")
                layout.addWidget(self.subtitle_lbl)

    def _ensure_layout(self) -> QVBoxLayout:
        curr = self.layout()
        if curr is None:
            l = QVBoxLayout(self)
            l.setContentsMargins(18, 16, 18, 16)
            l.setSpacing(10)
            return l
        return curr  # type: ignore

    def add_widget(self, widget: QWidget):
        self._ensure_layout().addWidget(widget)

    def add_layout(self, layout):
        self._ensure_layout().addLayout(layout)


class MetricCard(QFrame):
    """
    Prominent metric card featuring:
    - Clean category title & icon
    - Crisp, bold primary value
    - Descriptive secondary subtitle or status
    - Optional top accent highlight bar
    """

    def __init__(
        self,
        title: str,
        value: str = "—",
        subtitle: str = "",
        icon_name: str = "storage",
        accent_color: str = ThemeTokens.ACCENT_LIGHT,
        parent=None,
    ):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.accent_color = accent_color
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: {ThemeTokens.BG_SURFACE};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-top: 3px solid {accent_color};
                border-radius: {ThemeTokens.RADIUS_LG};
            }}
            MetricCard:hover {{
                background-color: {ThemeTokens.BG_SURFACE_HOVER};
                border-color: {ThemeTokens.BORDER_HOVER};
                border-top: 3px solid {accent_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Header: Icon + Title
        hdr_layout = QHBoxLayout()
        hdr_layout.setSpacing(8)

        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(get_icon(icon_name, accent_color, 16).pixmap(16, 16))
        hdr_layout.addWidget(self.icon_lbl)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"font-size: 12px; color: {ThemeTokens.TEXT_SECONDARY}; font-weight: 500;")
        hdr_layout.addWidget(self.title_lbl)
        hdr_layout.addStretch()

        layout.addLayout(hdr_layout)

        # Value
        self.value_lbl = QLabel(value)
        self.value_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.value_lbl.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY};")
        self.val_label = self.value_lbl
        layout.addWidget(self.value_lbl)

        # Subtitle
        self.subtitle_lbl = QLabel(subtitle)
        self.subtitle_lbl.setStyleSheet(f"font-size: 11px; color: {ThemeTokens.TEXT_MUTED};")
        self.subtitle_lbl.setVisible(bool(subtitle))
        layout.addWidget(self.subtitle_lbl)

    def set_value(self, value: str, subtitle: Optional[str] = None):
        self.value_lbl.setText(value)
        if subtitle is not None:
            self.subtitle_lbl.setText(subtitle)
            self.subtitle_lbl.setVisible(bool(subtitle))


class InfoRow(QWidget):
    """
    Clean, borderless specification key-value row.
    Replaces ugly nested tables and harsh separator lines with spacious Fluent typography.
    """

    def __init__(self, key: str, value: str = "—", icon_name: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        if icon_name:
            ic = QLabel()
            ic.setPixmap(get_icon(icon_name, ThemeTokens.ACCENT_LIGHT, 14).pixmap(14, 14))
            layout.addWidget(ic)

        self.key_lbl = QLabel(key)
        self.key_lbl.setStyleSheet(f"font-size: 12px; color: {ThemeTokens.TEXT_SECONDARY};")
        self.key_lbl.setMinimumWidth(120)
        layout.addWidget(self.key_lbl)

        layout.addStretch()

        self.val_lbl = QLabel(value)
        self.val_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.val_lbl.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY};")
        self.val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.val_lbl)

    def set_value(self, value: str):
        self.val_lbl.setText(value)

    def setText(self, text: str):
        self.set_value(text)

    def text(self) -> str:
        return self.val_lbl.text()


class StatusBadge(QLabel):
    """
    Compact modern pill badge with status indicator color,
    soft semi-transparent background, and gentle border.
    """

    def __init__(self, text: str, status: str = "success", parent=None):
        super().__init__(text, parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setAlignment(Qt.AlignCenter)
        self.set_status(status, text)

    def set_status(self, status: str, text: Optional[str] = None):
        if text:
            self.setText(text)

        colors = {
            "success": (ThemeTokens.SUCCESS, ThemeTokens.SUCCESS_BG, ThemeTokens.SUCCESS_BORDER),
            "warning": (ThemeTokens.WARNING, ThemeTokens.WARNING_BG, ThemeTokens.WARNING_BORDER),
            "danger": (ThemeTokens.DANGER, ThemeTokens.DANGER_BG, ThemeTokens.DANGER_BORDER),
            "info": (ThemeTokens.INFO, ThemeTokens.INFO_BG, ThemeTokens.INFO_BORDER),
        }
        text_color, bg_color, border_color = colors.get(status, colors["info"])

        self.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {ThemeTokens.RADIUS_PILL};
                padding: 3px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)


class ActionTile(ModernCard):
    """
    Spacious interactive action tile with icon, title, description,
    and action launcher button.
    """

    clicked = Signal()

    def __init__(
        self,
        title: str,
        description: str,
        icon_name: str,
        button_text: str = "فتح الأداة",
        accent_color: str = ThemeTokens.ACCENT_LIGHT,
        parent=None,
    ):
        super().__init__(parent, elevated=False, hoverable=True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        # Icon box
        icon_box = QFrame()
        icon_box.setFixedSize(46, 46)
        icon_box.setStyleSheet(f"""
            QFrame {{
                background-color: {ThemeTokens.BG_ELEVATED};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_MD};
            }}
        """)
        ib_layout = QHBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setAlignment(Qt.AlignCenter)
        ic.setPixmap(get_icon(icon_name, accent_color, 24).pixmap(24, 24))
        ib_layout.addWidget(ic)
        layout.addWidget(icon_box)

        # Text column
        col = QVBoxLayout()
        col.setSpacing(4)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {ThemeTokens.TEXT_PRIMARY};")
        col.addWidget(t_lbl)

        d_lbl = QLabel(description)
        d_lbl.setStyleSheet(f"font-size: 11px; color: {ThemeTokens.TEXT_SECONDARY};")
        d_lbl.setWordWrap(True)
        col.addWidget(d_lbl)
        layout.addLayout(col, 1)

        # Action Button
        btn = QPushButton(f"  {button_text}")
        btn.setFixedHeight(ThemeTokens.BUTTON_HEIGHT)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ThemeTokens.BG_ELEVATED};
                color: {ThemeTokens.TEXT_PRIMARY};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_MD};
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {ThemeTokens.ACCENT_PRIMARY};
                border-color: {ThemeTokens.ACCENT_PRIMARY};
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: {ThemeTokens.ACCENT_HOVER};
            }}
        """)
        btn.clicked.connect(self.clicked.emit)
        layout.addWidget(btn)
