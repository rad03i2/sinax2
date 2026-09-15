# -*- coding: utf-8 -*-
"""
SINAX Audio Workflow Builder Widget
Interactive builder for chaining sequential audio processing actions into custom pipelines.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.audio.audio_registry import AUDIO_TOOLS_REGISTRY, get_audio_tool_by_id
from app.services.audio.audio_workflow import (
    AudioWorkflow,
    AudioWorkflowStep,
    DEFAULT_AUDIO_WORKFLOW_PRESETS,
)
from app.ui.icons import get_icon


class AudioWorkflowBuilderWidget(QWidget):
    """Widget allowing users to build and configure multi-step audio processing pipelines."""

    workflow_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.workflow = AudioWorkflow("سير عمل صوتي مخصص")
        self._init_ui()
        self._load_initial_template()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # -------------------------------------------------------------
        # Predefined Templates Selector
        # -------------------------------------------------------------
        tpl_layout = QHBoxLayout()
        tpl_layout.setSpacing(8)

        tpl_lbl = QLabel("قوالب جاهزة:")
        tpl_lbl.setStyleSheet("font-size: 12px; color: #00A4EF; font-weight: bold;")
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
        for wf in DEFAULT_AUDIO_WORKFLOW_PRESETS:
            self.combo_templates.addItem(wf.name, wf)
        self.combo_templates.currentIndexChanged.connect(self._on_template_selected)
        tpl_layout.addWidget(self.combo_templates, 1)

        layout.addLayout(tpl_layout)

        # -------------------------------------------------------------
        # Steps List Widget
        # -------------------------------------------------------------
        self.list_steps = QListWidget()
        self.list_steps.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                border: 1px solid #383838;
                border-radius: 6px;
                padding: 4px;
                min-height: 160px;
            }
            QListWidget::item {
                background-color: #282828;
                border: 1px solid #3A3A3A;
                border-radius: 4px;
                padding: 8px 10px;
                margin-bottom: 4px;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background-color: #1B3A57;
                border-color: #0078D4;
            }
        """)
        layout.addWidget(self.list_steps)

        # -------------------------------------------------------------
        # Controls Row 1: Add step
        # -------------------------------------------------------------
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)

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
        # Populate compatible audio tools for chaining
        chainable_tools = [
            t for t in AUDIO_TOOLS_REGISTRY
            if t.supports_batch and t.id not in ("audio_workflow_builder", "audio_analysis_inspector")
        ]
        for t in chainable_tools:
            self.combo_add_action.addItem(f"{t.title_ar} ({t.title_en})", t.id)
        add_layout.addWidget(self.combo_add_action, 1)

        btn_add = QPushButton("إضافة خطوة +")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1084D9; }
        """)
        btn_add.clicked.connect(self._on_add_step)
        add_layout.addWidget(btn_add)

        layout.addLayout(add_layout)

        # -------------------------------------------------------------
        # Controls Row 2: Move Up, Move Down, Delete, Clear
        # -------------------------------------------------------------
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(6)

        btn_up = QPushButton("▲ للأعلى")
        btn_up.setStyleSheet("background-color: #333333; color: #EEE; border-radius: 4px; padding: 4px 8px;")
        btn_up.clicked.connect(self._move_step_up)
        btns_layout.addWidget(btn_up)

        btn_down = QPushButton("▼ للأسفل")
        btn_down.setStyleSheet("background-color: #333333; color: #EEE; border-radius: 4px; padding: 4px 8px;")
        btn_down.clicked.connect(self._move_step_down)
        btns_layout.addWidget(btn_down)

        btn_del = QPushButton("حذف الخطوة")
        btn_del.setStyleSheet("background-color: #4A2828; color: #FFAAAA; border-radius: 4px; padding: 4px 8px;")
        btn_del.clicked.connect(self._remove_selected_step)
        btns_layout.addWidget(btn_del)

        btn_clear = QPushButton("مسح الكل")
        btn_clear.setStyleSheet("background-color: #333333; color: #AAAAAA; border-radius: 4px; padding: 4px 8px;")
        btn_clear.clicked.connect(self._clear_steps)
        btns_layout.addWidget(btn_clear)

        btns_layout.addStretch()

        btn_save = QPushButton("حفظ كملف قالب...")
        btn_save.setStyleSheet("background-color: #2D2D2D; color: #FFFFFF; border: 1px solid #444; border-radius: 4px; padding: 4px 10px;")
        btn_save.clicked.connect(self._save_preset)
        btns_layout.addWidget(btn_save)

        btn_load = QPushButton("استيراد قالب...")
        btn_load.setStyleSheet("background-color: #2D2D2D; color: #FFFFFF; border: 1px solid #444; border-radius: 4px; padding: 4px 10px;")
        btn_load.clicked.connect(self._load_preset)
        btns_layout.addWidget(btn_load)

        layout.addLayout(btns_layout)

    def _load_initial_template(self):
        if DEFAULT_AUDIO_WORKFLOW_PRESETS:
            wf = DEFAULT_AUDIO_WORKFLOW_PRESETS[0]
            self.workflow = AudioWorkflow.from_dict(wf.to_dict())
            self._refresh_list()

    def _on_template_selected(self, idx):
        wf = self.combo_templates.currentData()
        if wf:
            self.workflow = AudioWorkflow.from_dict(wf.to_dict())
            self._refresh_list()
            self.workflow_changed.emit()

    def _refresh_list(self):
        self.list_steps.clear()
        for idx, step in enumerate(self.workflow.steps):
            tool = get_audio_tool_by_id(step.action)
            name = tool.title_ar if tool else step.action
            item = QListWidgetItem(f"{idx + 1}. {name}")
            self.list_steps.addItem(item)

    def _on_add_step(self):
        action_id = self.combo_add_action.currentData()
        if action_id:
            # Default params based on tool type
            params = {}
            if action_id == "batch_audio_convert":
                params = {"format": "mp3", "bitrate": "192k"}
            elif action_id == "loudness_normalize_audio":
                params = {"target_lufs": -16.0, "true_peak": -1.0}
            elif action_id == "denoise_audio":
                params = {"nr_level_db": -24.0}
            elif action_id == "silence_remove_audio":
                params = {"threshold_db": -45.0, "min_dur_sec": 0.8}

            self.workflow.add_step(action_id, params)
            self._refresh_list()
            self.workflow_changed.emit()

    def _move_step_up(self):
        r = self.list_steps.currentRow()
        if r > 0:
            self.workflow.steps[r], self.workflow.steps[r - 1] = self.workflow.steps[r - 1], self.workflow.steps[r]
            self._refresh_list()
            self.list_steps.setCurrentRow(r - 1)
            self.workflow_changed.emit()

    def _move_step_down(self):
        r = self.list_steps.currentRow()
        if 0 <= r < len(self.workflow.steps) - 1:
            self.workflow.steps[r], self.workflow.steps[r + 1] = self.workflow.steps[r + 1], self.workflow.steps[r]
            self._refresh_list()
            self.list_steps.setCurrentRow(r + 1)
            self.workflow_changed.emit()

    def _remove_selected_step(self):
        r = self.list_steps.currentRow()
        if 0 <= r < len(self.workflow.steps):
            self.workflow.remove_step(r)
            self._refresh_list()
            self.workflow_changed.emit()

    def _clear_steps(self):
        self.workflow.steps.clear()
        self._refresh_list()
        self.workflow_changed.emit()

    def _save_preset(self):
        f, _ = QFileDialog.getSaveFileName(self, "حفظ سير العمل كملف قالب", "", "JSON Files (*.json)")
        if f:
            self.workflow.save_to_file(f)
            QMessageBox.information(self, "نجاح", "تم حفظ قالب سير العمل بنجاح.")

    def _load_preset(self):
        f, _ = QFileDialog.getOpenFileName(self, "استيراد قالب سير عمل", "", "JSON Files (*.json)")
        if f:
            try:
                self.workflow = AudioWorkflow.load_from_file(f)
                self._refresh_list()
                self.workflow_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"تعذر استيراد القالب: {e}")

    def get_workflow(self) -> AudioWorkflow:
        return self.workflow
