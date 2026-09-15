# -*- coding: utf-8 -*-
"""
SINAX Contextual Audio Options Panel
Dynamic options widget adapting to each audio tool type and schema
(Format Convert, Compression, Target Size, Trim, Split, Silence Detect, Merge, Crossfade,
Fade, Loudness LUFS, Peak Normalize, Gain, Compressor, Limiter, Noise Gate, Denoise,
Hum Removal, Declick, Truncate Silence, Podcast Enhancer, EQ, Filters, Speed, Pitch, Channels, Metadata, Workflow).
"""

import os
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services.audio.audio_registry import AudioToolDefinition
from app.services.audio.audio_utils import (
    AUDIO_FORMATS,
    COMPRESS_PRESETS,
    EQ_PRESETS,
    LOUDNORM_PRESETS,
)
from app.ui.icons import get_icon


class AudioOptionsPanel(QWidget):
    """Dynamic parameter configuration panel for audio tools."""

    options_changed = Signal()

    def __init__(self, tool: AudioToolDefinition, parent=None):
        super().__init__(parent)
        self.tool = tool
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #FFFFFF;
                border: 1px solid #3E3E3E;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #00A4EF;
            }
            QLabel {
                font-size: 12px;
                color: #DDDDDD;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #262626;
                color: #FFFFFF;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
                border-color: #0078D4;
            }
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
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        opt_type = self.tool.options_type

        if opt_type == "convert":
            self._build_convert_options(layout)
        elif opt_type == "compress":
            self._build_compress_options(layout)
        elif opt_type == "target_size":
            self._build_target_size_options(layout)
        elif opt_type == "trim":
            self._build_trim_options(layout)
        elif opt_type == "split":
            self._build_split_options(layout)
        elif opt_type == "silence_split":
            self._build_silence_split_options(layout)
        elif opt_type == "merge":
            self._build_merge_options(layout)
        elif opt_type == "crossfade":
            self._build_crossfade_options(layout)
        elif opt_type == "fade":
            self._build_fade_options(layout)
        elif opt_type == "loudness":
            self._build_loudness_options(layout)
        elif opt_type == "peak_norm":
            self._build_peak_norm_options(layout)
        elif opt_type == "volume":
            self._build_volume_options(layout)
        elif opt_type == "compressor":
            self._build_compressor_options(layout)
        elif opt_type == "limiter":
            self._build_limiter_options(layout)
        elif opt_type == "noise_gate":
            self._build_noise_gate_options(layout)
        elif opt_type == "denoise":
            self._build_denoise_options(layout)
        elif opt_type == "hum_removal":
            self._build_hum_options(layout)
        elif opt_type == "declick":
            self._build_declick_options(layout)
        elif opt_type == "silence_remove":
            self._build_silence_remove_options(layout)
        elif opt_type == "podcast_enhancer":
            self._build_podcast_enhancer_options(layout)
        elif opt_type == "eq":
            self._build_eq_options(layout)
        elif opt_type == "filters":
            self._build_filters_options(layout)
        elif opt_type == "bass_treble":
            self._build_bass_treble_options(layout)
        elif opt_type == "speed":
            self._build_speed_options(layout)
        elif opt_type == "pitch":
            self._build_pitch_options(layout)
        elif opt_type == "reverse":
            self._build_reverse_options(layout)
        elif opt_type == "channels":
            self._build_channels_options(layout)
        elif opt_type == "extract_channels":
            self._build_extract_channels_options(layout)
        elif opt_type == "metadata":
            self._build_metadata_options(layout)
        elif opt_type == "analysis":
            self._build_analysis_options(layout)
        elif opt_type == "workflow":
            self._build_workflow_options(layout)
        else:
            self._build_generic_options(layout)

        layout.addStretch()

    # -------------------------------------------------------------
    # 1. Convert
    # -------------------------------------------------------------
    def _build_convert_options(self, parent_layout):
        gb = QGroupBox("إعدادات تحويل الصيغ والجودة")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        # Output format
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("صيغة الإخراج المستهدفة:"))
        self.fmt_combo = QComboBox()
        for f in AUDIO_FORMATS:
            self.fmt_combo.addItem(f.upper(), f)
        self.fmt_combo.setCurrentText("MP3")
        self.fmt_combo.currentIndexChanged.connect(self.options_changed)
        r1.addWidget(self.fmt_combo, 1)
        vbox.addLayout(r1)

        # Bitrate
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("معدل البت (Bitrate):"))
        self.br_combo = QComboBox()
        for br in ["320k", "256k", "192k (موصى به)", "128k", "96k", "64k"]:
            val = br.split()[0]
            self.br_combo.addItem(br, val)
        self.br_combo.setCurrentIndex(2) # 192k
        self.br_combo.currentIndexChanged.connect(self.options_changed)
        r2.addWidget(self.br_combo, 1)
        vbox.addLayout(r2)

        # Sample rate
        r3 = QHBoxLayout()
        r3.addWidget(QLabel("معدل العينات (Sample Rate):"))
        self.sr_combo = QComboBox()
        self.sr_combo.addItem("الأصلي دون تغيير", None)
        self.sr_combo.addItem("44,100 Hz (CD Quality)", 44100)
        self.sr_combo.addItem("48,000 Hz (Studio / Video)", 48000)
        self.sr_combo.addItem("96,000 Hz (Hi-Res Audio)", 96000)
        self.sr_combo.currentIndexChanged.connect(self.options_changed)
        r3.addWidget(self.sr_combo, 1)
        vbox.addLayout(r3)

        # Channels
        r4 = QHBoxLayout()
        r4.addWidget(QLabel("توزيع القنوات:"))
        self.ch_combo = QComboBox()
        self.ch_combo.addItem("الأصلي", None)
        self.ch_combo.addItem("ستيريو (Stereo 2.0)", 2)
        self.ch_combo.addItem("مونو (Mono 1.0)", 1)
        self.ch_combo.currentIndexChanged.connect(self.options_changed)
        r4.addWidget(self.ch_combo, 1)
        vbox.addLayout(r4)

        # CBR / VBR
        r5 = QHBoxLayout()
        r5.addWidget(QLabel("نوع الترميز:"))
        self.vbr_cbr_combo = QComboBox()
        self.vbr_cbr_combo.addItem("ثابت CBR (أفضل توافقية)", "CBR")
        self.vbr_cbr_combo.addItem("متغير VBR (كفاءة مساحة أعلى)", "VBR")
        self.vbr_cbr_combo.currentIndexChanged.connect(self.options_changed)
        r5.addWidget(self.vbr_cbr_combo, 1)
        vbox.addLayout(r5)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 2. Compress
    # -------------------------------------------------------------
    def _build_compress_options(self, parent_layout):
        gb = QGroupBox("إعدادات ضغط الصوت")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("اختر الإعداد المسبق لنسبة الضغط والجودة:"))
        self.compress_preset_combo = QComboBox()
        for k, v in COMPRESS_PRESETS.items():
            self.compress_preset_combo.addItem(v["label"], k)
        self.compress_preset_combo.setCurrentIndex(1) # balanced
        self.compress_preset_combo.currentIndexChanged.connect(self.options_changed)
        vbox.addWidget(self.compress_preset_combo)

        # Custom bitrate slider
        vbox.addWidget(QLabel("أو حدد معدل بت مخصص (Bitrate):"))
        h = QHBoxLayout()
        self.compress_br_slider = QSlider(Qt.Horizontal)
        self.compress_br_slider.setRange(32, 320)
        self.compress_br_slider.setValue(192)
        self.compress_br_slider.setSingleStep(16)
        self.compress_br_lbl = QLabel("192 kbps")
        self.compress_br_slider.valueChanged.connect(lambda v: self.compress_br_lbl.setText(f"{v} kbps"))
        self.compress_br_slider.valueChanged.connect(self.options_changed)
        h.addWidget(self.compress_br_slider, 1)
        h.addWidget(self.compress_br_lbl)
        vbox.addLayout(h)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 3. Target Size
    # -------------------------------------------------------------
    def _build_target_size_options(self, parent_layout):
        gb = QGroupBox("تحديد الحجم المستهدف")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("الحجم الأقصى المطلوب للملف النهائي (MB):"))
        h = QHBoxLayout()
        self.target_size_spin = QDoubleSpinBox()
        self.target_size_spin.setRange(0.2, 500.0)
        self.target_size_spin.setValue(5.0)
        self.target_size_spin.setSingleStep(0.5)
        self.target_size_spin.setSuffix(" MB")
        self.target_size_spin.valueChanged.connect(self.options_changed)
        h.addWidget(self.target_size_spin, 1)

        # Quick preset buttons
        for sz in [1.0, 5.0, 10.0, 16.0]:
            btn = QPushButton(f"{int(sz)}MB")
            btn.setStyleSheet("padding: 4px 8px; font-size: 11px;")
            btn.clicked.connect(lambda _, s=sz: self.target_size_spin.setValue(s))
            h.addWidget(btn)
        vbox.addLayout(h)

        note = QLabel("ℹ️ يقوم SINAX بحساب الـ Bitrate بدقة رياضية مع هامش أمان 5% لضمان عدم تجاوز السقف.")
        note.setStyleSheet("color: #00A4EF; font-size: 11px;")
        note.setWordWrap(True)
        vbox.addWidget(note)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 4. Trim
    # -------------------------------------------------------------
    def _build_trim_options(self, parent_layout):
        gb = QGroupBox("تحديد نطاق القص والاجتزاء")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("وقت البداية (hh:mm:ss):"))
        self.trim_start_edit = QLineEdit("00:00:00")
        self.trim_start_edit.textChanged.connect(self.options_changed)
        h1.addWidget(self.trim_start_edit, 1)
        vbox.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("وقت النهاية (hh:mm:ss):"))
        self.trim_end_edit = QLineEdit("")
        self.trim_end_edit.setPlaceholderText("فارغ = حتى نهاية الملف")
        self.trim_end_edit.textChanged.connect(self.options_changed)
        h2.addWidget(self.trim_end_edit, 1)
        vbox.addLayout(h2)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 5. Split
    # -------------------------------------------------------------
    def _build_split_options(self, parent_layout):
        gb = QGroupBox("إعدادات تقسيم الملفات")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("مدة كل جزء بالدقائق:"))
        h = QHBoxLayout()
        self.split_dur_spin = QSpinBox()
        self.split_dur_spin.setRange(1, 180)
        self.split_dur_spin.setValue(5)
        self.split_dur_spin.setSuffix(" دقيقة")
        self.split_dur_spin.valueChanged.connect(self.options_changed)
        h.addWidget(self.split_dur_spin, 1)
        vbox.addLayout(h)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 6. Silence Split
    # -------------------------------------------------------------
    def _build_silence_split_options(self, parent_layout):
        gb = QGroupBox("إعدادات التقسيم باكتشاف الصمت")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("عتبة مستوى الصمت (dB):"))
        self.silence_thresh_spin = QSpinBox()
        self.silence_thresh_spin.setRange(-60, -20)
        self.silence_thresh_spin.setValue(-40)
        self.silence_thresh_spin.setSuffix(" dB")
        self.silence_thresh_spin.valueChanged.connect(self.options_changed)
        h1.addWidget(self.silence_thresh_spin, 1)
        vbox.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("الحد الأدنى لفترة السكون (ثانية):"))
        self.silence_dur_spin = QDoubleSpinBox()
        self.silence_dur_spin.setRange(0.5, 10.0)
        self.silence_dur_spin.setValue(1.5)
        self.silence_dur_spin.setSingleStep(0.2)
        self.silence_dur_spin.setSuffix(" ثانية")
        self.silence_dur_spin.valueChanged.connect(self.options_changed)
        h2.addWidget(self.silence_dur_spin, 1)
        vbox.addLayout(h2)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 7. Merge
    # -------------------------------------------------------------
    def _build_merge_options(self, parent_layout):
        gb = QGroupBox("إعدادات دمج المقاطع")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("اسم الملف المدمج الناتج:"))
        self.merge_filename_edit = QLineEdit("merged_audio.mp3")
        self.merge_filename_edit.textChanged.connect(self.options_changed)
        vbox.addWidget(self.merge_filename_edit)

        tip = QLabel("💡 نصيحة: يمكنك إعادة ترتيب المقاطع الصوتية في جدول الملفات بالأسفل ليتم دمجها بنفس الترتيب.")
        tip.setStyleSheet("color: #8E8E93; font-size: 11px;")
        tip.setWordWrap(True)
        vbox.addWidget(tip)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 8. Crossfade
    # -------------------------------------------------------------
    def _build_crossfade_options(self, parent_layout):
        gb = QGroupBox("إعدادات الدمج المتداخل (Crossfade)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("مدة التداخل بين التراكات (ثوانٍ):"))
        h = QHBoxLayout()
        self.crossfade_dur_slider = QSlider(Qt.Horizontal)
        self.crossfade_dur_slider.setRange(1, 10)
        self.crossfade_dur_slider.setValue(3)
        self.crossfade_lbl = QLabel("3.0 ثوانٍ")
        self.crossfade_dur_slider.valueChanged.connect(lambda v: self.crossfade_lbl.setText(f"{v}.0 ثوانٍ"))
        self.crossfade_dur_slider.valueChanged.connect(self.options_changed)
        h.addWidget(self.crossfade_dur_slider, 1)
        h.addWidget(self.crossfade_lbl)
        vbox.addLayout(h)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("منحنى التلاشي (Curve):"))
        self.crossfade_curve_combo = QComboBox()
        self.crossfade_curve_combo.addItem("خطي مثلثي (Triangular)", "tri")
        self.crossfade_curve_combo.addItem("جيبي دائري (Quarter Sine)", "qsin")
        self.crossfade_curve_combo.addItem("لوغاريتمي (Logarithmic)", "log")
        self.crossfade_curve_combo.currentIndexChanged.connect(self.options_changed)
        r2.addWidget(self.crossfade_curve_combo, 1)
        vbox.addLayout(r2)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 9. Fade In / Fade Out
    # -------------------------------------------------------------
    def _build_fade_options(self, parent_layout):
        gb = QGroupBox("إعدادات تلاشي الصوت (Fade)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("مدة الدخول التدريجي (Fade In):"))
        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0.0, 15.0)
        self.fade_in_spin.setValue(2.0)
        self.fade_in_spin.setSuffix(" ثانية")
        self.fade_in_spin.valueChanged.connect(self.options_changed)
        h1.addWidget(self.fade_in_spin, 1)
        vbox.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("مدة الختام التدريجي (Fade Out):"))
        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0.0, 15.0)
        self.fade_out_spin.setValue(2.0)
        self.fade_out_spin.setSuffix(" ثانية")
        self.fade_out_spin.valueChanged.connect(self.options_changed)
        h2.addWidget(self.fade_out_spin, 1)
        vbox.addLayout(h2)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 10. Loudness Normalization (LUFS)
    # -------------------------------------------------------------
    def _build_loudness_options(self, parent_layout):
        gb = QGroupBox("معايرة علو الصوت القياسية (EBU R128)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("المعيار المستهدف للمنصة:"))
        self.lufs_preset_combo = QComboBox()
        for k, v in LOUDNORM_PRESETS.items():
            self.lufs_preset_combo.addItem(v["label"], k)
        self.lufs_preset_combo.currentIndexChanged.connect(self._on_lufs_preset_changed)
        vbox.addWidget(self.lufs_preset_combo)

        h = QHBoxLayout()
        h.addWidget(QLabel("قيمة LUFS المستهدفة:"))
        self.lufs_spin = QDoubleSpinBox()
        self.lufs_spin.setRange(-30.0, -8.0)
        self.lufs_spin.setValue(-14.0)
        self.lufs_spin.setSingleStep(0.5)
        self.lufs_spin.setSuffix(" LUFS")
        self.lufs_spin.valueChanged.connect(self.options_changed)
        h.addWidget(self.lufs_spin, 1)
        vbox.addLayout(h)

        h_tp = QHBoxLayout()
        h_tp.addWidget(QLabel("الحد الأقصى للذروة الحقيقية (True Peak):"))
        self.tp_spin = QDoubleSpinBox()
        self.tp_spin.setRange(-6.0, 0.0)
        self.tp_spin.setValue(-1.0)
        self.tp_spin.setSingleStep(0.5)
        self.tp_spin.setSuffix(" dBFS")
        self.tp_spin.valueChanged.connect(self.options_changed)
        h_tp.addWidget(self.tp_spin, 1)
        vbox.addLayout(h_tp)

        self.dual_pass_cb = QCheckBox("تفعيل التحليل الثنائي عالي الدقة (Dual-Pass) [موصى به]")
        self.dual_pass_cb.setChecked(True)
        self.dual_pass_cb.toggled.connect(self.options_changed)
        vbox.addWidget(self.dual_pass_cb)

        parent_layout.addWidget(gb)

    def _on_lufs_preset_changed(self):
        k = self.lufs_preset_combo.currentData()
        if k in LOUDNORM_PRESETS:
            cfg = LOUDNORM_PRESETS[k]
            self.lufs_spin.setValue(cfg["i"])
            self.tp_spin.setValue(cfg["tp"])
        self.options_changed.emit()

    # -------------------------------------------------------------
    # 11. Peak Normalize
    # -------------------------------------------------------------
    def _build_peak_norm_options(self, parent_layout):
        gb = QGroupBox("المعايرة الذروية (Peak Normalize)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("المستوى الأقصى للذروة (Peak Target):"))
        h = QHBoxLayout()
        self.peak_spin = QDoubleSpinBox()
        self.peak_spin.setRange(-12.0, 0.0)
        self.peak_spin.setValue(-1.0)
        self.peak_spin.setSingleStep(0.5)
        self.peak_spin.setSuffix(" dB")
        self.peak_spin.valueChanged.connect(self.options_changed)
        h.addWidget(self.peak_spin, 1)
        vbox.addLayout(h)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 12. Volume Adjust (Gain)
    # -------------------------------------------------------------
    def _build_volume_options(self, parent_layout):
        gb = QGroupBox("تعديل وتضخيم الصوت (Gain)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("نسبة التضخيم أو الخفض بالديسيبل (+dB / -dB):"))
        h = QHBoxLayout()
        self.vol_gain_slider = QSlider(Qt.Horizontal)
        self.vol_gain_slider.setRange(-24, 18)
        self.vol_gain_slider.setValue(0)
        self.vol_gain_lbl = QLabel("0.0 dB")
        self.vol_gain_slider.valueChanged.connect(lambda v: self.vol_gain_lbl.setText(f"{v:+.1f} dB"))
        self.vol_gain_slider.valueChanged.connect(self.options_changed)
        h.addWidget(self.vol_gain_slider, 1)
        h.addWidget(self.vol_gain_lbl)
        vbox.addLayout(h)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 13. Compressor
    # -------------------------------------------------------------
    def _build_compressor_options(self, parent_layout):
        gb = QGroupBox("إعدادات ضاغط الديناميكا (Compressor)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(8)

        # Threshold
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("عتبة الضغط (Threshold):"))
        self.comp_thresh_spin = QSpinBox()
        self.comp_thresh_spin.setRange(-40, 0)
        self.comp_thresh_spin.setValue(-20)
        self.comp_thresh_spin.setSuffix(" dB")
        self.comp_thresh_spin.valueChanged.connect(self.options_changed)
        h1.addWidget(self.comp_thresh_spin, 1)
        vbox.addLayout(h1)

        # Ratio
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("نسبة الضغط (Ratio):"))
        self.comp_ratio_spin = QDoubleSpinBox()
        self.comp_ratio_spin.setRange(1.0, 20.0)
        self.comp_ratio_spin.setValue(4.0)
        self.comp_ratio_spin.setSingleStep(0.5)
        self.comp_ratio_spin.setSuffix(":1")
        self.comp_ratio_spin.valueChanged.connect(self.options_changed)
        h2.addWidget(self.comp_ratio_spin, 1)
        vbox.addLayout(h2)

        # Makeup Gain
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("تعويض الكسب (Makeup Gain):"))
        self.comp_makeup_spin = QDoubleSpinBox()
        self.comp_makeup_spin.setRange(0.0, 18.0)
        self.comp_makeup_spin.setValue(2.0)
        self.comp_makeup_spin.setSuffix(" dB")
        self.comp_makeup_spin.valueChanged.connect(self.options_changed)
        h3.addWidget(self.comp_makeup_spin, 1)
        vbox.addLayout(h3)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 14. Limiter
    # -------------------------------------------------------------
    def _build_limiter_options(self, parent_layout):
        gb = QGroupBox("إعدادات محدد الذروة (Peak Limiter)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("السقف الأقصى المسموح (Limit Ceiling):"))
        h = QHBoxLayout()
        self.limiter_spin = QDoubleSpinBox()
        self.limiter_spin.setRange(-6.0, 0.0)
        self.limiter_spin.setValue(-1.0)
        self.limiter_spin.setSuffix(" dB")
        self.limiter_spin.valueChanged.connect(self.options_changed)
        h.addWidget(self.limiter_spin, 1)
        vbox.addLayout(h)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 15. Noise Gate
    # -------------------------------------------------------------
    def _build_noise_gate_options(self, parent_layout):
        gb = QGroupBox("إعدادات بوابة الضوضاء (Noise Gate)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        h = QHBoxLayout()
        h.addWidget(QLabel("عتبة الإسكات (Threshold):"))
        self.gate_thresh_spin = QSpinBox()
        self.gate_thresh_spin.setRange(-60, -20)
        self.gate_thresh_spin.setValue(-40)
        self.gate_thresh_spin.setSuffix(" dB")
        self.gate_thresh_spin.valueChanged.connect(self.options_changed)
        h.addWidget(self.gate_thresh_spin, 1)
        vbox.addLayout(h)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 16. Denoise
    # -------------------------------------------------------------
    def _build_denoise_options(self, parent_layout):
        gb = QGroupBox("إزالة الضوضاء والوشيش (FFT Denoise)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("قوة إزالة الضوضاء والتنقية:"))
        self.denoise_combo = QComboBox()
        self.denoise_combo.addItem("تنقية خفيفة (-18 dB)", -18.0)
        self.denoise_combo.addItem("تنقية متوازنة (-24 dB) [موصى بها]", -24.0)
        self.denoise_combo.addItem("تنقية قوية (-32 dB)", -32.0)
        self.denoise_combo.setCurrentIndex(1)
        self.denoise_combo.currentIndexChanged.connect(self.options_changed)
        vbox.addWidget(self.denoise_combo)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 17. Hum Removal
    # -------------------------------------------------------------
    def _build_hum_options(self, parent_layout):
        gb = QGroupBox("إزالة طنين الكهرباء (Hum)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("تردد الكهرباء في بلد التسجيل:"))
        self.hum_combo = QComboBox()
        self.hum_combo.addItem("50 Hz ومضاعفاتها (الشرق الأوسط، مصر، أوروبا)", 50)
        self.hum_combo.addItem("60 Hz ومضاعفاتها (أمريكا الشمالية، بعض شبكات الخليج)", 60)
        self.hum_combo.currentIndexChanged.connect(self.options_changed)
        vbox.addWidget(self.hum_combo)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 18. Declick / Declip
    # -------------------------------------------------------------
    def _build_declick_options(self, parent_layout):
        gb = QGroupBox("معالجة الطقطقة والتشويه الرقمي")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        lbl = QLabel("يقوم هذا الفلتر بفحص المسار الصوتي وتحديد القمم المبتورة رقمياً وترميمها بالإضافة لحذف النقر والطقطقة الناتجة عن الميكروفون.")
        lbl.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        lbl.setWordWrap(True)
        vbox.addWidget(lbl)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 19. Silence Remove
    # -------------------------------------------------------------
    def _build_silence_remove_options(self, parent_layout):
        gb = QGroupBox("إعدادات حذف فترات الصمت (Truncate Silence)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("عتبة اعتبار الصوت صمتاً:"))
        self.sr_thresh_spin = QSpinBox()
        self.sr_thresh_spin.setRange(-60, -25)
        self.sr_thresh_spin.setValue(-45)
        self.sr_thresh_spin.setSuffix(" dB")
        self.sr_thresh_spin.valueChanged.connect(self.options_changed)
        h1.addWidget(self.sr_thresh_spin, 1)
        vbox.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("أقل مدة صمت يتم حذفها:"))
        self.sr_dur_spin = QDoubleSpinBox()
        self.sr_dur_spin.setRange(0.2, 5.0)
        self.sr_dur_spin.setValue(0.8)
        self.sr_dur_spin.setSuffix(" ثانية")
        self.sr_dur_spin.valueChanged.connect(self.options_changed)
        h2.addWidget(self.sr_dur_spin, 1)
        vbox.addLayout(h2)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 20. Podcast Voice Enhancer
    # -------------------------------------------------------------
    def _build_podcast_enhancer_options(self, parent_layout):
        gb = QGroupBox("معزز البودكاست والكلام بنقرة واحدة")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("اختر طابع المعالجة المفضل:"))
        self.podcast_profile_combo = QComboBox()
        self.podcast_profile_combo.addItem("بودكاست نقي ومشرق (Crisp Podcast)", "crisp_podcast")
        self.podcast_profile_combo.addItem("صوت إذاعي دافئ (Warm Broadcast Voice)", "warm_speech")
        self.podcast_profile_combo.currentIndexChanged.connect(self.options_changed)
        vbox.addWidget(self.podcast_profile_combo)

        desc = QLabel("✨ تتضمن هذه السلسلة التلقائية: إزالة وشيش الخلفية + تصفية هواء الميكروفون (HPF 80Hz) + إبراز نبرة الصوت البشري + موازنة ديناميكية + معايرة -16 LUFS القياسية.")
        desc.setStyleSheet("color: #FFB74D; font-size: 11px; line-height: 1.4;")
        desc.setWordWrap(True)
        vbox.addWidget(desc)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 21. Graphic EQ
    # -------------------------------------------------------------
    def _build_eq_options(self, parent_layout):
        gb = QGroupBox("المعادل الصوتي (Graphic EQ)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("الإعداد المسبق:"))
        self.eq_preset_combo = QComboBox()
        for k, v in EQ_PRESETS.items():
            self.eq_preset_combo.addItem(v["label"], k)
        self.eq_preset_combo.currentIndexChanged.connect(self._on_eq_preset_changed)
        vbox.addWidget(self.eq_preset_combo)

        # Bass
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("البيز (Bass 100Hz):"))
        self.bass_slider = QSlider(Qt.Horizontal)
        self.bass_slider.setRange(-12, 12)
        self.bass_slider.setValue(0)
        self.bass_lbl = QLabel("0 dB")
        self.bass_slider.valueChanged.connect(lambda v: self.bass_lbl.setText(f"{v:+} dB"))
        self.bass_slider.valueChanged.connect(self.options_changed)
        h1.addWidget(self.bass_slider, 1)
        h1.addWidget(self.bass_lbl)
        vbox.addLayout(h1)

        # Mid
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("المتوسط (Mid 1kHz):"))
        self.mid_slider = QSlider(Qt.Horizontal)
        self.mid_slider.setRange(-12, 12)
        self.mid_slider.setValue(0)
        self.mid_lbl = QLabel("0 dB")
        self.mid_slider.valueChanged.connect(lambda v: self.mid_lbl.setText(f"{v:+} dB"))
        self.mid_slider.valueChanged.connect(self.options_changed)
        h2.addWidget(self.mid_slider, 1)
        h2.addWidget(self.mid_lbl)
        vbox.addLayout(h2)

        # Treble
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("التريبل (Treble 10kHz):"))
        self.treble_slider = QSlider(Qt.Horizontal)
        self.treble_slider.setRange(-12, 12)
        self.treble_slider.setValue(0)
        self.treble_lbl = QLabel("0 dB")
        self.treble_slider.valueChanged.connect(lambda v: self.treble_lbl.setText(f"{v:+} dB"))
        self.treble_slider.valueChanged.connect(self.options_changed)
        h3.addWidget(self.treble_slider, 1)
        h3.addWidget(self.treble_lbl)
        vbox.addLayout(h3)

        parent_layout.addWidget(gb)

    def _on_eq_preset_changed(self):
        k = self.eq_preset_combo.currentData()
        if k in EQ_PRESETS:
            cfg = EQ_PRESETS[k]
            self.bass_slider.setValue(cfg["bass"])
            self.mid_slider.setValue(cfg["mid"])
            self.treble_slider.setValue(cfg["treble"])
        self.options_changed.emit()

    # -------------------------------------------------------------
    # 22. Filters (HPF / LPF)
    # -------------------------------------------------------------
    def _build_filters_options(self, parent_layout):
        gb = QGroupBox("الفلاتر الصوتية (Acoustic Filters)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("نوع الفلتر:"))
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItem("تمرير الترددات العالية High-Pass (عزل هواء الميكروفون)", "highpass")
        self.filter_type_combo.addItem("تمرير الترددات المنخفضة Low-Pass (كتم الصرير والحدة)", "lowpass")
        self.filter_type_combo.currentIndexChanged.connect(self.options_changed)
        h1.addWidget(self.filter_type_combo, 1)
        vbox.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("تردد القطع (Cutoff Hz):"))
        self.cutoff_spin = QSpinBox()
        self.cutoff_spin.setRange(20, 20000)
        self.cutoff_spin.setValue(120)
        self.cutoff_spin.setSuffix(" Hz")
        self.cutoff_spin.valueChanged.connect(self.options_changed)
        h2.addWidget(self.cutoff_spin, 1)
        vbox.addLayout(h2)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 23. Bass & Treble Boost
    # -------------------------------------------------------------
    def _build_bass_treble_options(self, parent_layout):
        gb = QGroupBox("تعزيز البيز والتريبل السريع")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("تعزيز البيز (Bass Boost):"))
        self.quick_bass_slider = QSlider(Qt.Horizontal)
        self.quick_bass_slider.setRange(-10, 10)
        self.quick_bass_slider.setValue(3)
        self.quick_bass_lbl = QLabel("+3 dB")
        self.quick_bass_slider.valueChanged.connect(lambda v: self.quick_bass_lbl.setText(f"{v:+} dB"))
        self.quick_bass_slider.valueChanged.connect(self.options_changed)
        h1.addWidget(self.quick_bass_slider, 1)
        h1.addWidget(self.quick_bass_lbl)
        vbox.addLayout(h1)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("تعزيز التريبل (Treble Boost):"))
        self.quick_treble_slider = QSlider(Qt.Horizontal)
        self.quick_treble_slider.setRange(-10, 10)
        self.quick_treble_slider.setValue(3)
        self.quick_treble_lbl = QLabel("+3 dB")
        self.quick_treble_slider.valueChanged.connect(lambda v: self.quick_treble_lbl.setText(f"{v:+} dB"))
        self.quick_treble_slider.valueChanged.connect(self.options_changed)
        h2.addWidget(self.quick_treble_slider, 1)
        h2.addWidget(self.quick_treble_lbl)
        vbox.addLayout(h2)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 24. Speed & Tempo
    # -------------------------------------------------------------
    def _build_speed_options(self, parent_layout):
        gb = QGroupBox("تغيير سرعة الصوت (Tempo)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("معامل السرعة:"))
        h = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200) # 0.5x to 2.0x
        self.speed_slider.setValue(125)
        self.speed_lbl = QLabel("1.25x")
        self.speed_slider.valueChanged.connect(lambda v: self.speed_lbl.setText(f"{v/100:.2f}x"))
        self.speed_slider.valueChanged.connect(self.options_changed)
        h.addWidget(self.speed_slider, 1)
        h.addWidget(self.speed_lbl)
        vbox.addLayout(h)

        self.preserve_pitch_cb = QCheckBox("الحفاظ على طبقة ونبرة الصوت الطبيعية دون تغيير نبرة المتحدث")
        self.preserve_pitch_cb.setChecked(True)
        self.preserve_pitch_cb.toggled.connect(self.options_changed)
        vbox.addWidget(self.preserve_pitch_cb)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 25. Pitch Shift
    # -------------------------------------------------------------
    def _build_pitch_options(self, parent_layout):
        gb = QGroupBox("تغيير طبقة الصوت (Pitch Shift)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("مقدار التغيير بالأنصاف النغمية (Semitones):"))
        h = QHBoxLayout()
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-12, 12)
        self.pitch_slider.setValue(2)
        self.pitch_lbl = QLabel("+2 Semitones")
        self.pitch_slider.valueChanged.connect(lambda v: self.pitch_lbl.setText(f"{v:+} Semitones"))
        self.pitch_slider.valueChanged.connect(self.options_changed)
        h.addWidget(self.pitch_slider, 1)
        h.addWidget(self.pitch_lbl)
        vbox.addLayout(h)

        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 26. Reverse
    # -------------------------------------------------------------
    def _build_reverse_options(self, parent_layout):
        gb = QGroupBox("عكس الصوت للخلف")
        vbox = QVBoxLayout(gb)
        lbl = QLabel("يقوم هذا الخيار بعكس المقطع الصوتي ليعمل من النهاية إلى البداية دون فقدان الجودة.")
        lbl.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        vbox.addWidget(lbl)
        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 27. Channel Routing
    # -------------------------------------------------------------
    def _build_channels_options(self, parent_layout):
        gb = QGroupBox("توجيه القنوات والستيريو")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(10)

        vbox.addWidget(QLabel("العملية المطلوبة:"))
        self.channel_mode_combo = QComboBox()
        self.channel_mode_combo.addItem("التحويل من ستيريو لمونو (Downmix to Mono)", "stereo_to_mono")
        self.channel_mode_combo.addItem("التحويل من مونو لستيريو مزدوج (Dual Mono to Stereo)", "mono_to_stereo")
        self.channel_mode_combo.addItem("عكس السماعتين اليمنى واليسرى (Swap L/R)", "swap_lr")
        self.channel_mode_combo.addItem("موازنة وميلان الستيريو (Stereo Pan)", "pan")
        self.channel_mode_combo.currentIndexChanged.connect(self.options_changed)
        vbox.addWidget(self.channel_mode_combo)

        # Pan slider
        h = QHBoxLayout()
        h.addWidget(QLabel("موازنة الـ Pan (يسار ← يمين):"))
        self.pan_slider = QSlider(Qt.Horizontal)
        self.pan_slider.setRange(-100, 100)
        self.pan_slider.setValue(0)
        self.pan_lbl = QLabel("الوسط (Center)")
        self.pan_slider.valueChanged.connect(self._on_pan_changed)
        self.pan_slider.valueChanged.connect(self.options_changed)
        h.addWidget(self.pan_slider, 1)
        h.addWidget(self.pan_lbl)
        vbox.addLayout(h)

        parent_layout.addWidget(gb)

    def _on_pan_changed(self, v: int):
        if v == 0:
            self.pan_lbl.setText("الوسط (Center)")
        elif v < 0:
            self.pan_lbl.setText(f"{abs(v)}% يسار")
        else:
            self.pan_lbl.setText(f"{v}% يمين")

    # -------------------------------------------------------------
    # 28. Extract Channels
    # -------------------------------------------------------------
    def _build_extract_channels_options(self, parent_layout):
        gb = QGroupBox("فصل القنوات الصوتية")
        vbox = QVBoxLayout(gb)
        lbl = QLabel("سيتم استخراج القناة اليسرى كملف مستقل والقناة اليمنى كملف مستقل تماماً في نفس مجلد الإخراج المحدد.")
        lbl.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        lbl.setWordWrap(True)
        vbox.addWidget(lbl)
        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 29. Metadata & Tags
    # -------------------------------------------------------------
    def _build_metadata_options(self, parent_layout):
        gb = QGroupBox("محرر البيانات الوصفية والغلاف (ID3 Tags)")
        vbox = QVBoxLayout(gb)
        vbox.setSpacing(8)

        # Artist
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("الفنان / المنشد:"))
        self.meta_artist_edit = QLineEdit()
        self.meta_artist_edit.textChanged.connect(self.options_changed)
        h1.addWidget(self.meta_artist_edit, 1)
        vbox.addLayout(h1)

        # Album
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("الألبوم:"))
        self.meta_album_edit = QLineEdit()
        self.meta_album_edit.textChanged.connect(self.options_changed)
        h2.addWidget(self.meta_album_edit, 1)
        vbox.addLayout(h2)

        # Year & Genre
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("السنة:"))
        self.meta_year_edit = QLineEdit()
        self.meta_year_edit.setPlaceholderText("2026")
        self.meta_year_edit.textChanged.connect(self.options_changed)
        h3.addWidget(self.meta_year_edit, 1)

        h3.addWidget(QLabel("النوع:"))
        self.meta_genre_edit = QLineEdit()
        self.meta_genre_edit.textChanged.connect(self.options_changed)
        h3.addWidget(self.meta_genre_edit, 1)
        vbox.addLayout(h3)

        # Cover Art Picker
        h4 = QHBoxLayout()
        h4.addWidget(QLabel("صورة الغلاف:"))
        self.cover_path_edit = QLineEdit()
        self.cover_path_edit.setPlaceholderText("اختر صورة غلاف (JPG, PNG)...")
        h4.addWidget(self.cover_path_edit, 1)

        browse_cover_btn = QPushButton("استعراض...")
        browse_cover_btn.clicked.connect(self._browse_cover)
        h4.addWidget(browse_cover_btn)
        vbox.addLayout(h4)

        parent_layout.addWidget(gb)

    def _browse_cover(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر صورة الغلاف", "", "Images (*.jpg *.jpeg *.png *.webp)")
        if f:
            self.cover_path_edit.setText(f)
            self.options_changed.emit()

    # -------------------------------------------------------------
    # 30. Analysis
    # -------------------------------------------------------------
    def _build_analysis_options(self, parent_layout):
        gb = QGroupBox("الفحص الهندسي للصوت")
        vbox = QVBoxLayout(gb)
        lbl = QLabel("انقر على زر 'فحص متقدم' لمعاينة المخطط الموجي (Waveform)، المخطط الطيفي (Spectrogram)، وقياسات LUFS الحقيقية بدقة هندسية كاملة.")
        lbl.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        lbl.setWordWrap(True)
        vbox.addWidget(lbl)
        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # 31. Workflow
    # -------------------------------------------------------------
    def _build_workflow_options(self, parent_layout):
        gb = QGroupBox("سير العمل الصوتي المخصص")
        vbox = QVBoxLayout(gb)
        lbl = QLabel("قم بإعداد سلسلة العمل المخصصة بالتبديل إلى تبويب 'منشئ سلاسل المعالجة' بالأعلى لتخصيص الخطوات وحفظها كقالب.")
        lbl.setStyleSheet("color: #00A4EF; font-size: 12px;")
        lbl.setWordWrap(True)
        vbox.addWidget(lbl)
        parent_layout.addWidget(gb)

    def _build_generic_options(self, parent_layout):
        gb = QGroupBox("خيارات المعالجة")
        vbox = QVBoxLayout(gb)
        lbl = QLabel("الأداة جاهزة للتنفيذ على الملفات المحددة.")
        lbl.setStyleSheet("color: #888888; font-size: 12px;")
        vbox.addWidget(lbl)
        parent_layout.addWidget(gb)

    # -------------------------------------------------------------
    # Output Options Dictionary
    # -------------------------------------------------------------
    def get_options(self) -> Dict[str, Any]:
        """Returns normalized parameter dictionary ready for execution."""
        opt_type = self.tool.options_type
        opts: Dict[str, Any] = {}

        if opt_type == "convert":
            opts["format"] = self.fmt_combo.currentData()
            opts["bitrate"] = self.br_combo.currentData()
            opts["sample_rate"] = self.sr_combo.currentData()
            opts["channels"] = self.ch_combo.currentData()
            opts["vbr_cbr"] = self.vbr_cbr_combo.currentData()

        elif opt_type == "compress":
            opts["preset"] = self.compress_preset_combo.currentData()
            opts["custom_bitrate"] = f"{self.compress_br_slider.value()}k"

        elif opt_type == "target_size":
            opts["target_mb"] = self.target_size_spin.value()

        elif opt_type == "trim":
            opts["start_time"] = self.trim_start_edit.text().strip() or "00:00:00"
            opts["end_time"] = self.trim_end_edit.text().strip() or None

        elif opt_type == "split":
            opts["segment_seconds"] = self.split_dur_spin.value() * 60

        elif opt_type == "silence_split":
            opts["threshold_db"] = float(self.silence_thresh_spin.value())
            opts["min_silence_dur"] = float(self.silence_dur_spin.value())

        elif opt_type == "merge":
            opts["output_filename"] = self.merge_filename_edit.text().strip() or "merged_audio.mp3"

        elif opt_type == "crossfade":
            opts["crossfade_dur"] = float(self.crossfade_dur_slider.value())
            opts["curve"] = self.crossfade_curve_combo.currentData()

        elif opt_type == "fade":
            opts["fade_in_sec"] = self.fade_in_spin.value()
            opts["fade_out_sec"] = self.fade_out_spin.value()

        elif opt_type == "loudness":
            opts["target_lufs"] = self.lufs_spin.value()
            opts["true_peak"] = self.tp_spin.value()
            opts["dual_pass"] = self.dual_pass_cb.isChecked()

        elif opt_type == "peak_norm":
            opts["peak_db"] = self.peak_spin.value()

        elif opt_type == "volume":
            opts["gain_db"] = float(self.vol_gain_slider.value())

        elif opt_type == "compressor":
            opts["threshold_db"] = float(self.comp_thresh_spin.value())
            opts["ratio"] = float(self.comp_ratio_spin.value())
            opts["makeup_gain_db"] = float(self.comp_makeup_spin.value())

        elif opt_type == "limiter":
            opts["limit_db"] = float(self.limiter_spin.value())

        elif opt_type == "noise_gate":
            opts["threshold_db"] = float(self.gate_thresh_spin.value())

        elif opt_type == "denoise":
            opts["nr_level_db"] = float(self.denoise_combo.currentData())

        elif opt_type == "hum_removal":
            opts["freq"] = int(self.hum_combo.currentData())

        elif opt_type == "silence_remove":
            opts["threshold_db"] = float(self.sr_thresh_spin.value())
            opts["min_dur_sec"] = float(self.sr_dur_spin.value())

        elif opt_type == "podcast_enhancer":
            opts["profile"] = self.podcast_profile_combo.currentData()

        elif opt_type == "eq":
            opts["bass_db"] = float(self.bass_slider.value())
            opts["mid_db"] = float(self.mid_slider.value())
            opts["treble_db"] = float(self.treble_slider.value())

        elif opt_type == "filters":
            opts["filter_type"] = self.filter_type_combo.currentData()
            opts["cutoff_freq"] = int(self.cutoff_spin.value())

        elif opt_type == "bass_treble":
            opts["bass_gain"] = float(self.quick_bass_slider.value())
            opts["treble_gain"] = float(self.quick_treble_slider.value())

        elif opt_type == "speed":
            opts["speed_factor"] = self.speed_slider.value() / 100.0
            opts["preserve_pitch"] = self.preserve_pitch_cb.isChecked()

        elif opt_type == "pitch":
            opts["semitones"] = float(self.pitch_slider.value())

        elif opt_type == "channels":
            opts["mode"] = self.channel_mode_combo.currentData()
            opts["pan_val"] = self.pan_slider.value() / 100.0

        elif opt_type == "metadata":
            opts["tags"] = {
                "artist": self.meta_artist_edit.text().strip(),
                "album": self.meta_album_edit.text().strip(),
                "date": self.meta_year_edit.text().strip(),
                "genre": self.meta_genre_edit.text().strip(),
            }
            opts["cover_art_path"] = self.cover_path_edit.text().strip() or None

        return opts
