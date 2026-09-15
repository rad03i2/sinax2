# -*- coding: utf-8 -*-
"""
Placeholder subpage for planned Privacy & Security features.
Honest and transparent UI: explicitly informs the user that the feature
is scheduled for an upcoming sub-phase (e.g. Phase 13.2, Phase 13.4)
without presenting a fake 'ready' state.
"""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from app.ui.icons import get_icon


class PlannedFeatureSubpage(QWidget):
    """Subpage displaying detailed roadmap information for planned tools."""

    back_requested = Signal()

    def __init__(
        self,
        key: str,
        title_ar: str,
        phase_label: str,
        icon_name: str,
        summary_ar: str,
        planned_features: List[str],
        parent=None,
    ):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.key = key
        self.title_ar = title_ar
        self.phase_label = phase_label
        self.icon_name = icon_name
        self.summary_ar = summary_ar
        self.planned_features = planned_features

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(20)

        # Header card
        header_card = QFrame()
        header_card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 12px;
                padding: 24px;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setSpacing(20)

        # Large icon
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(self.icon_name, color_hex="#38BDF8", size=56).pixmap(56, 56))
        h_layout.addWidget(icon_lbl)

        # Title & Phase tag
        text_col = QVBoxLayout()
        text_col.setSpacing(8)

        top_row = QHBoxLayout()
        title_lbl = QLabel(self.title_ar)
        title_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #F0F6FC;")
        top_row.addWidget(title_lbl)

        phase_tag = QLabel(f" {self.phase_label} ")
        phase_tag.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            border: 1px solid #0284C7;
            border-radius: 6px;
            padding: 3px 10px;
            font-size: 12px;
            font-weight: bold;
        """)
        top_row.addWidget(phase_tag)
        top_row.addStretch(1)
        text_col.addLayout(top_row)

        desc_lbl = QLabel(self.summary_ar)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 14px; color: #8B949E; line-height: 1.5;")
        text_col.addWidget(desc_lbl)

        h_layout.addLayout(text_col, 1)
        c_layout.addWidget(header_card)

        # Roadmap Details Card
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 12px;
                padding: 24px;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(14)

        info_title = QLabel("القدرات والميزات المجدولة للتنفيذ:")
        info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58A6FF;")
        info_layout.addWidget(info_title)

        for feat in self.planned_features:
            item_row = QHBoxLayout()
            item_row.setSpacing(10)
            dot = QLabel("•")
            dot.setStyleSheet("color: #38BDF8; font-size: 16px; font-weight: bold;")
            item_row.addWidget(dot)

            lbl = QLabel(feat)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #C9D1D9; font-size: 13px; line-height: 1.4;")
            item_row.addWidget(lbl, 1)
            info_layout.addLayout(item_row)

        # Status note banner
        note_box = QFrame()
        note_box.setStyleSheet("""
            QFrame {
                background-color: #1C2333;
                border: 1px solid #1D4ED8;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        n_layout = QHBoxLayout(note_box)
        n_icon = QLabel()
        n_icon.setPixmap(get_icon("doctor", color_hex="#60A5FA", size=24).pixmap(24, 24))
        n_layout.addWidget(n_icon)

        n_text = QLabel(
            "هذه الميزة ستتم إضافتها في مرحلة لاحقة\n"
            "وفق خطة التطوير التدريجي لـ SINAX. تلتزم SINAX بالشفافية البرمجية التامة وعدم تقديم واجهات وهمية غير مكتملة."
        )
        n_text.setStyleSheet("color: #93C5FD; font-size: 13px; font-weight: bold; line-height: 1.5;")
        n_text.setWordWrap(True)
        n_layout.addWidget(n_text, 1)

        info_layout.addWidget(note_box)
        c_layout.addWidget(info_card)

        # Back Button
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("العودة إلى نظرة عامة")
        back_btn.setIcon(get_icon("back", color_hex="#F0F6FC"))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #F0F6FC;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #30363D;
                border-color: #8B949E;
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        btn_layout.addWidget(back_btn)
        btn_layout.addStretch(1)
        c_layout.addLayout(btn_layout)

        c_layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
