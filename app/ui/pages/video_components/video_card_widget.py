# -*- coding: utf-8 -*-
"""
SINAX Video Tool Card Widget
Fluent UI tool card for the Video Center catalog featuring icon, Arabic & English titles,
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

from app.services.video.video_registry import VideoToolDefinition
from app.ui.icons import get_icon


class VideoCardWidget(QFrame):
    """Interactive card representing a video processing tool in the Video Center."""

    clicked = Signal(str)  # Emits tool_id when opened
    favorite_toggled = Signal(str, bool)  # (tool_id, is_favorite)

    def __init__(self, tool: VideoToolDefinition, is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.is_favorite = is_favorite
        self.setObjectName("VideoCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame#VideoCard {
                background-color: #262626;
                border: 1px solid #383838;
                border-radius: 10px;
                padding: 14px;
            }
            QFrame#VideoCard:hover {
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

        # Gradient Icon Box
        icon_box = QFrame()
        icon_box.setFixedSize(44, 44)
        icon_box.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E2838, stop:1 #0078D4);
                border-radius: 8px;
            }
        """)
        ib_layout = QVBoxLayout(icon_box)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        ib_layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(self.tool.icon, "#FFFFFF", 24).pixmap(24, 24))
        ib_layout.addWidget(icon_lbl)
        header_layout.addWidget(icon_box)

        # Titles
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        ar_title = QLabel(self.tool.title_ar)
        ar_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        title_layout.addWidget(ar_title)

        en_title = QLabel(self.tool.title_en)
        en_title.setStyleSheet("font-size: 11px; color: #888888;")
        title_layout.addWidget(en_title)

        header_layout.addLayout(title_layout, 1)

        # Favorite star button
        self.fav_btn = QPushButton("★" if self.is_favorite else "☆")
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self._update_fav_style()
        self.fav_btn.clicked.connect(self._toggle_favorite)
        header_layout.addWidget(self.fav_btn)

        layout.addLayout(header_layout)

        # -------------------------------------------------------------
        # Description
        # -------------------------------------------------------------
        desc_lbl = QLabel(self.tool.description_ar)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #B0B0B0; line-height: 1.4;")
        desc_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout.addWidget(desc_lbl)

        # -------------------------------------------------------------
        # Badges row (Batch tag + Status badge + Action Button)
        # -------------------------------------------------------------
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(6)

        if self.tool.supports_batch:
            batch_tag = QLabel("⚡ معالجة جماعية")
            batch_tag.setStyleSheet("""
                QLabel {
                    background-color: #1A3826;
                    color: #6CCB5F;
                    border: 1px solid #235A36;
                    border-radius: 4px;
                    padding: 3px 7px;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
            badges_layout.addWidget(batch_tag)

        if self.tool.badge:
            status_tag = QLabel(self.tool.badge)
            status_tag.setStyleSheet("""
                QLabel {
                    background-color: #0E2E4E;
                    color: #60CDFF;
                    border: 1px solid #14487A;
                    border-radius: 4px;
                    padding: 3px 7px;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
            badges_layout.addWidget(status_tag)

        badges_layout.addStretch(1)

        # Open action button
        open_btn = QPushButton("فتح الأداة ←")
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #484848;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0078D4;
                border-color: #0078D4;
            }
        """)
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(lambda: self.clicked.emit(self.tool.id))
        badges_layout.addWidget(open_btn)

        layout.addLayout(badges_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.tool.id)
        super().mousePressEvent(event)

    def _toggle_favorite(self):
        self.is_favorite = not self.is_favorite
        self.fav_btn.setText("★" if self.is_favorite else "☆")
        self._update_fav_style()
        self.favorite_toggled.emit(self.tool.id, self.is_favorite)

    def _update_fav_style(self):
        if self.is_favorite:
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 18px;
                    color: #FFB900;
                }
            """)
        else:
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 18px;
                    color: #666666;
                }
                QPushButton:hover {
                    color: #FFB900;
                }
            """)
