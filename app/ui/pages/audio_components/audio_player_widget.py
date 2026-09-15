# -*- coding: utf-8 -*-
"""
SINAX Audio Player Widget
Interactive in-app audio player featuring authentic waveform visualization,
position seeking, play/pause, volume control, and file metadata overview.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.core.logger import get_logger
from app.services.audio.audio_service import audio_service
from app.services.audio.audio_utils import format_duration
from app.ui.icons import get_icon

logger = get_logger("audio_player_widget")

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_QT_MULTIMEDIA = True
except ImportError:
    HAS_QT_MULTIMEDIA = False


class AudioPlayerWidget(QFrame):
    """Native media player with visual waveform display and interactive controls."""

    playback_state_changed = Signal(bool)  # is_playing

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AudioPlayerWidget")
        self.setStyleSheet("""
            QFrame#AudioPlayerWidget {
                background-color: #1F1F1F;
                border: 1px solid #333333;
                border-radius: 10px;
                padding: 12px;
            }
        """)

        self._current_file: Optional[str] = None
        self._temp_waveform_png: Optional[str] = None
        self._is_seeking = False
        self._duration_ms = 0

        self._init_player()
        self._init_ui()

    def _init_player(self):
        self._player = None
        self._audio_output = None
        if HAS_QT_MULTIMEDIA:
            try:
                self._player = QMediaPlayer(self)
                self._audio_output = QAudioOutput(self)
                self._player.setAudioOutput(self._audio_output)
                self._audio_output.setVolume(0.8)

                self._player.positionChanged.connect(self._on_position_changed)
                self._player.durationChanged.connect(self._on_duration_changed)
                self._player.playbackStateChanged.connect(self._on_state_changed)
            except Exception as e:
                logger.error(f"Error initializing QMediaPlayer: {e}")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. Header: Track title & Tech specs
        # -------------------------------------------------------------
        header_box = QHBoxLayout()
        header_box.setSpacing(8)

        track_icon = QLabel()
        track_icon.setPixmap(get_icon("audio", "#00A4EF").pixmap(18, 18))
        header_box.addWidget(track_icon)

        self.title_lbl = QLabel("لم يتم تحميل ملف صوتي بعد")
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFFFFF;")
        header_box.addWidget(self.title_lbl, 1)

        self.specs_lbl = QLabel("")
        self.specs_lbl.setStyleSheet("""
            background-color: #2D2D2D;
            color: #A0A0A0;
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 11px;
        """)
        self.specs_lbl.setVisible(False)
        header_box.addWidget(self.specs_lbl)

        layout.addLayout(header_box)

        # -------------------------------------------------------------
        # 2. Waveform Canvas
        # -------------------------------------------------------------
        self.waveform_frame = QFrame()
        self.waveform_frame.setFixedHeight(72)
        self.waveform_frame.setStyleSheet("""
            background-color: #141414;
            border: 1px solid #2B2B2B;
            border-radius: 6px;
        """)
        wf_layout = QVBoxLayout(self.waveform_frame)
        wf_layout.setContentsMargins(0, 0, 0, 0)
        wf_layout.setAlignment(Qt.AlignCenter)

        self.waveform_lbl = QLabel("مخطط الموجة الصوتية (Waveform)")
        self.waveform_lbl.setStyleSheet("color: #666666; font-size: 11px;")
        self.waveform_lbl.setAlignment(Qt.AlignCenter)
        wf_layout.addWidget(self.waveform_lbl)

        layout.addWidget(self.waveform_frame)

        # -------------------------------------------------------------
        # 3. Seekbar & Timestamps
        # -------------------------------------------------------------
        seek_layout = QHBoxLayout()
        seek_layout.setSpacing(10)

        self.curr_time_lbl = QLabel("00:00")
        self.curr_time_lbl.setStyleSheet("color: #00A4EF; font-size: 11px; font-weight: bold; min-width: 40px;")
        seek_layout.addWidget(self.curr_time_lbl)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #333333;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0078D4;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
                background: #FFFFFF;
            }
            QSlider::handle:horizontal:hover {
                background: #00A4EF;
            }
        """)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        seek_layout.addWidget(self.seek_slider, 1)

        self.total_time_lbl = QLabel("00:00")
        self.total_time_lbl.setStyleSheet("color: #8E8E93; font-size: 11px; min-width: 40px;")
        seek_layout.addWidget(self.total_time_lbl)

        layout.addLayout(seek_layout)

        # -------------------------------------------------------------
        # 4. Controls Row: Play, Stop, Volume
        # -------------------------------------------------------------
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        # Play / Pause button
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setIcon(get_icon("play", "#FFFFFF"))
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                border: none;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #1084D9;
            }
            QPushButton:pressed {
                background-color: #006CBE;
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_btn)

        # Stop button
        self.stop_btn = QPushButton()
        self.stop_btn.setFixedSize(32, 32)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setIcon(get_icon("stop", "#CCCCCC"))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: #383838;
            }
        """)
        self.stop_btn.clicked.connect(self.stop)
        controls_layout.addWidget(self.stop_btn)

        controls_layout.addSpacing(16)

        # Volume icon
        vol_icon = QLabel()
        vol_icon.setPixmap(get_icon("volume", "#AAAAAA").pixmap(16, 16))
        controls_layout.addWidget(vol_icon)

        # Volume slider
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(100)
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #333333;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #8E8E93;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 5px;
                background: #CCCCCC;
            }
        """)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        controls_layout.addWidget(self.vol_slider)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

    def load_audio(self, file_path: str):
        """Loads audio file, extracts metadata, renders waveform, and preps player."""
        if not os.path.exists(file_path):
            return

        self.stop()
        self._current_file = file_path
        p = Path(file_path)
        self.title_lbl.setText(p.name)

        # Metadata
        meta = audio_service.get_audio_metadata(file_path)
        sr = meta.get("sample_rate", 44100)
        ch = meta.get("channel_layout", "stereo")
        br = meta.get("bitrate_kbps", 0)
        codec = meta.get("codec", "").upper()
        spec_text = f"{codec} | {sr} Hz | {ch} | {br} kbps"
        self.specs_lbl.setText(spec_text)
        self.specs_lbl.setVisible(True)

        dur_sec = meta.get("duration", 0.0)
        self._duration_ms = int(dur_sec * 1000)
        self.total_time_lbl.setText(format_duration(dur_sec))
        self.curr_time_lbl.setText("00:00")
        self.seek_slider.setValue(0)

        # Generate waveform
        try:
            if not self._temp_waveform_png:
                fd, self._temp_waveform_png = tempfile.mkstemp(suffix=".png", prefix="sinax_wf_")
                os.close(fd)

            ok = audio_service.generate_waveform_image(
                input_file=file_path,
                output_png=self._temp_waveform_png,
                width=680,
                height=70,
                color="#00A4EF"
            )
            if ok and os.path.exists(self._temp_waveform_png):
                pix = QPixmap(self._temp_waveform_png)
                self.waveform_lbl.setPixmap(pix.scaled(
                    self.waveform_frame.width() - 4 if self.waveform_frame.width() > 10 else 680,
                    68,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
            else:
                self.waveform_lbl.setText("مخطط الموجة متاح عند المعالجة")
        except Exception as e:
            logger.debug(f"Waveform preview generation skipped: {e}")

        # Load media in player
        if self._player and HAS_QT_MULTIMEDIA:
            try:
                self._player.setSource(QUrl.fromLocalFile(file_path))
            except Exception as e:
                logger.error(f"Failed to setSource on QMediaPlayer: {e}")

    def toggle_play(self):
        if not self._player or not HAS_QT_MULTIMEDIA:
            return

        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def stop(self):
        if self._player and HAS_QT_MULTIMEDIA:
            self._player.stop()
        self.seek_slider.setValue(0)
        self.curr_time_lbl.setText("00:00")
        self.play_btn.setIcon(get_icon("play", "#FFFFFF"))

    def _on_state_changed(self, state):
        is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.play_btn.setIcon(get_icon("pause" if is_playing else "play", "#FFFFFF"))
        self.playback_state_changed.emit(is_playing)

    def _on_position_changed(self, pos_ms: int):
        if not self._is_seeking and self._duration_ms > 0:
            val = int((pos_ms / self._duration_ms) * 1000)
            self.seek_slider.setValue(val)
            self.curr_time_lbl.setText(format_duration(pos_ms / 1000.0))

    def _on_duration_changed(self, dur_ms: int):
        if dur_ms > 0:
            self._duration_ms = dur_ms
            self.total_time_lbl.setText(format_duration(dur_ms / 1000.0))

    def _on_seek_pressed(self):
        self._is_seeking = True

    def _on_seek_released(self):
        self._is_seeking = False
        if self._player and self._duration_ms > 0:
            pct = self.seek_slider.value() / 1000.0
            target_pos = int(pct * self._duration_ms)
            self._player.setPosition(target_pos)

    def _on_seek_moved(self, val: int):
        if self._duration_ms > 0:
            pct = val / 1000.0
            cur_sec = (pct * self._duration_ms) / 1000.0
            self.curr_time_lbl.setText(format_duration(cur_sec))

    def _on_volume_changed(self, val: int):
        if self._audio_output:
            self._audio_output.setVolume(val / 100.0)

    def closeEvent(self, event):
        self.stop()
        if self._temp_waveform_png and os.path.exists(self._temp_waveform_png):
            try:
                os.unlink(self._temp_waveform_png)
            except Exception:
                pass
        super().closeEvent(event)
