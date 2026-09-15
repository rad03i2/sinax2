# -*- coding: utf-8 -*-
"""
SINAX Duplicate Finder & Safe Batch Copy/Move Page
Modern, responsive Fluent interface with two primary tabs:
1. Duplicate & Similar Image Finder: 3-pass SHA-256 detection, dHash perceptual photo clustering,
   one-click smart selection rules, Windows Recycle Bin safe disposal, and quarantine.
2. Batch Safe Copy/Move: High-performance transfer with auto-renaming (1), speed meter, and undo.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QScrollArea,
    QFileDialog, QMessageBox, QProgressBar, QAbstractItemView,
    QRadioButton, QButtonGroup, QTabWidget, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QCursor

from app.core.constants import APP_NAME, FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.core.config import config
from app.core.logger import get_logger
from app.core.undo_manager import undo_manager
from app.models.file_item import format_file_size
from app.services.file_service import FileService
from app.services.duplicate_service import DuplicateService, DuplicateGroup, DuplicateItem
from app.services.transfer_service import TransferService, TransferPlan, TransferItem
from app.workers.duplicate_worker import DuplicateWorker
from app.workers.transfer_worker import TransferWorker
from app.ui.icons import get_icon

logger = get_logger("duplicate_copy_page")


class DuplicateCopyPage(QWidget):
    """Integrated Duplicate Finder and Batch Copy/Move Page."""

    status_changed = Signal(str, bool, bool)  # text, is_loading, is_error
    progress_changed = Signal(int, int)       # current, total
    back_to_hub_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_folder: Optional[Path] = None
        self.duplicate_groups: List[DuplicateGroup] = []
        self.transfer_source_files: List[Path] = []

        self.dup_worker: Optional[DuplicateWorker] = None
        self.transfer_worker: Optional[TransferWorker] = None

        self.setAcceptDrops(True)
        self._init_ui()

        # Load last folder if configured
        last_dir = config.get("last_opened_folder")
        if last_dir and Path(last_dir).exists():
            self.set_directory(Path(last_dir))

    def _wrap_in_scroll(self, content_widget: QWidget) -> QScrollArea:
        """Wraps a widget in a borderless responsive QScrollArea."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.verticalScrollBar().setSingleStep(30)
        scroll.setWidget(content_widget)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        return scroll

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # ----------------------------------------------------
        # 1. TOP BAR: Directory Selector & Back Button
        # ----------------------------------------------------
        top_frame = QFrame()
        top_frame.setObjectName("topFrame")
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(14, 8, 14, 8)
        top_layout.setSpacing(10)

        browse_btn = QPushButton(" اختيار مجلد...")
        browse_btn.setProperty("class", "PrimaryButton")
        browse_btn.setIcon(get_icon("folder_open", "#FFFFFF", 16))
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setMinimumHeight(36)
        browse_btn.clicked.connect(self._on_browse_folder)
        top_layout.addWidget(browse_btn)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("اختر المجلد المراد فحصه لكشف المكررات أو اسحبه إلى هنا...")
        self.path_edit.setMinimumHeight(36)
        self.path_edit.returnPressed.connect(self._on_path_entered)
        top_layout.addWidget(self.path_edit, 1)

        self.recent_combo = QComboBox()
        self.recent_combo.setFixedWidth(180)
        self.recent_combo.setMinimumHeight(36)
        self.recent_combo.addItem("▼ المجلدات الأخيرة")
        self._refresh_recent_folders()
        self.recent_combo.currentIndexChanged.connect(self._on_recent_selected)
        top_layout.addWidget(self.recent_combo)

        btn_back = QPushButton(" العودة للمركز")
        btn_back.setIcon(get_icon("back", "#AAAAAA", 14))
        btn_back.setMinimumHeight(36)
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(self.back_to_hub_requested.emit)
        top_layout.addWidget(btn_back)

        main_layout.addWidget(top_frame)

        # ----------------------------------------------------
        # 2. MAIN TAB WIDGET
        # ----------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setCursor(Qt.ArrowCursor)

        # Tab 1: Duplicate & Similar Images
        self.dup_tab = QWidget()
        self._init_duplicate_tab(self.dup_tab)
        self.tabs.addTab(self.dup_tab, "  كاشف الملفات المكررة والصور المتشابهة  ")

        # Tab 2: Batch Safe Copy/Move
        self.transfer_tab = QWidget()
        self._init_transfer_tab(self.transfer_tab)
        self.tabs.addTab(self.transfer_tab, "  النسخ والنقل الجماعي المتقدم  ")

        main_layout.addWidget(self.tabs, 1)

    # --------------------------------------------------------
    # TAB 1: DUPLICATE FINDER
    # --------------------------------------------------------
    def _init_duplicate_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # A. Top Controls
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("rulesPanel")
        ctrl_layout = QVBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(12, 12, 12, 12)
        ctrl_layout.setSpacing(10)

        r1 = QHBoxLayout()
        r1.setSpacing(10)

        lbl_mode = QLabel("نوع الفحص:")
        lbl_mode.setStyleSheet("font-size: 12px; font-weight: 600;")
        r1.addWidget(lbl_mode)

        self.scan_mode_combo = QComboBox()
        self.scan_mode_combo.setMinimumHeight(34)
        self.scan_mode_combo.addItem("ملفات متطابقة تماماً (خوارزمية SHA-256 الدقيقة)", "exact")
        self.scan_mode_combo.addItem("صور متشابهة بالبصمة الإدراكية (Perceptual Hash)", "similar_images")
        r1.addWidget(self.scan_mode_combo, 1)

        self.cb_dup_recursive = QCheckBox("تضمين المجلدات الفرعية (Recursive)")
        self.cb_dup_recursive.setChecked(True)
        r1.addWidget(self.cb_dup_recursive)

        self.btn_start_scan = QPushButton("  بدء فحص التكرار")
        self.btn_start_scan.setProperty("class", "PrimaryButton")
        self.btn_start_scan.setIcon(get_icon("search", "#FFFFFF", 16))
        self.btn_start_scan.setMinimumHeight(36)
        self.btn_start_scan.setCursor(Qt.PointingHandCursor)
        self.btn_start_scan.clicked.connect(self._start_duplicate_scan)
        r1.addWidget(self.btn_start_scan)

        self.btn_cancel_scan = QPushButton("  إلغاء الفحص")
        self.btn_cancel_scan.setProperty("class", "DangerButton")
        self.btn_cancel_scan.setMinimumHeight(36)
        self.btn_cancel_scan.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_scan.clicked.connect(self._cancel_duplicate_scan)
        self.btn_cancel_scan.hide()
        r1.addWidget(self.btn_cancel_scan)

        ctrl_layout.addLayout(r1)

        # Smart Auto-Select Toolbar
        sel_row = QHBoxLayout()
        sel_row.setSpacing(8)

        lbl_sel = QLabel("التحديد الذكي:")
        lbl_sel.setStyleSheet("font-size: 11px; color: #AAAAAA; font-weight: bold;")
        sel_row.addWidget(lbl_sel)

        btn_sel_except_one = QPushButton("تحديد الكل عدا نسخة واحدة (أصلية)")
        btn_sel_except_one.setMinimumHeight(30)
        btn_sel_except_one.setCursor(Qt.PointingHandCursor)
        btn_sel_except_one.clicked.connect(lambda: self._apply_auto_select("all_except_first"))
        sel_row.addWidget(btn_sel_except_one)

        btn_sel_newest = QPushButton("تحديد الأحدث")
        btn_sel_newest.setMinimumHeight(30)
        btn_sel_newest.setCursor(Qt.PointingHandCursor)
        btn_sel_newest.clicked.connect(lambda: self._apply_auto_select("all_except_oldest"))
        sel_row.addWidget(btn_sel_newest)

        btn_sel_oldest = QPushButton("تحديد الأقدم")
        btn_sel_oldest.setMinimumHeight(30)
        btn_sel_oldest.setCursor(Qt.PointingHandCursor)
        btn_sel_oldest.clicked.connect(lambda: self._apply_auto_select("all_except_newest"))
        sel_row.addWidget(btn_sel_oldest)

        btn_sel_deep = QPushButton("تحديد المسار الأطول")
        btn_sel_deep.setMinimumHeight(30)
        btn_sel_deep.setCursor(Qt.PointingHandCursor)
        btn_sel_deep.clicked.connect(lambda: self._apply_auto_select("all_except_shortest"))
        sel_row.addWidget(btn_sel_deep)

        btn_desel = QPushButton("إلغاء التحديد")
        btn_desel.setMinimumHeight(30)
        btn_desel.setCursor(Qt.PointingHandCursor)
        btn_desel.clicked.connect(lambda: self._apply_auto_select("deselect_all"))
        sel_row.addWidget(btn_desel)

        sel_row.addStretch(1)
        ctrl_layout.addLayout(sel_row)

        layout.addWidget(ctrl_frame)

        # B. Duplicates Table
        self.dup_table = QTableWidget(0, 6)
        self.dup_table.setHorizontalHeaderLabels([
            "تحديد", "المجموعة", "اسم الملف", "الحجم", "تاريخ التعديل", "المسار الكامل"
        ])
        self.dup_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dup_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.dup_table.horizontalHeader().setStretchLastSection(True)
        self.dup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dup_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.dup_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.dup_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.dup_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.dup_table.setColumnWidth(2, 240)
        self.dup_table.verticalHeader().setDefaultSectionSize(32)
        self.dup_table.verticalHeader().hide()
        self.dup_table.itemChanged.connect(self._on_dup_item_changed)
        self.dup_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dup_table.customContextMenuRequested.connect(self._show_dup_context_menu)
        self.dup_table.itemDoubleClicked.connect(self._on_dup_item_double_clicked)
        layout.addWidget(self.dup_table, 1)

        # C. Actions & Summary Footer
        footer_frame = QFrame()
        footer_frame.setObjectName("bottomActionPanel")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.setSpacing(10)

        self.dup_footer_lbl = QLabel("لا توجد مكررات معروضة. اضغط على 'بدء فحص التكرار'.")
        self.dup_footer_lbl.setStyleSheet("font-size: 11px;")
        footer_layout.addWidget(self.dup_footer_lbl, 1)

        self.btn_recycle_dups = QPushButton("  نقل المحدد إلى سلة المحذوفات")
        self.btn_recycle_dups.setProperty("class", "DangerButton")
        self.btn_recycle_dups.setIcon(get_icon("close", "#FFFFFF", 14))
        self.btn_recycle_dups.setMinimumHeight(36)
        self.btn_recycle_dups.setCursor(Qt.PointingHandCursor)
        self.btn_recycle_dups.setEnabled(False)
        self.btn_recycle_dups.clicked.connect(self._on_recycle_selected_dups)
        footer_layout.addWidget(self.btn_recycle_dups)

        self.btn_quarantine_dups = QPushButton("  عزل المحدد في مجلد خاص")
        self.btn_quarantine_dups.setIcon(get_icon("organize", "#FFB900", 14))
        self.btn_quarantine_dups.setMinimumHeight(36)
        self.btn_quarantine_dups.setCursor(Qt.PointingHandCursor)
        self.btn_quarantine_dups.setEnabled(False)
        self.btn_quarantine_dups.clicked.connect(self._on_quarantine_selected_dups)
        footer_layout.addWidget(self.btn_quarantine_dups)

        self.btn_undo_dup = QPushButton("  تراجع عن الحذف")
        self.btn_undo_dup.setIcon(get_icon("undo", "#AAAAAA", 14))
        self.btn_undo_dup.setMinimumHeight(36)
        self.btn_undo_dup.setCursor(Qt.PointingHandCursor)
        self.btn_undo_dup.clicked.connect(self._on_undo_dup)
        footer_layout.addWidget(self.btn_undo_dup)

        layout.addWidget(footer_frame)

    # --------------------------------------------------------
    # TAB 2: BATCH SAFE COPY / MOVE
    # --------------------------------------------------------
    def _init_transfer_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        # Left: Source Files Table
        left_box = QGroupBox("الملفات المحددة للنقل أو النسخ")
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(12, 20, 12, 12)
        left_layout.setSpacing(8)

        # Toolbar above table
        src_bar = QHBoxLayout()
        src_bar.setSpacing(8)

        btn_add_files = QPushButton(" إضافة ملفات...")
        btn_add_files.setIcon(get_icon("file", "#60CDFF", 14))
        btn_add_files.setMinimumHeight(30)
        btn_add_files.setCursor(Qt.PointingHandCursor)
        btn_add_files.clicked.connect(self._on_add_source_files)
        src_bar.addWidget(btn_add_files)

        btn_add_folder = QPushButton(" إضافة محتويات مجلد...")
        btn_add_folder.setIcon(get_icon("folder_open", "#FFB900", 14))
        btn_add_folder.setMinimumHeight(30)
        btn_add_folder.setCursor(Qt.PointingHandCursor)
        btn_add_folder.clicked.connect(self._on_add_source_folder)
        src_bar.addWidget(btn_add_folder)

        btn_remove_src = QPushButton("إزالة المحدد")
        btn_remove_src.setMinimumHeight(30)
        btn_remove_src.setCursor(Qt.PointingHandCursor)
        btn_remove_src.clicked.connect(self._on_remove_source_item)
        src_bar.addWidget(btn_remove_src)

        btn_clear_src = QPushButton("مسح القائمة")
        btn_clear_src.setMinimumHeight(30)
        btn_clear_src.setCursor(Qt.PointingHandCursor)
        btn_clear_src.clicked.connect(self._on_clear_source_files)
        src_bar.addWidget(btn_clear_src)

        src_bar.addStretch(1)
        left_layout.addLayout(src_bar)

        self.transfer_table = QTableWidget(0, 3)
        self.transfer_table.setHorizontalHeaderLabels(["#", "اسم الملف", "الحجم"])
        self.transfer_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transfer_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.transfer_table.horizontalHeader().setStretchLastSection(True)
        self.transfer_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.transfer_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.transfer_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.transfer_table.setColumnWidth(1, 260)
        self.transfer_table.verticalHeader().hide()
        left_layout.addWidget(self.transfer_table, 1)

        self.transfer_src_footer = QLabel("لا توجد ملفات محددة. اسحب الملفات إلى هنا أو اضغط 'إضافة ملفات'.")
        self.transfer_src_footer.setStyleSheet("font-size: 11px; color: #888888;")
        left_layout.addWidget(self.transfer_src_footer)

        split.addWidget(left_box)

        # Right: Target Directory & Transfer Options Panel
        right_panel = QFrame()
        right_panel.setObjectName("rulesPanel")
        right_panel.setMinimumWidth(380)
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(14, 14, 14, 14)
        rp_layout.setSpacing(12)

        # Destination Group
        dest_box = QGroupBox("مجلد الوجهة (Destination)")
        dest_box_layout = QVBoxLayout(dest_box)
        dest_box_layout.setContentsMargins(12, 20, 12, 12)
        dest_box_layout.setSpacing(8)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(6)

        self.transfer_dest_edit = QLineEdit(str(Path.home() / "Desktop"))
        self.transfer_dest_edit.setMinimumHeight(34)
        dest_row.addWidget(self.transfer_dest_edit, 1)

        btn_browse_dst = QPushButton("استعراض...")
        btn_browse_dst.setMinimumHeight(34)
        btn_browse_dst.setCursor(Qt.PointingHandCursor)
        btn_browse_dst.clicked.connect(self._on_browse_transfer_dest)
        dest_row.addWidget(btn_browse_dst)

        dest_box_layout.addLayout(dest_row)
        rp_layout.addWidget(dest_box)

        # Operation Mode Group
        op_box = QGroupBox("نوع العملية وسياسة التعارض")
        op_layout = QVBoxLayout(op_box)
        op_layout.setContentsMargins(12, 20, 12, 12)
        op_layout.setSpacing(10)

        lbl_op = QLabel("نوع العملية:")
        lbl_op.setStyleSheet("font-size: 12px; font-weight: 600;")
        op_layout.addWidget(lbl_op)

        op_row = QHBoxLayout()
        self.rb_transfer_copy = QRadioButton("نسخ الملفات (Copy)")
        self.rb_transfer_copy.setChecked(True)
        op_row.addWidget(self.rb_transfer_copy)

        self.rb_transfer_move = QRadioButton("نقل الملفات (Move)")
        op_row.addWidget(self.rb_transfer_move)
        op_layout.addLayout(op_row)

        lbl_col = QLabel("عند وجود ملف بنفس الاسم في الوجهة:")
        lbl_col.setStyleSheet("font-size: 12px; font-weight: 600;")
        op_layout.addWidget(lbl_col)

        self.transfer_collision_combo = QComboBox()
        self.transfer_collision_combo.setMinimumHeight(34)
        self.transfer_collision_combo.addItem("إعادة تسمية ذكية تلقائياً: (1)", "rename")
        self.transfer_collision_combo.addItem("تخطي الملف الموجود", "skip")
        self.transfer_collision_combo.addItem("استبدال الملف الموجود", "overwrite")
        op_layout.addWidget(self.transfer_collision_combo)

        rp_layout.addWidget(op_box)

        # Progress Section
        self.transfer_progress_box = QFrame()
        pb_layout = QVBoxLayout(self.transfer_progress_box)
        pb_layout.setContentsMargins(0, 4, 0, 4)
        pb_layout.setSpacing(4)

        self.transfer_progress_lbl = QLabel("جاري النقل...")
        self.transfer_progress_lbl.setStyleSheet("font-size: 11px; color: #60CDFF;")
        pb_layout.addWidget(self.transfer_progress_lbl)

        self.transfer_progress_bar = QProgressBar()
        self.transfer_progress_bar.setRange(0, 100)
        self.transfer_progress_bar.setValue(0)
        self.transfer_progress_bar.setFixedHeight(12)
        pb_layout.addWidget(self.transfer_progress_bar)

        self.transfer_speed_lbl = QLabel("السرعة: --")
        self.transfer_speed_lbl.setStyleSheet("font-size: 10px; color: #AAAAAA;")
        pb_layout.addWidget(self.transfer_speed_lbl)

        self.transfer_progress_box.hide()
        rp_layout.addWidget(self.transfer_progress_box)

        rp_layout.addStretch(1)

        # Execute Button
        self.btn_execute_transfer = QPushButton("  بدء عملية النقل/النسخ")
        self.btn_execute_transfer.setProperty("class", "PrimaryButton")
        self.btn_execute_transfer.setIcon(get_icon("play", "#FFFFFF", 16))
        self.btn_execute_transfer.setMinimumHeight(42)
        self.btn_execute_transfer.setCursor(Qt.PointingHandCursor)
        self.btn_execute_transfer.clicked.connect(self._on_start_transfer)
        rp_layout.addWidget(self.btn_execute_transfer)

        self.btn_cancel_transfer = QPushButton("  إلغاء العملية")
        self.btn_cancel_transfer.setProperty("class", "DangerButton")
        self.btn_cancel_transfer.setMinimumHeight(36)
        self.btn_cancel_transfer.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_transfer.clicked.connect(self._on_cancel_transfer)
        self.btn_cancel_transfer.hide()
        rp_layout.addWidget(self.btn_cancel_transfer)

        split.addWidget(right_panel)
        split.setSizes([600, 400])

        layout.addWidget(split, 1)

    # --------------------------------------------------------
    # DIRECTORY & RECENT FOLDERS
    # --------------------------------------------------------
    def set_directory(self, path: Path):
        if not path or not path.exists() or not path.is_dir():
            return
        self.current_folder = path.resolve()
        self.path_edit.setText(str(self.current_folder))
        config.set("last_opened_folder", str(self.current_folder), auto_save=True)
        self._add_recent_folder(str(self.current_folder))

    def _on_browse_folder(self):
        start = str(self.current_folder) if self.current_folder else str(Path.home() / "Desktop")
        folder = QFileDialog.getExistingDirectory(self, "اختر المجلد لفحص التكرار", start)
        if folder:
            self.set_directory(Path(folder))

    def _on_path_entered(self):
        p = Path(self.path_edit.text().strip())
        if p.exists() and p.is_dir():
            self.set_directory(p)
        else:
            QMessageBox.warning(self, "مسار غير صالح", "المجلد المدخل غير موجود أو غير قابل للوصول.")

    def _refresh_recent_folders(self):
        recents = config.get("recent_folders", [])
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        self.recent_combo.addItem("▼ المجلدات الأخيرة")
        for f in recents:
            self.recent_combo.addItem(f)
        self.recent_combo.blockSignals(False)

    def _add_recent_folder(self, folder_str: str):
        recents = config.get("recent_folders", [])
        if folder_str in recents:
            recents.remove(folder_str)
        recents.insert(0, folder_str)
        config.set("recent_folders", recents[:10], auto_save=True)
        self._refresh_recent_folders()

    def _on_recent_selected(self, index: int):
        if index > 0:
            target = self.recent_combo.itemText(index)
            if target and Path(target).exists():
                self.set_directory(Path(target))

    # --------------------------------------------------------
    # DUPLICATE SCAN OPERATIONS
    # --------------------------------------------------------
    def _start_duplicate_scan(self):
        if not self.current_folder or not self.current_folder.exists():
            QMessageBox.information(self, "تنبيه", "يرجى اختيار مجلد صالح أولاً للبحث عن المكررات.")
            return

        mode = self.scan_mode_combo.currentData()
        use_perceptual = (mode == "similar_images")
        recursive = self.cb_dup_recursive.isChecked()

        self.btn_start_scan.hide()
        self.btn_cancel_scan.show()
        self.dup_table.setRowCount(0)
        self.duplicate_groups = []
        self.btn_recycle_dups.setEnabled(False)
        self.btn_quarantine_dups.setEnabled(False)
        self.dup_footer_lbl.setText("جاري فحص المكررات...")
        self.status_changed.emit("جاري فحص المكررات في الخلفية...", True, False)

        self.dup_worker = DuplicateWorker(
            directory=self.current_folder,
            recursive=recursive,
            use_perceptual_hash=use_perceptual
        )
        self.dup_worker.progress_updated.connect(self._on_dup_progress)
        self.dup_worker.duplicates_found.connect(self._on_dup_finished)
        self.dup_worker.scan_failed.connect(self._on_dup_failed)
        self.dup_worker.start()

    def _cancel_duplicate_scan(self):
        if self.dup_worker and self.dup_worker.isRunning():
            self.dup_worker.cancel()
            self.status_changed.emit("جاري إلغاء فحص المكررات...", True, False)

    def _on_dup_progress(self, pass_num: int, count: int, text: str):
        self.dup_footer_lbl.setText(f"[مرحلة {pass_num}]: {text}")

    def _on_dup_finished(self, groups: List[DuplicateGroup]):
        self.btn_start_scan.show()
        self.btn_cancel_scan.hide()
        self.duplicate_groups = groups

        self._populate_dup_table()
        self._update_dup_summary()

        total_dups = sum(len(g.files) for g in groups)
        wasted = sum(g.wasted_size_bytes for g in groups)
        wasted_str = format_file_size(wasted)

        if groups:
            self.status_changed.emit(f"اكتمل الفحص: عُثر على {len(groups)} مجموعة مكررة ({total_dups} ملف). مساحة مهدرة: {wasted_str}.", False, False)
        else:
            self.status_changed.emit("اكتمل الفحص: لا توجد أي ملفات مكررة في هذا المجلد.", False, False)
            self.dup_footer_lbl.setText("لا توجد ملفات مكررة. المجلد نظيف تماماً.")

    def _on_dup_failed(self, error_msg: str):
        self.btn_start_scan.show()
        self.btn_cancel_scan.hide()
        self.dup_footer_lbl.setText("حدث خطأ أثناء فحص المكررات.")
        self.status_changed.emit(f"خطأ أثناء الفحص: {error_msg}", False, True)
        QMessageBox.critical(self, "خطأ في الفحص", f"تعذر إكمال فحص المكررات: {error_msg}")

    def _populate_dup_table(self):
        self.dup_table.setRowCount(0)
        self.dup_table.blockSignals(True)

        row_idx = 0
        group_colors = ["#222222", "#2A2A2A"]

        for grp in self.duplicate_groups:
            bg_color = QColor(group_colors[grp.group_id % len(group_colors)])

            for it in grp.files:
                self.dup_table.insertRow(row_idx)

                # 0: Checkbox
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk.setCheckState(Qt.Checked if it.is_selected else Qt.Unchecked)
                chk.setBackground(bg_color)
                self.dup_table.setItem(row_idx, 0, chk)

                # 1: Group Badge
                badge = QTableWidgetItem(f"مجموعة {grp.group_id}")
                badge.setTextAlignment(Qt.AlignCenter)
                badge.setBackground(bg_color)
                badge.setForeground(QColor("#FFB900"))
                self.dup_table.setItem(row_idx, 1, badge)

                # 2: Filename + Icon
                cat_color = FILE_CATEGORIES.get(it.category_key, {}).get("color", "#888888")
                icon = get_icon(it.category_key if it.category_key != "other" else "file", cat_color, 16)
                it_name = QTableWidgetItem(icon, it.filename)
                it_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                it_name.setBackground(bg_color)
                self.dup_table.setItem(row_idx, 2, it_name)

                # 3: Size
                it_sz = QTableWidgetItem(it.formatted_size)
                it_sz.setTextAlignment(Qt.AlignCenter)
                it_sz.setBackground(bg_color)
                self.dup_table.setItem(row_idx, 3, it_sz)

                # 4: Modified Date
                it_dt = QTableWidgetItem(it.formatted_date)
                it_dt.setTextAlignment(Qt.AlignCenter)
                it_dt.setBackground(bg_color)
                self.dup_table.setItem(row_idx, 4, it_dt)

                # 5: Full Path
                it_path = QTableWidgetItem(str(it.path))
                it_path.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                it_path.setBackground(bg_color)
                it_path.setForeground(QColor("#60CDFF"))
                self.dup_table.setItem(row_idx, 5, it_path)

                row_idx += 1

        self.dup_table.blockSignals(False)

    def _on_dup_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0:
            row = item.row()
            # Map table row back to duplicate item
            current_row = 0
            for grp in self.duplicate_groups:
                for it in grp.files:
                    if current_row == row:
                        it.is_selected = (item.checkState() == Qt.Checked)
                        self._update_dup_summary()
                        return
                    current_row += 1

    def _apply_auto_select(self, rule: str):
        if not self.duplicate_groups:
            return
        DuplicateService.apply_auto_select(self.duplicate_groups, rule)
        self.dup_table.blockSignals(True)

        row = 0
        for grp in self.duplicate_groups:
            for it in grp.files:
                chk = self.dup_table.item(row, 0)
                if chk:
                    chk.setCheckState(Qt.Checked if it.is_selected else Qt.Unchecked)
                row += 1

        self.dup_table.blockSignals(False)
        self._update_dup_summary()

    def _update_dup_summary(self):
        total_groups = len(self.duplicate_groups)
        wasted_bytes = sum(g.wasted_size_bytes for g in self.duplicate_groups)

        selected_items = [
            it for g in self.duplicate_groups for it in g.files if it.is_selected
        ]
        sel_count = len(selected_items)
        sel_bytes = sum(it.size_bytes for it in selected_items)

        self.dup_footer_lbl.setText(
            f"المجموعات: {total_groups} | مساحة مكررة مهدرة: {format_file_size(wasted_bytes)} | "
            f"المحدد للإجراء: {sel_count} ملف ({format_file_size(sel_bytes)})"
        )
        self.btn_recycle_dups.setEnabled(sel_count > 0)
        self.btn_quarantine_dups.setEnabled(sel_count > 0)

    def _show_dup_context_menu(self, pos):
        row = self.dup_table.rowAt(pos.y())
        if row < 0:
            return

        current_row = 0
        target_item = None
        for grp in self.duplicate_groups:
            for it in grp.files:
                if current_row == row:
                    target_item = it
                    break
                current_row += 1
            if target_item:
                break

        if not target_item:
            return

        menu = QMenu(self)
        act_open = menu.addAction("فتح الملف")
        act_open.setIcon(get_icon("play", "#FFFFFF", 14))
        act_open.triggered.connect(lambda: FileService.open_file(target_item.path))

        act_exp = menu.addAction("فتح في مستكشف ويندوز (Explorer)")
        act_exp.setIcon(get_icon("folder_open", "#60CDFF", 14))
        act_exp.triggered.connect(lambda: FileService.open_in_explorer(target_item.path))

        act_copy = menu.addAction("نسخ المسار الكامل")
        act_copy.setIcon(get_icon("rename", "#FFB900", 14))
        act_copy.triggered.connect(lambda: self._copy_to_clipboard(str(target_item.path)))

        menu.exec(QCursor.pos())

    def _on_dup_item_double_clicked(self, table_item: QTableWidgetItem):
        row = table_item.row()
        current_row = 0
        for grp in self.duplicate_groups:
            for it in grp.files:
                if current_row == row:
                    FileService.open_file(it.path)
                    return
                current_row += 1

    def _copy_to_clipboard(self, text: str):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.status_changed.emit("تم نسخ المسار إلى الحافظة.", False, False)

    def _on_recycle_selected_dups(self):
        selected_items = [
            it for g in self.duplicate_groups for it in g.files if it.is_selected
        ]
        if not selected_items:
            return

        reply = QMessageBox.question(
            self, "تأكيد الحذف الآمن",
            f"هل أنت متأكد من نقل {len(selected_items)} ملف مكرر إلى سلة المحذوفات؟ لن تفقد أي بيانات لأنه ستبقى نسخة أصلية من كل ملف.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        success, failed = DuplicateService.safe_delete_items(selected_items)
        msg = f"تم إرسال {success} ملف بنجاح إلى سلة المحذوفات."
        if failed:
            msg += f" (تعذر حذف {failed} ملف)"
        QMessageBox.information(self, "اكتمل الحذف", msg)
        # Refresh scan
        self._start_duplicate_scan()

    def _on_quarantine_selected_dups(self):
        selected_items = [
            it for g in self.duplicate_groups for it in g.files if it.is_selected
        ]
        if not selected_items:
            return

        quarantine_base = self.current_folder or Path.home() / "Desktop"
        success, failed, q_dir = DuplicateService.quarantine_items(selected_items, quarantine_base)

        QMessageBox.information(
            self, "اكتمل العزل",
            f"تم عزل {success} ملف مكرر بنجاح داخل المجلد: {q_dir.name}\nيمكنك مراجعته بأمان واسترجاع أي ملف متى شئت."
        )
        # Refresh scan
        self._start_duplicate_scan()

    def _on_undo_dup(self):
        last_op = undo_manager.get_last_operation()
        if not last_op or "duplicate" not in last_op.operation_type:
            QMessageBox.information(self, "تنبيه", "لا توجد عملية حذف أو عزل مكررات سابقة للتراجع عنها.")
            return

        if undo_manager.undo_last_operation():
            QMessageBox.information(self, "تم التراجع", "تم استرجاع الملفات بنجاح إلى أماكنها السابقة.")
            self._start_duplicate_scan()
        else:
            QMessageBox.critical(self, "خطأ", "تعذر التراجع عن العملية السابقة.")

    # --------------------------------------------------------
    # BATCH TRANSFER OPERATIONS
    # --------------------------------------------------------
    def _on_add_source_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "اختر الملفات للنقل أو النسخ")
        if files:
            for f in files:
                p = Path(f)
                if p not in self.transfer_source_files:
                    self.transfer_source_files.append(p)
            self._populate_transfer_table()

    def _on_add_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر المجلد لإضافة ملفاته")
        if folder:
            p = Path(folder)
            for f in p.glob('*'):
                if f.is_file() and f not in self.transfer_source_files:
                    self.transfer_source_files.append(f)
            self._populate_transfer_table()

    def _on_remove_source_item(self):
        selected_rows = sorted(set(idx.row() for idx in self.transfer_table.selectedIndexes()), reverse=True)
        for r in selected_rows:
            if 0 <= r < len(self.transfer_source_files):
                self.transfer_source_files.pop(r)
        self._populate_transfer_table()

    def _on_clear_source_files(self):
        self.transfer_source_files = []
        self._populate_transfer_table()

    def _populate_transfer_table(self):
        self.transfer_table.setRowCount(0)
        self.transfer_table.blockSignals(True)

        total_sz = 0
        for idx, p in enumerate(self.transfer_source_files):
            self.transfer_table.insertRow(idx)

            # 0: #
            it_idx = QTableWidgetItem(str(idx + 1))
            it_idx.setTextAlignment(Qt.AlignCenter)
            self.transfer_table.setItem(idx, 0, it_idx)

            # 1: Name + Icon
            ext = p.suffix.lower()
            cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
            cat_color = FILE_CATEGORIES.get(cat_key, {}).get("color", "#888888")
            icon = get_icon(cat_key if cat_key != "other" else "file", cat_color, 16)
            it_name = QTableWidgetItem(icon, p.name)
            it_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.transfer_table.setItem(idx, 1, it_name)

            # 2: Size
            try:
                sz = p.stat().st_size
                total_sz += sz
                sz_str = format_file_size(sz)
            except Exception:
                sz_str = "0 بايت"
            it_sz = QTableWidgetItem(sz_str)
            it_sz.setTextAlignment(Qt.AlignCenter)
            self.transfer_table.setItem(idx, 2, it_sz)

        self.transfer_table.blockSignals(False)

        count = len(self.transfer_source_files)
        self.transfer_src_footer.setText(f"إجمالي الملفات: {count} ملف | الحجم الكلي: {format_file_size(total_sz)}")
        self.btn_execute_transfer.setEnabled(count > 0)

    def _on_browse_transfer_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد الوجهة")
        if folder:
            self.transfer_dest_edit.setText(folder)

    def _on_start_transfer(self):
        if not self.transfer_source_files:
            QMessageBox.information(self, "تنبيه", "يرجى إضافة ملفات أولاً لنقلها أو نسخها.")
            return

        dst_str = self.transfer_dest_edit.text().strip()
        dst_path = Path(dst_str)
        if not dst_str or not dst_path.exists():
            QMessageBox.warning(self, "وجهة غير صالحة", "يرجى تحديد مجلد وجهة صالح وموجود.")
            return

        action = "move" if self.rb_transfer_move.isChecked() else "copy"
        collision = self.transfer_collision_combo.currentData()

        plan = TransferService.generate_plan(
            sources=self.transfer_source_files,
            destination_dir=dst_path,
            action_type=action,
            collision_policy=collision
        )

        self.btn_execute_transfer.hide()
        self.btn_cancel_transfer.show()
        self.transfer_progress_box.show()
        self.transfer_progress_bar.setValue(0)
        self.transfer_progress_lbl.setText("بدء العملية...")
        self.transfer_speed_lbl.setText("السرعة: --")

        self.transfer_worker = TransferWorker(plan)
        self.transfer_worker.progress_updated.connect(self._on_transfer_progress)
        self.transfer_worker.transfer_finished.connect(self._on_transfer_finished)
        self.transfer_worker.transfer_failed.connect(self._on_transfer_failed)
        self.transfer_worker.start()

    def _on_cancel_transfer(self):
        if self.transfer_worker and self.transfer_worker.isRunning():
            self.transfer_worker.cancel()
            self.status_changed.emit("جاري إلغاء النقل بأمان...", True, False)

    def _on_transfer_progress(self, curr: int, tot: int, fname: str, pct: float, speed_str: str):
        self.transfer_progress_bar.setValue(int(pct))
        self.transfer_progress_lbl.setText(f"معالجة: {fname} ({curr}/{tot})")
        self.transfer_speed_lbl.setText(f"السرعة: {speed_str}")

    def _on_transfer_finished(self, success: int, skipped: int, failed: int):
        self.btn_execute_transfer.show()
        self.btn_cancel_transfer.hide()
        self.transfer_progress_box.hide()

        msg = f"اكتملت العملية بنجاح: تم نقل/نسخ {success} ملف."
        if skipped:
            msg += f"\nتم تخطي {skipped} ملف موجود مسبقاً."
        if failed:
            msg += f"\nفشل معالجة {failed} ملف."

        QMessageBox.information(self, "اكتمل النقل", msg)
        self.status_changed.emit(f"اكتملت العملية: {success} ملف.", False, False)

        # Clear transfer table
        self._on_clear_source_files()

    def _on_transfer_failed(self, error_msg: str):
        self.btn_execute_transfer.show()
        self.btn_cancel_transfer.hide()
        self.transfer_progress_box.hide()
        QMessageBox.critical(self, "خطأ في النقل", f"تعذر إكمال العملية:\n{error_msg}")

    # --------------------------------------------------------
    # DRAG AND DROP
    # --------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return

        # If on duplicate tab, set directory
        if self.tabs.currentIndex() == 0:
            p = Path(urls[0].toLocalFile())
            if p.is_dir():
                self.set_directory(p)
            elif p.is_file():
                self.set_directory(p.parent)
        else:
            # Transfer tab: add dropped files
            for u in urls:
                p = Path(u.toLocalFile())
                if p.is_file() and p not in self.transfer_source_files:
                    self.transfer_source_files.append(p)
                elif p.is_dir():
                    for f in p.glob('*'):
                        if f.is_file() and f not in self.transfer_source_files:
                            self.transfer_source_files.append(f)
            self._populate_transfer_table()
