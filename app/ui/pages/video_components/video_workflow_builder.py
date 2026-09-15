# -*- coding: utf-8 -*-
"""
SINAX Video Workflow Builder Widget
Interactive builder for chaining sequential video processing actions into custom pipelines.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.video.video_workflow import (
    VideoWorkflow,
    VideoWorkflowStep,
    get_predefined_workflows,
)
from app.ui.icons import get_icon


class VideoWorkflowBuilderWidget(QWidget):
    """Widget allowing users to build and configure multi-step video processing pipelines."""

    workflow_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.workflow = VideoWorkflow("سير عمل مخصص")
        self._init_ui()
        self._load_initial_template()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Predefined Templates Selector
        tpl_layout = QHBoxLayout()
        tpl_layout.setSpacing(8)

        tpl_lbl = QLabel("قوالب جاهزة:")
        tpl_lbl.setStyleSheet("font-size: 12px; color: #60CDFF; font-weight: bold;")
        tpl_layout.addWidget(tpl_lbl)

        self.combo_templates = QComboBox()
        self.combo_templates.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        for tpl in get_predefined_workflows():
            self.combo_templates.addItem(tpl["name"], tpl)
        self.combo_templates.currentIndexChanged.connect(self._on_template_selected)
        tpl_layout.addWidget(self.combo_templates, 1)

        layout.addLayout(tpl_layout)

        # Steps List Widget
        self.list_steps = QListWidget()
        self.list_steps.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                border: 1px solid #383838;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #3E3E3E;
                border-radius: 4px;
                margin-bottom: 4px;
                padding: 8px;
            }
            QListWidget::item:selected {
                border-color: #0078D4;
                background-color: #333333;
            }
        """)
        layout.addWidget(self.list_steps, 1)

        # Action Buttons Row (Add Step, Move Up, Move Down, Delete)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.combo_add_action = QComboBox()
        self.combo_add_action.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        actions = [
            ("compress", "➕ ضغط الفيديو (CRF)"),
            ("resize", "➕ تغيير المقاس / Shorts 9:16"),
            ("watermark", "➕ إضافة علامة مائية"),
            ("normalize_volume", "➕ ضبط الصوت القياسي EBU"),
            ("mute", "➕ كتم الصوت كلياً"),
            ("speed", "➕ تسريع / إبطاء الحركة"),
            ("rotate_flip", "➕ تدوير وعكس الفيديو"),
            ("enhance", "➕ تحسين الألوان وتنعيم التشويش"),
            ("strip_metadata", "➕ إزالة البيانات الوصفية والخصوصية"),
        ]
        for act_id, act_label in actions:
            self.combo_add_action.addItem(act_label, act_id)
        btn_row.addWidget(self.combo_add_action, 1)

        self.btn_add = QPushButton("إضافة خطوة")
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #106EBE; }
        """)
        self.btn_add.clicked.connect(self._add_action_step)
        btn_row.addWidget(self.btn_add)

        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedWidth(28)
        self.btn_up.setStyleSheet("background-color: #333333; color: #FFF; border-radius: 4px;")
        self.btn_up.clicked.connect(self._move_step_up)
        btn_row.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedWidth(28)
        self.btn_down.setStyleSheet("background-color: #333333; color: #FFF; border-radius: 4px;")
        self.btn_down.clicked.connect(self._move_step_down)
        btn_row.addWidget(self.btn_down)

        self.btn_remove = QPushButton("🗑 حذف")
        self.btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #4A1A1A;
                color: #FF7070;
                border: 1px solid #662222;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #6A2424; }
        """)
        self.btn_remove.clicked.connect(self._remove_step)
        btn_row.addWidget(self.btn_remove)

        layout.addLayout(btn_row)

    def _load_initial_template(self):
        if self.combo_templates.count() > 0:
            self._on_template_selected(0)

    def _on_template_selected(self, index: int):
        tpl = self.combo_templates.itemData(index)
        if not tpl:
            return
        self.workflow = VideoWorkflow(
            name=tpl.get("name", "سير عمل"),
            description=tpl.get("description", ""),
            steps=[VideoWorkflowStep.from_dict(s) for s in tpl.get("steps", [])],
        )
        self._refresh_list()

    def _refresh_list(self):
        self.list_steps.clear()
        action_names = {
            "compress": "ضغط الفيديو (Balanced)",
            "resize": "تغيير المقاس (Shorts 9:16)",
            "watermark": "إضافة علامة مائية (SINAX)",
            "normalize_volume": "ضبط مستوى الصوت (EBU R128)",
            "mute": "كتم وإزالة الصوت",
            "speed": "تسريع الحركة (x2.0)",
            "rotate_flip": "تدوير 90 درجة",
            "enhance": "تحسين الألوان والتشويش",
            "strip_metadata": "إزالة البيانات الوصفية",
            "convert": "تحويل الصيغة",
        }
        for idx, step in enumerate(self.workflow.steps, 1):
            act_label = action_names.get(step.action, step.action)
            item = QListWidgetItem(f"خطوة {idx}: {act_label}")
            self.list_steps.addItem(item)
        self.workflow_changed.emit()

    def _add_action_step(self):
        act_id = self.combo_add_action.currentData()
        defaults = {
            "compress": {"preset": "balanced"},
            "resize": {"resolution": "shorts_9_16", "mode": "vertical_blur"},
            "watermark": {"text": "SINAX", "position": "bottom_right"},
            "normalize_volume": {"mode": "ebu_r128"},
            "mute": {},
            "speed": {"speed_factor": 2.0},
            "rotate_flip": {"rotation": 90},
            "enhance": {"contrast": 1.1, "saturation": 1.1},
            "strip_metadata": {},
        }
        self.workflow.add_step(act_id, defaults.get(act_id, {}))
        self._refresh_list()

    def _move_step_up(self):
        row = self.list_steps.currentRow()
        if row > 0:
            self.workflow.steps[row - 1], self.workflow.steps[row] = (
                self.workflow.steps[row],
                self.workflow.steps[row - 1],
            )
            self._refresh_list()
            self.list_steps.setCurrentRow(row - 1)

    def _move_step_down(self):
        row = self.list_steps.currentRow()
        if 0 <= row < len(self.workflow.steps) - 1:
            self.workflow.steps[row + 1], self.workflow.steps[row] = (
                self.workflow.steps[row],
                self.workflow.steps[row + 1],
            )
            self._refresh_list()
            self.list_steps.setCurrentRow(row + 1)

    def _remove_step(self):
        row = self.list_steps.currentRow()
        if 0 <= row < len(self.workflow.steps):
            self.workflow.remove_step(row)
            self._refresh_list()

    def get_workflow(self) -> VideoWorkflow:
        return self.workflow
