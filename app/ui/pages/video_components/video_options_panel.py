# -*- coding: utf-8 -*-
"""
SINAX Contextual Video Options Panel
Dynamic options widget adapting to each video tool type and schema
(Compression, Target Size, Formats, Remux, Resize/Shorts, Trim, Remove Segment, Split, Merge,
Audio Extraction, Mute, Mix, Volume Normalization, Speed, Rotate, Watermark, GIF, Storyboard, Enhance, Workflow).
"""

from pathlib import Path
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

from app.services.video.hardware_detector import hardware_detector
from app.services.video.video_registry import VideoToolDefinition
from app.ui.pages.video_components.video_workflow_builder import VideoWorkflowBuilderWidget


class VideoOptionsPanel(QWidget):
    """Dynamic parameter configuration panel for video tools."""

    options_changed = Signal()

    def __init__(self, tool: VideoToolDefinition, parent=None):
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
                padding: 0 5px;
                color: #60CDFF;
            }
            QRadioButton {
                color: #E8E8E8;
                font-size: 12px;
                padding: 4px;
            }
            QRadioButton:hover { color: #FFFFFF; }
            QLabel { color: #E0E0E0; font-size: 12px; }
            QCheckBox { color: #E0E0E0; font-size: 12px; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 5px 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        opt_type = self.tool.options_type
        tool_id = self.tool.id

        # -------------------------------------------------------------
        # 1. COMPRESSION
        # -------------------------------------------------------------
        if opt_type == "compress" or "compress" in tool_id:
            if opt_type == "target_size" or "target_size" in tool_id:
                grp = QGroupBox("تحديد الحجم النهائي المطلوب")
                gl = QVBoxLayout(grp)
                gl.setSpacing(10)

                gl.addWidget(QLabel("أدخل أقصى حجم مستهدف للملف النهائي:"))
                s_row = QHBoxLayout()
                self.spin_target_mb = QSpinBox()
                self.spin_target_mb.setRange(1, 10000)
                self.spin_target_mb.setValue(25)
                self.spin_target_mb.setSuffix(" ميجابايت (MB)")
                s_row.addWidget(self.spin_target_mb, 1)
                gl.addLayout(s_row)

                # Quick presets
                gl.addWidget(QLabel("خيارات سريعة:"))
                q_row = QHBoxLayout()
                for size_val, label in [(10, "10 MB"), (16, "16 MB (واتساب)"), (25, "25 MB (إيميل)"), (50, "50 MB"), (100, "100 MB")]:
                    btn = QPushButton(label)
                    btn.setStyleSheet("background-color: #333333; color: #60CDFF; border-radius: 4px; padding: 4px;")
                    btn.clicked.connect(lambda _, s=size_val: self.spin_target_mb.setValue(s))
                    q_row.addWidget(btn)
                gl.addLayout(q_row)

                info = QLabel("يقوم البرنامج بحساب معدل البت المناسب بدقة وتطبيق الضغط للوصول إلى الحجم المستهدف.")
                info.setWordWrap(True)
                info.setStyleSheet("color: #888888; font-size: 11px;")
                gl.addWidget(info)
                layout.addWidget(grp)

            else:
                grp = QGroupBox("خيارات ضغط الفيديو")
                gl = QVBoxLayout(grp)
                gl.setSpacing(8)

                self.preset_group = QButtonGroup(self)
                self.rb_light = QRadioButton("ضغط خفيف (جودة فائقة - CRF 20)")
                self.rb_balanced = QRadioButton("ضغط متوازن (موصى به - CRF 24)")
                self.rb_strong = QRadioButton("ضغط قوي (حجم أصغر - CRF 28)")
                self.rb_max = QRadioButton("أقصى ضغط (CRF 32)")

                self.rb_balanced.setChecked(True)
                for rb in (self.rb_light, self.rb_balanced, self.rb_strong, self.rb_max):
                    self.preset_group.addButton(rb)
                    gl.addWidget(rb)

                self.chk_gpu = QCheckBox("تفعيل تسريع بطاقة الشاشة (Hardware Acceleration)")
                self.chk_gpu.setChecked(hardware_detector.has_gpu_acceleration())
                gl.addWidget(self.chk_gpu)

                layout.addWidget(grp)

        # -------------------------------------------------------------
        # 2. TARGET SIZE
        # -------------------------------------------------------------
        elif opt_type == "target_size":
            grp = QGroupBox("تحديد الحجم النهائي المطلوب")
            gl = QVBoxLayout(grp)
            gl.setSpacing(10)

            gl.addWidget(QLabel("أدخل أقصى حجم مستهدف للملف النهائي:"))
            s_row = QHBoxLayout()
            self.spin_target_mb = QSpinBox()
            self.spin_target_mb.setRange(1, 10000)
            self.spin_target_mb.setValue(25)
            self.spin_target_mb.setSuffix(" ميجابايت (MB)")
            s_row.addWidget(self.spin_target_mb, 1)
            gl.addLayout(s_row)

            gl.addWidget(QLabel("خيارات سريعة:"))
            q_row = QHBoxLayout()
            for size_val, label in [(10, "10 MB"), (16, "16 MB (واتساب)"), (25, "25 MB (إيميل)"), (50, "50 MB"), (100, "100 MB")]:
                btn = QPushButton(label)
                btn.setStyleSheet("background-color: #333333; color: #60CDFF; border-radius: 4px; padding: 4px;")
                btn.clicked.connect(lambda _, s=size_val: self.spin_target_mb.setValue(s))
                q_row.addWidget(btn)
            gl.addLayout(q_row)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 3. FORMAT CONVERSION
        # -------------------------------------------------------------
        elif opt_type == "convert":
            grp = QGroupBox("خيارات تحويل الصيغة والترميز")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("صيغة الحاوية المستهدفة:"))
            self.combo_fmt = QComboBox()
            for fmt in ["mp4", "mkv", "webm", "mov", "avi", "flv", "wmv", "ts"]:
                self.combo_fmt.addItem(fmt.upper(), fmt)
            gl.addWidget(self.combo_fmt)

            gl.addWidget(QLabel("ترميز الفيديو (Video Codec):"))
            self.combo_vcodec = QComboBox()
            self.combo_vcodec.addItem("تلقائي (الأفضل والموصى به)", "auto")
            self.combo_vcodec.addItem("H.264 / AVC (توافق واسع عالمياً)", "h264")
            self.combo_vcodec.addItem("H.265 / HEVC (ضغط أعلى وجودة ممتازة)", "hevc")
            self.combo_vcodec.addItem("VP9 (مثالي للويب)", "vp9")
            self.combo_vcodec.addItem("نسخ بدون إعادة ترميز (Copy)", "copy")
            gl.addWidget(self.combo_vcodec)

            gl.addWidget(QLabel("ترميز الصوت (Audio Codec):"))
            self.combo_acodec = QComboBox()
            self.combo_acodec.addItem("تلقائي (AAC / Opus)", "auto")
            self.combo_acodec.addItem("AAC (192 kb/s)", "aac")
            self.combo_acodec.addItem("MP3 (libmp3lame)", "libmp3lame")
            self.combo_acodec.addItem("نسخ مباشر (Copy)", "copy")
            gl.addWidget(self.combo_acodec)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 4. FAST REMUX
        # -------------------------------------------------------------
        elif opt_type in ("remux", "fast_remux"):
            grp = QGroupBox("نقل الحاوية السريع (Fast Remux)")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("الصيغة الهدف:"))
            self.combo_remux_fmt = QComboBox()
            for fmt in ["mp4", "mkv", "mov", "webm"]:
                self.combo_remux_fmt.addItem(fmt.upper(), fmt)
            gl.addWidget(self.combo_remux_fmt)

            info = QLabel("⚡ عملية فائقة السرعة تستغرق ثوانٍ معدودة بدون فقد أي ذرة جودة وبدون استهلاك المعالج.")
            info.setStyleSheet("color: #6CCB5F; font-size: 11px;")
            gl.addWidget(info)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 5. RESIZE & SOCIAL FORMATS
        # -------------------------------------------------------------
        elif opt_type in ("resize", "social_presets", "crop", "black_bars"):
            grp = QGroupBox("خيارات تغيير المقاس والأبعاد")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("الدقة المستهدفة:"))
            self.combo_res = QComboBox()
            self.combo_res.addItem("1080p Full HD (1920x1080)", "1080p")
            self.combo_res.addItem("720p HD (1280x720)", "720p")
            self.combo_res.addItem("4K Ultra HD (3840x2160)", "4k")
            self.combo_res.addItem("480p SD (854x480)", "480p")
            self.combo_res.addItem("Shorts / Reels / TikTok (9:16 طولي)", "shorts_9_16")
            self.combo_res.addItem("مربع إنستغرام (1:1 Square)", "square_1_1")
            if opt_type == "social_presets":
                self.combo_res.setCurrentIndex(4)  # Shorts 9:16
            gl.addWidget(self.combo_res)

            gl.addWidget(QLabel("طريقة التعديل (Fit Mode):"))
            self.combo_mode = QComboBox()
            self.combo_mode.addItem("ملاءمة مع الحفاظ على النسبة (Fit)", "fit")
            self.combo_mode.addItem("خلفية ضبابية للمقاطع الطولية (Vertical Blur)", "vertical_blur")
            self.combo_mode.addItem("إضافة حواف سوداء (Letterbox Pad)", "pad")
            self.combo_mode.addItem("تمديد الشاشة (Stretch)", "stretch")
            if opt_type == "social_presets":
                self.combo_mode.setCurrentIndex(1)  # Vertical Blur
            gl.addWidget(self.combo_mode)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 6. TRIM & CUT
        # -------------------------------------------------------------
        elif opt_type == "trim":
            grp = QGroupBox("خيارات القص والاقتطاع")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("وقت البدء (HH:MM:SS):"))
            self.txt_trim_start = QLineEdit("00:00:00")
            gl.addWidget(self.txt_trim_start)

            gl.addWidget(QLabel("وقت الانتهاء (HH:MM:SS):"))
            self.txt_trim_end = QLineEdit("00:01:00")
            gl.addWidget(self.txt_trim_end)

            self.rb_trim_accurate = QRadioButton("قص دقيق بالملي ثانية (إعادة تشفير)")
            self.rb_trim_fast = QRadioButton("قص سريع فوري (نسخ مسارات بدون تشفير)")
            self.rb_trim_accurate.setChecked(True)
            gl.addWidget(self.rb_trim_accurate)
            gl.addWidget(self.rb_trim_fast)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 7. CUT MIDDLE / REMOVE SEGMENT
        # -------------------------------------------------------------
        elif opt_type in ("cut_middle", "remove_segment"):
            grp = QGroupBox("حذف جزء من المنتصف ودمج الباقي")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("بداية الجزء المراد حذفه:"))
            self.txt_cut_start = QLineEdit("00:00:10")
            gl.addWidget(self.txt_cut_start)

            gl.addWidget(QLabel("نهاية الجزء المراد حذفه:"))
            self.txt_cut_end = QLineEdit("00:00:20")
            gl.addWidget(self.txt_cut_end)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 8. SPLIT VIDEO
        # -------------------------------------------------------------
        elif opt_type == "split":
            grp = QGroupBox("خيارات تقسيم وتجزئة الفيديو")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            self.combo_split_mode = QComboBox()
            self.combo_split_mode.addItem("تقسيم حسب مدة زمنية محددة", "duration")
            self.combo_split_mode.addItem("تقسيم إلى عدد أجزاء متساوية", "parts")
            gl.addWidget(self.combo_split_mode)

            self.spin_split_val = QSpinBox()
            self.spin_split_val.setRange(1, 3600)
            self.spin_split_val.setValue(60)
            self.spin_split_val.setSuffix(" ثانية")
            gl.addWidget(self.spin_split_val)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 9. MERGE VIDEOS
        # -------------------------------------------------------------
        elif opt_type == "merge":
            grp = QGroupBox("خيارات دمج المقاطع")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("اسم الملف المدمج النهائي:"))
            self.txt_merge_name = QLineEdit("merged_video.mp4")
            gl.addWidget(self.txt_merge_name)

            self.chk_merge_reencode = QCheckBox("إعادة التشفير لتوحيد المقاسات والترميزات")
            self.chk_merge_reencode.setChecked(True)
            gl.addWidget(self.chk_merge_reencode)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 10. MUTE VIDEO
        # -------------------------------------------------------------
        elif opt_type == "mute":
            grp = QGroupBox("خيارات كتم وإزالة الصوت")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)
            info = QLabel("سيتم كتم وإزالة مسارات الصوت نهائياً من الفيديو بدون المساس بجودة الصورة الأصلية.")
            info.setStyleSheet("color: #60CDFF; font-size: 12px;")
            info.setWordWrap(True)
            gl.addWidget(info)
            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 11. EXTRACT AUDIO
        # -------------------------------------------------------------
        elif opt_type == "extract_audio":
            grp = QGroupBox("خيارات استخراج الصوت")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("صيغة الصوت:"))
            self.combo_audio_fmt = QComboBox()
            for afmt in ["mp3", "wav", "aac", "flac", "ogg", "opus"]:
                self.combo_audio_fmt.addItem(afmt.upper(), afmt)
            gl.addWidget(self.combo_audio_fmt)

            gl.addWidget(QLabel("معدل البت للصوت:"))
            self.combo_audio_br = QComboBox()
            for br in ["128k", "192k", "256k", "320k"]:
                self.combo_audio_br.addItem(f"{br} bps", br)
            self.combo_audio_br.setCurrentIndex(1)
            gl.addWidget(self.combo_audio_br)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 12. REPLACE / MIX AUDIO
        # -------------------------------------------------------------
        elif opt_type == "replace_audio":
            grp = QGroupBox("استبدال أو دمج مقطع صوتي")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("ملف الصوت الجديد:"))
            aud_row = QHBoxLayout()
            self.txt_audio_file = QLineEdit()
            self.txt_audio_file.setPlaceholderText("اختر ملف صوتي (MP3, WAV, AAC...)")
            aud_row.addWidget(self.txt_audio_file, 1)

            btn_browse_aud = QPushButton("استعراض...")
            btn_browse_aud.setStyleSheet("background-color: #333333; color: #FFF;")
            btn_browse_aud.clicked.connect(self._browse_audio)
            aud_row.addWidget(btn_browse_aud)
            gl.addLayout(aud_row)

            gl.addWidget(QLabel("وضع الصوت:"))
            self.combo_mix_mode = QComboBox()
            self.combo_mix_mode.addItem("استبدال الصوت الأصلي بالكامل", "replace")
            self.combo_mix_mode.addItem("دمج الصوت الجديد كخلفية موسيقية (Mix)", "mix")
            gl.addWidget(self.combo_mix_mode)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 13. VOLUME & LOUDNORM
        # -------------------------------------------------------------
        elif opt_type in ("volume", "volume_normalize"):
            grp = QGroupBox("خيارات موازنة وتعديل مستوى الصوت")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            self.combo_vol_mode = QComboBox()
            self.combo_vol_mode.addItem("الموازنة القياسية العالمية (EBU R128 Loudnorm)", "ebu_r128")
            self.combo_vol_mode.addItem("مضاعفة / تخفيض الصوت بنسبة محددة", "scale")
            gl.addWidget(self.combo_vol_mode)

            v_row = QHBoxLayout()
            v_row.addWidget(QLabel("معامل الصوت (عند اختيار النسبة):"))
            self.spin_vol_factor = QDoubleSpinBox()
            self.spin_vol_factor.setRange(0.1, 5.0)
            self.spin_vol_factor.setValue(1.5)
            self.spin_vol_factor.setSingleStep(0.1)
            v_row.addWidget(self.spin_vol_factor)
            gl.addLayout(v_row)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 14. SPEED & REVERSE
        # -------------------------------------------------------------
        elif opt_type in ("speed", "reverse"):
            grp = QGroupBox("خيارات التحكم في السرعة والاتجاه")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("معامل السرعة:"))
            self.combo_speed = QComboBox()
            for spd, lbl in [
                (0.25, "0.25x (بطيء جداً)"),
                (0.5, "0.5x (نصف السرعة)"),
                (1.25, "1.25x"),
                (1.5, "1.5x"),
                (2.0, "2.0x (ضعف السرعة)"),
                (4.0, "4.0x (تسريع فائق)"),
            ]:
                self.combo_speed.addItem(lbl, spd)
            self.combo_speed.setCurrentIndex(4)  # 2.0x
            gl.addWidget(self.combo_speed)

            self.chk_reverse = QCheckBox("عكس اتجاه الفيديو والصوت (Reverse)")
            if opt_type == "reverse" or tool_id == "reverse_video":
                self.chk_reverse.setChecked(True)
            gl.addWidget(self.chk_reverse)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 15. ROTATE & FLIP
        # -------------------------------------------------------------
        elif opt_type == "rotate":
            grp = QGroupBox("خيارات التدوير والانعكاس")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("زاوية التدوير:"))
            self.combo_rotate = QComboBox()
            self.combo_rotate.addItem("بدون تدوير (0°)", 0)
            self.combo_rotate.addItem("90° مع اتجاه عقارب الساعة", 90)
            self.combo_rotate.addItem("180° رأساً على عقب", 180)
            self.combo_rotate.addItem("270° عكس اتجاه عقارب الساعة", 270)
            self.combo_rotate.setCurrentIndex(1)
            gl.addWidget(self.combo_rotate)

            self.chk_flip_h = QCheckBox("عكس أفقي (مرآة)")
            self.chk_flip_v = QCheckBox("عكس رأسي")
            gl.addWidget(self.chk_flip_h)
            gl.addWidget(self.chk_flip_v)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 16. WATERMARK
        # -------------------------------------------------------------
        elif opt_type == "watermark":
            grp = QGroupBox("خيارات العلامة المائية")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("النص المكتوب:"))
            self.txt_wm = QLineEdit("SINAX")
            gl.addWidget(self.txt_wm)

            gl.addWidget(QLabel("شعار صورة اختياري (PNG):"))
            logo_row = QHBoxLayout()
            self.txt_logo = QLineEdit()
            logo_row.addWidget(self.txt_logo, 1)
            btn_logo = QPushButton("استعراض...")
            btn_logo.clicked.connect(self._browse_logo)
            logo_row.addWidget(btn_logo)
            gl.addLayout(logo_row)

            gl.addWidget(QLabel("الموضع:"))
            self.combo_wm_pos = QComboBox()
            self.combo_wm_pos.addItem("أسفل اليمين (موصى به)", "bottom_right")
            self.combo_wm_pos.addItem("أسفل اليسار", "bottom_left")
            self.combo_wm_pos.addItem("أعلى اليمين", "top_right")
            self.combo_wm_pos.addItem("أعلى اليسار", "top_left")
            self.combo_wm_pos.addItem("في المنتصف", "center")
            gl.addWidget(self.combo_wm_pos)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 17. ANIMATED GIF
        # -------------------------------------------------------------
        elif opt_type == "gif":
            grp = QGroupBox("خيارات صناعة الصور المتحركة GIF")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("وقت البدء:"))
            self.txt_gif_start = QLineEdit("00:00:00")
            gl.addWidget(self.txt_gif_start)

            gl.addWidget(QLabel("مدة الـ GIF:"))
            self.spin_gif_dur = QSpinBox()
            self.spin_gif_dur.setRange(1, 60)
            self.spin_gif_dur.setValue(5)
            self.spin_gif_dur.setSuffix(" ثانية")
            gl.addWidget(self.spin_gif_dur)

            gl.addWidget(QLabel("عرض الـ GIF:"))
            self.combo_gif_w = QComboBox()
            for w in [320, 480, 640]:
                self.combo_gif_w.addItem(f"{w} px", w)
            self.combo_gif_w.setCurrentIndex(1)
            gl.addWidget(self.combo_gif_w)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 18. THUMBNAIL / FRAMES
        # -------------------------------------------------------------
        elif opt_type in ("thumbnail", "frames"):
            grp = QGroupBox("خيارات التقاط واستخراج الصور")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            gl.addWidget(QLabel("اللحظة الزمنية (HH:MM:SS):"))
            self.txt_thumb_time = QLineEdit("00:00:02")
            gl.addWidget(self.txt_thumb_time)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 19. CONTACT SHEET / STORYBOARD
        # -------------------------------------------------------------
        elif opt_type == "contact_sheet":
            grp = QGroupBox("خيارات لوحة المعاينة (Contact Sheet)")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            r_row = QHBoxLayout()
            r_row.addWidget(QLabel("الصفوف:"))
            self.spin_cs_rows = QSpinBox()
            self.spin_cs_rows.setValue(3)
            r_row.addWidget(self.spin_cs_rows)

            r_row.addWidget(QLabel("الأعمدة:"))
            self.spin_cs_cols = QSpinBox()
            self.spin_cs_cols.setValue(4)
            r_row.addWidget(self.spin_cs_cols)
            gl.addLayout(r_row)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 20. FILTERS & ENHANCEMENT
        # -------------------------------------------------------------
        elif opt_type in ("filters", "enhance"):
            grp = QGroupBox("خيارات الفلاتر وتحسين الصورة")
            gl = QVBoxLayout(grp)
            gl.setSpacing(8)

            self.chk_denoise = QCheckBox("إزالة التشويش وتنعيم الصورة (Denoise)")
            self.chk_sharpen = QCheckBox("زيادة الحدة والوضوح (Sharpen)")
            gl.addWidget(self.chk_denoise)
            gl.addWidget(self.chk_sharpen)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 21. WORKFLOW PIPELINE BUILDER
        # -------------------------------------------------------------
        elif opt_type == "workflow":
            grp = QGroupBox("بناء خط سير العمل المتسلسل")
            gl = QVBoxLayout(grp)
            self.wf_widget = VideoWorkflowBuilderWidget(self)
            gl.addWidget(self.wf_widget)
            layout.addWidget(grp)

        # -------------------------------------------------------------
        # DEFAULT / GENERAL
        # -------------------------------------------------------------
        else:
            grp = QGroupBox("خيارات العملية")
            gl = QVBoxLayout(grp)
            gl.addWidget(QLabel("لا توجد إعدادات إضافية مطلوبة لهذه العملية."))
            layout.addWidget(grp)

        # -------------------------------------------------------------
        # File Naming Group (Common across all tools)
        # -------------------------------------------------------------
        naming_grp = QGroupBox("تسمية الملفات الناتجة")
        nl = QVBoxLayout(naming_grp)
        nl.setSpacing(6)

        p_row = QHBoxLayout()
        p_row.addWidget(QLabel("بادئة الاسم:"))
        self.txt_prefix = QLineEdit()
        self.txt_prefix.setPlaceholderText("مثال: sinax_")
        p_row.addWidget(self.txt_prefix)
        nl.addLayout(p_row)

        s_row = QHBoxLayout()
        s_row.addWidget(QLabel("لاحقة الاسم:"))
        self.txt_suffix = QLineEdit()
        self.txt_suffix.setPlaceholderText("مثال: _opt")
        s_row.addWidget(self.txt_suffix)
        nl.addLayout(s_row)

        layout.addWidget(naming_grp)
        layout.addStretch(1)

    def _browse_audio(self):
        fn, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف صوتي", "", "Audio Files (*.mp3 *.wav *.aac *.m4a *.flac *.ogg)"
        )
        if fn:
            self.txt_audio_file.setText(fn)

    def _browse_logo(self):
        fn, _ = QFileDialog.getOpenFileName(
            self, "اختر صورة الشعار", "", "Images (*.png *.jpg *.webp)"
        )
        if fn:
            self.txt_logo.setText(fn)

    def get_options(self) -> Dict[str, Any]:
        """Gathers all current configuration options into a dictionary."""
        opts: Dict[str, Any] = {
            "filename_prefix": self.txt_prefix.text().strip(),
            "filename_suffix": self.txt_suffix.text().strip(),
            "use_gpu": True,
        }
        t = self.tool.options_type
        tool_id = self.tool.id

        if t == "compress" or "compress" in tool_id:
            if t == "target_size" or "target_size" in tool_id:
                if hasattr(self, "spin_target_mb"):
                    opts["target_size_mb"] = float(self.spin_target_mb.value())
            else:
                if hasattr(self, "rb_light"):
                    if self.rb_light.isChecked():
                        opts["preset"] = "light"
                        opts["crf"] = 20
                    elif self.rb_strong.isChecked():
                        opts["preset"] = "strong"
                        opts["crf"] = 28
                    elif self.rb_max.isChecked():
                        opts["preset"] = "max"
                        opts["crf"] = 32
                    else:
                        opts["preset"] = "balanced"
                        opts["crf"] = 24
                if hasattr(self, "chk_gpu"):
                    opts["use_gpu"] = self.chk_gpu.isChecked()

        elif t == "target_size":
            if hasattr(self, "spin_target_mb"):
                opts["target_size_mb"] = float(self.spin_target_mb.value())

        elif t == "convert":
            if hasattr(self, "combo_fmt"):
                opts["target_format"] = self.combo_fmt.currentData()
            if hasattr(self, "combo_vcodec"):
                opts["video_codec"] = self.combo_vcodec.currentData()
            if hasattr(self, "combo_acodec"):
                opts["audio_codec"] = self.combo_acodec.currentData()

        elif t in ("remux", "fast_remux"):
            if hasattr(self, "combo_remux_fmt"):
                opts["target_format"] = self.combo_remux_fmt.currentData()

        elif t in ("resize", "social_presets", "crop", "black_bars"):
            if hasattr(self, "combo_res"):
                opts["resolution"] = self.combo_res.currentData()
            if hasattr(self, "combo_mode"):
                opts["mode"] = self.combo_mode.currentData()

        elif t == "trim":
            if hasattr(self, "txt_trim_start"):
                opts["start_time"] = self.txt_trim_start.text().strip()
            if hasattr(self, "txt_trim_end"):
                opts["end_time"] = self.txt_trim_end.text().strip()
            if hasattr(self, "rb_trim_accurate"):
                opts["mode"] = "accurate" if self.rb_trim_accurate.isChecked() else "fast_copy"

        elif t in ("cut_middle", "remove_segment"):
            if hasattr(self, "txt_cut_start"):
                opts["cut_start"] = self.txt_cut_start.text().strip()
            if hasattr(self, "txt_cut_end"):
                opts["cut_end"] = self.txt_cut_end.text().strip()

        elif t == "split":
            if hasattr(self, "combo_split_mode"):
                opts["mode"] = self.combo_split_mode.currentData()
            if hasattr(self, "spin_split_val"):
                if opts.get("mode") == "parts":
                    opts["parts_count"] = self.spin_split_val.value()
                else:
                    opts["interval_sec"] = float(self.spin_split_val.value())

        elif t == "merge":
            if hasattr(self, "txt_merge_name"):
                opts["output_filename"] = self.txt_merge_name.text().strip()
            if hasattr(self, "chk_merge_reencode"):
                opts["reencode"] = self.chk_merge_reencode.isChecked()

        elif t == "extract_audio":
            if hasattr(self, "combo_audio_fmt"):
                opts["audio_format"] = self.combo_audio_fmt.currentData()
            if hasattr(self, "combo_audio_br"):
                opts["bitrate"] = self.combo_audio_br.currentData()

        elif t == "replace_audio":
            if hasattr(self, "txt_audio_file"):
                opts["audio_path"] = self.txt_audio_file.text().strip()
            if hasattr(self, "combo_mix_mode"):
                opts["mode"] = self.combo_mix_mode.currentData()

        elif t in ("volume", "volume_normalize"):
            if hasattr(self, "combo_vol_mode"):
                opts["mode"] = self.combo_vol_mode.currentData()
            if hasattr(self, "spin_vol_factor"):
                opts["factor"] = float(self.spin_vol_factor.value())

        elif t in ("speed", "reverse"):
            if hasattr(self, "combo_speed"):
                opts["speed_factor"] = float(self.combo_speed.currentData())
            if hasattr(self, "chk_reverse"):
                opts["reverse"] = self.chk_reverse.isChecked()

        elif t == "rotate":
            if hasattr(self, "combo_rotate"):
                opts["rotation"] = int(self.combo_rotate.currentData())
            if hasattr(self, "chk_flip_h"):
                opts["flip_h"] = self.chk_flip_h.isChecked()
            if hasattr(self, "chk_flip_v"):
                opts["flip_v"] = self.chk_flip_v.isChecked()

        elif t == "watermark":
            if hasattr(self, "txt_wm"):
                opts["text"] = self.txt_wm.text().strip()
            if hasattr(self, "txt_logo"):
                opts["logo_path"] = self.txt_logo.text().strip()
            if hasattr(self, "combo_wm_pos"):
                opts["position"] = self.combo_wm_pos.currentData()

        elif t in ("thumbnail", "frames"):
            if hasattr(self, "txt_thumb_time"):
                opts["timestamp"] = self.txt_thumb_time.text().strip()

        elif t == "gif":
            if hasattr(self, "txt_gif_start"):
                opts["start_time"] = self.txt_gif_start.text().strip()
            if hasattr(self, "spin_gif_dur"):
                opts["duration"] = float(self.spin_gif_dur.value())
            if hasattr(self, "combo_gif_w"):
                opts["width"] = int(self.combo_gif_w.currentData())

        elif t == "contact_sheet":
            if hasattr(self, "spin_cs_rows"):
                opts["rows"] = self.spin_cs_rows.value()
            if hasattr(self, "spin_cs_cols"):
                opts["cols"] = self.spin_cs_cols.value()

        elif t in ("filters", "enhance"):
            if hasattr(self, "chk_denoise"):
                opts["denoise"] = self.chk_denoise.isChecked()
            if hasattr(self, "chk_sharpen"):
                opts["sharpen"] = self.chk_sharpen.isChecked()

        elif t == "workflow":
            if hasattr(self, "wf_widget"):
                opts["workflow"] = self.wf_widget.get_workflow()

        return opts
