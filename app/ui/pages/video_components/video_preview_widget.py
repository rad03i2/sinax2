# -*- coding: utf-8 -*-
"""
SINAX Video Preview & Inspector Widget
Displays video snapshot previews, key format metadata, and launches the deep media inspector.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.services.video.ffmpeg_service import ffmpeg_service
from app.services.video.video_service import video_service
from app.services.video.video_utils import format_seconds
from app.ui.icons import get_icon
from app.ui.pages.video_components.media_inspector_dialog import MediaInspectorDialog


class VideoPreviewWidget(QWidget):
    """Interactive preview panel for inspecting video frames and metadata."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_video_path: Optional[str] = None
        self.current_meta: Dict[str, Any] = {}
        self._temp_thumb_path: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Preview Container Box
        self.preview_box = QFrame()
        self.preview_box.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        pb_layout = QVBoxLayout(self.preview_box)
        pb_layout.setContentsMargins(0, 0, 0, 0)
        pb_layout.setAlignment(Qt.AlignCenter)

        self.img_label = QLabel("حدد مقطع فيديو من القائمة لمعاينته")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("color: #777777; font-size: 13px;")
        self.img_label.setMinimumHeight(240)
        pb_layout.addWidget(self.img_label)

        layout.addWidget(self.preview_box, 1)

        # Seek Preview Slider
        seek_layout = QHBoxLayout()
        seek_layout.setSpacing(8)
        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setStyleSheet("font-size: 11px; color: #888888; font-family: monospace;")
        seek_layout.addWidget(self.lbl_time)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(0)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #333333;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #0078D4;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }
        """)
        self.slider.sliderReleased.connect(self._on_seek_released)
        seek_layout.addWidget(self.slider, 1)

        self.lbl_dur = QLabel("00:00:00")
        self.lbl_dur.setStyleSheet("font-size: 11px; color: #888888; font-family: monospace;")
        seek_layout.addWidget(self.lbl_dur)

        layout.addLayout(seek_layout)

        # Metadata Card
        self.meta_frame = QFrame()
        self.meta_frame.setStyleSheet("""
            QFrame {
                background-color: #262626;
                border: 1px solid #383838;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        mf_layout = QVBoxLayout(self.meta_frame)
        mf_layout.setContentsMargins(10, 8, 10, 8)
        mf_layout.setSpacing(6)

        self.lbl_meta_main = QLabel("لا يوجد ملف محدد")
        self.lbl_meta_main.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFFFFF;")
        mf_layout.addWidget(self.lbl_meta_main)

        self.lbl_meta_details = QLabel("--")
        self.lbl_meta_details.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        self.lbl_meta_details.setWordWrap(True)
        mf_layout.addWidget(self.lbl_meta_details)

        layout.addWidget(self.meta_frame)

        # Inspector Launch Button
        self.btn_inspect = QPushButton("🔍 فحص تفاصيل الوسائط المتقدمة (Inspector)")
        self.btn_inspect.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #60CDFF;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
                border-color: #60CDFF;
            }
        """)
        self.btn_inspect.setEnabled(False)
        self.btn_inspect.clicked.connect(self._open_inspector)
        layout.addWidget(self.btn_inspect)

    def load_video(self, video_path: str):
        """Probes video metadata and extracts snapshot thumbnail."""
        self.current_video_path = video_path
        if not video_path or not Path(video_path).exists():
            self.lbl_meta_main.setText("لا يوجد ملف محدد")
            self.lbl_meta_details.setText("--")
            self.btn_inspect.setEnabled(False)
            self.img_label.setText("حدد مقطع فيديو من القائمة لمعاينته")
            return

        self.current_meta = ffmpeg_service.probe_media(video_path)
        filename = self.current_meta.get("filename", Path(video_path).name)
        duration = self.current_meta.get("duration", 0.0)
        dur_str = self.current_meta.get("duration_formatted", "00:00:00")
        size_str = self.current_meta.get("size_formatted", "0 MB")
        res = self.current_meta.get("resolution", "")
        fps = self.current_meta.get("fps", 0.0)
        v_codec = self.current_meta.get("video_codec", "")
        a_codec = self.current_meta.get("audio_codec", "")

        self.lbl_meta_main.setText(filename)
        self.lbl_dur.setText(dur_str)
        self.lbl_meta_details.setText(
            f"الدقة: {res or 'غير محدد'}  |  الترميز: {v_codec} / {a_codec}  |  "
            f"الإطارات: {fps:.1f} FPS  |  الحجم: {size_str}  |  المدة: {dur_str}"
        )
        self.btn_inspect.setEnabled(True)

        # Extract snapshot at 10% of duration
        target_sec = min(5.0, duration * 0.1) if duration > 0 else 1.0
        self._extract_and_show_snapshot(target_sec)

    def _on_seek_released(self):
        if not self.current_video_path or not self.current_meta:
            return
        duration = self.current_meta.get("duration", 0.0)
        if duration <= 0:
            return
        pct = self.slider.value() / 100.0
        sec = duration * pct
        self.lbl_time.setText(format_seconds(sec))
        self._extract_and_show_snapshot(sec)

    def _extract_and_show_snapshot(self, timestamp_sec: float):
        if not self.current_video_path:
            return
        try:
            if not self._temp_thumb_path:
                self._temp_thumb_path = tempfile.mktemp(suffix=".jpg", prefix="sinax_preview_")

            res = video_service.extract_thumbnail(
                self.current_video_path,
                self._temp_thumb_path,
                timestamp=format_seconds(timestamp_sec, include_ms=True),
                width=480,
            )
            if res.get("success") and Path(self._temp_thumb_path).exists():
                pix = QPixmap(self._temp_thumb_path)
                if not pix.isNull():
                    scaled = pix.scaled(
                        self.preview_box.size().width() - 20,
                        self.preview_box.size().height() - 20,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    self.img_label.setPixmap(scaled)
                    self.img_label.setText("")
        except Exception:
            pass

    def _open_inspector(self):
        if not self.current_meta:
            return
        dlg = MediaInspectorDialog(self.current_meta, self)
        dlg.exec()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._temp_thumb_path and Path(self._temp_thumb_path).exists():
            pix = QPixmap(self._temp_thumb_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    self.preview_box.size().width() - 20,
                    self.preview_box.size().height() - 20,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.img_label.setPixmap(scaled)
