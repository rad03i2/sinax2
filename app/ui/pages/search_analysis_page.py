# -*- coding: utf-8 -*-
"""
SINAX Advanced Search & Storage Analysis Page
Modern, responsive Fluent interface with two primary tabs:
1. Advanced Search: Regex, wildcards, metadata filters, full-text content search.
2. Storage & Space Dashboard: KPI metric cards, category space breakdown with colored bars, and top space hogs.
"""

import csv
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QScrollArea,
    QFileDialog, QMessageBox, QProgressBar, QAbstractItemView,
    QTabWidget, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QAction, QCursor

from app.core.constants import APP_NAME, FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.core.config import config
from app.core.logger import get_logger
from app.models.file_item import format_file_size
from app.services.file_service import FileService
from app.services.search_service import SearchService, SearchFilter, SearchResultItem
from app.services.storage_analysis_service import (
    StorageAnalysisService, StorageReport, CategorySpaceInfo, StorageItemInfo
)
from app.workers.search_worker import SearchWorker
from app.workers.storage_worker import StorageWorker
from app.ui.icons import get_icon

logger = get_logger("search_analysis_page")


class SearchAnalysisPage(QWidget):
    """Integrated Advanced Search and Storage Analytics Page."""

    status_changed = Signal(str, bool, bool)  # text, is_loading, is_error
    progress_changed = Signal(int, int)       # current, total
    back_to_hub_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_folder: Optional[Path] = None
        self.search_results: List[SearchResultItem] = []
        self.current_storage_report: Optional[StorageReport] = None

        self.search_worker: Optional[SearchWorker] = None
        self.storage_worker: Optional[StorageWorker] = None

        self.setAcceptDrops(True)
        self._kpi_card_list = []
        self._init_ui()
        from app.ui.themes.theme_manager import theme_manager
        theme_manager.theme_changed.connect(self._on_theme_changed)

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
        self.path_edit.setPlaceholderText("اختر المجلد المراد فحصه أو اسحبه إلى هنا...")
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
        # 2. MAIN TAB WIDGET: Search Tab vs Storage Tab
        # ----------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setCursor(Qt.ArrowCursor)

        # Tab 1: Advanced Search
        self.search_tab = QWidget()
        self._init_search_tab(self.search_tab)
        self.tabs.addTab(self.search_tab, "  البحث الذكي المتقدم  ")

        # Tab 2: Storage & Disk Space Dashboard
        self.storage_tab = QWidget()
        self._init_storage_tab(self.storage_tab)
        self.tabs.addTab(self.storage_tab, "  لوحة تحليل مساحة التخزين  ")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs, 1)

    # --------------------------------------------------------
    # TAB 1: ADVANCED SEARCH
    # --------------------------------------------------------
    def _init_search_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # A. Search Controls Panel
        ctrl_frame = QFrame()
        ctrl_frame.setObjectName("rulesPanel")
        ctrl_layout = QVBoxLayout(ctrl_frame)
        ctrl_layout.setContentsMargins(12, 12, 12, 12)
        ctrl_layout.setSpacing(10)

        # Row 1: Search query input + Search buttons
        r1 = QHBoxLayout()
        r1.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(r"أدخل اسم الملف، عبارة البحث، أو التعبير النمطي (مثال: *.pdf, report_\d+)...")
        self.search_input.setMinimumHeight(36)
        self.search_input.returnPressed.connect(self._start_search)
        r1.addWidget(self.search_input, 1)

        self.btn_search = QPushButton("  بدء البحث")
        self.btn_search.setProperty("class", "PrimaryButton")
        self.btn_search.setIcon(get_icon("search", "#FFFFFF", 16))
        self.btn_search.setMinimumHeight(36)
        self.btn_search.setCursor(Qt.PointingHandCursor)
        self.btn_search.clicked.connect(self._start_search)
        r1.addWidget(self.btn_search)

        self.btn_cancel_search = QPushButton("  إلغاء")
        self.btn_cancel_search.setProperty("class", "DangerButton")
        self.btn_cancel_search.setMinimumHeight(36)
        self.btn_cancel_search.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_search.clicked.connect(self._cancel_search)
        self.btn_cancel_search.hide()
        r1.addWidget(self.btn_cancel_search)

        self.btn_clear_results = QPushButton("مسح النتائج")
        self.btn_clear_results.setMinimumHeight(36)
        self.btn_clear_results.setCursor(Qt.PointingHandCursor)
        self.btn_clear_results.clicked.connect(self._clear_search_results)
        r1.addWidget(self.btn_clear_results)

        ctrl_layout.addLayout(r1)

        # Row 2: Search Toggles & Criteria
        r2 = QHBoxLayout()
        r2.setSpacing(16)

        self.cb_regex = QCheckBox("تعبير نمطي (Regex)")
        r2.addWidget(self.cb_regex)

        self.cb_case = QCheckBox("مطابقة حالة الأحرف (Case)")
        r2.addWidget(self.cb_case)

        self.cb_recursive = QCheckBox("تضمين المجلدات الفرعية (Recursive)")
        self.cb_recursive.setChecked(True)
        r2.addWidget(self.cb_recursive)

        self.cb_hidden = QCheckBox("الملفات المخفية")
        r2.addWidget(self.cb_hidden)

        r2.addStretch(1)
        ctrl_layout.addLayout(r2)

        # Row 3: Extended Filters (Category, Size, Date, Content)
        r3 = QHBoxLayout()
        r3.setSpacing(12)

        # Category
        lbl_cat = QLabel("التصنيف:")
        lbl_cat.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        r3.addWidget(lbl_cat)

        self.search_cat_combo = QComboBox()
        self.search_cat_combo.setMinimumHeight(32)
        self.search_cat_combo.addItem("جميع الملفات", "all")
        for k, v in FILE_CATEGORIES.items():
            if k not in ("all", "other"):
                self.search_cat_combo.addItem(v.get("label_ar", k), k)
        self.search_cat_combo.addItem("ملفات أخرى", "other")
        r3.addWidget(self.search_cat_combo)

        # Size preset
        lbl_sz = QLabel("الحجم:")
        lbl_sz.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        r3.addWidget(lbl_sz)

        self.search_size_combo = QComboBox()
        self.search_size_combo.setMinimumHeight(32)
        self.search_size_combo.addItem("أي حجم", "any")
        self.search_size_combo.addItem("أقل من 1 م.ب", "<1MB")
        self.search_size_combo.addItem("1 - 100 م.ب", "1-100MB")
        self.search_size_combo.addItem("أكبر من 100 م.ب", ">100MB")
        self.search_size_combo.addItem("أكبر من 1 ج.ب", ">1GB")
        r3.addWidget(self.search_size_combo)

        # Date preset
        lbl_dt = QLabel("تاريخ التعديل:")
        lbl_dt.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        r3.addWidget(lbl_dt)

        self.search_date_combo = QComboBox()
        self.search_date_combo.setMinimumHeight(32)
        self.search_date_combo.addItem("أي تاريخ", "any")
        self.search_date_combo.addItem("خلال آخر 24 ساعة", "1day")
        self.search_date_combo.addItem("خلال آخر أسبوع", "7days")
        self.search_date_combo.addItem("خلال آخر شهر", "30days")
        self.search_date_combo.addItem("خلال هذا العام", "year")
        r3.addWidget(self.search_date_combo)

        # Full-text content search
        lbl_cont = QLabel("البحث داخل المحتوى:")
        lbl_cont.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        r3.addWidget(lbl_cont)

        self.content_search_input = QLineEdit()
        self.content_search_input.setPlaceholderText("نص داخل ملفات txt, py, csv, json...")
        self.content_search_input.setMinimumHeight(32)
        self.content_search_input.returnPressed.connect(self._start_search)
        r3.addWidget(self.content_search_input, 1)

        ctrl_layout.addLayout(r3)
        layout.addWidget(ctrl_frame)

        # B. Search Results Table
        self.search_table = QTableWidget(0, 6)
        self.search_table.setHorizontalHeaderLabels([
            "#", "اسم الملف", "التصنيف", "الحجم", "تاريخ التعديل", "المسار / سطر التطابق"
        ])
        self.search_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.search_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.search_table.horizontalHeader().setStretchLastSection(True)
        self.search_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.search_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.search_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.search_table.setColumnWidth(1, 240)
        self.search_table.verticalHeader().setDefaultSectionSize(32)
        self.search_table.verticalHeader().hide()
        self.search_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.search_table.customContextMenuRequested.connect(self._show_search_context_menu)
        self.search_table.itemDoubleClicked.connect(self._on_search_item_double_clicked)
        layout.addWidget(self.search_table, 1)

        # C. Search Footer & Export Toolbar
        footer_row = QHBoxLayout()
        self.search_footer_lbl = QLabel("جاهز للبحث. اختر مجلداً وأدخل معايير البحث.")
        self.search_footer_lbl.setStyleSheet("font-size: 11px; color: #888888;")
        footer_row.addWidget(self.search_footer_lbl, 1)

        self.btn_export_csv = QPushButton("  تصدير النتائج إلى CSV")
        self.btn_export_csv.setIcon(get_icon("excel", "#107C41", 14))
        self.btn_export_csv.setMinimumHeight(30)
        self.btn_export_csv.setCursor(Qt.PointingHandCursor)
        self.btn_export_csv.setEnabled(False)
        self.btn_export_csv.clicked.connect(self._export_search_csv)
        footer_row.addWidget(self.btn_export_csv)

        layout.addLayout(footer_row)

    # --------------------------------------------------------
    # TAB 2: STORAGE & SPACE DASHBOARD
    # --------------------------------------------------------
    def _init_storage_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Header toolbar for Storage Dashboard
        dash_bar = QHBoxLayout()
        dash_title = QLabel("لوحة إحصائيات وتوزيع مساحة التخزين")
        dash_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        dash_bar.addWidget(dash_title)

        dash_bar.addStretch(1)

        self.btn_analyze_storage = QPushButton("  فحص وتحليل المساحة الآن")
        self.btn_analyze_storage.setProperty("class", "PrimaryButton")
        self.btn_analyze_storage.setIcon(get_icon("search", "#FFFFFF", 16))
        self.btn_analyze_storage.setMinimumHeight(34)
        self.btn_analyze_storage.setCursor(Qt.PointingHandCursor)
        self.btn_analyze_storage.clicked.connect(self._start_storage_analysis)
        dash_bar.addWidget(self.btn_analyze_storage)

        self.btn_cancel_storage = QPushButton("  إلغاء الفحص")
        self.btn_cancel_storage.setProperty("class", "DangerButton")
        self.btn_cancel_storage.setMinimumHeight(34)
        self.btn_cancel_storage.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_storage.clicked.connect(self._cancel_storage_analysis)
        self.btn_cancel_storage.hide()
        dash_bar.addWidget(self.btn_cancel_storage)

        layout.addLayout(dash_bar)

        # Storage Content inside a responsive ScrollArea
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(14)

        # 1. Metric Cards (KPIs)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.card_total_size = self._create_kpi_card("إجمالي المساحة المستهلكة", "0 بايت", "#60CDFF")
        self.card_total_files = self._create_kpi_card("إجمالي عدد الملفات", "0 ملف", "#52C41A")
        self.card_total_dirs = self._create_kpi_card("عدد المجلدات الفرعية", "0 مجلد", "#FFB900")

        kpi_layout.addWidget(self.card_total_size)
        kpi_layout.addWidget(self.card_total_files)
        kpi_layout.addWidget(self.card_total_dirs)
        sc_layout.addLayout(kpi_layout)

        # 2. Main Analytics Splitter
        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        # Left Panel: Category Storage Distribution
        cat_box = QGroupBox("توزيع المساحة حسب تصنيف الملفات")
        cat_box_layout = QVBoxLayout(cat_box)
        cat_box_layout.setContentsMargins(14, 20, 14, 14)
        cat_box_layout.setSpacing(10)

        self.cat_bars_widget = QWidget()
        self.cat_bars_layout = QVBoxLayout(self.cat_bars_widget)
        self.cat_bars_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_bars_layout.setSpacing(10)

        self.empty_cats_lbl = QLabel("اضغط على 'فحص وتحليل المساحة الآن' لعرض مخطط التوزيع.")
        self.empty_cats_lbl.setStyleSheet("color: #888888; font-size: 12px; padding: 20px;")
        self.empty_cats_lbl.setAlignment(Qt.AlignCenter)
        self.cat_bars_layout.addWidget(self.empty_cats_lbl)

        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cat_scroll.verticalScrollBar().setSingleStep(28)
        cat_scroll.setWidget(self.cat_bars_widget)
        cat_box_layout.addWidget(cat_scroll)

        split.addWidget(cat_box)

        # Right Panel: Top Largest Space Hogs
        top_box = QGroupBox("أكبر الملفات حجماً في المجلد (Space Hogs)")
        top_box_layout = QVBoxLayout(top_box)
        top_box_layout.setContentsMargins(14, 20, 14, 14)
        top_box_layout.setSpacing(8)

        self.top_table = QTableWidget(0, 4)
        self.top_table.setHorizontalHeaderLabels(["#", "اسم الملف", "الحجم", "المسار الكامل"])
        self.top_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.top_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.top_table.horizontalHeader().setStretchLastSection(True)
        self.top_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.top_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.top_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.top_table.setColumnWidth(1, 200)
        self.top_table.verticalHeader().hide()
        self.top_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.top_table.customContextMenuRequested.connect(self._show_top_context_menu)
        self.top_table.itemDoubleClicked.connect(self._on_top_item_double_clicked)
        top_box_layout.addWidget(self.top_table, 1)

        split.addWidget(top_box)
        split.setSizes([380, 520])

        sc_layout.addWidget(split, 1)

        scroll_area = self._wrap_in_scroll(scroll_content)
        layout.addWidget(scroll_area, 1)

    def _create_kpi_card(self, title: str, default_val: str, accent_color: str) -> QFrame:
        """Creates a modern Fluent KPI stat card."""
        card = QFrame()
        card.setProperty("accent_color", accent_color)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(4)

        lbl_t = QLabel(title)
        lbl_t.setObjectName("kpiTitle")
        c_layout.addWidget(lbl_t)

        lbl_v = QLabel(default_val)
        lbl_v.setObjectName("kpiValue")
        c_layout.addWidget(lbl_v)

        if not hasattr(self, "_kpi_card_list"):
            self._kpi_card_list = []
        self._kpi_card_list.append(card)

        self._style_kpi_card(card)
        return card

    def _style_kpi_card(self, card: QFrame, theme_name: Optional[str] = None):
        if theme_name is None:
            try:
                from app.ui.themes.theme_manager import theme_manager
                theme_name = theme_manager.effective_theme
            except Exception:
                theme_name = "dark"
        is_dark = (theme_name == "dark")
        accent = card.property("accent_color") or "#0078D4"
        bg = "#202020" if is_dark else "#FFFFFF"
        border = "#333333" if is_dark else "#E2E8F0"
        val_color = "#FFFFFF" if is_dark else "#0F172A"
        title_color = "#888888" if is_dark else "#64748B"

        card.setStyleSheet(
            f"background-color: {bg}; border-radius: 8px; border: 1px solid {border}; "
            f"border-top: 3px solid {accent}; padding: 10px;"
        )
        t_lbl = card.findChild(QLabel, "kpiTitle")
        if t_lbl:
            t_lbl.setStyleSheet(f"font-size: 11px; color: {title_color}; font-weight: 600;")
        v_lbl = card.findChild(QLabel, "kpiValue")
        if v_lbl:
            v_lbl.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {val_color};")

    def _on_theme_changed(self, theme_name: str):
        for card in getattr(self, "_kpi_card_list", []):
            self._style_kpi_card(card, theme_name)

    def _set_kpi_value(self, card: QFrame, val: str):
        lbl = card.findChild(QLabel, "kpiValue")
        if lbl:
            lbl.setText(val)

    # --------------------------------------------------------
    # DIRECTORY MANAGEMENT & RECENT FOLDERS
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
        folder = QFileDialog.getExistingDirectory(self, "اختر المجلد للبحث والتحليل", start)
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

    def _on_tab_changed(self, idx: int):
        if idx == 1 and not self.current_storage_report and self.current_folder:
            # Auto-trigger storage analysis on first view if folder loaded
            self._start_storage_analysis()

    # --------------------------------------------------------
    # SEARCH OPERATIONS
    # --------------------------------------------------------
    def _start_search(self):
        if not self.current_folder or not self.current_folder.exists():
            QMessageBox.information(self, "تنبيه", "يرجى اختيار مجلد صالح أولاً للبحث داخله.")
            return

        filt = SearchFilter()
        filt.query = self.search_input.text().strip()
        filt.use_regex = self.cb_regex.isChecked()
        filt.case_sensitive = self.cb_case.isChecked()
        filt.recursive = self.cb_recursive.isChecked()
        filt.include_hidden = self.cb_hidden.isChecked()
        filt.category = self.search_cat_combo.currentData()
        filt.content_query = self.content_search_input.text().strip()

        # Size preset
        sz_preset = self.search_size_combo.currentData()
        if sz_preset == "<1MB":
            filt.max_size_bytes = 1024 * 1024
        elif sz_preset == "1-100MB":
            filt.min_size_bytes = 1024 * 1024
            filt.max_size_bytes = 100 * 1024 * 1024
        elif sz_preset == ">100MB":
            filt.min_size_bytes = 100 * 1024 * 1024
        elif sz_preset == ">1GB":
            filt.min_size_bytes = 1024 * 1024 * 1024

        # Date preset
        now = datetime.now()
        dt_preset = self.search_date_combo.currentData()
        if dt_preset == "1day":
            filt.date_from = now - timedelta(days=1)
        elif dt_preset == "7days":
            filt.date_from = now - timedelta(days=7)
        elif dt_preset == "30days":
            filt.date_from = now - timedelta(days=30)
        elif dt_preset == "year":
            filt.date_from = now - timedelta(days=365)

        self.btn_search.hide()
        self.btn_cancel_search.show()
        self.search_table.setRowCount(0)
        self.search_results = []
        self.btn_export_csv.setEnabled(False)
        self.search_footer_lbl.setText("جاري البحث في الملفات...")
        self.status_changed.emit("جاري البحث في الملفات...", True, False)

        self.search_worker = SearchWorker(self.current_folder, filt)
        self.search_worker.progress_updated.connect(self._on_search_progress)
        self.search_worker.search_finished.connect(self._on_search_finished)
        self.search_worker.search_failed.connect(self._on_search_failed)
        self.search_worker.start()

    def _cancel_search(self):
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.status_changed.emit("جاري إلغاء البحث...", True, False)

    def _on_search_progress(self, found_count: int, scanned_count: int, current_file: str):
        self.search_footer_lbl.setText(f"تم فحص {scanned_count} ملف | عُثر على: {found_count} تطابق...")

    def _on_search_finished(self, results: List[SearchResultItem]):
        self.btn_search.show()
        self.btn_cancel_search.hide()
        self.search_results = results
        self._populate_search_table(results)

        total_bytes = sum(it.size_bytes for it in results)
        sz_str = format_file_size(total_bytes)
        self.search_footer_lbl.setText(f"اكتمل البحث: تم العثور على {len(results)} ملف | الحجم الإجمالي: {sz_str}")
        self.status_changed.emit(f"اكتمل البحث: {len(results)} ملف مطابقة.", False, False)
        self.btn_export_csv.setEnabled(len(results) > 0)

    def _on_search_failed(self, error_msg: str):
        self.btn_search.show()
        self.btn_cancel_search.hide()
        self.search_footer_lbl.setText("حدث خطأ أثناء البحث.")
        self.status_changed.emit(f"خطأ أثناء البحث: {error_msg}", False, True)
        QMessageBox.critical(self, "خطأ في البحث", f"فشلت عملية البحث:\n{error_msg}")

    def _populate_search_table(self, results: List[SearchResultItem]):
        self.search_table.setRowCount(0)
        self.search_table.blockSignals(True)

        for idx, it in enumerate(results):
            self.search_table.insertRow(idx)

            # 0: #
            it_idx = QTableWidgetItem(str(idx + 1))
            it_idx.setTextAlignment(Qt.AlignCenter)
            self.search_table.setItem(idx, 0, it_idx)

            # 1: Filename + Icon
            cat_color = FILE_CATEGORIES.get(it.category_key, {}).get("color", "#888888")
            icon = get_icon(it.category_key if it.category_key != "other" else "file", cat_color, 16)
            it_name = QTableWidgetItem(icon, it.filename)
            it_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.search_table.setItem(idx, 1, it_name)

            # 2: Category
            it_cat = QTableWidgetItem(it.category_label)
            it_cat.setTextAlignment(Qt.AlignCenter)
            self.search_table.setItem(idx, 2, it_cat)

            # 3: Size
            it_sz = QTableWidgetItem(it.formatted_size)
            it_sz.setTextAlignment(Qt.AlignCenter)
            self.search_table.setItem(idx, 3, it_sz)

            # 4: Modified Date
            it_dt = QTableWidgetItem(it.formatted_date)
            it_dt.setTextAlignment(Qt.AlignCenter)
            self.search_table.setItem(idx, 4, it_dt)

            # 5: Path or Snippet
            desc = str(it.path)
            if it.match_snippet:
                desc = f"[سطر {it.match_line_num}]: {it.match_snippet}  ({it.path})"
            it_path = QTableWidgetItem(desc)
            it_path.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            it_path.setForeground(QColor("#60CDFF"))
            self.search_table.setItem(idx, 5, it_path)

        self.search_table.blockSignals(False)

    def _clear_search_results(self):
        self.search_table.setRowCount(0)
        self.search_results = []
        self.search_input.clear()
        self.content_search_input.clear()
        self.btn_export_csv.setEnabled(False)
        self.search_footer_lbl.setText("تم مسح النتائج.")

    def _show_search_context_menu(self, pos):
        row = self.search_table.rowAt(pos.y())
        if row < 0 or row >= len(self.search_results):
            return

        item = self.search_results[row]
        menu = QMenu(self)

        act_open = menu.addAction("فتح الملف")
        act_open.setIcon(get_icon("play", "#FFFFFF", 14))
        act_open.triggered.connect(lambda: FileService.open_file(item.path))

        act_exp = menu.addAction("فتح في مستكشف ويندوز (Explorer)")
        act_exp.setIcon(get_icon("folder_open", "#60CDFF", 14))
        act_exp.triggered.connect(lambda: FileService.open_in_explorer(item.path))

        act_copy = menu.addAction("نسخ المسار الكامل")
        act_copy.setIcon(get_icon("rename", "#FFB900", 14))
        act_copy.triggered.connect(lambda: self._copy_to_clipboard(str(item.path)))

        menu.addSeparator()

        act_del = menu.addAction("حذف الملف إلى سلة المحذوفات")
        act_del.setIcon(get_icon("close", "#F5222D", 14))
        act_del.triggered.connect(lambda: self._delete_search_file(item, row))

        menu.exec(QCursor.pos())

    def _on_search_item_double_clicked(self, table_item: QTableWidgetItem):
        row = table_item.row()
        if 0 <= row < len(self.search_results):
            FileService.open_file(self.search_results[row].path)

    def _copy_to_clipboard(self, text: str):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.status_changed.emit("تم نسخ المسار إلى الحافظة.", False, False)

    def _delete_search_file(self, item: SearchResultItem, row: int):
        reply = QMessageBox.question(
            self, "تأكيد الحذف الآمن",
            f"هل أنت متأكد من نقل الملف التالي إلى سلة المحذوفات؟\n\n{item.filename}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if FileService.send_to_recycle_bin(item.path):
                self.search_table.removeRow(row)
                self.search_results.remove(item)
                self.status_changed.emit(f"تم إرسال {item.filename} إلى سلة المحذوفات.", False, False)
            else:
                QMessageBox.critical(self, "خطأ", "تعذر نقل الملف إلى سلة المحذوفات.")

    def _export_search_csv(self):
        if not self.search_results:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "حفظ تقرير نتائج البحث",
            str(Path.home() / "Desktop" / "نتائج_البحث_SINAX.csv"),
            "ملفات CSV (*.csv)"
        )
        if dest:
            try:
                with open(dest, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["#", "اسم الملف", "التصنيف", "الحجم (بايت)", "الحجم المنسق", "تاريخ التعديل", "المسار الكامل", "سطر التطابق"])
                    for idx, it in enumerate(self.search_results, 1):
                        writer.writerow([
                            idx, it.filename, it.category_label, it.size_bytes,
                            it.formatted_size, it.formatted_date, str(it.path), it.match_snippet
                        ])
                self.status_changed.emit(f"تم تصدير التقرير بنجاح إلى: {dest}", False, False)
                QMessageBox.information(self, "نجاح التصدير", f"تم حفظ نتائج البحث بنجاح في:\n{dest}")
            except Exception as e:
                logger.error(f"Failed to export CSV: {e}")
                QMessageBox.critical(self, "خطأ في التصدير", f"تعذر حفظ التقرير: {e}")

    # --------------------------------------------------------
    # STORAGE ANALYTICS OPERATIONS
    # --------------------------------------------------------
    def _start_storage_analysis(self):
        if not self.current_folder or not self.current_folder.exists():
            QMessageBox.information(self, "تنبيه", "يرجى اختيار مجلد صالح أولاً للتحليل.")
            return

        self.btn_analyze_storage.hide()
        self.btn_cancel_storage.show()
        self.status_changed.emit("جاري فحص وتحليل مساحة التخزين...", True, False)

        self.storage_worker = StorageWorker(self.current_folder, top_n=50)
        self.storage_worker.progress_updated.connect(self._on_storage_progress)
        self.storage_worker.analysis_finished.connect(self._on_storage_finished)
        self.storage_worker.analysis_failed.connect(self._on_storage_failed)
        self.storage_worker.start()

    def _cancel_storage_analysis(self):
        if self.storage_worker and self.storage_worker.isRunning():
            self.storage_worker.cancel()
            self.status_changed.emit("جاري إلغاء فحص المساحة...", True, False)

    def _on_storage_progress(self, file_count: int, total_dirs: int, current_name: str):
        self.status_changed.emit(f"جاري الفحص: تم مسح {file_count} ملف...", True, False)

    def _on_storage_finished(self, report: StorageReport):
        self.btn_analyze_storage.show()
        self.btn_cancel_storage.hide()
        self.current_storage_report = report

        # 1. Update KPI cards
        self._set_kpi_value(self.card_total_size, report.formatted_total_size)
        self._set_kpi_value(self.card_total_files, f"{report.total_files:,} ملف")
        self._set_kpi_value(self.card_total_dirs, f"{report.total_dirs:,} مجلد")

        # 2. Populate Category Distribution Bars
        self._populate_category_breakdown(report.categories)

        # 3. Populate Top Space Hogs
        self._populate_top_table(report.top_largest_files)

        self.status_changed.emit(
            f"اكتمل تحليل التخزين: {report.total_files} ملف بحجم إجمالي {report.formatted_total_size}.",
            False, False
        )

    def _on_storage_failed(self, error_msg: str):
        self.btn_analyze_storage.show()
        self.btn_cancel_storage.hide()
        self.status_changed.emit(f"فشل تحليل التخزين: {error_msg}", False, True)
        QMessageBox.critical(self, "خطأ في التحليل", f"تعذر تحليل مساحة التخزين:\n{error_msg}")

    def _populate_category_breakdown(self, categories: Dict[str, CategorySpaceInfo]):
        # Clear existing category items cleanly
        while self.cat_bars_layout.count():
            item = self.cat_bars_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        # Sort categories by size descending
        sorted_cats = sorted(categories.values(), key=lambda c: c.total_bytes, reverse=True)
        active_cats = [c for c in sorted_cats if c.file_count > 0]

        if not active_cats:
            lbl = QLabel("لا توجد ملفات في هذا المجلد.")
            lbl.setStyleSheet("color: #888888; padding: 10px;")
            self.cat_bars_layout.addWidget(lbl)
            return

        for cat in active_cats:
            row_widget = QWidget(self.cat_bars_widget)
            row_layout = QVBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 4, 4, 4)
            row_layout.setSpacing(4)

            # Top label row: Category name + Size + Percentage
            lbl_row = QHBoxLayout()
            lbl_row.setSpacing(8)

            color_dot = QLabel("●")
            color_dot.setStyleSheet(f"color: {cat.color}; font-size: 14px;")
            lbl_row.addWidget(color_dot)

            name_lbl = QLabel(f"{cat.label_ar} ({cat.file_count} ملف)")
            name_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #FFFFFF;")
            lbl_row.addWidget(name_lbl, 1)

            size_lbl = QLabel(f"{cat.formatted_size} ({cat.percentage:.1f}%)")
            size_lbl.setStyleSheet("font-size: 11px; color: #60CDFF; font-weight: bold;")
            lbl_row.addWidget(size_lbl)

            row_layout.addLayout(lbl_row)

            # Custom progress bar
            pb = QProgressBar()
            pb.setRange(0, 100)
            pb.setValue(int(round(cat.percentage)))
            pb.setFixedHeight(8)
            pb.setTextVisible(False)
            pb.setStyleSheet(
                f"QProgressBar {{ background-color: #2D2D2D; border-radius: 4px; border: none; }} "
                f"QProgressBar::chunk {{ background-color: {cat.color}; border-radius: 4px; }}"
            )
            row_layout.addWidget(pb)

            row_widget.show()
            self.cat_bars_layout.addWidget(row_widget)

    def _populate_top_table(self, top_files: List[StorageItemInfo]):
        self.top_table.setRowCount(0)
        self.top_table.blockSignals(True)

        for idx, it in enumerate(top_files):
            self.top_table.insertRow(idx)

            # 0: #
            it_idx = QTableWidgetItem(str(idx + 1))
            it_idx.setTextAlignment(Qt.AlignCenter)
            self.top_table.setItem(idx, 0, it_idx)

            # 1: Filename + Icon
            cat_color = FILE_CATEGORIES.get(it.category_key, {}).get("color", "#888888")
            icon = get_icon(it.category_key if it.category_key != "other" else "file", cat_color, 16)
            it_name = QTableWidgetItem(icon, it.filename)
            it_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.top_table.setItem(idx, 1, it_name)

            # 2: Size
            it_sz = QTableWidgetItem(it.formatted_size)
            it_sz.setTextAlignment(Qt.AlignCenter)
            it_sz.setForeground(QColor("#FFB900"))
            self.top_table.setItem(idx, 2, it_sz)

            # 3: Full Path
            it_path = QTableWidgetItem(str(it.path))
            it_path.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            it_path.setForeground(QColor("#AAAAAA"))
            self.top_table.setItem(idx, 3, it_path)

        self.top_table.blockSignals(False)

    def _show_top_context_menu(self, pos):
        row = self.top_table.rowAt(pos.y())
        if not self.current_storage_report or row < 0 or row >= len(self.current_storage_report.top_largest_files):
            return

        item = self.current_storage_report.top_largest_files[row]
        menu = QMenu(self)

        act_open = menu.addAction("فتح الملف")
        act_open.setIcon(get_icon("play", "#FFFFFF", 14))
        act_open.triggered.connect(lambda: FileService.open_file(item.path))

        act_exp = menu.addAction("فتح في مستكشف ويندوز (Explorer)")
        act_exp.setIcon(get_icon("folder_open", "#60CDFF", 14))
        act_exp.triggered.connect(lambda: FileService.open_in_explorer(item.path))

        menu.addSeparator()

        act_del = menu.addAction("حذف الملف إلى سلة المحذوفات")
        act_del.setIcon(get_icon("close", "#F5222D", 14))
        act_del.triggered.connect(lambda: self._delete_top_file(item, row))

        menu.exec(QCursor.pos())

    def _on_top_item_double_clicked(self, table_item: QTableWidgetItem):
        row = table_item.row()
        if self.current_storage_report and 0 <= row < len(self.current_storage_report.top_largest_files):
            FileService.open_file(self.current_storage_report.top_largest_files[row].path)

    def _delete_top_file(self, item: StorageItemInfo, row: int):
        reply = QMessageBox.question(
            self, "تأكيد الحذف الآمن",
            f"هل أنت متأكد من نقل هذا الملف الكبير إلى سلة المحذوفات؟\n\n{item.filename} ({item.formatted_size})",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if FileService.send_to_recycle_bin(item.path):
                self.top_table.removeRow(row)
                self.current_storage_report.top_largest_files.remove(item)
                self.status_changed.emit(f"تم إرسال {item.filename} إلى سلة المحذوفات.", False, False)
            else:
                QMessageBox.critical(self, "خطأ", "تعذر نقل الملف إلى سلة المحذوفات.")

    # --------------------------------------------------------
    # DRAG AND DROP SUPPORT
    # --------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        p = Path(urls[0].toLocalFile())
        if p.is_dir():
            self.set_directory(p)
        elif p.is_file():
            self.set_directory(p.parent)
