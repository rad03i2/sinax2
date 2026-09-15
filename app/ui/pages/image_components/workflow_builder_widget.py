# -*- coding: utf-8 -*-
"""
SINAX Batch Workflow Builder Widget
Interactive UI for chaining multiple image processing steps into a single workflow,
configuring parameters per step, and loading/saving presets.
"""

from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QComboBox, QLineEdit, QSpinBox,
    QCheckBox, QFrame, QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from app.services.image.image_workflow import ImageWorkflow, WorkflowStep, BUILTIN_WORKFLOWS


class WorkflowBuilderWidget(QWidget):
    """Visual workflow pipeline builder."""

    workflow_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_workflow: ImageWorkflow = BUILTIN_WORKFLOWS[0]
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Preset Selector Bar
        preset_bar = QHBoxLayout()
        preset_bar.setSpacing(8)

        lbl_preset = QLabel("سير العمل المحفوظ:")
        lbl_preset.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
        preset_bar.addWidget(lbl_preset)

        self.preset_combo = QComboBox()
        self.preset_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 12px;
                color: #FFFFFF;
                font-size: 12px;
            }
        """)
        for wf in BUILTIN_WORKFLOWS:
            self.preset_combo.addItem(wf.name, wf)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_bar.addWidget(self.preset_combo, 1)

        layout.addLayout(preset_bar)

        # Description Label
        self.desc_lbl = QLabel(self.current_workflow.description)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("font-size: 11px; color: #AAAAAA; padding: 4px 2px;")
        layout.addWidget(self.desc_lbl)

        # Steps List Widget
        self.steps_list = QListWidget()
        self.steps_list.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                border: 1px solid #383838;
                border-radius: 8px;
                padding: 6px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QListWidget::item {
                background-color: #262626;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px 12px;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background-color: #0078D4;
                border-color: #60CDFF;
            }
        """)
        layout.addWidget(self.steps_list, 1)

        # Step Actions Bar (Add Step, Remove, Move)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(6)

        self.add_step_combo = QComboBox()
        self.add_step_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 5px 10px;
                color: #FFFFFF;
                font-size: 11px;
            }
        """)
        self.add_step_combo.addItem("➕ تدوير تلقائي (Auto-Orient)", "auto_orient")
        self.add_step_combo.addItem("➕ تغيير الأبعاد (Resize)", "resize")
        self.add_step_combo.addItem("➕ قص بنسبة (Crop 1:1)", "crop")
        self.add_step_combo.addItem("➕ علامة مائية (Watermark)", "watermark")
        self.add_step_combo.addItem("➕ تحسين تلقائي (Auto Enhance)", "enhance")
        self.add_step_combo.addItem("➕ حذف موقع GPS فقط", "strip_gps")
        self.add_step_combo.addItem("➕ حذف الميتاداتا والخصوصية بالكامل", "strip_metadata")
        self.add_step_combo.addItem("➕ تحويل إلى WebP (Quality 82)", "convert_webp")
        self.add_step_combo.addItem("➕ تحويل إلى JPG (Quality 90)", "convert_jpg")
        self.add_step_combo.addItem("➕ ضغط الصور (Compress Balanced)", "compress")
        btn_bar.addWidget(self.add_step_combo, 1)

        btn_add = QPushButton("إضافة خطوة")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #106EBE; }
        """)
        btn_add.clicked.connect(self._add_selected_step)
        btn_bar.addWidget(btn_add)

        btn_remove = QPushButton("🗑️ حذف خطوة")
        btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #382424;
                color: #FF8888;
                border: 1px solid #553333;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #552828; color: #FFFFFF; }
        """)
        btn_remove.clicked.connect(self._remove_selected_step)
        btn_bar.addWidget(btn_remove)

        layout.addLayout(btn_bar)
        self._refresh_steps_list()

    def _on_preset_selected(self, index: int):
        wf = self.preset_combo.currentData()
        if wf:
            self.current_workflow = wf
            self.desc_lbl.setText(wf.description)
            self._refresh_steps_list()
            self.workflow_changed.emit()

    def _refresh_steps_list(self):
        self.steps_list.clear()
        action_names = {
            "auto_orient": "1. تصحيح الاتجاه التلقائي (Auto Orient)",
            "resize": "2. تغيير الأبعاد حتى 1920px (Resize Lanczos)",
            "crop": "3. قص بنسبة 1:1 مربع (Square Crop)",
            "strip_gps": "4. حذف إحداثيات GPS لحماية الخصوصية",
            "strip_metadata": "5. تنظيف كافة بيانات EXIF/IPTC/XMP للمشاركة الآمنة",
            "watermark": "6. إضافة علامة مائية لحماية الحقوق (Watermark)",
            "enhance": "7. تحسين تلقائي للتباين والألوان (Auto Enhance)",
            "convert": "8. تحويل الصيغة والجودة",
            "compress": "9. ضغط حجم الصورة بذكاء",
            "border": "10. إضافة إطار وحواف ملونة"
        }

        for idx, step in enumerate(self.current_workflow.steps):
            display = action_names.get(step.action, f"{idx+1}. عملية: {step.action}")
            item = QListWidgetItem(f"🔽  {display}")
            self.steps_list.addItem(item)

    def _add_selected_step(self):
        action_key = self.add_step_combo.currentData()
        params = {}
        if action_key == "resize":
            params = {"mode": "longest", "longest_edge": 1920, "do_not_enlarge": True}
        elif action_key == "crop":
            params = {"aspect_ratio": "1:1", "align": "center"}
        elif action_key == "watermark":
            params = {"text": "© SINAX", "position": "bottom_right", "opacity": 0.8}
        elif action_key == "convert_webp":
            action_key = "convert"
            params = {"target_format": "webp", "quality": 82}
        elif action_key == "convert_jpg":
            action_key = "convert"
            params = {"target_format": "jpg", "quality": 90}
        elif action_key == "compress":
            params = {"preset": "balanced", "quality": 80}

        self.current_workflow.add_step(action_key, params)
        self._refresh_steps_list()
        self.workflow_changed.emit()

    def _remove_selected_step(self):
        row = self.steps_list.currentRow()
        if row >= 0:
            self.current_workflow.remove_step(row)
            self._refresh_steps_list()
            self.workflow_changed.emit()

    def get_workflow(self) -> ImageWorkflow:
        return self.current_workflow
