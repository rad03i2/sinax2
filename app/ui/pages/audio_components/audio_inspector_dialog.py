# -*- coding: utf-8 -*-
"""
SINAX Audio Inspector & Analyzer Dialog
Detailed technical inspection dialog displaying container metadata, stream codecs,
sample rates, channels, ID3 tags, Waveform preview, Spectrogram preview, and EBU R128 LUFS metrics.
"""

import json
import os
import tempfile
from typing import Any, Dict
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.audio.audio_service import audio_service
from app.services.audio.audio_utils import format_file_size
from app.ui.icons import get_icon


class AudioInspectorDialog(QDialog):
    """Deep audio inspection and analysis dialog."""

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.meta = audio_service.get_audio_metadata(file_path)
        self.setWindowTitle(f"فاحص ومحلل الصوت الهندسي: {self.meta.get('filename', 'الملف')}")
        self.resize(780, 620)
        self.setMinimumSize(640, 500)
        self._temp_files = []
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
        h_box = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("search", "#00A4EF").pixmap(24, 24))
        h_box.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        main_title = QLabel(self.meta.get("filename", "Audio File"))
        main_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        title_vbox.addWidget(main_title)

        sub_title = QLabel(self.file_path)
        sub_title.setStyleSheet("font-size: 11px; color: #8E8E93;")
        title_vbox.addWidget(sub_title)
        h_box.addLayout(title_vbox, 1)

        layout.addLayout(h_box)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(14)

        # -------------------------------------------------------------
        # Table of Properties
        # -------------------------------------------------------------
        table_lbl = QLabel("الخصائص التقنية والترميز:")
        table_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #00A4EF;")
        c_layout.addWidget(table_lbl)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["الخاصية", "القيمة"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        props = [
            ("اسم الملف", self.meta.get("filename", "")),
            ("حجم الملف", format_file_size(self.meta.get("size_bytes", 0))),
            ("المدة الإجمالية", self.meta.get("duration_formatted", "")),
            ("صيغة الحاوية", self.meta.get("format", "")),
            ("الترميز الصوتي (Codec)", self.meta.get("codec", "").upper()),
            ("معدل العينات (Sample Rate)", f"{self.meta.get('sample_rate', 0)} Hz"),
            ("القنوات وتوزيع الصوت", f"{self.meta.get('channels', 0)} ({self.meta.get('channel_layout', '')})"),
            ("معدل البت (Bitrate)", f"{self.meta.get('bitrate_kbps', 0)} kbps"),
            ("غلاف مدمج (Cover Art)", "نعم متوفر" if self.meta.get("has_cover_art") else "لا يوجد"),
        ]

        # Add tags
        tags = self.meta.get("tags", {})
        for tag_name in ["title", "artist", "album", "date", "genre", "track"]:
            if tag_name in tags:
                props.append((f"وسم ID3: {tag_name.capitalize()}", str(tags[tag_name])))

        table.setRowCount(len(props))
        for row, (k, v) in enumerate(props):
            item_k = QTableWidgetItem(k)
            item_k.setForeground(Qt.lightGray)
            item_v = QTableWidgetItem(str(v))
            table.setItem(row, 0, item_k)
            table.setItem(row, 1, item_v)

        table.setFixedHeight(min(240, len(props) * 28 + 32))
        c_layout.addWidget(table)

        # -------------------------------------------------------------
        # Visual Waveform
        # -------------------------------------------------------------
        wf_lbl = QLabel("المخطط الموجي الحقيقي (Waveform):")
        wf_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #00A4EF;")
        c_layout.addWidget(wf_lbl)

        self.wf_img_lbl = QLabel("جارٍ توليد المخطط الموجي...")
        self.wf_img_lbl.setStyleSheet("""
            background-color: #141414;
            border: 1px solid #2D2D2D;
            border-radius: 6px;
            padding: 4px;
            min-height: 80px;
        """)
        self.wf_img_lbl.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(self.wf_img_lbl)

        # -------------------------------------------------------------
        # Visual Spectrogram
        # -------------------------------------------------------------
        spec_lbl = QLabel("المخطط الطيفي للترددات (Spectrogram):")
        spec_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #00A4EF;")
        c_layout.addWidget(spec_lbl)

        self.spec_img_lbl = QLabel("جارٍ توليد المخطط الطيفي...")
        self.spec_img_lbl.setStyleSheet("""
            background-color: #141414;
            border: 1px solid #2D2D2D;
            border-radius: 6px;
            padding: 4px;
            min-height: 80px;
        """)
        self.spec_img_lbl.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(self.spec_img_lbl)

        # -------------------------------------------------------------
        # Loudness Analysis EBU R128
        # -------------------------------------------------------------
        lufs_lbl = QLabel("قياسات العلو القياسية (EBU R128 Metrics):")
        lufs_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #00A4EF;")
        c_layout.addWidget(lufs_lbl)

        self.lufs_info_lbl = QLabel("انقر على 'بدء فحص LUFS' لحساب العلو المتكامل والذروة الحقيقية.")
        self.lufs_info_lbl.setStyleSheet("""
            background-color: #242424;
            color: #FFB74D;
            border: 1px solid #383838;
            border-radius: 6px;
            padding: 10px;
            font-size: 12px;
        """)
        c_layout.addWidget(self.lufs_info_lbl)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # -------------------------------------------------------------
        # Bottom Buttons
        # -------------------------------------------------------------
        btn_layout = QHBoxLayout()

        self.analyze_lufs_btn = QPushButton("بدء فحص LUFS المتقدم ⚡")
        self.analyze_lufs_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover { background-color: #1084D9; }
        """)
        self.analyze_lufs_btn.clicked.connect(self._run_lufs_analysis)
        btn_layout.addWidget(self.analyze_lufs_btn)

        copy_btn = QPushButton("نسخ التقرير (JSON)")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover { background-color: #383838; }
        """)
        copy_btn.clicked.connect(self._copy_json)
        btn_layout.addWidget(copy_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("إغلاق")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover { background-color: #484848; }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Generate Waveform & Spectrogram in background
        self._load_visualizations()

    def _load_visualizations(self):
        try:
            fd1, wf_png = tempfile.mkstemp(suffix=".png", prefix="sinax_insp_wf_")
            os.close(fd1)
            self._temp_files.append(wf_png)

            if audio_service.generate_waveform_image(self.file_path, wf_png, width=700, height=80, color="#00A4EF"):
                self.wf_img_lbl.setPixmap(QPixmap(wf_png).scaled(700, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.wf_img_lbl.setText("تعذر توليد المخطط الموجي لهذا الملف.")

            fd2, sp_png = tempfile.mkstemp(suffix=".png", prefix="sinax_insp_sp_")
            os.close(fd2)
            self._temp_files.append(sp_png)

            if audio_service.generate_spectrogram_image(self.file_path, sp_png, width=700, height=80, color="plasma"):
                self.spec_img_lbl.setPixmap(QPixmap(sp_png).scaled(700, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.spec_img_lbl.setText("تعذر توليد المخطط الطيفي لهذا الملف.")
        except Exception as e:
            self.wf_img_lbl.setText(f"خطأ: {e}")

    def _run_lufs_analysis(self):
        self.analyze_lufs_btn.setEnabled(False)
        self.lufs_info_lbl.setText("جارٍ فحص وتحليل العلو الصوتي بدقة...")
        QGuiApplication.processEvents()

        res = audio_service.analyze_audio_loudness(self.file_path)
        if res.get("success"):
            txt = (
                f"• Integrated Loudness: {res['input_i']:.1f} LUFS\n"
                f"• True Peak: {res['input_tp']:.2f} dBFS\n"
                f"• Loudness Range (LRA): {res['input_lra']:.1f} LU\n"
                f"• Threshold: {res['input_thresh']:.1f} LUFS"
            )
            self.lufs_info_lbl.setText(txt)
            self.meta["lufs_analysis"] = res
        else:
            self.lufs_info_lbl.setText("تعذر إجراء فحص LUFS على هذا الملف.")

        self.analyze_lufs_btn.setEnabled(True)

    def _copy_json(self):
        text = json.dumps(self.meta, ensure_ascii=False, indent=2)
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setText(text)

    def closeEvent(self, event):
        for t in self._temp_files:
            if os.path.exists(t):
                try:
                    os.unlink(t)
                except Exception:
                    pass
        super().closeEvent(event)
