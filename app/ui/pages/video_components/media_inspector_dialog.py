# -*- coding: utf-8 -*-
"""
SINAX Media Inspector Dialog
Detailed technical inspection dialog displaying container metadata, stream codecs,
bitrates, frame rates, audio channels, and stream parameters with clipboard export.
"""

import json
from typing import Any, Dict
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.ui.icons import get_icon


class MediaInspectorDialog(QDialog):
    """Deep media inspection dialog for video and audio files."""

    def __init__(self, media_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.media_info = media_info
        self.setWindowTitle(f"فاحص الوسائط: {media_info.get('filename', 'الملف')}")
        self.resize(720, 560)
        self.setMinimumSize(600, 450)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }
            QLabel {
                color: #E0E0E0;
            }
            QTableWidget {
                background-color: #262626;
                color: #FFFFFF;
                border: 1px solid #383838;
                border-radius: 6px;
                gridline-color: #333333;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #A0A0A0;
                font-weight: bold;
                border: 1px solid #383838;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("info", "#60CDFF", 28).pixmap(28, 28))
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        t = QLabel(f"فحص الوسائط: {self.media_info.get('filename', '')}")
        t.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        title_box.addWidget(t)

        p = QLabel(self.media_info.get("path", ""))
        p.setStyleSheet("font-size: 11px; color: #888888;")
        title_box.addWidget(p)
        header.addLayout(title_box, 1)

        layout.addLayout(header)

        # Summary Cards Row
        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)

        def make_card(title: str, val: str, color: str):
            box = QFrame()
            box.setStyleSheet(f"""
                QFrame {{
                    background-color: #262626;
                    border: 1px solid #383838;
                    border-radius: 6px;
                    padding: 8px;
                }}
            """)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(6, 4, 6, 4)
            bl.setSpacing(2)
            tl = QLabel(title)
            tl.setStyleSheet("font-size: 11px; color: #999999;")
            vl = QLabel(str(val))
            vl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
            bl.addWidget(tl)
            bl.addWidget(vl)
            return box

        summary_row.addWidget(make_card("مدة المقطع", self.media_info.get("duration_formatted", "--:--"), "#60CDFF"))
        summary_row.addWidget(make_card("حجم الملف", self.media_info.get("size_formatted", "0 MB"), "#6CCB5F"))
        summary_row.addWidget(make_card("الدقة", self.media_info.get("resolution", "غير متوفر"), "#FFB900"))
        summary_row.addWidget(make_card("معدل البت", f"{self.media_info.get('bitrate_kbps', 0)} kb/s", "#C58AF9"))

        layout.addLayout(summary_row)

        # Streams Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["الخاصية", "القيمة", "النوع"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        self._populate_table()
        layout.addWidget(self.table, 1)

        # Bottom Buttons
        bottom_row = QHBoxLayout()

        copy_btn = QPushButton("📋 نسخ البيانات كـ JSON")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #484848;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        copy_btn.clicked.connect(self._copy_json)
        bottom_row.addWidget(copy_btn)

        bottom_row.addStretch(1)

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 7px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
        """)
        close_btn.clicked.connect(self.accept)
        bottom_row.addWidget(close_btn)

        layout.addLayout(bottom_row)

    def _populate_table(self):
        rows = [
            ("اسم الملف", self.media_info.get("filename", ""), "حاوية"),
            ("المسار الكامل", self.media_info.get("path", ""), "حاوية"),
            ("حجم الملف", f"{self.media_info.get('size_bytes', 0):,} بايت ({self.media_info.get('size_formatted', '')})", "حاوية"),
            ("مدة التشغيل", f"{self.media_info.get('duration_formatted', '')} ({self.media_info.get('duration', 0.0):.2f} ثانية)", "حاوية"),
            ("إجمالي معدل البت", f"{self.media_info.get('bitrate_kbps', 0)} kb/s", "حاوية"),
            ("ترميز الفيديو", self.media_info.get("video_codec", "غير متوفر"), "فيديو"),
            ("دقة العرض", self.media_info.get("resolution", "غير متوفر"), "فيديو"),
            ("العرض x الارتفاع", f"{self.media_info.get('width', 0)} × {self.media_info.get('height', 0)} بكسل", "فيديو"),
            ("معدل الإطارات (FPS)", f"{self.media_info.get('fps', 0.0):.2f} إطار/ثانية", "فيديو"),
            ("نسبة الأبعاد (Aspect)", self.media_info.get("aspect_ratio", "غير متوفر"), "فيديو"),
            ("ترميز الصوت", self.media_info.get("audio_codec", "غير متوفر"), "صوت"),
            ("قنوات الصوت", self.media_info.get("audio_channels", "غير متوفر"), "صوت"),
            ("تردد الصوت (Hz)", f"{self.media_info.get('sample_rate_hz', 0)} هرتز", "صوت"),
            ("معدل بت الصوت", f"{self.media_info.get('audio_bitrate_kbps', 0)} kb/s", "صوت"),
            ("يحتوي ترجمات مدمجة", "نعم" if self.media_info.get("has_subtitles") else "لا", "ترجمة"),
        ]

        self.table.setRowCount(len(rows))
        for r_idx, (prop, val, grp) in enumerate(rows):
            p_item = QTableWidgetItem(prop)
            p_item.setForeground(Qt.white)
            v_item = QTableWidgetItem(str(val))
            v_item.setForeground(Qt.white)
            g_item = QTableWidgetItem(grp)
            g_item.setTextAlignment(Qt.AlignCenter)
            g_item.setForeground(Qt.lightGray)

            self.table.setItem(r_idx, 0, p_item)
            self.table.setItem(r_idx, 1, v_item)
            self.table.setItem(r_idx, 2, g_item)

    def _copy_json(self):
        try:
            dump = json.dumps(self.media_info, indent=2, ensure_ascii=False)
            QGuiApplication.clipboard().setText(dump)
        except Exception:
            pass
