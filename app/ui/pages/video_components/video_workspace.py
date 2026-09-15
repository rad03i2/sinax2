# -*- coding: utf-8 -*-
"""
SINAX Video Tool Workspace
Unified interactive workspace for configuring, previewing, inspecting,
and executing video operations across single files or batches of any size.
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
from app.services.video.ffmpeg_service import ffmpeg_service
from app.services.video.hardware_detector import hardware_detector
from app.services.video.video_registry import VideoToolDefinition
from app.services.video.video_utils import (
    VIDEO_EXTENSIONS,
    format_bytes,
    format_seconds,
    scan_video_files,
)
from app.ui.icons import get_icon
from app.ui.pages.video_components.video_options_panel import VideoOptionsPanel
from app.ui.pages.video_components.video_preview_widget import VideoPreviewWidget
from app.workers.video_worker import VideoWorker


class VideoToolWorkspace(QWidget):
    """Unified interactive workspace for single and batch video processing."""

    back_to_catalog_requested = Signal()
    status_changed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, tool: VideoToolDefinition, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.files: List[str] = []
        self.base_folder: Optional[str] = None
        self.worker: Optional[VideoWorker] = None
        self._is_paused = False
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. TOP HEADER BAR
        # -------------------------------------------------------------
        top_bar = QFrame()
        top_bar.setStyleSheet(
            "background-color: #262626; border: 1px solid #383838; border-radius: 8px;"
        )
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(14, 10, 14, 10)
        tb_layout.setSpacing(12)

        self.btn_back = QPushButton("← العودة إلى قائمة أدوات الفيديو")
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

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(self.tool.icon, "#60CDFF", 26).pixmap(26, 26))
        tb_layout.addWidget(icon_lbl)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        t_lbl = QLabel(f"{self.tool.title_ar}  ({self.tool.title_en})")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        title_layout.addWidget(t_lbl)

        d_lbl = QLabel(self.tool.description_ar)
        d_lbl.setWordWrap(True)
        d_lbl.setStyleSheet("font-size: 11px; color: #CCCCCC;")
        title_layout.addWidget(d_lbl)
        tb_layout.addLayout(title_layout, 1)

        # Hardware acceleration badge
        hw_info = hardware_detector.get_status_summary()
        self.lbl_hw_badge = QLabel(hw_info["badge_text"])
        self.lbl_hw_badge.setStyleSheet("""
            QLabel {
                background-color: #11283D;
                color: #60CDFF;
                border: 1px solid #1B456B;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        tb_layout.addWidget(self.lbl_hw_badge)

        main_layout.addWidget(top_bar)

        # -------------------------------------------------------------
        # 2. MAIN SPLITTER (Left: File List | Right: Options & Preview)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE: Files & Destination
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Action Buttons
        action_row = QHBoxLayout()
        self.btn_add_files = QPushButton("➕ إضافة مقاطع فيديو...")
        self.btn_add_files.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #106EBE; }
        """)
        self.btn_add_files.clicked.connect(self._on_add_files)
        action_row.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton("📁 إضافة مجلد...")
        self.btn_add_folder.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #FFFFFF;
                border: 1px solid #484848;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #3D3D3D; }
        """)
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        action_row.addWidget(self.btn_add_folder)

        self.btn_remove = QPushButton("🗑 حذف المحدد")
        self.btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #FF8080;
                border: 1px solid #484848;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #4A2222; }
        """)
        self.btn_remove.clicked.connect(self._on_remove_selected)
        action_row.addWidget(self.btn_remove)

        self.btn_clear = QPushButton("مسح الكل")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #AAAAAA;
                border: 1px solid #484848;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #444444; }
        """)
        self.btn_clear.clicked.connect(self._on_clear_all)
        action_row.addWidget(self.btn_clear)

        action_row.addStretch(1)
        self.lbl_count = QLabel("0 ملفات")
        self.lbl_count.setStyleSheet("color: #888888; font-size: 12px; font-weight: bold;")
        action_row.addWidget(self.lbl_count)
        left_layout.addLayout(action_row)

        # File List Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "#", "اسم الملف", "المدة", "الدقة", "الحجم", "الحالة", "النتيجة"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 6px;
                gridline-color: #2D2D2D;
            }
            QHeaderView::section {
                background-color: #262626;
                color: #AAAAAA;
                font-weight: bold;
                border: 1px solid #333333;
                padding: 5px;
            }
        """)
        left_layout.addWidget(self.table, 1)

        # Output Destination Box
        dest_box = QFrame()
        dest_box.setStyleSheet(
            "background-color: #222222; border: 1px solid #333333; border-radius: 6px; padding: 6px;"
        )
        dest_layout = QVBoxLayout(dest_box)
        dest_layout.setContentsMargins(6, 4, 6, 4)
        dest_layout.setSpacing(6)

        d_row = QHBoxLayout()
        d_lbl = QLabel("مجلد الحفظ:")
        d_lbl.setStyleSheet("color: #60CDFF; font-weight: bold; font-size: 11px;")
        d_row.addWidget(d_lbl)

        default_out = str(Path.home() / "Videos" / "SINAX_Output")
        self.txt_dest = QLineEdit(default_out)
        d_row.addWidget(self.txt_dest, 1)

        btn_browse_dest = QPushButton("استعراض...")
        btn_browse_dest.setStyleSheet("background-color: #333333; color: #FFF; border-radius: 4px;")
        btn_browse_dest.clicked.connect(self._on_browse_dest)
        d_row.addWidget(btn_browse_dest)
        dest_layout.addLayout(d_row)

        chk_row = QHBoxLayout()
        self.chk_preserve_dirs = QCheckBox("الحفاظ على التسلسل الشجري للمجلدات")
        self.chk_preserve_dirs.setChecked(True)
        chk_row.addWidget(self.chk_preserve_dirs)

        self.chk_open_folder = QCheckBox("فتح المجلد تلقائياً بعد اكتمال المعالجة")
        self.chk_open_folder.setChecked(True)
        chk_row.addWidget(self.chk_open_folder)
        chk_row.addStretch(1)
        dest_layout.addLayout(chk_row)

        left_layout.addWidget(dest_box)
        splitter.addWidget(left_widget)

        # RIGHT PANE: Tabs (Options + Preview & Inspector)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #383838;
                border-radius: 6px;
                background-color: #222222;
            }
            QTabBar::tab {
                background-color: #2A2A2A;
                color: #CCCCCC;
                border: 1px solid #383838;
                padding: 8px 16px;
                margin-left: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #0078D4;
                color: #FFFFFF;
                border-color: #0078D4;
            }
        """)

        # Tab 1: Options
        self.options_panel = VideoOptionsPanel(self.tool)
        self.tabs.addTab(self.options_panel, "⚙ إعدادات العملية")

        # Tab 2: Preview & Inspector
        self.preview_panel = VideoPreviewWidget()
        self.tabs.addTab(self.preview_panel, "👁 معاينة وفحص الفيديو")

        right_layout.addWidget(self.tabs, 1)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, 1)

        # -------------------------------------------------------------
        # 3. BOTTOM EXECUTION BAR
        # -------------------------------------------------------------
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet(
            "background-color: #262626; border: 1px solid #383838; border-radius: 8px; padding: 10px;"
        )
        bb_layout = QVBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(10, 8, 10, 8)
        bb_layout.setSpacing(6)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E1E1E;
                border: 1px solid #383838;
                border-radius: 4px;
                text-align: center;
                color: #FFFFFF;
                height: 18px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0078D4, stop:1 #60CDFF);
                border-radius: 3px;
            }
        """)
        bb_layout.addWidget(self.progress_bar)

        # Metrics row
        metrics_row = QHBoxLayout()
        self.lbl_status = QLabel("جاهز للبدء...")
        self.lbl_status.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        metrics_row.addWidget(self.lbl_status, 1)

        self.lbl_metrics = QLabel("")
        self.lbl_metrics.setStyleSheet(
            "color: #60CDFF; font-size: 11px; font-weight: bold; font-family: monospace;"
        )
        metrics_row.addWidget(self.lbl_metrics)

        # Buttons
        self.btn_pause = QPushButton("⏸ إيقاف مؤقت")
        self.btn_pause.setStyleSheet("background-color: #333333; color: #FFF; border-radius: 6px; padding: 7px 14px;")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._toggle_pause)
        metrics_row.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("⏹ إلغاء")
        self.btn_cancel.setStyleSheet("background-color: #4A2222; color: #FF8080; border-radius: 6px; padding: 7px 14px;")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_processing)
        metrics_row.addWidget(self.btn_cancel)

        self.btn_start = QPushButton("▶ بدء معالجة الفيديو")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 22px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #106EBE; }
            QPushButton:disabled { background-color: #333333; color: #777777; }
        """)
        self.btn_start.clicked.connect(self._start_processing)
        metrics_row.addWidget(self.btn_start)

        bb_layout.addLayout(metrics_row)
        main_layout.addWidget(bottom_bar)

        # Enable Drag and Drop
        self.setAcceptDrops(True)

    # -------------------------------------------------------------
    # Drag & Drop Handlers
    # -------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        self.add_paths(paths)

    # -------------------------------------------------------------
    # File Management
    # -------------------------------------------------------------
    def add_paths(self, paths: List[str]):
        new_files = scan_video_files(paths, recursive=True)
        for f in new_files:
            if f not in self.files:
                self.files.append(f)
                self._add_table_row(f)

        self._update_count()
        if self.files and not self.preview_panel.current_video_path:
            self.table.selectRow(0)

    def _add_table_row(self, file_path: str):
        row = self.table.rowCount()
        self.table.insertRow(row)

        p = Path(file_path)
        size_str = format_bytes(p.stat().st_size) if p.exists() else "0 B"

        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table.setItem(row, 1, QTableWidgetItem(p.name))
        self.table.setItem(row, 2, QTableWidgetItem("--:--"))
        self.table.setItem(row, 3, QTableWidgetItem("--"))
        self.table.setItem(row, 4, QTableWidgetItem(size_str))
        self.table.setItem(row, 5, QTableWidgetItem("في الانتظار"))
        self.table.setItem(row, 6, QTableWidgetItem("--"))

    def _on_add_files(self):
        ext_filter = " ".join([f"*{ext}" for ext in sorted(VIDEO_EXTENSIONS)])
        fns, _ = QFileDialog.getOpenFileNames(
            self, "اختر ملفات فيديو", "", f"Video Files ({ext_filter});;All Files (*.*)"
        )
        if fns:
            self.add_paths(fns)

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد يحتوي على مقاطع فيديو")
        if folder:
            self.base_folder = folder
            self.add_paths([folder])

    def _on_remove_selected(self):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        for r in selected_rows:
            if 0 <= r < len(self.files):
                self.files.pop(r)
            self.table.removeRow(r)
        self._renumber_table()
        self._update_count()

    def _on_clear_all(self):
        self.files.clear()
        self.table.setRowCount(0)
        self._update_count()

    def _renumber_table(self):
        for r in range(self.table.rowCount()):
            self.table.setItem(r, 0, QTableWidgetItem(str(r + 1)))

    def _update_count(self):
        cnt = len(self.files)
        self.lbl_count.setText(f"{cnt} مقطع فيديو")
        self.btn_start.setEnabled(cnt > 0)

    def _on_browse_dest(self):
        f = QFileDialog.getExistingDirectory(self, "اختر مجلد حفظ الفيديو")
        if f:
            self.txt_dest.setText(f)

    def _on_table_selection_changed(self):
        sel = self.table.selectedIndexes()
        if not sel:
            return
        row = sel[0].row()
        if 0 <= row < len(self.files):
            fpath = self.files[row]
            self.preview_panel.load_video(fpath)
            # Update duration and resolution in table if probe has info
            meta = self.preview_panel.current_meta
            if meta:
                self.table.setItem(row, 2, QTableWidgetItem(meta.get("duration_formatted", "--:--")))
                self.table.setItem(row, 3, QTableWidgetItem(meta.get("resolution", "--")))

    # -------------------------------------------------------------
    # Execution & Worker Management
    # -------------------------------------------------------------
    def _start_processing(self):
        if not self.files:
            return

        out_dir = self.txt_dest.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مجلد الحفظ أولاً.")
            return

        Path(out_dir).mkdir(parents=True, exist_ok=True)
        opts = self.options_panel.get_options()
        wf = opts.get("workflow") if self.tool.options_type == "workflow" else None

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("جارٍ بدء المعالجة...")

        self.worker = VideoWorker(
            files=self.files,
            tool_id=self.tool.id,
            options=opts,
            output_folder=out_dir,
            base_folder=self.base_folder,
            preserve_folders=self.chk_preserve_dirs.isChecked(),
            workflow=wf,
            parent=self,
        )

        self.worker.file_started.connect(self._on_file_started)
        self.worker.file_progress.connect(self._on_file_progress)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.batch_progress.connect(self._on_batch_progress)
        self.worker.status_message.connect(self._on_status_message)
        self.worker.all_finished.connect(self._on_all_finished)

        self.worker.start()

    def _on_file_started(self, idx: int, filename: str):
        row = idx - 1
        if 0 <= row < self.table.rowCount():
            item = QTableWidgetItem("جارٍ المعالجة...")
            item.setForeground(Qt.cyan)
            self.table.setItem(row, 5, item)

    def _on_file_progress(self, idx: int, filename: str, pct: float, info: dict):
        row = idx - 1
        if 0 <= row < self.table.rowCount():
            item = QTableWidgetItem(f"{pct:.0f}%")
            item.setForeground(Qt.yellow)
            self.table.setItem(row, 5, item)

        spd = info.get("speed", "")
        fps = info.get("fps", "")
        eta = info.get("eta_formatted", "")
        self.lbl_metrics.setText(f"السرعة: {spd}  |  FPS: {fps}  |  المتبقي: {eta}")

    def _on_file_finished(self, idx: int, filename: str, success: bool, msg: str, bytes_saved: int):
        row = idx - 1
        if 0 <= row < self.table.rowCount():
            st_item = QTableWidgetItem("مكتمل ✓" if success else "فشل ✕")
            st_item.setForeground(Qt.green if success else Qt.red)
            self.table.setItem(row, 5, st_item)

            res_text = format_bytes(bytes_saved) if bytes_saved > 0 else msg
            self.table.setItem(row, 6, QTableWidgetItem(res_text))

    def _on_batch_progress(self, curr: int, total: int, pct: float, speed: float, eta_sec: int):
        self.progress_bar.setValue(int(pct))
        self.progress_changed.emit(int(pct))

    def _on_status_message(self, msg: str):
        self.lbl_status.setText(msg)
        self.status_changed.emit(msg)

    def _on_all_finished(self, summary: dict):
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("اكتملت جميع العمليات بنجاح!")
        self.lbl_metrics.setText("")

        processed = summary.get("processed", 0)
        failed = summary.get("failed", 0)
        elapsed = summary.get("elapsed_seconds", 0)
        out_folder = summary.get("output_folder", "")

        msg = (
            f"تمت معالجة {processed} مقطع فيديو بنجاح خلال {elapsed} ثانية.\n"
            f"عدد الإخفاقات: {failed}\n\n"
            f"مجلد الحفظ:\n{out_folder}"
        )
        QMessageBox.information(self, "اكتملت المعالجة", msg)

        if self.chk_open_folder.isChecked() and Path(out_folder).exists():
            try:
                os.startfile(out_folder)
            except Exception:
                pass

    def _toggle_pause(self):
        if not self.worker:
            return
        self._is_paused = not self._is_paused
        if self._is_paused:
            self.worker.pause()
            self.btn_pause.setText("▶ استئناف")
            self.lbl_status.setText("تم إيقاف المعالجة مؤقتاً")
        else:
            self.worker.resume()
            self.btn_pause.setText("⏸ إيقاف مؤقت")
            self.lbl_status.setText("جارٍ استئناف المعالجة...")

    def _cancel_processing(self):
        if not self.worker:
            return
        if QMessageBox.question(
            self, "تأكيد الإلغاء", "هل أنت متأكد من رغبتك في إلغاء معالجة قائمة الفيديو المتبقية؟"
        ) == QMessageBox.Yes:
            self.worker.cancel()
            self.lbl_status.setText("تم إلغاء العملية.")
            self.btn_pause.setEnabled(False)
            self.btn_cancel.setEnabled(False)
            self.btn_start.setEnabled(True)
