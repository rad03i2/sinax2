# -*- coding: utf-8 -*-
"""
SINAX PDF Tool Card Widget
Interactive card displaying a single PDF tool in the catalog with status badges,
favorite toggles, descriptions, and action triggers.
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from app.ui.icons import get_icon
from app.services.pdf.pdf_registry import PDFToolDefinition


class PDFCardWidget(QFrame):
    clicked = Signal(str)                   # emits tool_id
    favorite_toggled = Signal(str, bool)    # emits (tool_id, is_favorite)

    def __init__(self, tool: PDFToolDefinition, is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.tool = tool
        self._is_favorite = is_favorite
        self.setProperty("class", "ToolCard")
        self.setCursor(Qt.PointingHandCursor if tool.status != "upcoming" else Qt.ArrowCursor)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # 1. Top Bar: Icon + Star + Badge
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Icon
        icon_lbl = QLabel()
        icon_name = self.tool.icon
        # Map common icons safely
        if icon_name not in ("merge", "split", "compress", "image", "pdf", "number", "watermark", "lock", "unlock", "reorder", "rotate", "crop", "flatten", "redact", "text", "check", "compare", "print", "trash", "info", "ocr"):
            icon_name = "pdf"

        icon_color = "#60CDFF"
        if self.tool.category == "compress_optimize":
            icon_color = "#FFB900"
        elif self.tool.category == "security_privacy":
            icon_color = "#F7630C"
        elif self.tool.category == "extract":
            icon_color = "#52C41A"
        elif self.tool.category == "inspect_repair":
            icon_color = "#13C2C2"

        icon_lbl.setPixmap(get_icon(icon_name, icon_color, 28).pixmap(28, 28))
        top_row.addWidget(icon_lbl)

        # Favorite Star Button
        self.star_btn = QPushButton("★" if self._is_favorite else "☆")
        self.star_btn.setFixedSize(26, 26)
        self.star_btn.setCursor(Qt.PointingHandCursor)
        self._update_star_style()
        self.star_btn.clicked.connect(self._on_star_clicked)
        top_row.addWidget(self.star_btn)

        top_row.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Status Badge
        badge = QLabel()
        if self.tool.status == "ready":
            badge.setText("جاهز للاستخدام")
            badge.setStyleSheet("background-color: #107C41; color: #FFFFFF; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
        elif self.tool.status == "needs_dep":
            badge.setText("يتطلب مكوناً")
            badge.setStyleSheet("background-color: #D83B01; color: #FFFFFF; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
        else:
            badge.setText("قريباً")
            badge.setStyleSheet("background-color: #383838; color: #888888; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
        top_row.addWidget(badge)
        layout.addLayout(top_row)

        # 2. Titles (Arabic & English)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_ar = QLabel(self.tool.title_ar)
        title_ar.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        title_box.addWidget(title_ar)

        title_en = QLabel(self.tool.title_en)
        title_en.setStyleSheet("font-size: 11px; color: #888888;")
        title_box.addWidget(title_en)
        layout.addLayout(title_box)

        # 3. Description
        desc_lbl = QLabel(self.tool.description_ar)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #AAAAAA; line-height: 1.4;")
        layout.addWidget(desc_lbl)

        layout.addSpacerItem(QSpacerItem(10, 6, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 4. Action Button
        action_btn = QPushButton("فتح الأداة  ←" if self.tool.status != "upcoming" else "قيد التطوير في التحديث القادم")
        if self.tool.status == "ready":
            action_btn.setProperty("class", "PrimaryButton")
        elif self.tool.status == "needs_dep":
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D2D;
                    color: #FFB900;
                    border: 1px solid #444444;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #383838;
                    border-color: #FFB900;
                }
            """)
        else:
            action_btn.setEnabled(False)

        action_btn.setCursor(Qt.PointingHandCursor if self.tool.status != "upcoming" else Qt.ArrowCursor)
        action_btn.clicked.connect(self._on_action_clicked)
        layout.addWidget(action_btn)

    def _update_star_style(self):
        color = "#FFD700" if self._is_favorite else "#666666"
        self.star_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {color};
                font-size: 16px;
                padding: 0;
            }}
            QPushButton:hover {{
                color: #FFD700;
            }}
        """)

    def _on_star_clicked(self):
        self._is_favorite = not self._is_favorite
        self.star_btn.setText("★" if self._is_favorite else "☆")
        self._update_star_style()
        self.favorite_toggled.emit(self.tool.id, self._is_favorite)

    def _on_action_clicked(self):
        if self.tool.status != "upcoming":
            self.clicked.emit(self.tool.id)

    def mousePressEvent(self, event):
        if self.tool.status != "upcoming" and event.button() == Qt.LeftButton:
            # Check if star button was clicked directly
            if not self.star_btn.geometry().contains(event.pos()):
                self.clicked.emit(self.tool.id)
        super().mousePressEvent(event)
