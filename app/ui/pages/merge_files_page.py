# -*- coding: utf-8 -*-
"""
SINAX Merge Files Page
Professional, responsive File Merging & Bundling tool with drag-and-drop ordering,
smart auto-sorting, live preview, and multi-format support (PDF, DOCX, XLSX, Images, ZIP).
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QScrollArea,
    QFileDialog, QMessageBox, QProgressBar, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize, QItemSelectionModel
from PySide6.QtGui import QIcon, QColor

from app.core.constants import APP_NAME, FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.core.logger import get_logger
from app.core.undo_manager import undo_manager
from app.models.file_item import format_file_size
from app.services.file_service import FileService
from app.services.rename_service import RenameService
from app.services.merge_service import MergeService
from app.workers.merge_worker import MergeWorker
from app.ui.icons import get_icon

logger = get_logger("merge_page")


class MergeTableWidget(QTableWidget):
    """QTableWidget with robust row selection in RTL and offscreen headless modes."""
    def selectRow(self, row: int):
        super().selectRow(row)
        if 0 <= row < self.rowCount():
            if self.selectionModel():
                self.selectionModel().select(self.model().index(row, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)
            self.setCurrentCell(row, 0)


class MergeFilesPage(QWidget):
    """Interactive File Merging & Bundling Hub Page."""
    
    status_changed = Signal(str, bool, bool)  # text, is_loading, is_error
    progress_changed = Signal(int, int)  # current, total
    back_to_hub_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files_list: List[Path] = []
        self.merge_worker: Optional[MergeWorker] = None
        self.current_detected_mode: Dict[str, Any] = {}
        self.setAcceptDrops(True)

        self._init_ui()

    def _wrap_in_scroll(self, content_widget: QWidget) -> QScrollArea:
        """Wraps a widget in a clean, borderless QScrollArea."""
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
        # 1. TOP TOOLBAR: File picking, folder adding, sorting
        # ----------------------------------------------------
        top_frame = QFrame()
        top_frame.setObjectName("topFrame")
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setSpacing(8)

        add_files_btn = QPushButton("  إضافة ملفات...")
        add_files_btn.setProperty("class", "PrimaryButton")
        add_files_btn.setIcon(get_icon("file", "#FFFFFF", 16))
        add_files_btn.setMinimumHeight(36)
        add_files_btn.setCursor(Qt.PointingHandCursor)
        add_files_btn.clicked.connect(self._on_add_files)
        top_layout.addWidget(add_files_btn)

        add_folder_btn = QPushButton("  إضافة مجلد...")
        add_folder_btn.setIcon(get_icon("folder_open", "#AAAAAA", 16))
        add_folder_btn.setMinimumHeight(36)
        add_folder_btn.setCursor(Qt.PointingHandCursor)
        add_folder_btn.clicked.connect(self._on_add_folder)
        top_layout.addWidget(add_folder_btn)

        clear_btn = QPushButton("  مسح الكل")
        clear_btn.setIcon(get_icon("trash", "#AAAAAA", 16))
        clear_btn.setMinimumHeight(36)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_files)
        top_layout.addWidget(clear_btn)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #444444;")
        top_layout.addWidget(sep)

        # Sorting combo & button
        lbl_sort = QLabel("الترتيب التلقائي:")
        lbl_sort.setStyleSheet("font-size: 12px; font-weight: 600;")
        top_layout.addWidget(lbl_sort)

        self.sort_combo = QComboBox()
        self.sort_combo.setMinimumHeight(36)
        self.sort_combo.addItem("الترتيب الذكي للأرقام (1, 2, 10)", "numeric")
        self.sort_combo.addItem("حسب الاسم (أ إلى ي)", "name_asc")
        self.sort_combo.addItem("حسب الاسم (ي إلى أ)", "name_desc")
        self.sort_combo.addItem("حسب التاريخ (من الأحدث للأقدم)", "date_desc")
        self.sort_combo.addItem("حسب التاريخ (من الأقدم للأحدث)", "date_asc")
        self.sort_combo.addItem("حسب الحجم (من الأصغر للأكبر)", "size_asc")
        self.sort_combo.addItem("حسب الحجم (من الأكبر للأصغر)", "size_desc")
        top_layout.addWidget(self.sort_combo)

        apply_sort_btn = QPushButton("تطبيق الترتيب")
        apply_sort_btn.setMinimumHeight(36)
        apply_sort_btn.setCursor(Qt.PointingHandCursor)
        apply_sort_btn.clicked.connect(self._apply_sorting)
        top_layout.addWidget(apply_sort_btn)

        top_layout.addStretch(1)

        back_btn = QPushButton("  العودة للمركز")
        back_btn.setIcon(get_icon("arrow_back", "#AAAAAA", 16))
        back_btn.setMinimumHeight(36)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_hub_requested.emit)
        top_layout.addWidget(back_btn)

        main_layout.addWidget(top_frame)

        # ----------------------------------------------------
        # 2. MAIN SPLITTER: File Table (Right/Center) & Rules Panel (Left)
        # ----------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- FILE TABLE PANEL ---
        table_panel = QFrame()
        table_panel.setObjectName("tablePanel")
        table_panel.setMinimumWidth(480)
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(10, 10, 10, 10)
        table_layout.setSpacing(8)

        # Order manipulation buttons bar
        order_bar = QHBoxLayout()
        order_bar.setSpacing(6)

        lbl_table_tip = QLabel("اسحب الملفات لتغيير ترتيبها، أو استخدم الأزرار:")
        lbl_table_tip.setStyleSheet("font-size: 11px; color: #888888;")
        order_bar.addWidget(lbl_table_tip)
        order_bar.addStretch(1)

        self.btn_move_top = QPushButton("  ⤒ للبداية")
        self.btn_move_top.setMinimumHeight(30)
        self.btn_move_top.setCursor(Qt.PointingHandCursor)
        self.btn_move_top.clicked.connect(self._move_to_top)
        order_bar.addWidget(self.btn_move_top)

        self.btn_move_up = QPushButton("  ⬆ للأعلى")
        self.btn_move_up.setMinimumHeight(30)
        self.btn_move_up.setCursor(Qt.PointingHandCursor)
        self.btn_move_up.clicked.connect(self._move_up)
        order_bar.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("  ⬇ للأسفل")
        self.btn_move_down.setMinimumHeight(30)
        self.btn_move_down.setCursor(Qt.PointingHandCursor)
        self.btn_move_down.clicked.connect(self._move_down)
        order_bar.addWidget(self.btn_move_down)

        self.btn_move_bottom = QPushButton("  ⤓ للنهاية")
        self.btn_move_bottom.setMinimumHeight(30)
        self.btn_move_bottom.setCursor(Qt.PointingHandCursor)
        self.btn_move_bottom.clicked.connect(self._move_to_bottom)
        order_bar.addWidget(self.btn_move_bottom)

        self.btn_remove = QPushButton("  ✕ إزالة")
        self.btn_remove.setProperty("class", "DangerButton")
        self.btn_remove.setMinimumHeight(30)
        self.btn_remove.setCursor(Qt.PointingHandCursor)
        self.btn_remove.clicked.connect(self._remove_selected)
        order_bar.addWidget(self.btn_remove)

        table_layout.addLayout(order_bar)

        # Table widget
        self.table = MergeTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "اسم الملف", "النوع", "الحجم", "المسار الكامل"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(1, 260)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().hide()
        self.table.itemSelectionChanged.connect(self._update_button_states)
        table_layout.addWidget(self.table, 1)

        self.table_footer = QLabel("لا توجد ملفات محددة. قم بإضافة ملفات أو اسحبها إلى هنا.")
        self.table_footer.setStyleSheet("font-size: 11px; color: #888888; padding: 2px 4px;")
        table_layout.addWidget(self.table_footer)

        splitter.addWidget(table_panel)

        # --- SETTINGS & EXECUTION PANEL ---
        settings_panel = QFrame()
        settings_panel.setObjectName("rulesPanel")
        settings_panel.setMinimumWidth(400)
        settings_outer_layout = QVBoxLayout(settings_panel)
        settings_outer_layout.setContentsMargins(0, 0, 0, 0)
        settings_outer_layout.setSpacing(0)

        # Content widget for scroll area
        content_widget = QWidget()
        rules_layout = QVBoxLayout(content_widget)
        rules_layout.setContentsMargins(12, 12, 12, 12)
        rules_layout.setSpacing(12)

        # 1. Detection Badge Card
        self.mode_card = QFrame()
        self.mode_card.setObjectName("summaryCard")
        mc_layout = QVBoxLayout(self.mode_card)
        mc_layout.setContentsMargins(12, 10, 12, 10)
        mc_layout.setSpacing(4)

        self.mode_title = QLabel("في انتظار تحديد الملفات...")
        self.mode_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #60CDFF;")
        mc_layout.addWidget(self.mode_title)

        self.mode_desc = QLabel("حدد ملفات لاكتشاف نوع الدمج الأمثل تلقائياً.")
        self.mode_desc.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        self.mode_desc.setWordWrap(True)
        mc_layout.addWidget(self.mode_desc)

        rules_layout.addWidget(self.mode_card)

        # 2. Options Group
        self.options_box = QGroupBox("خيارات الدمج والتجميع")
        opt_layout = QVBoxLayout(self.options_box)
        opt_layout.setContentsMargins(14, 22, 14, 14)
        opt_layout.setSpacing(10)

        # Image-specific mode
        self.img_mode_label = QLabel("طريقة دمج الصور:")
        self.img_mode_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        opt_layout.addWidget(self.img_mode_label)

        self.img_mode_combo = QComboBox()
        self.img_mode_combo.setMinimumHeight(36)
        self.img_mode_combo.addItem("تحويل الصور إلى مستند PDF واحد", "images_pdf")
        self.img_mode_combo.addItem("دمج الصور رأسياً (Vertical Stitch)", "images_stitch_v")
        self.img_mode_combo.addItem("دمج الصور أفقياً (Horizontal Stitch)", "images_stitch_h")
        self.img_mode_combo.addItem("تجميع الصور في ملف مضغوط ZIP", "zip")
        self.img_mode_combo.currentIndexChanged.connect(self._on_img_mode_changed)
        opt_layout.addWidget(self.img_mode_combo)

        # Excel-specific mode
        self.excel_mode_label = QLabel("طريقة دمج جداول Excel:")
        self.excel_mode_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        opt_layout.addWidget(self.excel_mode_label)

        self.excel_mode_combo = QComboBox()
        self.excel_mode_combo.setMinimumHeight(36)
        self.excel_mode_combo.addItem("كل ملف في ورقة عمل مستقلة (Sheet)", "sheets")
        self.excel_mode_combo.addItem("دمج الصفوف في ورقة عمل واحدة (Concat)", "concat")
        opt_layout.addWidget(self.excel_mode_combo)

        # Word page break checkbox
        self.docx_page_break_cb = QCheckBox("إدراج فاصل صفحات بين المستندات المدمجة")
        self.docx_page_break_cb.setChecked(True)
        self.docx_page_break_cb.setMinimumHeight(28)
        opt_layout.addWidget(self.docx_page_break_cb)

        # Video / FFmpeg notice label
        self.video_notice_lbl = QLabel()
        self.video_notice_lbl.setWordWrap(True)
        self.video_notice_lbl.setStyleSheet("font-size: 11px; color: #FFA940; background-color: rgba(250, 140, 22, 0.1); padding: 8px; border-radius: 4px;")
        opt_layout.addWidget(self.video_notice_lbl)

        rules_layout.addWidget(self.options_box)

        # 3. Output Configuration Group
        out_box = QGroupBox("الملف الناتج ومكان الحفظ")
        out_layout = QVBoxLayout(out_box)
        out_layout.setContentsMargins(14, 22, 14, 14)
        out_layout.setSpacing(10)

        lbl_out_name = QLabel("اسم الملف الناتج:")
        lbl_out_name.setStyleSheet("font-size: 12px; font-weight: 600;")
        out_layout.addWidget(lbl_out_name)

        self.out_name_edit = QLineEdit("ملف_مدمج.pdf")
        self.out_name_edit.setMinimumHeight(36)
        self.out_name_edit.textChanged.connect(self._update_preview)
        out_layout.addWidget(self.out_name_edit)

        lbl_out_dir = QLabel("مجلد الحفظ:")
        lbl_out_dir.setStyleSheet("font-size: 12px; font-weight: 600;")
        out_layout.addWidget(lbl_out_dir)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)

        self.out_dir_edit = QLineEdit(str(Path.home() / "Desktop"))
        self.out_dir_edit.setMinimumHeight(36)
        dir_row.addWidget(self.out_dir_edit, 1)

        browse_dir_btn = QPushButton("استعراض...")
        browse_dir_btn.setMinimumHeight(36)
        browse_dir_btn.setCursor(Qt.PointingHandCursor)
        browse_dir_btn.clicked.connect(self._on_browse_output_dir)
        dir_row.addWidget(browse_dir_btn)

        out_layout.addLayout(dir_row)
        rules_layout.addWidget(out_box)

        # 4. Live Merge Preview Group
        prev_box = QGroupBox("معاينة ترتيب الدمج")
        prev_layout = QVBoxLayout(prev_box)
        prev_layout.setContentsMargins(14, 22, 14, 14)
        prev_layout.setSpacing(6)

        self.preview_lbl = QLabel("أضف ملفات لعرض المعاينة التسلسلية.")
        self.preview_lbl.setStyleSheet("font-size: 11px; color: #CCCCCC; line-height: 1.5;")
        self.preview_lbl.setWordWrap(True)
        prev_layout.addWidget(self.preview_lbl)

        rules_layout.addWidget(prev_box)

        # 5. Progress & Execution section
        self.progress_box = QFrame()
        pb_layout = QVBoxLayout(self.progress_box)
        pb_layout.setContentsMargins(0, 4, 0, 4)
        pb_layout.setSpacing(6)

        self.progress_lbl = QLabel("جاري المعالجة...")
        self.progress_lbl.setStyleSheet("font-size: 11px; color: #60CDFF;")
        pb_layout.addWidget(self.progress_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        pb_layout.addWidget(self.progress_bar)
        self.progress_box.hide()

        rules_layout.addWidget(self.progress_box)

        # Action Buttons
        btn_box = QVBoxLayout()
        btn_box.setSpacing(8)

        self.merge_btn = QPushButton("  بدء عملية الدمج والتجميع")
        self.merge_btn.setProperty("class", "PrimaryButton")
        self.merge_btn.setIcon(get_icon("play", "#FFFFFF", 16))
        self.merge_btn.setMinimumHeight(40)
        self.merge_btn.setCursor(Qt.PointingHandCursor)
        self.merge_btn.clicked.connect(self._on_start_merge)
        btn_box.addWidget(self.merge_btn)

        self.cancel_btn = QPushButton("  إلغاء العملية")
        self.cancel_btn.setProperty("class", "DangerButton")
        self.cancel_btn.setMinimumHeight(34)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._on_cancel_merge)
        self.cancel_btn.hide()
        btn_box.addWidget(self.cancel_btn)

        rules_layout.addLayout(btn_box)
        rules_layout.addStretch(1)

        scroll_area = self._wrap_in_scroll(content_widget)
        settings_outer_layout.addWidget(scroll_area)

        splitter.addWidget(settings_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([650, 420])
        main_layout.addWidget(splitter, 1)

        self._update_button_states()
        self._on_files_changed()

    # ----------------------------------------------------
    # FILE LIST MANAGEMENT & DRAG AND DROP
    # ----------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths: List[Path] = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_file():
                paths.append(p)
            elif p.is_dir():
                for f in p.glob("*"):
                    if f.is_file():
                        paths.append(f)

        if paths:
            self.add_paths(paths)

    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "اختر الملفات للدمج والتجميع",
            str(Path.home() / "Desktop"),
            "كافة الملفات المدعومة (*.pdf *.docx *.xlsx *.png *.jpg *.jpeg *.bmp *.mp4 *.mkv *.zip);;ملفات PDF (*.pdf);;مستندات Word (*.docx);;جداول Excel (*.xlsx);;الصور (*.png *.jpg *.jpeg);;جميع الملفات (*.*)"
        )
        if files:
            self.add_paths([Path(f) for f in files])

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "اختر المجلد لإضافة ملفاته",
            str(Path.home() / "Desktop")
        )
        if folder:
            p = Path(folder)
            files = [f for f in p.glob("*") if f.is_file()]
            self.add_paths(files)

    def add_paths(self, new_paths: List[Path]):
        existing_set = set(self.files_list)
        for p in new_paths:
            if p not in existing_set and p.is_file():
                self.files_list.append(p)
                existing_set.add(p)

        if self.files_list and not self.out_dir_edit.text():
            self.out_dir_edit.setText(str(self.files_list[0].parent))

        self._refresh_table()
        self._on_files_changed()

    def _clear_files(self):
        self.files_list.clear()
        self._refresh_table()
        self._on_files_changed()

    def _refresh_table(self):
        self.table.setRowCount(0)
        total_bytes = 0

        for idx, p in enumerate(self.files_list):
            self.table.insertRow(idx)

            # 0: Order index
            it_idx = QTableWidgetItem(str(idx + 1))
            it_idx.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 0, it_idx)

            # 1: Filename
            ext = p.suffix.lower()
            cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
            cat_info = FILE_CATEGORIES.get(cat_key, {"color": "#888888", "label_ar": "ملف"})
            cat_color = cat_info.get("color", "#888888")
            cat_label = cat_info.get("label_ar", "ملف")
            icon_map = {
                'pdf': 'pdf',
                'word': 'word',
                'excel': 'excel',
                'powerpoint': 'powerpoint',
                'images': 'image',
                'videos': 'video',
                'audio': 'audio',
                'archive': 'archive'
            }
            icon_name = icon_map.get(cat_key, "file")
            icon = get_icon(icon_name, cat_color, 16)

            it_name = QTableWidgetItem(icon, p.name)
            self.table.setItem(idx, 1, it_name)

            # 2: Type
            it_type = QTableWidgetItem(cat_label)
            it_type.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 2, it_type)

            # 3: Size
            try:
                sz = p.stat().st_size
                total_bytes += sz
                sz_str = format_file_size(sz)
            except Exception:
                sz_str = "غير معروف"

            it_sz = QTableWidgetItem(sz_str)
            it_sz.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 3, it_sz)

            # 4: Full Path
            it_path = QTableWidgetItem(str(p.parent))
            it_path.setForeground(QColor("#777777"))
            self.table.setItem(idx, 4, it_path)

        count = len(self.files_list)
        if count == 0:
            self.table_footer.setText("لا توجد ملفات محددة. قم بإضافة ملفات أو اسحبها إلى هنا.")
        else:
            total_sz_str = format_file_size(total_bytes)
            self.table_footer.setText(f"إجمالي الملفات: {count} ملف | الحجم الإجمالي: {total_sz_str}")

        self._update_button_states()

    # ----------------------------------------------------
    # ROW ORDER MANIPULATION
    # ----------------------------------------------------
    def _get_selected_row(self) -> int:
        sel = self.table.selectedItems()
        if sel:
            return sel[0].row()
        return -1

    def _move_up(self):
        row = self._get_selected_row()
        if row > 0:
            self.files_list[row], self.files_list[row - 1] = self.files_list[row - 1], self.files_list[row]
            self._refresh_table()
            self.table.selectRow(row - 1)
            self._update_preview()

    def _move_down(self):
        row = self._get_selected_row()
        if 0 <= row < len(self.files_list) - 1:
            self.files_list[row], self.files_list[row + 1] = self.files_list[row + 1], self.files_list[row]
            self._refresh_table()
            self.table.selectRow(row + 1)
            self._update_preview()

    def _move_to_top(self):
        row = self._get_selected_row()
        if row > 0:
            item = self.files_list.pop(row)
            self.files_list.insert(0, item)
            self._refresh_table()
            self.table.selectRow(0)
            self._update_preview()

    def _move_to_bottom(self):
        row = self._get_selected_row()
        if 0 <= row < len(self.files_list) - 1:
            item = self.files_list.pop(row)
            self.files_list.append(item)
            self._refresh_table()
            self.table.selectRow(len(self.files_list) - 1)
            self._update_preview()

    def _remove_selected(self):
        row = self._get_selected_row()
        if 0 <= row < len(self.files_list):
            self.files_list.pop(row)
            self._refresh_table()
            if self.files_list:
                new_row = min(row, len(self.files_list) - 1)
                self.table.selectRow(new_row)
            self._on_files_changed()

    def _update_button_states(self):
        row = self._get_selected_row()
        count = len(self.files_list)
        has_sel = (row >= 0)

        self.btn_move_up.setEnabled(has_sel and row > 0)
        self.btn_move_top.setEnabled(has_sel and row > 0)
        self.btn_move_down.setEnabled(has_sel and row < count - 1)
        self.btn_move_bottom.setEnabled(has_sel and row < count - 1)
        self.btn_remove.setEnabled(has_sel)

    # ----------------------------------------------------
    # SMART AUTO-SORTING
    # ----------------------------------------------------
    def _apply_sorting(self):
        if len(self.files_list) <= 1:
            return

        mode = self.sort_combo.currentData()

        if mode == "numeric":
            import re
            def natural_key(p: Path):
                return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', p.name)]
            self.files_list.sort(key=natural_key)

        elif mode == "name_asc":
            self.files_list.sort(key=lambda p: p.name.lower())

        elif mode == "name_desc":
            self.files_list.sort(key=lambda p: p.name.lower(), reverse=True)

        elif mode == "date_desc":
            self.files_list.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

        elif mode == "date_asc":
            self.files_list.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0)

        elif mode == "size_asc":
            self.files_list.sort(key=lambda p: p.stat().st_size if p.exists() else 0)

        elif mode == "size_desc":
            self.files_list.sort(key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)

        self._refresh_table()
        self._update_preview()
        self.status_changed.emit("تمت إعادة ترتيب الملفات بنجاح.", False, False)

    # ----------------------------------------------------
    # DETECTION & LIVE PREVIEW
    # ----------------------------------------------------
    def _on_files_changed(self):
        if not self.files_list:
            self.mode_title.setText("في انتظار تحديد الملفات...")
            self.mode_desc.setText("حدد ملفات لاكتشاف نوع الدمج الأمثل تلقائياً.")
            self.options_box.hide()
            self.merge_btn.setEnabled(False)
            self.preview_lbl.setText("أضف ملفات لعرض المعاينة التسلسلية.")
            return

        self.current_detected_mode = MergeService.detect_merge_mode(self.files_list)
        mode = self.current_detected_mode["mode"]

        self.mode_title.setText(f"النمط المكتشف: {self.current_detected_mode['label_ar']}")
        self.options_box.show()
        self.merge_btn.setEnabled(True)

        # Update controls visibility based on detected mode
        self.img_mode_label.hide()
        self.img_mode_combo.hide()
        self.excel_mode_label.hide()
        self.excel_mode_combo.hide()
        self.docx_page_break_cb.hide()
        self.video_notice_lbl.hide()

        if mode == "pdf":
            self.mode_desc.setText("سيتم دمج صفحات جميع ملفات PDF في مستند واحد مع الحفاظ على التخطيط.")
            self.out_name_edit.setText(self.current_detected_mode.get("suggested_name", "مستند_مدمج.pdf"))

        elif mode == "docx":
            self.mode_desc.setText("سيتم دمج نصوص وجداول مستندات Word في مستند واحد.")
            self.docx_page_break_cb.show()
            self.out_name_edit.setText(self.current_detected_mode.get("suggested_name", "مستند_مدمج.docx"))

        elif mode == "excel":
            self.mode_desc.setText("سيتم تجميع أوراق العمل وجداول Excel المحددة.")
            self.excel_mode_label.show()
            self.excel_mode_combo.show()
            self.out_name_edit.setText(self.current_detected_mode.get("suggested_name", "بيانات_مجمعة.xlsx"))

        elif mode == "images":
            self.mode_desc.setText("حدد الخيار المفضل لمعالجة الصور المحددة.")
            self.img_mode_label.show()
            self.img_mode_combo.show()
            self._on_img_mode_changed()

        elif mode == "videos":
            import shutil
            has_ffmpeg = bool(shutil.which("ffmpeg"))
            if has_ffmpeg:
                self.video_notice_lbl.setText("✓ أداة FFmpeg متوفرة في النظام لدمج الفيديو.")
            else:
                self.video_notice_lbl.setText("ℹ تنبيه: أداة FFmpeg غير مثبتة في النظام. سيتم حزم الفيديوهات في ملف مضغوط ZIP عالي السرعة للحفاظ على سلامة الملفات.")
            self.video_notice_lbl.show()
            self.mode_desc.setText("تجميع الفيديوهات في حزمة مضغوطة ZIP آمنة.")
            self.out_name_edit.setText(self.current_detected_mode.get("suggested_name", "فيديوهات.zip"))

        else:
            self.mode_desc.setText("ملفات مختلطة الامتدادات. سيتم حزمها معاً داخل أرشيف مضغوط ZIP.")
            self.out_name_edit.setText(self.current_detected_mode.get("suggested_name", "أرشيف_ملفات.zip"))

        self._update_preview()

    def _on_img_mode_changed(self):
        sel = self.img_mode_combo.currentData()
        if sel == "images_pdf":
            self.out_name_edit.setText("ألبوم_صور_مدمج.pdf")
        elif sel in ["images_stitch_v", "images_stitch_h"]:
            self.out_name_edit.setText("صورة_مدمجة.png")
        else:
            self.out_name_edit.setText("ألبوم_صور.zip")
        self._update_preview()

    def _update_preview(self):
        if not self.files_list:
            self.preview_lbl.setText("أضف ملفات لعرض المعاينة التسلسلية.")
            return

        lines = []
        for idx, p in enumerate(self.files_list[:6]):
            lines.append(f"{idx + 1} — {p.name}")

        if len(self.files_list) > 6:
            lines.append(f"... والمزيد ({len(self.files_list) - 6} ملف إضافي)")

        out_name = self.out_name_edit.text().strip() or "ملف_مدمج"
        lines.append("")
        lines.append(f"➔ الملف الناتج: <b style='color:#60CDFF;'>{out_name}</b>")

        self.preview_lbl.setText("<br>".join(lines))

    def _on_browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "اختر مجلد الحفظ",
            self.out_dir_edit.text() or str(Path.home() / "Desktop")
        )
        if dir_path:
            self.out_dir_edit.setText(dir_path)

    # ----------------------------------------------------
    # EXECUTION & BACKGROUND WORKER
    # ----------------------------------------------------
    def _on_start_merge(self):
        if not self.files_list:
            QMessageBox.warning(self, "تنبيه", "الرجاء إضافة ملفات أولاً قبل بدء الدمج.")
            return

        out_dir = Path(self.out_dir_edit.text().strip())
        if not out_dir.exists():
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "خطأ في المجلد", f"تعذر إنشاء مجلد الحفظ: {e}")
                return

        out_name = self.out_name_edit.text().strip()
        if not out_name:
            QMessageBox.warning(self, "تنبيه", "يرجى كتابة اسم صحيح للملف الناتج.")
            return

        out_path = out_dir / out_name

        # Determine effective mode
        base_mode = self.current_detected_mode.get("mode", "zip")
        extra_params: Dict[str, Any] = {}

        if base_mode == "images":
            img_choice = self.img_mode_combo.currentData()
            if img_choice == "images_pdf":
                eff_mode = "images_pdf"
            elif img_choice == "images_stitch_v":
                eff_mode = "images_stitch"
                extra_params["stitch_direction"] = "vertical"
            elif img_choice == "images_stitch_h":
                eff_mode = "images_stitch"
                extra_params["stitch_direction"] = "horizontal"
            else:
                eff_mode = "zip"

        elif base_mode == "excel":
            eff_mode = "excel"
            extra_params["excel_mode"] = self.excel_mode_combo.currentData()

        elif base_mode == "docx":
            eff_mode = "docx"
            extra_params["docx_page_breaks"] = self.docx_page_break_cb.isChecked()

        elif base_mode == "videos":
            eff_mode = "videos_zip"

        else:
            eff_mode = base_mode

        # Check existing output file overwrite
        if out_path.exists():
            reply = QMessageBox.question(
                self,
                "الملف موجود مسبقاً",
                f"الملف التالي موجود بالفعل في مسار الحفظ:\\n{out_name}\\n\\nهل تريد استبداله؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Start background worker
        self.merge_btn.setEnabled(False)
        self.cancel_btn.show()
        self.progress_box.show()
        self.progress_bar.setValue(0)
        self.progress_lbl.setText("جاري تهيئة العملية...")

        self.merge_worker = MergeWorker(
            mode=eff_mode,
            input_paths=self.files_list,
            output_path=out_path,
            extra_params=extra_params,
            parent=self
        )
        self.merge_worker.progress_updated.connect(self._on_merge_progress)
        self.merge_worker.merge_finished.connect(self._on_merge_finished)
        self.merge_worker.merge_failed.connect(self._on_merge_failed)
        self.merge_worker.operation_canceled.connect(self._on_merge_canceled)
        self.merge_worker.start()

        self.status_changed.emit("جاري تنفيذ عملية الدمج في الخلفية...", True, False)

    def _on_merge_progress(self, current: int, total: int, filename: str, percent: int):
        self.progress_bar.setValue(percent)
        self.progress_lbl.setText(f"معالجة {current} من {total} ({percent}%): {filename}")
        self.progress_changed.emit(current, total)

    def _on_merge_finished(self, out_path_str: str, elapsed: float):
        self.merge_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress_box.hide()
        self.status_changed.emit(f"اكتملت العملية بنجاح خلال {elapsed} ثانية.", False, False)

        # Record in UndoManager
        out_path = Path(out_path_str)
        undo_manager.record(
            operation_type="merge",
            items_count=len(self.files_list),
            details={
                "output_path": str(out_path),
                "inputs_count": len(self.files_list),
                "elapsed": elapsed
            }
        )

        msg = QMessageBox(self)
        msg.setWindowTitle("تم الدمج بنجاح")
        msg.setText(f"<b>اكتملت عملية الدمج والتجميع بنجاح!</b><br><br>الملف الناتج: {out_path.name}<br>استغرقت العملية: {elapsed} ثانية.")
        btn_open = msg.addButton("  فتح الملف الناتج", QMessageBox.ActionRole)
        btn_folder = msg.addButton("  فتح المجلد الحاوي", QMessageBox.ActionRole)
        btn_ok = msg.addButton("  تم", QMessageBox.AcceptRole)

        msg.exec()

        if msg.clickedButton() == btn_open:
            if out_path.exists():
                os.startfile(str(out_path))
        elif msg.clickedButton() == btn_folder:
            if out_path.exists():
                subprocess.run(f'explorer /select,"{str(out_path)}"', shell=True)

    def _on_merge_failed(self, err_msg: str):
        self.merge_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress_box.hide()
        self.status_changed.emit(f"فشلت عملية الدمج: {err_msg}", False, True)
        QMessageBox.critical(self, "خطأ في الدمج", f"حدث خطأ أثناء تنفيذ عملية الدمج:\\n\\n{err_msg}")

    def _on_cancel_merge(self):
        if self.merge_worker and self.merge_worker.isRunning():
            self.progress_lbl.setText("جاري إيقاف العملية...")
            self.merge_worker.cancel()

    def _on_merge_canceled(self):
        self.merge_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress_box.hide()
        self.status_changed.emit("تم إلغاء عملية الدمج.", False, False)
        QMessageBox.information(self, "تم الإلغاء", "تم إلغاء العملية بأمان.")
