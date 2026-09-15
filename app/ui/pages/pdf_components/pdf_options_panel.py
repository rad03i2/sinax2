# -*- coding: utf-8 -*-
"""
SINAX Dynamic PDF Options Panel
Generates contextual settings controls for each individual PDF tool.
"""

from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton,
    QButtonGroup, QGroupBox, QPushButton, QFileDialog, QSlider
)
from PySide6.QtCore import Qt, Signal
from app.ui.icons import get_icon


class PDFOptionsPanel(QWidget):
    options_changed = Signal()

    def __init__(self, tool_id: str, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self._controls: Dict[str, Any] = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(12)

        tid = self.tool_id

        # -----------------------------------------------------------------
        # 1. MERGE
        # -----------------------------------------------------------------
        if tid == "merge":
            box = QGroupBox("خيارات الدمج")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            l.addWidget(QLabel("اسم الملف المدمج الناتج:"))
            self.merge_name = QLineEdit("merged_document.pdf")
            l.addWidget(self.merge_name)
            self._controls["output_filename"] = self.merge_name

            info = QLabel("💡 يمكنك إعادة ترتيب الملفات وتحديد نطاق صفحات كل ملف في قائمة الملفات بالأسفل.")
            info.setStyleSheet("color: #60CDFF; font-size: 11px;")
            info.setWordWrap(True)
            l.addWidget(info)
            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 2. SPLIT
        # -----------------------------------------------------------------
        elif tid == "split":
            box = QGroupBox("طريقة التقسيم")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            self.split_combo = QComboBox()
            self.split_combo.addItem("كل صفحة في ملف مستقل (Page_001.pdf)", "pages")
            self.split_combo.addItem("كل X صفحات (مجموعات متساوية)", "chunks")
            self.split_combo.addItem("نطاقات صفحات مخصصة (مثال: 1-5, 6-10)", "custom")
            self.split_combo.addItem("القطع بعد صفحات محددة (Split After)", "split_after")
            l.addWidget(self.split_combo)
            self._controls["split_mode"] = self.split_combo

            # Chunk size
            chunk_row = QHBoxLayout()
            chunk_row.addWidget(QLabel("عدد الصفحات في كل جزء:"))
            self.chunk_spin = QSpinBox()
            self.chunk_spin.setRange(1, 1000)
            self.chunk_spin.setValue(10)
            chunk_row.addWidget(self.chunk_spin)
            l.addLayout(chunk_row)
            self._controls["chunk_size"] = self.chunk_spin

            # Custom ranges input
            l.addWidget(QLabel("النطاقات المخصصة (مفصولة بفواصل):"))
            self.ranges_input = QLineEdit("1-5, 6-10")
            l.addWidget(self.ranges_input)
            self._controls["custom_ranges"] = self.ranges_input

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 3. COMPRESS
        # -----------------------------------------------------------------
        elif tid == "compress":
            box = QGroupBox("مستوى الضغط والتحسين")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            self.preset_combo = QComboBox()
            self.preset_combo.addItem("متوازن (150 DPI - مستحسن)", "balanced")
            self.preset_combo.addItem("خفيف (200 DPI - أعلى جودة)", "light")
            self.preset_combo.addItem("قوي (100 DPI - تقليل ملحوظ)", "strong")
            self.preset_combo.addItem("أقصى ضغط (72 DPI - أصغر حجم)", "max")
            l.addWidget(self.preset_combo)
            self._controls["preset"] = self.preset_combo

            self.gray_check = QCheckBox("تحويل المستند إلى درجات الرمادي (Grayscale)")
            l.addWidget(self.gray_check)
            self._controls["grayscale"] = self.gray_check

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 4. COMPRESS TARGET SIZE
        # -----------------------------------------------------------------
        elif tid == "compress_target":
            box = QGroupBox("الحجم المستهدف المطلوب")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            t_row = QHBoxLayout()
            t_row.addWidget(QLabel("الحجم الأقصى المرغوب (MB):"))
            self.target_mb = QDoubleSpinBox()
            self.target_mb.setRange(0.1, 500.0)
            self.target_mb.setValue(2.0)
            self.target_mb.setSingleStep(0.5)
            t_row.addWidget(self.target_mb)
            l.addLayout(t_row)
            self._controls["target_mb"] = self.target_mb

            # Quick Presets
            q_row = QHBoxLayout()
            for size_val in [0.5, 1.0, 2.0, 5.0, 10.0]:
                btn = QPushButton(f"{size_val} MB")
                btn.setFixedHeight(26)
                btn.clicked.connect(lambda _, v=size_val: self.target_mb.setValue(v))
                q_row.addWidget(btn)
            l.addLayout(q_row)

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 5. EXTRACT PAGES
        # -----------------------------------------------------------------
        elif tid == "extract_pages":
            box = QGroupBox("الصفحات المطلوب استخراجها")
            l = QVBoxLayout(box)
            l.setSpacing(8)

            l.addWidget(QLabel("أرقام أو نطاقات الصفحات (مثال: 1, 3-5, 8):"))
            self.extract_input = QLineEdit("1-3")
            l.addWidget(self.extract_input)
            self._controls["pages_str"] = self.extract_input
            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 6. DELETE PAGES
        # -----------------------------------------------------------------
        elif tid == "delete_pages":
            box = QGroupBox("خيارات حذف الصفحات")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            self.del_combo = QComboBox()
            self.del_combo.addItem("صفحات محددة حسب الأرقام", "custom")
            self.del_combo.addItem("حذف كافة الصفحات الفردية (Odd)", "odd")
            self.del_combo.addItem("حذف كافة الصفحات الزوجية (Even)", "even")
            l.addWidget(self.del_combo)
            self._controls["delete_mode"] = self.del_combo

            l.addWidget(QLabel("نطاقات الصفحات للحذف (في حال التحديد المخصص):"))
            self.del_input = QLineEdit("1")
            l.addWidget(self.del_input)
            self._controls["pages_str"] = self.del_input

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 7. ROTATE PAGES
        # -----------------------------------------------------------------
        elif tid == "rotate":
            box = QGroupBox("إعدادات التدوير")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            rot_row = QHBoxLayout()
            rot_row.addWidget(QLabel("زاوية الدوران مع عقارب الساعة:"))
            self.rot_combo = QComboBox()
            self.rot_combo.addItem("90° يميناً", 90)
            self.rot_combo.addItem("180° قلباً", 180)
            self.rot_combo.addItem("270° (90° يساراً)", 270)
            rot_row.addWidget(self.rot_combo)
            l.addLayout(rot_row)
            self._controls["angle"] = self.rot_combo

            l.addWidget(QLabel("الصفحات المستهدفة (اكتب 'all' أو 1,3-5):"))
            self.rot_pages = QLineEdit("all")
            l.addWidget(self.rot_pages)
            self._controls["pages_str"] = self.rot_pages

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 8. CROP & HALVE
        # -----------------------------------------------------------------
        elif tid in ("crop", "halve_pages"):
            box = QGroupBox("خيارات القص وتقسيم الصفحات")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            self.crop_combo = QComboBox()
            if tid == "halve_pages":
                self.crop_combo.addItem("شق الصفحات عمودياً (يسار / يمين)", "halve_vertical")
                self.crop_combo.addItem("شق الصفحات أفقياً (أعلى / أسفل)", "halve_horizontal")
            else:
                self.crop_combo.addItem("اقتصاص الهوامش بانتظام (Crop Margins)", "margins")
                self.crop_combo.addItem("شق الصفحات عمودياً (يسار / يمين)", "halve_vertical")
            l.addWidget(self.crop_combo)
            self._controls["crop_mode"] = self.crop_combo

            l.addWidget(QLabel("الصفحات المستهدفة (مثال: all أو 1-10):"))
            self.crop_pages = QLineEdit("all")
            l.addWidget(self.crop_pages)
            self._controls["pages_str"] = self.crop_pages

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 9. WATERMARK
        # -----------------------------------------------------------------
        elif tid == "watermark":
            box = QGroupBox("إعدادات العلامة المائية")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            l.addWidget(QLabel("نص العلامة المائية:"))
            self.wm_text = QLineEdit("DRAFT - مسودة")
            l.addWidget(self.wm_text)
            self._controls["text"] = self.wm_text

            op_row = QHBoxLayout()
            op_row.addWidget(QLabel("الشفافية:"))
            self.wm_slider = QSlider(Qt.Horizontal)
            self.wm_slider.setRange(10, 100)
            self.wm_slider.setValue(35)
            op_row.addWidget(self.wm_slider)
            l.addLayout(op_row)
            self._controls["opacity_slider"] = self.wm_slider

            ang_row = QHBoxLayout()
            ang_row.addWidget(QLabel("زاوية الميل (درجة):"))
            self.wm_angle = QSpinBox()
            self.wm_angle.setRange(0, 360)
            self.wm_angle.setValue(45)
            ang_row.addWidget(self.wm_angle)
            l.addLayout(ang_row)
            self._controls["angle"] = self.wm_angle

            # Optional Image Watermark
            img_row = QHBoxLayout()
            self.wm_img_path = QLineEdit()
            self.wm_img_path.setPlaceholderText("أو اختر صورة (PNG شفاف)...")
            btn_pick = QPushButton("استعراض...")
            btn_pick.clicked.connect(self._on_pick_watermark_img)
            img_row.addWidget(self.wm_img_path)
            img_row.addWidget(btn_pick)
            l.addLayout(img_row)
            self._controls["image_path"] = self.wm_img_path

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 10. PAGE NUMBERS
        # -----------------------------------------------------------------
        elif tid == "page_numbers":
            box = QGroupBox("تنسيق وموضع الأرقام")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            pos_row = QHBoxLayout()
            pos_row.addWidget(QLabel("موضع الرقم في الصفحة:"))
            self.num_pos = QComboBox()
            self.num_pos.addItem("أسفل الوسط", "bottom_center")
            self.num_pos.addItem("أسفل اليمين", "bottom_right")
            self.num_pos.addItem("أسفل اليسار", "bottom_left")
            self.num_pos.addItem("أعلى الوسط", "top_center")
            self.num_pos.addItem("أعلى اليمين", "top_right")
            pos_row.addWidget(self.num_pos)
            l.addLayout(pos_row)
            self._controls["position"] = self.num_pos

            l.addWidget(QLabel("صيغة الترقيم (النمط):"))
            self.num_pattern = QLineEdit("صفحة {page} من {total}")
            l.addWidget(self.num_pattern)
            self._controls["pattern"] = self.num_pattern

            bates_row = QHBoxLayout()
            bates_row.addWidget(QLabel("بادئة Bates (اختياري، مثلاً DOC-):"))
            self.bates_prefix = QLineEdit()
            bates_row.addWidget(self.bates_prefix)
            l.addLayout(bates_row)
            self._controls["prefix"] = self.bates_prefix

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 11. PROTECT & UNLOCK
        # -----------------------------------------------------------------
        elif tid == "protect":
            box = QGroupBox("كلمة المرور وصلاحيات الأمان")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            l.addWidget(QLabel("كلمة مرور فتح المستند:"))
            self.user_pwd = QLineEdit()
            self.user_pwd.setEchoMode(QLineEdit.Password)
            l.addWidget(self.user_pwd)
            self._controls["user_password"] = self.user_pwd

            self.allow_print = QCheckBox("السماح بطباعة المستند")
            self.allow_print.setChecked(True)
            l.addWidget(self.allow_print)
            self._controls["allow_print"] = self.allow_print

            self.allow_copy = QCheckBox("السماح بنسخ النصوص والمحتوى")
            self.allow_copy.setChecked(True)
            l.addWidget(self.allow_copy)
            self._controls["allow_copy"] = self.allow_copy

            main_layout.addWidget(box)

        elif tid == "unlock":
            box = QGroupBox("فك تشفير المستند")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            l.addWidget(QLabel("أدخل كلمة المرور الحالية للمستند:"))
            self.unlock_pwd = QLineEdit()
            self.unlock_pwd.setEchoMode(QLineEdit.Password)
            l.addWidget(self.unlock_pwd)
            self._controls["password"] = self.unlock_pwd

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 12. REDACTION
        # -----------------------------------------------------------------
        elif tid == "redact":
            box = QGroupBox("تنقيح وحجب البيانات الحساسة")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            l.addWidget(QLabel("الكلمات أو الأرقام المراد حجبها (مفصولة بفواصل):"))
            self.redact_terms = QLineEdit()
            self.redact_terms.setPlaceholderText("مثال: سري, رقم الهوية, 0501234567")
            l.addWidget(self.redact_terms)
            self._controls["search_terms_input"] = self.redact_terms

            self.case_check = QCheckBox("مطابقة حالة الأحرف اللاتينية (Case Sensitive)")
            l.addWidget(self.case_check)
            self._controls["case_sensitive"] = self.case_check

            info = QLabel("⚠️ التنقيح يمسح النصوص نهائياً من بنية الملف دون إمكانية استرجاعها.")
            info.setStyleSheet("color: #FFB900; font-size: 11px;")
            info.setWordWrap(True)
            l.addWidget(info)

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 13. PDF TO IMAGES
        # -----------------------------------------------------------------
        elif tid == "pdf_to_images":
            box = QGroupBox("خيارات تصدير الصور")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            fmt_row = QHBoxLayout()
            fmt_row.addWidget(QLabel("صيغة الصور:"))
            self.img_fmt = QComboBox()
            self.img_fmt.addItems(["PNG", "JPG", "WebP", "TIFF"])
            fmt_row.addWidget(self.img_fmt)
            l.addLayout(fmt_row)
            self._controls["img_format"] = self.img_fmt

            dpi_row = QHBoxLayout()
            dpi_row.addWidget(QLabel("دقة العرض (DPI):"))
            self.dpi_combo = QComboBox()
            self.dpi_combo.addItems(["72 (شاشة)", "150 (عادي - مستحسن)", "300 (طباعة عالية)", "600 (فائقة الدقة)"])
            self.dpi_combo.setCurrentIndex(1)
            dpi_row.addWidget(self.dpi_combo)
            l.addLayout(dpi_row)
            self._controls["dpi_combo"] = self.dpi_combo

            l.addWidget(QLabel("الصفحات المستهدفة (مثال: all أو 1-5):"))
            self.img_pages = QLineEdit("all")
            l.addWidget(self.img_pages)
            self._controls["pages_str"] = self.img_pages

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 14. IMAGES TO PDF
        # -----------------------------------------------------------------
        elif tid == "images_to_pdf":
            box = QGroupBox("إعدادات تجميع الصور في PDF")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            sz_row = QHBoxLayout()
            sz_row.addWidget(QLabel("حجم الصفحة:"))
            self.img_page_size = QComboBox()
            self.img_page_size.addItem("A4 (قياسي)", "a4")
            self.img_page_size.addItem("A3 (كبير)", "a3")
            self.img_page_size.addItem("Letter (رسائل)", "letter")
            self.img_page_size.addItem("مطابقة حجم كل صورة تماماً", "original")
            sz_row.addWidget(self.img_page_size)
            l.addLayout(sz_row)
            self._controls["page_size"] = self.img_page_size

            fit_row = QHBoxLayout()
            fit_row.addWidget(QLabel("ملاءمة الصورة:"))
            self.fit_combo = QComboBox()
            self.fit_combo.addItem("ملاءمة بنسبة الأبعاد (Fit)", "fit")
            self.fit_combo.addItem("ملء الصفحة بالكامل (Fill)", "fill")
            fit_row.addWidget(self.fit_combo)
            l.addLayout(fit_row)
            self._controls["fit_mode"] = self.fit_combo

            main_layout.addWidget(box)

        # -----------------------------------------------------------------
        # 15. METADATA
        # -----------------------------------------------------------------
        elif tid == "metadata":
            box = QGroupBox("البيانات الوصفية (Metadata)")
            l = QVBoxLayout(box)
            l.setSpacing(10)

            self.strip_meta_rb = QRadioButton("مسح كافة البيانات الوصفية تماماً (حماية الخصوصية)")
            self.strip_meta_rb.setChecked(True)
            l.addWidget(self.strip_meta_rb)
            self._controls["strip_all"] = self.strip_meta_rb

            main_layout.addWidget(box)

        # Default general notice for other tools
        else:
            box = QGroupBox("الإعدادات")
            l = QVBoxLayout(box)
            info = QLabel("تم ضبط إعدادات هذه الأداة تلقائياً بأعلى مستويات الجودة والأمان.")
            info.setStyleSheet("color: #CCCCCC; font-size: 12px;")
            l.addWidget(info)
            main_layout.addWidget(box)

        main_layout.addStretch(1)

    def _on_pick_watermark_img(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر صورة العلامة المائية", "", "Images (*.png *.jpg *.jpeg)")
        if f:
            self.wm_img_path.setText(f)

    def get_options(self) -> Dict[str, Any]:
        """Collects all configured parameters into a dictionary."""
        res: Dict[str, Any] = {}
        tid = self.tool_id

        if tid == "merge":
            res["output_filename"] = self.merge_name.text().strip() or "merged_document.pdf"
        elif tid == "split":
            res["split_mode"] = self.split_combo.currentData()
            res["chunk_size"] = self.chunk_spin.value()
            res["custom_ranges"] = self.ranges_input.text().strip()
        elif tid == "compress":
            res["preset"] = self.preset_combo.currentData()
            res["grayscale"] = self.gray_check.isChecked()
        elif tid == "compress_target":
            res["target_mb"] = self.target_mb.value()
        elif tid in ("extract_pages", "delete_pages"):
            ctrl = self._controls.get("pages_str")
            if ctrl:
                res["pages_str"] = ctrl.text().strip()
            if "delete_mode" in self._controls:
                res["delete_mode"] = self.del_combo.currentData()
        elif tid == "rotate":
            res["angle"] = self.rot_combo.currentData()
            res["pages_str"] = self.rot_pages.text().strip() or "all"
        elif tid in ("crop", "halve_pages"):
            res["crop_mode"] = self.crop_combo.currentData()
            res["pages_str"] = self.crop_pages.text().strip() or "all"
        elif tid == "watermark":
            res["text"] = self.wm_text.text().strip()
            res["opacity"] = self.wm_slider.value() / 100.0
            res["angle"] = float(self.wm_angle.value())
            img_p = self.wm_img_path.text().strip()
            if img_p and Path(img_p).exists():
                res["image_path"] = Path(img_p)
        elif tid == "page_numbers":
            res["position"] = self.num_pos.currentData()
            res["pattern"] = self.num_pattern.text().strip() or "صفحة {page} من {total}"
            res["prefix"] = self.bates_prefix.text().strip()
        elif tid == "protect":
            res["user_password"] = self.user_pwd.text().strip()
            res["allow_print"] = self.allow_print.isChecked()
            res["allow_copy"] = self.allow_copy.isChecked()
        elif tid == "unlock":
            res["password"] = self.unlock_pwd.text().strip()
        elif tid == "redact":
            raw_terms = self.redact_terms.text().strip()
            res["search_terms"] = [t.strip() for t in raw_terms.split(",") if t.strip()]
            res["case_sensitive"] = self.case_check.isChecked()
        elif tid == "pdf_to_images":
            res["img_format"] = self.img_fmt.currentText().lower()
            dpi_map = {0: 72, 1: 150, 2: 300, 3: 600}
            res["dpi"] = dpi_map.get(self.dpi_combo.currentIndex(), 150)
            res["pages_str"] = self.img_pages.text().strip() or "all"
        elif tid == "images_to_pdf":
            res["page_size"] = self.img_page_size.currentData()
            res["fit_mode"] = self.fit_combo.currentData()
        elif tid == "metadata":
            res["strip_all"] = self.strip_meta_rb.isChecked()

        return res
