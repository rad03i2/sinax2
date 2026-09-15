# -*- coding: utf-8 -*-
"""
SINAX Placeholder Page
Displays upcoming features and sections with a modern Fluent placeholder card.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from app.ui.icons import get_icon

class PlaceholderPage(QWidget):
    back_to_hub_requested = Signal()

    def __init__(self, title: str, subtitle: str, stage_label: str, parent=None):
        super().__init__(parent)
        self._init_ui(title, subtitle, stage_label)

    def _init_ui(self, title, subtitle, stage_label):
        from PySide6.QtWidgets import QScrollArea
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.verticalScrollBar().setSingleStep(28)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 40)

        card = QFrame()
        card.setStyleSheet("background-color: #262626; border: 1px solid #383838; border-radius: 12px;")
        card.setMinimumWidth(560)
        card.setMaximumWidth(700)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(16)

        # Icon
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("logo", "#60CDFF", 56).pixmap(56, 56))
        icon_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_lbl)

        # Title
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        t_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(t_lbl)

        # Stage Badge
        stage_badge = QLabel(stage_label)
        stage_badge.setStyleSheet("background-color: #004578; color: #60CDFF; border-radius: 6px; padding: 4px 14px; font-size: 12px; font-weight: bold;")
        stage_badge.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(stage_badge)

        # Subtitle / description (No clipping, natural breathing room)
        s_lbl = QLabel(subtitle)
        s_lbl.setWordWrap(True)
        s_lbl.setAlignment(Qt.AlignCenter)
        s_lbl.setStyleSheet("font-size: 13px; color: #CCCCCC; padding: 4px 6px; background: transparent; border: none;")
        card_layout.addWidget(s_lbl)

        card_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Back button
        back_btn = QPushButton("العودة إلى مركز إدارة الملفات")
        back_btn.setProperty("class", "PrimaryButton")
        back_btn.setFixedWidth(240)
        back_btn.setMinimumHeight(38)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_hub_requested.emit)
        card_layout.addWidget(back_btn, 0, Qt.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(card, 0, Qt.AlignCenter)
        layout.addStretch(1)

        scroll.setWidget(container)
        outer_layout.addWidget(scroll)
