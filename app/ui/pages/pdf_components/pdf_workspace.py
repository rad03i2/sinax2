# -*- coding: utf-8 -*-
"""
SINAX PDF Tool Workspace
Unified interactive workspace for configuring, previewing, and executing
any tool from the PDF Center.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QFrame,
    QFileDialog, QProgressBar, QMessageBox, QTabWidget, QRadioButton,
    QLineEdit
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from app.ui.icons import get_icon
from app.services.pdf.pdf_registry import PDFToolDefinition
from app.services.pdf.pdf_service import pdf_service
from app.services.pdf.pdf_utils import parse_page_ranges
from app.workers.pdf_worker import PDFWorker
from app.ui.pages.pdf_components.pdf_viewer_widget import PDFViewerWidget
from app.ui.pages.pdf_components.pdf_options_panel import PDFOptionsPanel


class PDFToolWorkspace(QWidget):
    back_to_catalog_requested = Signal()
    status_changed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, tool: PDFToolDefinition, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.files: List[Path] = []
        self.worker: Optional[PDFWorker] = None
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

        self.btn_back = QPushButton("← العودة إلى قائمة أدوات PDF")
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
        d_lbl.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        title_layout.addWidget(d_lbl)
        tb_layout.addLayout(title_layout)

        tb_layout.addStretch(1)
        main_layout.addWidget(top_bar)

        # -------------------------------------------------------------
        # 2. MAIN SPLITTER (Left: Files & Destination | Right: Viewer & Options)
        # -------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANE: File List & Output Destination
        left_pane = QWidget()
        lp_layout = QVBoxLayout(left_pane)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.setSpacing(8)

        # File Drop / Picker Bar
        file_tools = QHBoxLayout()
        file_tools.setSpacing(8)

        self.btn_add_files = QPushButton("إضافة ملفات...")
        self.btn_add_files.setIcon(get_icon("plus", "#60CDFF", 14))
        self.btn_add_files.clicked.connect(self._on_add_files_clicked)
        file_tools.addWidget(self.btn_add_files)

        self.btn_clear = QPushButton("مسح الكل")
        self.btn_clear.setIcon(get_icon("trash", "#FF4D4F", 14))
        self.btn_clear.clicked.connect(self._on_clear_files)
        file_tools.addWidget(self.btn_clear)

        file_tools.addStretch(1)

        self.btn_up = QPushButton("▲")
        self.btn_up.setToolTip("تحريك لأعلى")
        self.btn_up.setFixedWidth(28)
        self.btn_up.clicked.connect(self._on_move_file_up)
        file_tools.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setToolTip("تحريك لأسفل")
        self.btn_down.setFixedWidth(28)
        self.btn_down.clicked.connect(self._on_move_file_down)
        file_tools.addWidget(self.btn_down)

        lp_layout.addLayout(file_tools)

        # Files Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "اسم الملف", "الحجم", "النطاق", "حذف"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.setAcceptDrops(True)
        lp_layout.addWidget(self.table, 1)

        # Output Destination Box
        dest_box = QFrame()
        dest_box.setStyleSheet("background-color: #222222; border: 1px solid #333333; border-radius: 6px; padding: 6px;")
        dest_l = QVBoxLayout(dest_box)
        dest_l.setContentsMargins(8, 6, 8, 6)
        dest_l.setSpacing(6)

        self.rb_same_dir = QRadioButton("حفظ في نفس مجلد الملف المصدر")
        self.rb_same_dir.setChecked(True)
        dest_l.addWidget(self.rb_same_dir)

        custom_row = QHBoxLayout()
        self.rb_custom_dir = QRadioButton("مجلد مخصص:")
        self.rb_custom_dir.toggled.connect(self._on_dest_mode_changed)
        custom_row.addWidget(self.rb_custom_dir)

        self.txt_custom_dir = QLineEdit()
        self.txt_custom_dir.setPlaceholderText("اختر مجلد الحفظ...")
        self.txt_custom_dir.setEnabled(False)
        custom_row.addWidget(self.txt_custom_dir)

        self.btn_pick_dir = QPushButton("استعراض...")
        self.btn_pick_dir.setEnabled(False)
        self.btn_pick_dir.clicked.connect(self._on_pick_dest_dir)
        custom_row.addWidget(self.btn_pick_dir)
        dest_l.addLayout(custom_row)

        lp_layout.addWidget(dest_box)
        splitter.addWidget(left_pane)

        # RIGHT PANE: Tabs (Options & Preview)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background: #262626;
                color: #CCCCCC;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #333333;
                color: #60CDFF;
                font-weight: bold;
            }
        """)

        # Tab 1: Options
        self.options_panel = PDFOptionsPanel(self.tool.id)
        self.tabs.addTab(self.options_panel, "إعدادات الأداة ⚙️")

        # Tab 2: Viewer / Preview
        self.viewer = PDFViewerWidget()
        self.tabs.addTab(self.viewer, "معاينة المستند 👁️")

        splitter.addWidget(self.tabs)

        # Proportions: 45% left (files), 55% right (viewer & options)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)

        main_layout.addWidget(splitter, 1)

        # -------------------------------------------------------------
        # 3. BOTTOM EXECUTION & PROGRESS BAR
        # -------------------------------------------------------------
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet("background-color: #222222; border: 1px solid #333333; border-radius: 6px;")
        bb_layout = QVBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(12, 8, 12, 8)
        bb_layout.setSpacing(6)

        # Status & Stats row
        info_row = QHBoxLayout()
        self.lbl_status = QLabel("جاهز للبدء. اختر ملفات ثم اضغط بدء المعالجة.")
        self.lbl_status.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        info_row.addWidget(self.lbl_status)

        info_row.addStretch(1)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("color: #60CDFF; font-size: 12px; font-weight: bold;")
        info_row.addWidget(self.lbl_stats)
        bb_layout.addLayout(info_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        bb_layout.addWidget(self.progress_bar)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_open_folder = QPushButton("فتح مجلد المخرجات 📂")
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._on_open_output_dir)
        btn_row.addWidget(self.btn_open_folder)

        btn_row.addStretch(1)

        self.btn_cancel = QPushButton("إلغاء العملية")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setStyleSheet("background-color: #A80000; color: #FFFFFF;")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self.btn_cancel)

        self.btn_execute = QPushButton("بدء المعالجة الآن 🚀")
        self.btn_execute.setProperty("class", "PrimaryButton")
        self.btn_execute.setMinimumHeight(38)
        self.btn_execute.setMinimumWidth(180)
        self.btn_execute.setCursor(Qt.PointingHandCursor)
        self.btn_execute.clicked.connect(self._on_execute_clicked)
        btn_row.addWidget(self.btn_execute)

        bb_layout.addLayout(btn_row)
        main_layout.addWidget(bottom_bar)

    # -----------------------------------------------------------------
    # File Drag & Drop
    # -----------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        valid_paths = []
        for url in urls:
            p = Path(url.toLocalFile())
            if p.is_file():
                if self.tool.id == "images_to_pdf":
                    if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"):
                        valid_paths.append(p)
                else:
                    if p.suffix.lower() == ".pdf":
                        valid_paths.append(p)
        if valid_paths:
            self.add_files(valid_paths)

    def _on_add_files_clicked(self):
        if self.tool.id == "images_to_pdf":
            files, _ = QFileDialog.getOpenFileNames(self, "اختر صوراً", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)")
        else:
            files, _ = QFileDialog.getOpenFileNames(self, "اختر ملفات PDF", "", "PDF Files (*.pdf)")
        if files:
            self.add_files([Path(f) for f in files])

    def add_files(self, new_paths: List[Path]):
        for p in new_paths:
            if p not in self.files:
                self.files.append(p)
        self._refresh_table()

        # Automatically load first file in viewer
        if self.files and not self.viewer.doc:
            if self.files[0].suffix.lower() == ".pdf":
                self.viewer.load_document(self.files[0])

    def _refresh_table(self):
        self.table.setRowCount(0)
        for idx, f in enumerate(self.files):
            r = self.table.rowCount()
            self.table.insertRow(r)

            self.table.setItem(r, 0, QTableWidgetItem(str(idx + 1)))
            self.table.setItem(r, 1, QTableWidgetItem(f.name))

            sz_kb = f.stat().st_size / 1024.0 if f.exists() else 0
            sz_str = f"{sz_kb:.1f} KB" if sz_kb < 1024 else f"{sz_kb/1024.0:.2f} MB"
            self.table.setItem(r, 2, QTableWidgetItem(sz_str))

            range_item = QTableWidgetItem("all")
            self.table.setItem(r, 3, range_item)

            btn_del = QPushButton("×")
            btn_del.setFixedSize(22, 22)
            btn_del.setStyleSheet("color: #FF4D4F; font-weight: bold; background: transparent; border: none;")
            btn_del.clicked.connect(lambda _, row=idx: self._remove_file_at(row))
            self.table.setCellWidget(r, 4, btn_del)

        self.lbl_status.setText(f"تم إدراج {len(self.files)} ملف.")

    def _remove_file_at(self, idx: int):
        if 0 <= idx < len(self.files):
            removed = self.files.pop(idx)
            self._refresh_table()
            if self.viewer.doc and len(self.files) == 0:
                self.viewer.close_document()

    def _on_clear_files(self):
        self.files.clear()
        self.viewer.close_document()
        self._refresh_table()

    def _on_move_file_up(self):
        row = self.table.currentRow()
        if row > 0:
            self.files[row - 1], self.files[row] = self.files[row], self.files[row - 1]
            self._refresh_table()
            self.table.selectRow(row - 1)

    def _on_move_file_down(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.files) - 1:
            self.files[row + 1], self.files[row] = self.files[row], self.files[row + 1]
            self._refresh_table()
            self.table.selectRow(row + 1)

    def _on_table_selection_changed(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.files):
            selected_path = self.files[row]
            if selected_path.suffix.lower() == ".pdf":
                self.viewer.load_document(selected_path)

    def _on_dest_mode_changed(self, is_custom: bool):
        self.txt_custom_dir.setEnabled(is_custom)
        self.btn_pick_dir.setEnabled(is_custom)

    def _on_pick_dest_dir(self):
        d = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ")
        if d:
            self.txt_custom_dir.setText(d)

    # -----------------------------------------------------------------
    # Execution & Background Worker
    # -----------------------------------------------------------------
    def _on_execute_clicked(self):
        if not self.files:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار ملف واحد على الأقل للبدء.")
            return

        # Determine Output Directory
        if self.rb_custom_dir.isChecked():
            c_dir = self.txt_custom_dir.text().strip()
            if not c_dir:
                QMessageBox.warning(self, "تنبيه", "يرجى تحديد مجلد الحفظ المخصص.")
                return
            out_dir = Path(c_dir)
        else:
            out_dir = self.files[0].parent

        out_dir.mkdir(parents=True, exist_ok=True)
        self._last_out_dir = out_dir

        # Collect Options
        opts = self.options_panel.get_options()

        # If reorder tool, grab visual page order from viewer
        if self.tool.id == "reorder":
            opts["page_order"] = self.viewer.get_page_order()

        # Lock UI
        self._set_ui_busy(True)

        # Launch Worker
        self.worker = PDFWorker(
            tool_id=self.tool.id,
            files=list(self.files),
            output_dir=out_dir,
            options=opts
        )
        self.worker.overall_progress.connect(self._on_overall_progress)
        self.worker.file_progress.connect(self._on_file_progress)
        self.worker.stats_updated.connect(self._on_stats_updated)
        self.worker.finished_all.connect(self._on_finished)
        self.worker.operation_canceled.connect(self._on_cancelled)
        self.worker.start()

    def _set_ui_busy(self, busy: bool):
        self.btn_execute.setEnabled(not busy)
        self.btn_add_files.setEnabled(not busy)
        self.btn_clear.setEnabled(not busy)
        self.btn_cancel.setVisible(busy)
        self.btn_open_folder.setVisible(False)
        if busy:
            self.progress_bar.setValue(0)

    def _on_overall_progress(self, curr: int, total: int, pct: float):
        self.progress_bar.setValue(int(pct))
        self.progress_changed.emit(int(pct))

    def _on_file_progress(self, pct: float, msg: str):
        self.lbl_status.setText(msg)
        self.status_changed.emit(msg)

    def _on_stats_updated(self, speed_mb: float, eta: str):
        self.lbl_stats.setText(f"السرعة: {speed_mb:.1f} MB/s | المتبقي: {eta}")

    def _on_cancel_clicked(self):
        if self.worker:
            self.lbl_status.setText("جاري إيقاف العملية بأمان...")
            self.worker.cancel()

    def _on_cancelled(self):
        self._set_ui_busy(False)
        self.lbl_status.setText("تم إلغاء العملية بأمان.")
        self.lbl_stats.setText("")

    def _on_finished(self, success: int, fail: int, skipped: int, failed_files: list):
        self._set_ui_busy(False)
        self.progress_bar.setValue(100)
        self.lbl_stats.setText("")
        self.btn_open_folder.setVisible(True)

        msg = f"اكتملت العملية بنجاح! ({success} ملف ناجح"
        if fail > 0:
            msg += f"، و {fail} ملف تعذر)"
        else:
            msg += ")"

        self.lbl_status.setText(msg)
        QMessageBox.information(self, "اكتملت المعالجة", msg)

    def _on_open_output_dir(self):
        if hasattr(self, "_last_out_dir") and self._last_out_dir.exists():
            os.startfile(str(self._last_out_dir))
