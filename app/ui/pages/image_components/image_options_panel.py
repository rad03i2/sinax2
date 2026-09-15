# -*- coding: utf-8 -*-
"""
SINAX Contextual Image Options Panel
Dynamic options widget adapting to the active tool type
(Compression, Resizing, Formats, Watermark, Enhancement, Privacy, Workflow).
"""

from typing import Dict, Any, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QSlider, QCheckBox, QRadioButton,
    QButtonGroup, QGroupBox, QPushButton, QFileDialog, QFrame,
    QColorDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.services.image.image_registry import ImageToolDefinition
from app.ui.pages.image_components.workflow_builder_widget import WorkflowBuilderWidget


class ImageOptionsPanel(QWidget):
    """Dynamic parameter configuration panel for image tools."""

    options_changed = Signal()

    def __init__(self, tool: ImageToolDefinition, parent=None):
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
            QRadioButton:hover {
                color: #FFFFFF;
            }
            QLabel {
                color: #E0E0E0;
                font-size: 12px;
            }
            QCheckBox {
                color: #E0E0E0;
                font-size: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        opt_type = self.tool.options_type

        # -------------------------------------------------------------
        # 1. COMPRESSION OPTIONS
        # -------------------------------------------------------------
        if opt_type == "compress":
            grp = QGroupBox("خيارات الضغط")
            grp_layout = QVBoxLayout(grp)

            self.preset_group = QButtonGroup(self)
            self.rb_light = QRadioButton("ضغط خفيف (أعلى جودة - 90%)")
            self.rb_balanced = QRadioButton("ضغط متوازن (موصى به - 80%)")
            self.rb_strong = QRadioButton("ضغط قوي (حجم أصغر - 60%)")
            self.rb_max = QRadioButton("أقصى ضغط (أصغر حجم - 40%)")
            self.rb_lossless = QRadioButton("ضغط بدون فقد (Lossless)")

            self.rb_balanced.setChecked(True)
            for rb in (self.rb_light, self.rb_balanced, self.rb_strong, self.rb_max, self.rb_lossless):
                self.preset_group.addButton(rb)
                grp_layout.addWidget(rb)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 2. TARGET SIZE OPTIONS
        # -------------------------------------------------------------
        elif opt_type == "target_size":
            grp = QGroupBox("الحجم المستهدف المطلوب")
            grp_layout = QVBoxLayout(grp)

            grp_layout.addWidget(QLabel("تحديد الحد الأقصى لحجم كل صورة:"))

            size_row = QHBoxLayout()
            self.spin_target_kb = QSpinBox()
            self.spin_target_kb.setRange(10, 50000)
            self.spin_target_kb.setValue(500)
            self.spin_target_kb.setSuffix(" KB")
            self.spin_target_kb.setStyleSheet("font-size: 13px; padding: 4px;")
            size_row.addWidget(self.spin_target_kb)

            grp_layout.addLayout(size_row)

            # Quick presets chips
            chips_layout = QHBoxLayout()
            for size_val in [100, 200, 500, 1024, 2048]:
                lbl = f"{size_val} KB" if size_val < 1024 else f"{size_val//1024} MB"
                btn = QPushButton(lbl)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2D2D2D;
                        border: 1px solid #444444;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 11px;
                        color: #E0E0E0;
                    }
                    QPushButton:hover { background-color: #0078D4; }
                """)
                btn.clicked.connect(lambda _, s=size_val: self.spin_target_kb.setValue(s))
                chips_layout.addWidget(btn)

            grp_layout.addLayout(chips_layout)
            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 3. RESIZE OPTIONS
        # -------------------------------------------------------------
        elif opt_type in ("resize", "social_presets"):
            grp = QGroupBox("أبعاد وتنسيق التحجيم")
            grp_layout = QVBoxLayout(grp)

            # Mode
            mode_row = QHBoxLayout()
            mode_row.addWidget(QLabel("وضع التحجيم:"))
            self.combo_resize_mode = QComboBox()
            self.combo_resize_mode.addItem("الحفاظ على النسبة (Fit)", "fit")
            self.combo_resize_mode.addItem("ملء المساحة والقص من المركز (Fill)", "fill")
            self.combo_resize_mode.addItem("تمديد بدون تناسب (Stretch)", "stretch")
            self.combo_resize_mode.addItem("أطول ضلع (Longest Edge)", "longest")
            self.combo_resize_mode.addItem("نسبة مئوية (Percentage %)", "percent")
            mode_row.addWidget(self.combo_resize_mode, 1)
            grp_layout.addLayout(mode_row)

            # Dimensions
            dim_row = QHBoxLayout()
            dim_row.addWidget(QLabel("العرض:"))
            self.spin_w = QSpinBox()
            self.spin_w.setRange(10, 10000)
            self.spin_w.setValue(1920)
            self.spin_w.setSuffix(" px")
            dim_row.addWidget(self.spin_w)

            dim_row.addWidget(QLabel("الارتفاع:"))
            self.spin_h = QSpinBox()
            self.spin_h.setRange(10, 10000)
            self.spin_h.setValue(1080)
            self.spin_h.setSuffix(" px")
            dim_row.addWidget(self.spin_h)
            grp_layout.addLayout(dim_row)

            # Presets combo
            pre_row = QHBoxLayout()
            pre_row.addWidget(QLabel("قوالب شائعة:"))
            self.combo_presets = QComboBox()
            self.combo_presets.addItem("مخصص (Custom)", (0, 0))
            self.combo_presets.addItem("Full HD (1920 × 1080)", (1920, 1080))
            self.combo_presets.addItem("4K UHD (3840 × 2160)", (3840, 2160))
            self.combo_presets.addItem("HD (1280 × 720)", (1280, 720))
            self.combo_presets.addItem("Instagram Square (1080 × 1080)", (1080, 1080))
            self.combo_presets.addItem("Instagram Portrait (1080 × 1350)", (1080, 1350))
            self.combo_presets.addItem("Story / Reels (1080 × 1920)", (1080, 1920))
            self.combo_presets.addItem("YouTube Thumbnail (1280 × 720)", (1280, 720))
            self.combo_presets.currentIndexChanged.connect(self._on_preset_change)
            pre_row.addWidget(self.combo_presets, 1)
            grp_layout.addLayout(pre_row)

            # Do not enlarge
            self.chk_no_enlarge = QCheckBox("عدم تكبير الصور الأصغر من الأبعاد المطلوبة")
            self.chk_no_enlarge.setChecked(True)
            grp_layout.addWidget(self.chk_no_enlarge)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 4. FORMAT CONVERSION OPTIONS
        # -------------------------------------------------------------
        elif opt_type in ("convert", "heic_quick"):
            grp = QGroupBox("إعدادات التحويل")
            grp_layout = QVBoxLayout(grp)

            fmt_row = QHBoxLayout()
            fmt_row.addWidget(QLabel("الصيغة المستهدفة:"))
            self.combo_fmt = QComboBox()
            formats = ["WebP", "JPG", "PNG", "AVIF", "ICO", "BMP", "TIFF", "GIF"]
            for f in formats:
                self.combo_fmt.addItem(f, f.lower())
            if opt_type == "heic_quick":
                self.combo_fmt.setCurrentText("JPG")
            fmt_row.addWidget(self.combo_fmt, 1)
            grp_layout.addLayout(fmt_row)

            q_row = QHBoxLayout()
            q_row.addWidget(QLabel("مستوى الجودة (1-100):"))
            self.spin_quality = QSpinBox()
            self.spin_quality.setRange(1, 100)
            self.spin_quality.setValue(85)
            q_row.addWidget(self.spin_quality)
            grp_layout.addLayout(q_row)

            # Transparency fallback color
            bg_row = QHBoxLayout()
            bg_row.addWidget(QLabel("لون خلفية الشفافية للـ JPG:"))
            self.btn_bg_color = QPushButton("أبيض #FFFFFF")
            self.btn_bg_color.setStyleSheet("background-color: #FFFFFF; color: #000000; border-radius: 4px;")
            self.selected_bg_color = "#FFFFFF"
            self.btn_bg_color.clicked.connect(self._pick_bg_color)
            bg_row.addWidget(self.btn_bg_color)
            grp_layout.addLayout(bg_row)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 5. WATERMARK OPTIONS
        # -------------------------------------------------------------
        elif opt_type == "watermark":
            grp = QGroupBox("العلامة المائية والشعار")
            grp_layout = QVBoxLayout(grp)

            grp_layout.addWidget(QLabel("النص المكتوب:"))
            self.txt_watermark = QLineEdit("© SINAX 2026")
            self.txt_watermark.setStyleSheet("background-color: #2D2D2D; color: #FFF; padding: 4px;")
            grp_layout.addWidget(self.txt_watermark)

            pos_row = QHBoxLayout()
            pos_row.addWidget(QLabel("الموضع:"))
            self.combo_pos = QComboBox()
            self.combo_pos.addItem("أسفل اليمين", "bottom_right")
            self.combo_pos.addItem("أسفل الوسط", "bottom_center")
            self.combo_pos.addItem("أسفل اليسار", "bottom_left")
            self.combo_pos.addItem("وسط الصورة", "center")
            self.combo_pos.addItem("أعلى اليمين", "top_right")
            self.combo_pos.addItem("أعلى الوسط", "top_center")
            self.combo_pos.addItem("أعلى اليسار", "top_left")
            pos_row.addWidget(self.combo_pos, 1)
            grp_layout.addLayout(pos_row)

            op_row = QHBoxLayout()
            op_row.addWidget(QLabel("الشفافية:"))
            self.slider_opacity = QSlider(Qt.Horizontal)
            self.slider_opacity.setRange(10, 100)
            self.slider_opacity.setValue(80)
            op_row.addWidget(self.slider_opacity)
            grp_layout.addLayout(op_row)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 6. CROP & ROTATE
        # -------------------------------------------------------------
        elif opt_type == "crop":
            grp = QGroupBox("إعدادات الاقتصاص")
            grp_layout = QVBoxLayout(grp)

            ar_row = QHBoxLayout()
            ar_row.addWidget(QLabel("نسبة الأبعاد Aspect Ratio:"))
            self.combo_ar = QComboBox()
            self.combo_ar.addItem("1:1 (مربع)", "1:1")
            self.combo_ar.addItem("16:9 (عريض)", "16:9")
            self.combo_ar.addItem("4:3 (شاشة قياسية)", "4:3")
            self.combo_ar.addItem("3:2 (كاميرا فوتوغرافية)", "3:2")
            self.combo_ar.addItem("9:16 (ستوري / طولي)", "9:16")
            self.combo_ar.addItem("4:5 (انستغرام طولي)", "4:5")
            ar_row.addWidget(self.combo_ar, 1)
            grp_layout.addLayout(ar_row)

            align_row = QHBoxLayout()
            align_row.addWidget(QLabel("التركيز على:"))
            self.combo_align = QComboBox()
            self.combo_align.addItem("مركز الصورة (Center)", "center")
            self.combo_align.addItem("الأعلى (Top)", "top")
            self.combo_align.addItem("الأسفل (Bottom)", "bottom")
            align_row.addWidget(self.combo_align, 1)
            grp_layout.addLayout(align_row)

            layout.addWidget(grp)

        elif opt_type == "rotate":
            grp = QGroupBox("خيارات التدوير والاتجاه")
            grp_layout = QVBoxLayout(grp)

            self.chk_auto_orient = QCheckBox("تصحيح الاتجاه التلقائي من EXIF (موصى به)")
            self.chk_auto_orient.setChecked(True)
            grp_layout.addWidget(self.chk_auto_orient)

            rot_row = QHBoxLayout()
            rot_row.addWidget(QLabel("زاوية التدوير:"))
            self.combo_rot = QComboBox()
            self.combo_rot.addItem("بدون تدوير (0°)", 0)
            self.combo_rot.addItem("90° باتجاه عقارب الساعة", 90)
            self.combo_rot.addItem("180° دوران كامل", 180)
            self.combo_rot.addItem("270° عكس عقارب الساعة", 270)
            rot_row.addWidget(self.combo_rot, 1)
            grp_layout.addLayout(rot_row)

            self.chk_flip_h = QCheckBox("قلب أفقي (Flip Horizontal)")
            self.chk_flip_v = QCheckBox("قلب عمودي (Flip Vertical)")
            grp_layout.addWidget(self.chk_flip_h)
            grp_layout.addWidget(self.chk_flip_v)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 7. ENHANCEMENT & FILTERS
        # -------------------------------------------------------------
        elif opt_type in ("auto_enhance", "adjustments"):
            grp = QGroupBox("الفلاتر وتعديل الألوان")
            grp_layout = QVBoxLayout(grp)

            self.chk_auto_enhance = QCheckBox("تحسين تلقائي فوري (Auto-Contrast & Sharpness)")
            self.chk_auto_enhance.setChecked(True)
            grp_layout.addWidget(self.chk_auto_enhance)

            self.chk_grayscale = QCheckBox("تحويل إلى أبيض وأسود (Grayscale)")
            self.chk_sepia = QCheckBox("تأثير سيبيا كلاسيكي (Sepia Tone)")
            self.chk_invert = QCheckBox("عكس الألوان (Invert Colors)")
            grp_layout.addWidget(self.chk_grayscale)
            grp_layout.addWidget(self.chk_sepia)
            grp_layout.addWidget(self.chk_invert)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 8. PRIVACY & METADATA
        # -------------------------------------------------------------
        elif opt_type in ("metadata_strip", "gps_only", "date_shift"):
            grp = QGroupBox("إعدادات الخصوصية")
            grp_layout = QVBoxLayout(grp)

            if opt_type == "metadata_strip":
                grp_layout.addWidget(QLabel("🔒 سيتم مسح كافة معلومات الكاميرا، والعدسة، و GPS، و EXIF بالكامل للمشاركة الآمنة."))
            elif opt_type == "gps_only":
                grp_layout.addWidget(QLabel("📍 سيتم مسح موقع GPS الجغرافي حصراً مع الاحتفاظ ببيانات تاريخ الالتقاط."))
            elif opt_type == "date_shift":
                grp_layout.addWidget(QLabel("إزاحة تاريخ الالتقاط بالساعات والأيام:"))
                h_row = QHBoxLayout()
                h_row.addWidget(QLabel("الساعات:"))
                self.spin_hours = QSpinBox()
                self.spin_hours.setRange(-24, 24)
                self.spin_hours.setValue(0)
                h_row.addWidget(self.spin_hours)

                h_row.addWidget(QLabel("الأيام:"))
                self.spin_days = QSpinBox()
                self.spin_days.setRange(-365, 365)
                self.spin_days.setValue(0)
                h_row.addWidget(self.spin_days)
                grp_layout.addLayout(h_row)

            layout.addWidget(grp)

        # -------------------------------------------------------------
        # 9. WORKFLOW BUILDER
        # -------------------------------------------------------------
        elif opt_type == "workflow":
            self.wf_widget = WorkflowBuilderWidget()
            layout.addWidget(self.wf_widget)

        # Fallback
        else:
            grp = QGroupBox("خيارات العملية")
            grp_layout = QVBoxLayout(grp)
            grp_layout.addWidget(QLabel("لا توجد إعدادات إضافية مطلوبة لهذه العملية."))
            layout.addWidget(grp)

        layout.addStretch(1)

    def _on_preset_change(self, index: int):
        w, h = self.combo_presets.currentData()
        if w > 0 and h > 0:
            self.spin_w.setValue(w)
            self.spin_h.setValue(h)

    def _pick_bg_color(self):
        col = QColorDialog.getColor(QColor(self.selected_bg_color), self, "اختر لون خلفية الشفافية")
        if col.isValid():
            self.selected_bg_color = col.name()
            self.btn_bg_color.setText(self.selected_bg_color)
            self.btn_bg_color.setStyleSheet(f"background-color: {self.selected_bg_color}; color: #000000; border-radius: 4px;")

    def get_options(self) -> Dict[str, Any]:
        """Collects all configured options as a dictionary for the worker."""
        opts: Dict[str, Any] = {}
        t = self.tool.options_type

        if t == "compress":
            if self.rb_light.isChecked():
                opts["preset"] = "light"
            elif self.rb_strong.isChecked():
                opts["preset"] = "strong"
            elif self.rb_max.isChecked():
                opts["preset"] = "max"
            elif self.rb_lossless.isChecked():
                opts["preset"] = "lossless"
                opts["lossless"] = True
            else:
                opts["preset"] = "balanced"

        elif t == "target_size":
            opts["target_size_kb"] = self.spin_target_kb.value()

        elif t in ("resize", "social_presets"):
            opts["mode"] = self.combo_resize_mode.currentData()
            opts["width"] = self.spin_w.value()
            opts["height"] = self.spin_h.value()
            opts["longest_edge"] = max(self.spin_w.value(), self.spin_h.value())
            opts["do_not_enlarge"] = self.chk_no_enlarge.isChecked()

        elif t in ("convert", "heic_quick"):
            opts["target_format"] = self.combo_fmt.currentData()
            opts["quality"] = self.spin_quality.value()
            opts["bg_color"] = self.selected_bg_color

        elif t == "watermark":
            opts["text"] = self.txt_watermark.text()
            opts["position"] = self.combo_pos.currentData()
            opts["opacity"] = self.slider_opacity.value() / 100.0

        elif t == "crop":
            opts["aspect_ratio"] = self.combo_ar.currentData()
            opts["align"] = self.combo_align.currentData()

        elif t == "rotate":
            opts["angle"] = self.combo_rot.currentData()
            opts["auto_orient"] = self.chk_auto_orient.isChecked()
            opts["flip_h"] = self.chk_flip_h.isChecked()
            opts["flip_v"] = self.chk_flip_v.isChecked()

        elif t in ("auto_enhance", "adjustments"):
            opts["auto_enhance"] = self.chk_auto_enhance.isChecked()
            opts["grayscale"] = self.chk_grayscale.isChecked()
            opts["sepia"] = self.chk_sepia.isChecked()
            opts["invert"] = self.chk_invert.isChecked()

        elif t == "date_shift":
            opts["shift_hours"] = self.spin_hours.value()
            opts["shift_days"] = self.spin_days.value()

        elif t == "workflow":
            opts["workflow"] = self.wf_widget.get_workflow()

        return opts
