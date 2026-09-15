# -*- coding: utf-8 -*-
"""
SINAX Conversion Card Widget
Card with two independent hoverable and clickable directional buttons.
RTL-aware layout, favorite pinning (⭐), and dynamic theme integration.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QCursor

from app.services.conversion.registry import ConversionCardDefinition, ConversionDefinition
from app.services.conversion.conversion_history import ConversionHistoryManager
from app.ui.pages.converter_components.dependency_dialog import DependencyDialog
from app.ui.icons import get_icon
from app.ui.themes.theme_manager import theme_manager


class DirectionButton(QFrame):
    """An independent hoverable and clickable button for a specific direction."""
    clicked = Signal(object)  # ConversionDefinition

    def __init__(self, direction: ConversionDefinition, color_hex: str, parent=None):
        super().__init__(parent)
        self.direction = direction
        self.color_hex = color_hex
        self.is_available = direction.is_available()
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self._init_ui()
        self.apply_theme(theme_manager.effective_theme)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Direction text e.g. "PDF → DOCX"
        self.lbl_dir = QLabel(f"{self.direction.source_ext.upper()}  →  {self.direction.target_ext.upper()}")
        layout.addWidget(self.lbl_dir)

        layout.addStretch(1)

        # Status Tag
        if not self.is_available:
            self.tag_lbl = QLabel("يحتاج مكوّناً إضافياً")
            layout.addWidget(self.tag_lbl)

            self.btn_dep = QPushButton("إعداد")
            self.btn_dep.setCursor(Qt.PointingHandCursor)
            self.btn_dep.clicked.connect(self._open_dep_dialog)
            layout.addWidget(self.btn_dep)
        else:
            self.arrow_lbl = QLabel("بدء")
            layout.addWidget(self.arrow_lbl)

    def apply_theme(self, theme_name: str):
        is_dark = (theme_name == "dark")
        text_color = "#F8FAFC" if is_dark else "#0F172A"
        self.lbl_dir.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_color};")

        if not self.is_available:
            tag_bg = "#332B00" if is_dark else "#FEF3C7"
            tag_fg = "#FFB900" if is_dark else "#D97706"
            tag_border = "#665200" if is_dark else "#FCD34D"
            self.tag_lbl.setStyleSheet(f"font-size: 10px; color: {tag_fg}; background: {tag_bg}; border: 1px solid {tag_border}; border-radius: 4px; padding: 2px 6px;")

            dep_bg = "#1F2E3D" if is_dark else "#EFF6FF"
            dep_fg = "#60CDFF" if is_dark else "#0284C7"
            dep_border = "#0078D4" if is_dark else "#93C5FD"
            self.btn_dep.setStyleSheet(f"font-size: 10px; color: {dep_fg}; background: {dep_bg}; border: 1px solid {dep_border}; border-radius: 4px; padding: 2px 6px;")
        else:
            start_color = self.color_hex if is_dark else "#0284C7"
            self.arrow_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {start_color};")

        self._set_idle_style(theme_name)

    def _set_idle_style(self, theme_name: Optional[str] = None):
        if theme_name is None:
            theme_name = theme_manager.effective_theme
        is_dark = (theme_name == "dark")
        bg = "#0F172A" if is_dark else "#F8FAFC"
        border = "#334155" if is_dark else "#E2E8F0"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)

    def enterEvent(self, event):
        is_dark = (theme_manager.effective_theme == "dark")
        bg_hover = "#1E293B" if is_dark else "#EFF6FF"
        hover_border = self.color_hex if is_dark else "#3B82F6"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_hover};
                border: 1px solid {hover_border};
                border-radius: 6px;
            }}
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_idle_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.direction)
        super().mousePressEvent(event)

    def _open_dep_dialog(self):
        tools = self.direction.get_missing_tools()
        if tools:
            dlg = DependencyDialog(tools[0], self)
            dlg.exec()


class ConversionCardWidget(QFrame):
    direction_selected = Signal(object, str)  # (ConversionDefinition, card_id)
    favorite_toggled = Signal(str, bool)

    def __init__(self, card_def: ConversionCardDefinition, parent=None):
        super().__init__(parent)
        self.card_def = card_def
        self.setMinimumWidth(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._init_ui()
        self.apply_theme(theme_manager.effective_theme)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # 1. Header: Icon + Title + Favorite Button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Icon
        self.icon_lbl = QLabel()
        icon = get_icon(self.card_def.icon_name, self.card_def.color_hex, 18)
        self.icon_lbl.setPixmap(icon.pixmap(18, 18))
        header_layout.addWidget(self.icon_lbl)

        # Title
        self.title_lbl = QLabel(self.card_def.title)
        header_layout.addWidget(self.title_lbl, 1)

        # Favorite Button (Star ⭐)
        self.btn_fav = QPushButton()
        self.btn_fav.setFixedSize(26, 26)
        self.btn_fav.setCursor(Qt.PointingHandCursor)
        self.btn_fav.clicked.connect(self._on_toggle_fav)
        self._update_fav_icon()
        header_layout.addWidget(self.btn_fav)

        layout.addLayout(header_layout)

        # 2. Forward Direction Button
        self.btn_forward = DirectionButton(self.card_def.forward_dir, self.card_def.color_hex, self)
        self.btn_forward.clicked.connect(lambda d: self.direction_selected.emit(d, self.card_def.card_id))
        layout.addWidget(self.btn_forward)

        # 3. Backward Direction Button (if available)
        if self.card_def.backward_dir:
            self.btn_backward = DirectionButton(self.card_def.backward_dir, self.card_def.color_hex, self)
            self.btn_backward.clicked.connect(lambda d: self.direction_selected.emit(d, self.card_def.card_id))
            layout.addWidget(self.btn_backward)
        else:
            self.btn_backward = None

    def apply_theme(self, theme_name: str):
        is_dark = (theme_name == "dark")
        card_bg = "#1E293B" if is_dark else "#FFFFFF"
        card_border = "#334155" if is_dark else "#E2E8F0"
        title_color = "#F8FAFC" if is_dark else "#0F172A"

        self.setStyleSheet(f"""
            ConversionCardWidget {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-top: 3px solid {self.card_def.color_hex};
                border-radius: 8px;
            }}
            ConversionCardWidget:hover {{
                border-color: {self.card_def.color_hex};
            }}
        """)
        self.title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {title_color};")

        if hasattr(self, "btn_forward") and self.btn_forward:
            self.btn_forward.apply_theme(theme_name)
        if hasattr(self, "btn_backward") and self.btn_backward:
            self.btn_backward.apply_theme(theme_name)

    def _update_fav_icon(self):
        is_fav = self.card_def.is_favorite()
        color = "#FFB900" if is_fav else "#94A3B8"
        self.btn_fav.setIcon(get_icon("star", color, 14))
        self.btn_fav.setStyleSheet("background: transparent; border: none;")

    def _on_toggle_fav(self):
        new_state = ConversionHistoryManager.toggle_favorite(self.card_def.card_id)
        self._update_fav_icon()
        self.favorite_toggled.emit(self.card_def.card_id, new_state)
