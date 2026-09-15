# -*- coding: utf-8 -*-
"""
SINAX Audio Tool Workspace
Unified interactive workspace for configuring, previewing, inspecting,
and executing audio operations across single files or batches of any size.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.config import config
from app.services.audio.audio_registry import AudioToolDefinition
from app.services.audio.audio_service import audio_service
from app.services.audio.audio_utils import (
    AUDIO_EXTENSIONS,
    format_duration,
    format_file_size,
    is_audio_file,
    scan_audio_files,
)
from app.ui.icons import get_icon
from app.ui.pages.audio_components.audio_inspector_dialog import AudioInspectorDialog
from app.ui.pages.audio_components.audio_options_panel import AudioOptionsPanel
from app.ui.pages.audio_components.audio_player_widget import AudioPlayerWidget
from app.ui.pages.audio_components.audio_workflow_builder import AudioWorkflowBuilderWidget
from app.workers.audio_worker import AudioWorker


class AudioToolWorkspace(QWidget):
    """Unified interactive workspace for single and batch audio processing."""

    back_to_catalog_requested = Signal()
    status_changed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, tool: AudioToolDefinition, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.files: List[str] = []
        self.base_folder: Optional[str] = None
        self.worker: Optional[AudioWorker] = None
        self._is_paused = False
        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. TOP HEADER BAR
        # -------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #262626; border: 1px solid #383838; border-radius: 8px;")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(14, 10, 14, 10)
        tb_layout.setSpacing(12)

        self.btn_back = QPushButton("← العودة إلى قائمة أدوات الصوت")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0078D4;
                border-color: #0078D4;
            }
        """)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_to_catalog_requested.emit)
        tb_layout.addWidget(self.btn_back)

        # Tool Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        t_title = QLabel(f"{self.tool.title_ar} – {self.tool.title_en}")
        t_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        info_layout.addWidget(t_title)

        t_desc = QLabel(self.tool.description_ar)
        t_desc.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        t_desc.setWordWrap(True)
        info_layout.addWidget(t_desc)

        tb_layout.addLayout(info_layout, 1)

        # Deep Inspector Button
        self.btn_inspect = QPushButton("فاحص الصوت المتقدم 🔍")
        self.btn_inspect.setStyleSheet("""
            QPushButton {
                background-color: #1E2D3D;
                color: #00A4EF;
                border: 1px solid #0078D4;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0078D4;
                color: #FFFFFF;
            }
        """)
        self.btn_inspect.setCursor(Qt.PointingHandCursor)
        self.btn_inspect.clicked.connect(self._open_audio_inspector)
        tb_layout.addWidget(self.btn_inspect)

        main_layout.addWidget(top_bar)

        # -------------------------------------------------------------
        # 2. CENTRAL SPLITTER: Left (Tabs) / Right (Options & Actions)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #333333;
                width: 2px;
            }
        """)

        # LEFT WIDGET: Tabbed view (Files Table, Preview Player, Workflow Builder)
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #383838;
                background-color: #1F1F1F;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #2D2D2D;
                color: #CCCCCC;
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #1F1F1F;
                color: #00A4EF;
                border-bottom: 2px solid #0078D4;
            }
        """)

        # Tab 1: Files Table
        tab_files = QWidget()
        tf_layout = QVBoxLayout(tab_files)
        tf_layout.setContentsMargins(8, 8, 8, 8)
        tf_layout.setSpacing(8)

        # Toolbar
        tb_files = QHBoxLayout()
        tb_files.setSpacing(8)

        btn_add_files = QPushButton("إضافة ملفات +")
        btn_add_files.setStyleSheet("background-color: #2A3B4C; color: #60CDFF; border: 1px solid #0078D4; border-radius: 4px; padding: 5px 12px; font-weight: bold;")
        btn_add_files.clicked.connect(self._browse_files)
        tb_files.addWidget(btn_add_files)

        btn_add_folder = QPushButton("إضافة مجلد كامل 📁")
        btn_add_folder.setStyleSheet("background-color: #2D2D2D; color: #FFFFFF; border: 1px solid #444; border-radius: 4px; padding: 5px 12px;")
        btn_add_folder.clicked.connect(self._browse_folder)
        tb_files.addWidget(btn_add_folder)

        tb_files.addStretch()

        self.lbl_file_count = QLabel("0 ملف محدد")
        self.lbl_file_count.setStyleSheet("color: #8E8E93; font-size: 12px;")
        tb_files.addWidget(self.lbl_file_count)

        btn_clear = QPushButton("تفريغ القائمة")
        btn_clear.setStyleSheet("background-color: #382424; color: #FFAAAA; border: 1px solid #663333; border-radius: 4px; padding: 5px 10px;")
        btn_clear.clicked.connect(self._clear_files)
        tb_files.addWidget(btn_clear)

        tf_layout.addLayout(tb_files)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["الملف", "الحجم", "المدة", "الصيغة", "الحالة"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #181818;
                border: 1px solid #333333;
                border-radius: 6px;
                gridline-color: #2A2A2A;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #262626;
                color: #AAAAAA;
                border: 1px solid #333333;
                padding: 6px;
                font-weight: bold;
            }
        """)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        tf_layout.addWidget(self.table)

        self.tabs.addTab(tab_files, "قائمة الملفات الصوتية")

        # Tab 2: Player & Waveform Preview
        self.player_widget = AudioPlayerWidget()
        self.tabs.addTab(self.player_widget, "مشغل الصوت والموجة (Player)")

        # Tab 3: Workflow Builder (if tool is workflow or accessible)
        self.workflow_builder = AudioWorkflowBuilderWidget()
        self.tabs.addTab(self.workflow_builder, "منشئ سلاسل المعالجة (Workflow)")

        if self.tool.options_type == "workflow":
            self.tabs.setCurrentIndex(2)

        left_layout.addWidget(self.tabs)
        splitter.addWidget(left_container)

        # RIGHT WIDGET: Options panel & Execution controls
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        # Tool Options
        self.options_panel = AudioOptionsPanel(self.tool)
        right_layout.addWidget(self.options_panel, 1)

        # Destination & Folder Options
        dest_box = QFrame()
        dest_box.setStyleSheet("background-color: #242424; border: 1px solid #383838; border-radius: 8px; padding: 10px;")
        db_layout = QVBoxLayout(dest_box)
        db_layout.setSpacing(8)

        db_lbl = QLabel("مجلد حفظ النتائج:")
        db_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
        db_layout.addWidget(db_lbl)

        dest_row = QHBoxLayout()
        self.dest_edit = QLineEdit()
        default_out = str(Path.home() / "Music" / "SINAX_Audio")
        self.dest_edit.setText(default_out)
        self.dest_edit.setStyleSheet("background-color: #1E1E1E; color: #FFFFFF; border: 1px solid #3E3E3E; border-radius: 4px; padding: 5px;")
        dest_row.addWidget(self.dest_edit, 1)

        btn_browse_dest = QPushButton("تحديد...")
        btn_browse_dest.setStyleSheet("background-color: #333; color: #FFF; border-radius: 4px; padding: 5px 10px;")
        btn_browse_dest.clicked.connect(self._browse_dest)
        dest_row.addWidget(btn_browse_dest)
        db_layout.addLayout(dest_row)

        self.cb_preserve_tree = QCheckBox("الاحتفاظ بهيكل المجلدات الفرعية عند المعالجة الجماعية")
        self.cb_preserve_tree.setChecked(True)
        self.cb_preserve_tree.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        db_layout.addWidget(self.cb_preserve_tree)

        right_layout.addWidget(dest_box)

        # Progress & Status Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2D2D2D;
                border-radius: 7px;
                border: 1px solid #3D3D3D;
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 6px;
            }
        """)
        right_layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("جاهز للبدء")
        self.status_lbl.setStyleSheet("color: #8E8E93; font-size: 11px;")
        right_layout.addWidget(self.status_lbl)

        # Action Buttons: Execute, Pause, Cancel
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        self.btn_execute = QPushButton("بدء المعالجة ⚡")
        self.btn_execute.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 16px;
            }
            QPushButton:hover { background-color: #1084D9; }
            QPushButton:pressed { background-color: #006CBE; }
            QPushButton:disabled { background-color: #333333; color: #666666; }
        """)
        self.btn_execute.clicked.connect(self._start_processing)
        action_layout.addWidget(self.btn_execute, 1)

        self.btn_pause = QPushButton("إيقاف مؤقت")
        self.btn_pause.setStyleSheet("background-color: #333; color: #FFF; border-radius: 6px; padding: 8px 12px;")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._toggle_pause)
        action_layout.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("إلغاء")
        self.btn_cancel.setStyleSheet("background-color: #4A2828; color: #FFAAAA; border-radius: 6px; padding: 8px 12px;")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_processing)
        action_layout.addWidget(self.btn_cancel)

        right_layout.addLayout(action_layout)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, 1)

    # -------------------------------------------------------------
    # Drag & Drop Handlers
    # -------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        new_files = []
        for u in urls:
            path = u.toLocalFile()
            if os.path.isfile(path) and is_audio_file(path):
                new_files.append(path)
            elif os.path.isdir(path):
                found = scan_audio_files(path, recursive=True)
                new_files.extend(found)
                if not self.base_folder:
                    self.base_folder = path
        if new_files:
            self.add_files(new_files)

    # -------------------------------------------------------------
    # File Management
    # -------------------------------------------------------------
    def add_files(self, file_paths: List[str]):
        added = 0
        for p in file_paths:
            if p not in self.files and os.path.exists(p) and is_audio_file(p):
                self.files.append(p)
                added += 1

        if added > 0:
            self._refresh_table()
            # If player has no file loaded, load the first one
            if not self.player_widget._current_file and self.files:
                self.player_widget.load_audio(self.files[0])

    def _browse_files(self):
        filt = "Audio Files (*.mp3 *.wav *.flac *.aac *.m4a *.ogg *.opus *.wma *.aiff *.ac3 *.amr);;All Files (*.*)"
        chosen, _ = QFileDialog.getOpenFileNames(self, "اختر ملفات صوتية", "", filt)
        if chosen:
            self.add_files(chosen)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد ملفات صوتية")
        if folder:
            self.base_folder = folder
            found = scan_audio_files(folder, recursive=True)
            if found:
                self.add_files(found)
            else:
                QMessageBox.information(self, "تنبيه", "لم يتم العثور على ملفات صوتية مدعومة داخل المجلد.")

    def _browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد حفظ النتائج", self.dest_edit.text())
        if folder:
            self.dest_edit.setText(folder)

    def _clear_files(self):
        self.files.clear()
        self.table.setRowCount(0)
        self.lbl_file_count.setText("0 ملف محدد")
        self.player_widget.stop()

    def _refresh_table(self):
        self.table.setRowCount(len(self.files))
        for row, f in enumerate(self.files):
            p = Path(f)
            fname_item = QTableWidgetItem(p.name)
            fname_item.setToolTip(f)
            self.table.setItem(row, 0, fname_item)

            size_str = format_file_size(os.path.getsize(f)) if os.path.exists(f) else "0 B"
            self.table.setItem(row, 1, QTableWidgetItem(size_str))

            meta = audio_service.get_audio_metadata(f)
            dur_str = meta.get("duration_formatted", "00:00")
            self.table.setItem(row, 2, QTableWidgetItem(dur_str))

            fmt_str = meta.get("codec", "").upper() or p.suffix.lstrip(".").upper()
            self.table.setItem(row, 3, QTableWidgetItem(fmt_str))

            status_item = QTableWidgetItem("جاهز")
            status_item.setForeground(Qt.lightGray)
            self.table.setItem(row, 4, status_item)

        self.lbl_file_count.setText(f"{len(self.files)} ملف محدد")

    def _on_table_selection_changed(self):
        sel = self.table.selectedItems()
        if sel:
            row = sel[0].row()
            if 0 <= row < len(self.files):
                file_to_load = self.files[row]
                if self.player_widget._current_file != file_to_load:
                    self.player_widget.load_audio(file_to_load)

    # -------------------------------------------------------------
    # Deep Audio Inspector
    # -------------------------------------------------------------
    def _open_audio_inspector(self):
        target = self.player_widget._current_file
        if not target and self.files:
            target = self.files[0]
        if not target:
            QMessageBox.information(self, "تنبيه", "يرجى اختيار أو إضافة ملف صوتي أولاً لفتحه في الفاحص.")
            return

        dlg = AudioInspectorDialog(target, self)
        dlg.exec()

    # -------------------------------------------------------------
    # Batch Worker Execution
    # -------------------------------------------------------------
    def _start_processing(self):
        if not self.files:
            QMessageBox.warning(self, "تنبيه", "يرجى إضافة ملف صوتي واحد على الأقل للبدء.")
            return

        out_dir = self.dest_edit.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مجلد صالح لحفظ النتائج.")
            return

        opts = self.options_panel.get_options()
        wf = self.workflow_builder.get_workflow() if self.tool.options_type == "workflow" else None

        self.btn_execute.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_lbl.setText("جارٍ بدء المعالجة...")

        self.worker = AudioWorker(
            files=self.files,
            tool_id=self.tool.id,
            options=opts,
            output_folder=out_dir,
            base_folder=self.base_folder,
            preserve_folders=self.cb_preserve_tree.isChecked(),
            workflow=wf,
            parent=self
        )

        self.worker.file_started.connect(self._on_worker_file_started)
        self.worker.file_progress.connect(self._on_worker_file_progress)
        self.worker.file_finished.connect(self._on_worker_file_finished)
        self.worker.batch_progress.connect(self._on_worker_batch_progress)
        self.worker.status_message.connect(self.status_lbl.setText)
        self.worker.all_finished.connect(self._on_worker_all_finished)

        self.worker.start()

    def _toggle_pause(self):
        if not self.worker:
            return
        if self._is_paused:
            self.worker.resume()
            self._is_paused = False
            self.btn_pause.setText("إيقاف مؤقت")
            self.status_lbl.setText("استئناف المعالجة...")
        else:
            self.worker.pause()
            self._is_paused = True
            self.btn_pause.setText("استئناف ▶")
            self.status_lbl.setText("تم الإيقاف المؤقت.")

    def _cancel_processing(self):
        if self.worker:
            self.worker.cancel()
            self.status_lbl.setText("جارٍ إلغاء المعالجة...")
            self.btn_cancel.setEnabled(False)

    def _on_worker_file_started(self, idx: int, fname: str):
        if 0 <= idx < self.table.rowCount():
            item = self.table.item(idx, 4)
            if item:
                item.setText("جارٍ المعالجة... (0%)")
                item.setForeground(Qt.yellow)

    def _on_worker_file_progress(self, idx: int, fname: str, pct: float, metrics: Dict[str, Any]):
        if 0 <= idx < self.table.rowCount():
            item = self.table.item(idx, 4)
            if item:
                item.setText(f"جارٍ المعالجة... ({int(pct)}%)")

    def _on_worker_file_finished(self, idx: int, fname: str, success: bool, msg: str, bytes_saved: int):
        if 0 <= idx < self.table.rowCount():
            item = self.table.item(idx, 4)
            if item:
                if success:
                    item.setText("اكتمل بنجاح ✓")
                    item.setForeground(Qt.green)
                else:
                    item.setText(f"فشل: {msg[:24]}")
                    item.setForeground(Qt.red)

    def _on_worker_batch_progress(self, curr: int, total: int, pct: float, speed: float, eta_sec: int):
        self.progress_bar.setValue(int(pct))
        eta_str = format_duration(eta_sec)
        self.status_lbl.setText(f"معالجة ({curr}/{total}) - السرعة: {speed:.1f} ملف/ثانية - المتبقي: {eta_str}")

    def _on_worker_all_finished(self, summary: Dict[str, Any]):
        self.btn_execute.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self._is_paused = False
        self.btn_pause.setText("إيقاف مؤقت")
        self.progress_bar.setValue(100)

        s_cnt = summary.get("success", 0)
        e_cnt = summary.get("errors", 0)
        elapsed = summary.get("elapsed_seconds", 0.0)
        saved_str = format_file_size(summary.get("bytes_saved", 0))

        msg = f"اكتملت المعالجة: {s_cnt} نجح، {e_cnt} فشل في {elapsed:.1f} ثانية."
        if summary.get("bytes_saved", 0) > 0:
            msg += f" (تم توفير: {saved_str})"

        self.status_lbl.setText(msg)
        QMessageBox.information(self, "انتهاء العملية", msg)
