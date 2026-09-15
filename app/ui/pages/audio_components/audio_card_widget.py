# -*- coding: utf-8 -*-
"""
SINAX Audio Tool Card Widget
Fluent UI tool card for the Audio Center catalog featuring icon, Arabic & English titles,
batch capability tags, category badges, favorite toggle, and interactive hover styling.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from app.services.audio.audio_registry import AudioToolDefinition
from app.ui.icons import get_icon


class AudioCardWidget(QFrame):
    """Interactive card representing an audio processing tool in the Audio Center."""

    clicked = Signal(str)  # Emits tool_id when opened
    favorite_toggled = Signal(str, bool)  # (tool_id, is_favorite)

    def __init__(self, tool: AudioToolDefinition, is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.is_favorite = is_favorite
        self.setObjectName("AudioCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame#AudioCard {
                background-color: #262626;
                border: 1px solid #383838;
                border-radius: 10px;
                padding: 14px;
            }
            QFrame#AudioCard:hover {
                border-color: #0078D4;
                background-color: #2C2C2C;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # -------------------------------------------------------------
        # Header: Icon + Titles + Favorite Star
        # -------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Icon container
        icon_box = QFrame()
        icon_box.setFixedSize(42, 42)
        icon_box.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1A2836, stop:1 #16202A);
            border: 1px solid #2B4255;
            border-radius: 8px;
        """)
        ib_layout = QVBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        ib_layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(self.tool.icon, "#00A4EF").pixmap(22, 22))
        icon_lbl.setAlignment(Qt.AlignCenter)
        ib_layout.addWidget(icon_lbl)
        header_layout.addWidget(icon_box)

        # Title container
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        ar_title = QLabel(self.tool.title_ar)
        ar_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        ar_title.setWordWrap(True)
        title_box.addWidget(ar_title)

        en_title = QLabel(self.tool.title_en)
        en_title.setStyleSheet("font-size: 11px; color: #8E8E93;")
        title_box.addWidget(en_title)

        header_layout.addLayout(title_box, 1)

        # Favorite Star Button
        self.fav_btn = QPushButton()
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self._update_favorite_style()
        self.fav_btn.clicked.connect(self._toggle_favorite)
        header_layout.addWidget(self.fav_btn, 0, Qt.AlignTop)

        layout.addLayout(header_layout)

        # -------------------------------------------------------------
        # Description
        # -------------------------------------------------------------
        desc_lbl = QLabel(self.tool.description_ar)
        desc_lbl.setStyleSheet("font-size: 12px; color: #CCCCCC; line-height: 1.4;")
        desc_lbl.setWordWrap(True)
        desc_lbl.setMinimumHeight(44)
        layout.addWidget(desc_lbl)

        # -------------------------------------------------------------
        # Badges & Tags Row
        # -------------------------------------------------------------
        badge_layout = QHBoxLayout()
        badge_layout.setSpacing(6)

        # Operational status badge
        badge_lbl = QLabel(self.tool.badge)
        if "الميزة النجمية" in self.tool.badge:
            badge_lbl.setStyleSheet("""
                background-color: #2D1B4E;
                color: #B388FF;
                border: 1px solid #5E35B1;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: bold;
            """)
        elif "شائع" in self.tool.badge:
            badge_lbl.setStyleSheet("""
                background-color: #382A14;
                color: #FFB74D;
                border: 1px solid #784712;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: bold;
            """)
        elif "متقدم" in self.tool.badge:
            badge_lbl.setStyleSheet("""
                background-color: #142F38;
                color: #4DD0E1;
                border: 1px solid #1A5466;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: bold;
            """)
        else:
            badge_lbl.setStyleSheet("""
                background-color: #1B2B1B;
                color: #66BB6A;
                border: 1px solid #2E562E;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
            """)
        badge_layout.addWidget(badge_lbl)

        # Batch Capability Tag
        if self.tool.supports_batch:
            batch_lbl = QLabel("معالجة جماعية")
            batch_lbl.setStyleSheet("""
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #0369A1;
                border-radius: 4px;
                padding: 2px 7px;
                font-size: 10px;
            """)
            badge_layout.addWidget(batch_lbl)

        badge_layout.addStretch()

        # Action open button
        open_btn = QPushButton("فتح الأداة ←")
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #0078D4;
                border: none;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 6px;
            }
            QPushButton:hover {
                color: #268fe6;
                text-decoration: underline;
            }
        """)
        open_btn.clicked.connect(lambda: self.clicked.emit(self.tool.id))
        badge_layout.addWidget(open_btn)

        layout.addLayout(badge_layout)

    def _update_favorite_style(self):
        if self.is_favorite:
            self.fav_btn.setIcon(get_icon("star", "#FFD700"))
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background: rgba(255, 215, 0, 0.15);
                    border-radius: 14px;
                }
            """)
        else:
            self.fav_btn.setIcon(get_icon("star", "#666666"))
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.08);
                    border-radius: 14px;
                }
            """)

    def _toggle_favorite(self):
        self.is_favorite = not self.is_favorite
        self._update_favorite_style()
        self.favorite_toggled.emit(self.tool.id, self.is_favorite)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.tool.id)
        super().mousePressEvent(event)
