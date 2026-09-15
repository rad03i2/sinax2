# -*- coding: utf-8 -*-
"""
SINAX Batch Rename Page
Professional, responsive Batch Rename interface with scrollable rule panels,
proper QGroupBox vertical margins, minimum heights on all inputs,
and robust Splitter layout for any display resolution and scaling.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QComboBox, QSpinBox, QTabWidget, QGroupBox, QTableView,
    QHeaderView, QMenu, QMessageBox, QFileDialog, QFrame, QSplitter,
    QScrollArea, QSpacerItem, QSizePolicy, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QAction, QColor, QFont

from app.models.file_item import FileItem
from app.models.rename_rule import RenameConfig
from app.services.file_service import FileService
from app.services.rename_service import RenameService, RenamePlan
from app.workers.scan_worker import ScanWorker
from app.workers.rename_worker import RenameWorker
from app.workers.undo_worker import UndoWorker
from app.core.config import config
from app.core.constants import FILE_CATEGORIES, NUMBER_SYSTEMS
from app.core.undo_manager import undo_manager
from app.ui.widgets.file_table_model import FileTableModel
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.icons import get_icon
from app.core.logger import get_logger

logger = get_logger("batch_rename_page")

class CategoryChip(QPushButton):
    """Clickable filter chip for file categories."""
    def __init__(self, cat_key: str, label: str, count: int = 0, color_hex: str = "#0078D4", parent=None):
        super().__init__(parent)
        self.cat_key = cat_key
        self.base_label = label
        self.count = count
        self.color_hex = color_hex
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(32)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._update_text()
        self._update_style(False)

    def set_count(self, count: int):
        self.count = count
        self._update_text()

    def _update_text(self):
        self.setText(f"{self.base_label} ({self.count})")

    def _update_style(self, checked: bool, theme_name: Optional[str] = None):
        if theme_name is None:
            try:
                from app.ui.themes.theme_manager import theme_manager
                theme_name = theme_manager.effective_theme
            except Exception:
                theme_name = "dark"
        is_dark = (theme_name == "dark")

        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.color_hex};
                    color: #FFFFFF;
                    border: 1px solid {self.color_hex};
                    border-radius: 14px;
                    padding: 4px 14px;
                    font-weight: bold;
                    font-size: 12px;
                    min-height: 28px;
                }}
            """)
        else:
            if is_dark:
                bg = "#21262D"
                border = "#30363D"
                color = "#CCCCCC"
                hover_bg = "#2D333B"
                hover_color = "#FFFFFF"
            else:
                bg = "#F1F5F9"
                border = "#CBD5E1"
                color = "#334155"
                hover_bg = "#E2E8F0"
                hover_color = "#0F172A"

            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg};
                    color: {color};
                    border: 1px solid {border};
                    border-radius: 14px;
                    padding: 4px 14px;
                    font-size: 12px;
                    min-height: 28px;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                    border-color: {self.color_hex};
                    color: {hover_color};
                }}
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_style(checked)

class BatchRenamePage(QWidget):
    status_changed = Signal(str, bool, bool)
    progress_changed = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_folder: Optional[Path] = None
        self.table_model = FileTableModel(self)
        self.current_plan: Optional[RenamePlan] = None
        self.scan_worker: Optional[ScanWorker] = None
        self.rename_worker: Optional[RenameWorker] = None
        self.undo_worker: Optional[UndoWorker] = None
        self.active_category: str = "all"
        self.chips: Dict[str, CategoryChip] = {}
        self.presets_data: List[Dict] = []
        
        self.setAcceptDrops(True)
        self._load_presets_data()
        self._init_ui()
        from app.ui.themes.theme_manager import theme_manager
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        for chip in self.chips.values():
            chip._update_style(chip.isChecked(), theme_name)

    def _load_presets_data(self):
        preset_file = Path(__file__).parents[2] / "resources" / "presets" / "rename_presets.json"
        if preset_file.exists():
            try:
                with open(preset_file, "r", encoding="utf-8") as f:
                    self.presets_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed loading presets: {e}")

    def _wrap_in_scroll(self, content_widget: QWidget) -> QScrollArea:
        """Wraps tab content inside a dedicated vertical QScrollArea."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.verticalScrollBar().setSingleStep(30)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        scroll.setWidget(content_widget)
        return scroll

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. TOP BAR: Folder Picker & Navigation
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
        self.path_edit.setPlaceholderText("اختر مجلداً للبدء أو اسحب المجلد إلى هنا...")
        self.path_edit.setMinimumHeight(36)
        self.path_edit.returnPressed.connect(self._on_path_entered)
        top_layout.addWidget(self.path_edit, 1)

        self.recent_combo = QComboBox()
        self.recent_combo.setFixedWidth(180)
        self.recent_combo.setMinimumHeight(36)
        self.recent_combo.addItem("المجلدات الأخيرة ▼")
        self._refresh_recent_folders()
        self.recent_combo.activated.connect(self._on_recent_selected)
        top_layout.addWidget(self.recent_combo)

        self.subfolder_cb = QCheckBox("تضمين المجلدات الفرعية")
        self.subfolder_cb.setCursor(Qt.PointingHandCursor)
        self.subfolder_cb.setMinimumHeight(32)
        self.subfolder_cb.toggled.connect(self._start_scan)
        top_layout.addWidget(self.subfolder_cb)

        refresh_btn = QPushButton()
        refresh_btn.setIcon(get_icon("refresh", "#AAAAAA", 16))
        refresh_btn.setToolTip("إعادة فحص المجلد")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.clicked.connect(self._start_scan)
        top_layout.addWidget(refresh_btn)

        main_layout.addWidget(top_frame)

        # 2. CATEGORY PILLS BAR (Horizontal scroll)
        chip_scroll = QScrollArea()
        chip_scroll.setFixedHeight(50)
        chip_scroll.setWidgetResizable(True)
        chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        chip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        chip_scroll.setFrameShape(QFrame.NoFrame)
        chip_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        chip_container = QWidget()
        self.chip_layout = QHBoxLayout(chip_container)
        self.chip_layout.setContentsMargins(4, 4, 4, 4)
        self.chip_layout.setSpacing(8)

        for cat_key, cat_data in FILE_CATEGORIES.items():
            chip = CategoryChip(cat_key, cat_data['label_ar'], 0, cat_data['color'])
            chip.clicked.connect(lambda checked, k=cat_key: self._on_category_chip_clicked(k))
            self.chips[cat_key] = chip
            self.chip_layout.addWidget(chip)
        
        self.chips['all'].setChecked(True)
        self.chip_layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        chip_scroll.setWidget(chip_container)
        main_layout.addWidget(chip_scroll)

        # 3. SPLITTER: File Table (Right in RTL) + Rules Panel (Left in RTL)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- TABLE PANEL ---
        table_panel = QWidget()
        table_panel.setMinimumWidth(480)
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث داخل الملفات...")
        self.search_input.setMinimumHeight(34)
        self.search_input.textChanged.connect(self.table_model.set_filter)
        toolbar.addWidget(self.search_input, 1)

        select_all_btn = QPushButton("تحديد الكل")
        select_all_btn.setMinimumHeight(34)
        select_all_btn.clicked.connect(lambda: self._select_all_items(True))
        toolbar.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("إلغاء التحديد")
        deselect_all_btn.setMinimumHeight(34)
        deselect_all_btn.clicked.connect(lambda: self._select_all_items(False))
        toolbar.addWidget(deselect_all_btn)

        invert_btn = QPushButton("عكس")
        invert_btn.setMinimumHeight(34)
        invert_btn.clicked.connect(self._invert_selection)
        toolbar.addWidget(invert_btn)

        self.sort_combo = QComboBox()
        self.sort_combo.setMinimumHeight(34)
        self.sort_combo.addItems([
            "الترتيب الذكي للأرقام",
            "الاسم (أ - ي)",
            "الاسم (ي - أ)",
            "تاريخ التعديل (الأقدم أولاً)",
            "تاريخ التعديل (الأحدث أولاً)",
            "الحجم (الأصغر أولاً)",
            "الحجم (الأكبر أولاً)"
        ])
        self.sort_combo.currentIndexChanged.connect(self._update_preview)
        toolbar.addWidget(self.sort_combo)

        table_layout.addLayout(toolbar)

        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.ExtendedSelection)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table_view.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table_view.setColumnWidth(2, 220)
        self.table_view.setColumnWidth(3, 240)
        self.table_view.verticalHeader().setDefaultSectionSize(32)
        self.table_view.verticalHeader().hide()
        self.table_model.dataChanged.connect(self._on_model_data_changed)
        table_layout.addWidget(self.table_view, 1)

        self.table_footer = QLabel("لا توجد ملفات محملة.")
        self.table_footer.setStyleSheet("font-size: 11px; color: #888888; padding: 2px 4px;")
        table_layout.addWidget(self.table_footer)

        splitter.addWidget(table_panel)

        # --- RULES PANEL (SETTINGS) ---
        rules_panel = QFrame()
        rules_panel.setObjectName("rulesPanel")
        rules_panel.setMinimumWidth(400)
        rules_layout = QVBoxLayout(rules_panel)
        rules_layout.setContentsMargins(10, 10, 10, 10)
        rules_layout.setSpacing(10)

        # Tabs with ScrollArea wrapping
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabs.addTab(self._wrap_in_scroll(self._build_presets_tab()), "الأنماط الجاهزة")
        self.tabs.addTab(self._wrap_in_scroll(self._build_custom_tab()), "تسمية مخصصة وأرقام")
        self.tabs.addTab(self._wrap_in_scroll(self._build_replace_tab()), "تعديل واستبدال")
        self.tabs.addTab(self._wrap_in_scroll(self._build_advanced_tab()), "خيارات متقدمة")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        rules_layout.addWidget(self.tabs, 1)

        # Live Summary Card (Fixed height, does not compress)
        self.summary_box = QFrame()
        self.summary_box.setObjectName("summaryCard")
        s_layout = QVBoxLayout(self.summary_box)
        s_layout.setContentsMargins(12, 8, 12, 8)
        s_layout.setSpacing(4)
        
        self.summary_stats_lbl = QLabel("حدد ملفات لاحتساب المعاينة")
        self.summary_stats_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
        s_layout.addWidget(self.summary_stats_lbl)

        self.summary_alert_lbl = QLabel("✓ لا توجد تعارضات")
        self.summary_alert_lbl.setStyleSheet("font-size: 11px; color: #52C41A;")
        s_layout.addWidget(self.summary_alert_lbl)
        rules_layout.addWidget(self.summary_box, 0)

        # Action Buttons (Fixed height, stay visible at bottom)
        btn_box = QVBoxLayout()
        btn_box.setSpacing(8)

        self.apply_btn = QPushButton("  تنفيذ إعادة التسمية")
        self.apply_btn.setProperty("class", "PrimaryButton")
        self.apply_btn.setIcon(get_icon("play", "#FFFFFF", 16))
        self.apply_btn.setMinimumHeight(40)
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self._on_execute_rename)
        btn_box.addWidget(self.apply_btn)

        self.undo_btn = QPushButton("  التراجع عن آخر عملية")
        self.undo_btn.setIcon(get_icon("undo", "#AAAAAA", 16))
        self.undo_btn.setMinimumHeight(36)
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.clicked.connect(self._on_undo_rename)
        self._refresh_undo_button()
        btn_box.addWidget(self.undo_btn)

        rules_layout.addLayout(btn_box, 0)

        splitter.addWidget(rules_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, 1)

    # ----------------------------------------------------
    # TAB 1: PRESETS
    # ----------------------------------------------------
    def _build_presets_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Category & Search Group
        cat_box = QGroupBox("اختيار الفئة والبحث")
        cat_layout = QVBoxLayout(cat_box)
        cat_layout.setContentsMargins(14, 22, 14, 14)
        cat_layout.setSpacing(8)

        lbl_cat = QLabel("فئة النمط الجاهز:")
        lbl_cat.setStyleSheet("font-size: 12px; font-weight: 600;")
        cat_layout.addWidget(lbl_cat)

        self.preset_cat_combo = QComboBox()
        self.preset_cat_combo.setMinimumHeight(36)
        for cat in self.presets_data:
            self.preset_cat_combo.addItem(cat['category_name_ar'], cat['category_id'])
        self.preset_cat_combo.currentIndexChanged.connect(self._populate_presets_list)
        cat_layout.addWidget(self.preset_cat_combo)

        lbl_search = QLabel("بحث داخل أنماط الفئة:")
        lbl_search.setStyleSheet("font-size: 12px; font-weight: 600;")
        cat_layout.addWidget(lbl_search)

        self.preset_search = QLineEdit()
        self.preset_search.setPlaceholderText("🔍 اكتب للبحث في أكثر من 160 نمطاً...")
        self.preset_search.setMinimumHeight(36)
        self.preset_search.textChanged.connect(self._filter_presets_list)
        cat_layout.addWidget(self.preset_search)

        layout.addWidget(cat_box)

        # Presets List Group
        list_box = QGroupBox("قائمة الأنماط الجاهزة")
        list_layout = QVBoxLayout(list_box)
        list_layout.setContentsMargins(14, 22, 14, 14)
        list_layout.setSpacing(8)

        self.presets_list = QListWidget()
        self.presets_list.setMinimumHeight(180)
        self.presets_list.itemClicked.connect(self._on_preset_selected)
        list_layout.addWidget(self.presets_list)
        layout.addWidget(list_box)

        # Presets Numbering Options Group
        num_box = QGroupBox("خيارات أرقام النمط الجاهز")
        num_layout = QVBoxLayout(num_box)
        num_layout.setContentsMargins(14, 22, 14, 14)
        num_layout.setSpacing(10)

        lbl_sys = QLabel("نظام الترقيم والحروف:")
        lbl_sys.setStyleSheet("font-size: 12px; font-weight: 600;")
        num_layout.addWidget(lbl_sys)

        self.preset_num_system = QComboBox()
        self.preset_num_system.setMinimumHeight(36)
        for k, v in NUMBER_SYSTEMS.items():
            self.preset_num_system.addItem(v, k)
        self.preset_num_system.currentIndexChanged.connect(self._update_preview)
        num_layout.addWidget(self.preset_num_system)

        grid_row = QHBoxLayout()
        grid_row.setSpacing(10)

        col1 = QVBoxLayout()
        lbl_start = QLabel("ابدأ من:")
        lbl_start.setStyleSheet("font-size: 12px; font-weight: 600;")
        col1.addWidget(lbl_start)
        self.preset_start_spin = QSpinBox()
        self.preset_start_spin.setRange(1, 999999)
        self.preset_start_spin.setValue(1)
        self.preset_start_spin.setMinimumHeight(36)
        self.preset_start_spin.valueChanged.connect(self._update_preview)
        col1.addWidget(self.preset_start_spin)
        grid_row.addLayout(col1)

        col2 = QVBoxLayout()
        lbl_pad = QLabel("عدد الخانات (Padding):")
        lbl_pad.setStyleSheet("font-size: 12px; font-weight: 600;")
        col2.addWidget(lbl_pad)
        self.preset_padding_combo = QComboBox()
        self.preset_padding_combo.addItem("بدون أصفار (1, 2, 3)", 1)
        self.preset_padding_combo.addItem("خانة واحدة (01, 02, 03)", 2)
        self.preset_padding_combo.addItem("خانتان (001, 002, 003)", 3)
        self.preset_padding_combo.addItem("ثلاث خانات (0001, 0002)", 4)
        self.preset_padding_combo.setMinimumHeight(36)
        self.preset_padding_combo.currentIndexChanged.connect(self._update_preview)
        col2.addWidget(self.preset_padding_combo)
        grid_row.addLayout(col2)

        num_layout.addLayout(grid_row)
        layout.addWidget(num_box)

        layout.addStretch(1)
        self._populate_presets_list()
        return widget

    def _populate_presets_list(self):
        self.presets_list.clear()
        idx = self.preset_cat_combo.currentIndex()
        if idx < 0 or idx >= len(self.presets_data):
            return

        cat_patterns = self.presets_data[idx]['patterns']
        for p in cat_patterns:
            item = QListWidgetItem(f"📄  {p['name_ar']}")
            item.setData(Qt.UserRole, p['pattern'])
            self.presets_list.addItem(item)

        if self.presets_list.count() > 0:
            self.presets_list.setCurrentRow(0)

    def _filter_presets_list(self, query: str):
        query = query.strip().lower()
        for i in range(self.presets_list.count()):
            item = self.presets_list.item(i)
            match = (query in item.text().lower()) or (query in item.data(Qt.UserRole).lower())
            item.setHidden(not match)

    def _on_preset_selected(self, item: QListWidgetItem):
        self._update_preview()

    # ----------------------------------------------------
    # TAB 2: CUSTOM & NUMBERS
    # ----------------------------------------------------
    def _build_custom_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Custom pattern input box
        pat_box = QGroupBox("صيغة التسمية المخصصة")
        p_layout = QVBoxLayout(pat_box)
        p_layout.setContentsMargins(14, 22, 14, 14)
        p_layout.setSpacing(10)

        lbl_inst = QLabel("اكتب صيغة التسمية المطلوبة بحرية واستخدم الرموز التلقائية:")
        lbl_inst.setStyleSheet("font-size: 12px; color: #BBBBBB;")
        p_layout.addWidget(lbl_inst)

        self.custom_pattern_input = QLineEdit("مشروع التخرج {n}")
        self.custom_pattern_input.setMinimumHeight(38)
        self.custom_pattern_input.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.custom_pattern_input.textChanged.connect(self._update_preview)
        p_layout.addWidget(self.custom_pattern_input)

        # Helper placeholder buttons
        chip_row = QHBoxLayout()
        chip_row.setSpacing(6)
        for code, label in [
            ("{n}", "+ رقم {n}"),
            ("{orig}", "+ الأصلي {orig}"),
            ("{date}", "+ تاريخ {date}"),
            ("{parent}", "+ المجلد {parent}")
        ]:
            b = QPushButton(label)
            b.setProperty("class", "ChipButton")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, c=code: self._insert_placeholder(c))
            chip_row.addWidget(b)
        p_layout.addLayout(chip_row)

        layout.addWidget(pat_box)

        # Numbering controls box
        num_box = QGroupBox("خيارات الأرقام والتسلسل")
        num_layout = QVBoxLayout(num_box)
        num_layout.setContentsMargins(14, 22, 14, 14)
        num_layout.setSpacing(10)

        lbl_ns = QLabel("نظام الترقيم والحروف:")
        lbl_ns.setStyleSheet("font-size: 12px; font-weight: 600;")
        num_layout.addWidget(lbl_ns)

        self.custom_num_system = QComboBox()
        self.custom_num_system.setMinimumHeight(36)
        for k, v in NUMBER_SYSTEMS.items():
            self.custom_num_system.addItem(v, k)
        self.custom_num_system.currentIndexChanged.connect(self._update_preview)
        num_layout.addWidget(self.custom_num_system)

        # Start and Step row
        row_spins = QHBoxLayout()
        row_spins.setSpacing(10)

        col_s1 = QVBoxLayout()
        lbl_start = QLabel("ابدأ الترقيم من:")
        lbl_start.setStyleSheet("font-size: 12px; font-weight: 600;")
        col_s1.addWidget(lbl_start)
        self.custom_start_spin = QSpinBox()
        self.custom_start_spin.setRange(1, 999999)
        self.custom_start_spin.setValue(1)
        self.custom_start_spin.setMinimumHeight(36)
        self.custom_start_spin.valueChanged.connect(self._update_preview)
        col_s1.addWidget(self.custom_start_spin)
        row_spins.addLayout(col_s1)

        col_s2 = QVBoxLayout()
        lbl_step = QLabel("مقدار الزيادة (Step):")
        lbl_step.setStyleSheet("font-size: 12px; font-weight: 600;")
        col_s2.addWidget(lbl_step)
        self.custom_step_spin = QSpinBox()
        self.custom_step_spin.setRange(1, 100)
        self.custom_step_spin.setValue(1)
        self.custom_step_spin.setMinimumHeight(36)
        self.custom_step_spin.valueChanged.connect(self._update_preview)
        col_s2.addWidget(self.custom_step_spin)
        row_spins.addLayout(col_s2)

        num_layout.addLayout(row_spins)

        # Padding
        lbl_pad = QLabel("تنسيق خانات الأرقام (Padding):")
        lbl_pad.setStyleSheet("font-size: 12px; font-weight: 600;")
        num_layout.addWidget(lbl_pad)

        self.custom_padding_combo = QComboBox()
        self.custom_padding_combo.addItem("بدون أصفار إضافية (1, 2, 3)", 1)
        self.custom_padding_combo.addItem("خانة واحدة إضافية (01, 02, 03)", 2)
        self.custom_padding_combo.addItem("خانتان إضافيتان (001, 002, 003)", 3)
        self.custom_padding_combo.addItem("ثلاث خانات إضافية (0001, 0002)", 4)
        self.custom_padding_combo.setMinimumHeight(36)
        self.custom_padding_combo.currentIndexChanged.connect(self._update_preview)
        num_layout.addWidget(self.custom_padding_combo)

        layout.addWidget(num_box)
        layout.addStretch(1)
        return widget

    def _insert_placeholder(self, code: str):
        cur = self.custom_pattern_input.text()
        self.custom_pattern_input.setText(cur + " " + code)

    # ----------------------------------------------------
    # TAB 3: MODIFY & REPLACE
    # ----------------------------------------------------
    def _build_replace_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Prefix & Suffix
        affix_box = QGroupBox("إضافة نص في البداية والنهاية")
        a_layout = QVBoxLayout(affix_box)
        a_layout.setContentsMargins(14, 22, 14, 14)
        a_layout.setSpacing(10)

        lbl_pre = QLabel("إضافة في بداية الاسم (Prefix):")
        lbl_pre.setStyleSheet("font-size: 12px; font-weight: 600;")
        a_layout.addWidget(lbl_pre)
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("مثال: جامعة الموصل - ")
        self.prefix_input.setMinimumHeight(36)
        self.prefix_input.textChanged.connect(self._update_preview)
        a_layout.addWidget(self.prefix_input)

        lbl_suf = QLabel("إضافة في نهاية الاسم (Suffix):")
        lbl_suf.setStyleSheet("font-size: 12px; font-weight: 600;")
        a_layout.addWidget(lbl_suf)
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("مثال:  - نهائي")
        self.suffix_input.setMinimumHeight(36)
        self.suffix_input.textChanged.connect(self._update_preview)
        a_layout.addWidget(self.suffix_input)

        layout.addWidget(affix_box)

        # Find & Replace
        rep_box = QGroupBox("البحث والاستبدال داخل الأسماء")
        r_layout = QVBoxLayout(rep_box)
        r_layout.setContentsMargins(14, 22, 14, 14)
        r_layout.setSpacing(10)

        lbl_find = QLabel("النص المطلوب استبداله:")
        lbl_find.setStyleSheet("font-size: 12px; font-weight: 600;")
        r_layout.addWidget(lbl_find)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("النص المراد تغييره داخل أسماء الملفات...")
        self.find_input.setMinimumHeight(36)
        self.find_input.textChanged.connect(self._update_preview)
        r_layout.addWidget(self.find_input)

        lbl_rep = QLabel("استبداله بالنص الجديد:")
        lbl_rep.setStyleSheet("font-size: 12px; font-weight: 600;")
        r_layout.addWidget(lbl_rep)
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("النص البديل الجديد...")
        self.replace_input.setMinimumHeight(36)
        self.replace_input.textChanged.connect(self._update_preview)
        r_layout.addWidget(self.replace_input)

        self.case_rep_cb = QCheckBox("حساس لحالة الأحرف الإنجليزية (Case Sensitive)")
        self.case_rep_cb.setMinimumHeight(28)
        self.case_rep_cb.toggled.connect(self._update_preview)
        r_layout.addWidget(self.case_rep_cb)

        layout.addWidget(rep_box)

        # Remove text & casing
        mod_box = QGroupBox("حذف نصوص وتغيير حالة الأحرف")
        m_layout = QVBoxLayout(mod_box)
        m_layout.setContentsMargins(14, 22, 14, 14)
        m_layout.setSpacing(10)

        lbl_rem = QLabel("إزالة نص معين بالكامل من الأسماء:")
        lbl_rem.setStyleSheet("font-size: 12px; font-weight: 600;")
        m_layout.addWidget(lbl_rem)
        self.remove_input = QLineEdit()
        self.remove_input.setPlaceholderText("اكتب النص لحذفه من كافة الأسماء...")
        self.remove_input.setMinimumHeight(36)
        self.remove_input.textChanged.connect(self._update_preview)
        m_layout.addWidget(self.remove_input)

        lbl_case = QLabel("تغيير حالة الأحرف الإنجليزية:")
        lbl_case.setStyleSheet("font-size: 12px; font-weight: 600;")
        m_layout.addWidget(lbl_case)
        self.casing_combo = QComboBox()
        self.casing_combo.addItem("بدون تغيير (الافتراضي)", "none")
        self.casing_combo.addItem("أحرف كبيرة بالكامل (UPPERCASE)", "upper")
        self.casing_combo.addItem("أحرف صغيرة بالكامل (lowercase)", "lower")
        self.casing_combo.addItem("بدايات الكلمات كبيرة (Title Case)", "title")
        self.casing_combo.setMinimumHeight(36)
        self.casing_combo.currentIndexChanged.connect(self._update_preview)
        m_layout.addWidget(self.casing_combo)

        layout.addWidget(mod_box)
        layout.addStretch(1)
        return widget

    # ----------------------------------------------------
    # TAB 4: ADVANCED & DATES
    # ----------------------------------------------------
    def _build_advanced_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Date settings
        date_box = QGroupBox("إدراج التواريخ في الأسماء")
        d_layout = QVBoxLayout(date_box)
        d_layout.setContentsMargins(14, 22, 14, 14)
        d_layout.setSpacing(10)

        lbl_dtype = QLabel("مصدر التاريخ المعتمد:")
        lbl_dtype.setStyleSheet("font-size: 12px; font-weight: 600;")
        d_layout.addWidget(lbl_dtype)

        self.date_type_combo = QComboBox()
        self.date_type_combo.addItem("تاريخ آخر تعديل للملف", "modified")
        self.date_type_combo.addItem("تاريخ إنشاء الملف الأصلي", "created")
        self.date_type_combo.addItem("تاريخ اليوم الحالي", "current")
        self.date_type_combo.setMinimumHeight(36)
        self.date_type_combo.currentIndexChanged.connect(self._update_preview)
        d_layout.addWidget(self.date_type_combo)

        lbl_dformat = QLabel("تنسيق عرض التاريخ:")
        lbl_dformat.setStyleSheet("font-size: 12px; font-weight: 600;")
        d_layout.addWidget(lbl_dformat)

        self.date_format_combo = QComboBox()
        self.date_format_combo.addItem("سنة-شهر-يوم (YYYY-MM-DD)", "%Y-%m-%d")
        self.date_format_combo.addItem("سنةشهر_يوم (YYYYMMDD)", "%Y%m%d")
        self.date_format_combo.addItem("يوم-شهر-سنة (DD-MM-YYYY)", "%d-%m-%Y")
        self.date_format_combo.setMinimumHeight(36)
        self.date_format_combo.currentIndexChanged.connect(self._update_preview)
        d_layout.addWidget(self.date_format_combo)

        layout.addWidget(date_box)

        # Extension and safety settings
        ext_box = QGroupBox("الامتدادات وسلامة الملفات")
        e_layout = QVBoxLayout(ext_box)
        e_layout.setContentsMargins(14, 22, 14, 14)
        e_layout.setSpacing(10)

        self.keep_ext_cb = QCheckBox("الحفاظ على امتداد الملف الأصلي تلقائياً (موصى به لحماية الملفات)")
        self.keep_ext_cb.setChecked(True)
        self.keep_ext_cb.setMinimumHeight(28)
        self.keep_ext_cb.toggled.connect(self._on_keep_ext_toggled)
        e_layout.addWidget(self.keep_ext_cb)

        lbl_cext = QLabel("تغيير الامتداد يدوياً (متقدم):")
        lbl_cext.setStyleSheet("font-size: 12px; font-weight: 600;")
        e_layout.addWidget(lbl_cext)

        self.custom_ext_input = QLineEdit()
        self.custom_ext_input.setPlaceholderText(".pdf أو .jpg")
        self.custom_ext_input.setEnabled(False)
        self.custom_ext_input.setMinimumHeight(36)
        self.custom_ext_input.textChanged.connect(self._update_preview)
        e_layout.addWidget(self.custom_ext_input)

        layout.addWidget(ext_box)
        layout.addStretch(1)
        return widget

    def _on_keep_ext_toggled(self, checked: bool):
        self.custom_ext_input.setEnabled(not checked)
        self._update_preview()

    def _on_tab_changed(self, index: int):
        self._update_preview()

    # ----------------------------------------------------
    # RECENT FOLDERS & BROWSE
    # ----------------------------------------------------
    def _refresh_recent_folders(self):
        self.recent_combo.clear()
        self.recent_combo.addItem("المجلدات الأخيرة ▼")
        recents = config.get_recent_folders()
        for p in recents:
            name = Path(p).name or p
            self.recent_combo.addItem(f"📁 {name} ({p})", p)

    def _on_recent_selected(self, index: int):
        if index <= 0:
            return
        path_str = self.recent_combo.itemData(index)
        if path_str and Path(path_str).exists():
            self.set_directory(Path(path_str))

    def _on_browse_folder(self):
        start_dir = str(self.current_folder) if self.current_folder else str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "اختر مجلداً لإعادة التسمية", start_dir)
        if chosen:
            self.set_directory(Path(chosen))

    def _on_path_entered(self):
        text = self.path_edit.text().strip()
        if text:
            p = Path(text)
            if p.exists() and p.is_dir():
                self.set_directory(p)
            else:
                QMessageBox.warning(self, "مسار غير صالح", "المسار المدخل غير موجود أو ليس مجلداً صالحاً.")

    def set_directory(self, path: Path):
        self.current_folder = path
        self.path_edit.setText(str(path))
        config.add_recent_folder(str(path))
        self._refresh_recent_folders()
        
        is_sys, warn = FileService.is_system_path(path)
        if is_sys:
            QMessageBox.warning(self, "تحذير: مجلد نظام", f"تنبيه أمان:\n{warn}\nيرجى الحذر عند تعديل ملفات النظام.")

        self._start_scan()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        local_path = Path(urls[0].toLocalFile())
        if local_path.is_dir():
            self.set_directory(local_path)
        elif local_path.is_file():
            self.set_directory(local_path.parent)

    # ----------------------------------------------------
    # SCANNING
    # ----------------------------------------------------
    def _start_scan(self):
        if not self.current_folder or not self.current_folder.exists():
            return

        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait()

        self.table_model.set_items([])
        self.status_changed.emit("جاري فحص المجلد وقراءة الملفات...", True, False)

        self.scan_worker = ScanWorker(
            directory=self.current_folder,
            recursive=self.subfolder_cb.isChecked(),
            category_filter=self.active_category,
            parent=self
        )
        self.scan_worker.chunk_loaded.connect(self.table_model.add_items)
        self.scan_worker.summary_ready.connect(self._on_scan_summary)
        self.scan_worker.scan_finished.connect(self._on_scan_finished)
        self.scan_worker.scan_error.connect(self._on_scan_error)
        self.scan_worker.start()

    def _on_scan_summary(self, counts: Dict[str, int], total_bytes: int):
        for cat_key, count in counts.items():
            if cat_key in self.chips:
                self.chips[cat_key].set_count(count)

    def _on_scan_finished(self, all_items: List[FileItem]):
        self.status_changed.emit(f"تم العثور على {len(all_items)} ملف.", False, False)
        self.table_footer.setText(f"إجمالي الملفات المعروضة: {len(all_items)} ملف")
        self._update_preview()

    def _on_scan_error(self, err: str):
        self.status_changed.emit(err, False, True)
        QMessageBox.critical(self, "خطأ في الفحص", err)

    def _on_category_chip_clicked(self, cat_key: str):
        for k, chip in self.chips.items():
            chip.setChecked(k == cat_key)
        self.active_category = cat_key
        self._start_scan()

    # ----------------------------------------------------
    # SELECTION & SORTING
    # ----------------------------------------------------
    def _select_all_items(self, select: bool):
        self.table_model.select_all(select)
        self._update_preview()

    def _invert_selection(self):
        self.table_model.invert_selection()
        self._update_preview()

    def _on_model_data_changed(self, top_left, bottom_right, roles):
        if Qt.CheckStateRole in roles:
            self._update_preview()

    # ----------------------------------------------------
    # CONFIG & PREVIEW GENERATION
    # ----------------------------------------------------
    def _build_rename_config(self) -> RenameConfig:
        config_obj = RenameConfig()
        current_tab_idx = self.tabs.currentIndex()

        sort_map = {
            0: "smart_numeric",
            1: "name_asc",
            2: "name_desc",
            3: "date_asc",
            4: "date_desc",
            5: "size_asc",
            6: "size_desc"
        }
        config_obj.sort_by = sort_map.get(self.sort_combo.currentIndex(), "smart_numeric")

        if current_tab_idx == 0:
            config_obj.mode = "preset"
            selected_item = self.presets_list.currentItem()
            if selected_item:
                config_obj.pattern = selected_item.data(Qt.UserRole)
            else:
                config_obj.pattern = "ملف {n}"
            config_obj.start_number = self.preset_start_spin.value()
            config_obj.padding = self.preset_padding_combo.currentData()
            config_obj.number_system = self.preset_num_system.currentData()

        elif current_tab_idx == 1:
            config_obj.mode = "custom"
            config_obj.pattern = self.custom_pattern_input.text() or "{orig}"
            config_obj.start_number = self.custom_start_spin.value()
            config_obj.step = self.custom_step_spin.value()
            config_obj.padding = self.custom_padding_combo.currentData()
            config_obj.number_system = self.custom_num_system.currentData()

        elif current_tab_idx == 2:
            config_obj.mode = "replace"
            config_obj.pattern = "{orig}"

        elif current_tab_idx == 3:
            config_obj.mode = "advanced"
            config_obj.pattern = "{orig}"

        config_obj.prefix = self.prefix_input.text()
        config_obj.suffix = self.suffix_input.text()
        config_obj.find_text = self.find_input.text()
        config_obj.replace_text = self.replace_input.text()
        config_obj.case_sensitive_replace = self.case_rep_cb.isChecked()
        config_obj.remove_text = self.remove_input.text()
        config_obj.case_transform = self.casing_combo.currentData()
        
        config_obj.date_type = self.date_type_combo.currentData()
        config_obj.date_format = self.date_format_combo.currentData()

        config_obj.keep_extension = self.keep_ext_cb.isChecked()
        config_obj.custom_extension = self.custom_ext_input.text().strip()

        return config_obj

    def _update_preview(self):
        items = self.table_model.get_all_items()
        if not items:
            self.summary_stats_lbl.setText("لا توجد ملفات في المجلد")
            self.summary_alert_lbl.setText("اختر مجلداً للبدء")
            self.apply_btn.setEnabled(False)
            return

        config_obj = self._build_rename_config()
        self.current_plan = RenameService.generate_preview(items, config_obj)
        self.table_model.refresh_previews()

        sel_count = len([i for i in items if i.is_selected])
        chg_count = self.current_plan.changed_count
        cnf_count = self.current_plan.conflicts_count

        self.summary_stats_lbl.setText(f"المحدد للتسمية: {sel_count}  |  تعديلات مطبقة: {chg_count}")

        if cnf_count > 0:
            self.summary_alert_lbl.setText(f"⚠ تم رصد {cnf_count} تعارض أو اسم غير صالح!")
            self.summary_alert_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #FF4D4F;")
            self.apply_btn.setEnabled(False)
        else:
            self.summary_alert_lbl.setText("✓ جميع الأسماء جاهزة ومتوافقة وبدون أي تعارض")
            self.summary_alert_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #52C41A;")
            self.apply_btn.setEnabled(chg_count > 0)

    # ----------------------------------------------------
    # EXECUTE RENAME
    # ----------------------------------------------------
    def _on_execute_rename(self):
        if not self.current_plan or not self.current_plan.rename_map:
            QMessageBox.information(self, "لا توجد تعديلات", "لم يتم إجراء أي تغيير على أسماء الملفات المحددة.")
            return

        if self.current_plan.conflicts_count > 0:
            QMessageBox.critical(self, "تعارض في الأسماء", "لا يمكن المتابعة مع وجود تعارض في الأسماء. يرجى تعديل النمط لحل التعارض.")
            return

        samples = []
        for old_p, new_p in self.current_plan.rename_map[:8]:
            samples.append((old_p.name, new_p.name))

        is_sys, sys_warn = FileService.is_system_path(self.current_folder)

        dlg = ConfirmDialog(
            op_title="إعادة تسمية الملفات الجماعية",
            folder_path=str(self.current_folder),
            file_count=len(self.current_plan.rename_map),
            samples=samples,
            warning_msg=sys_warn if is_sys else "",
            parent=self
        )

        if dlg.exec() != ConfirmDialog.Accepted:
            return

        self.apply_btn.setEnabled(False)
        self.status_changed.emit("جاري تنفيذ إعادة التسمية بأمان...", True, False)

        self.rename_worker = RenameWorker(self.current_plan, parent=self)
        self.rename_worker.progress.connect(self._on_rename_progress)
        self.rename_worker.finished.connect(self._on_rename_finished)
        self.rename_worker.operation_canceled.connect(self._on_rename_canceled)
        self.rename_worker.start()

    def _on_rename_progress(self, current: int, total: int, filename: str, success: int, fail: int):
        self.progress_changed.emit(current, total)
        self.status_changed.emit(f"جاري معالجة: {filename} ({current}/{total})", True, False)

    def _on_rename_finished(self, success: int, fail: int, errors: List[str], record):
        self.apply_btn.setEnabled(True)
        self.progress_changed.emit(0, 0)
        self._refresh_undo_button()

        if fail == 0:
            self.status_changed.emit(f"تمت إعادة تسمية {success} ملف بنجاح.", False, False)
            QMessageBox.information(
                self,
                "اكتملت العملية بنجاح",
                f"✓ تمت إعادة تسمية جميع الملفات المحددة ({success} ملف) بنجاح فائق.\n\nيمكنك التراجع عن العملية في أي وقت بالضغط على 'التراجع عن آخر عملية'."
            )
        else:
            self.status_changed.emit(f"اكتملت العملية جزئياً ({success} ناجح، {fail} فشل).", False, True)
            err_text = "\n".join(errors[:5])
            if len(errors) > 5:
                err_text += f"\n... والمزيد ({len(errors) - 5} أخطاء أخرى)"
            QMessageBox.warning(
                self,
                "اكتمال جزئي",
                f"نجحت معالجة {success} ملف، بينما تعذر تعديل {fail} ملف (قد تكون مفتوحة بواسطة برامج أخرى):\n\n{err_text}"
            )

        self._start_scan()

    def _on_rename_canceled(self):
        self.apply_btn.setEnabled(True)
        self.progress_changed.emit(0, 0)
        self.status_changed.emit("تم إلغاء عملية إعادة التسمية.", False, True)
        QMessageBox.information(self, "تم الإلغاء", "تم إيقاف عملية إعادة التسمية.")
        self._start_scan()

    def _refresh_undo_button(self):
        rec = undo_manager.get_last_undoable()
        if rec and rec.op_type == "rename":
            self.undo_btn.setEnabled(True)
            self.undo_btn.setText(f"  التراجع عن آخر عملية ({len(rec.items)} ملف)")
        else:
            self.undo_btn.setEnabled(False)
            self.undo_btn.setText("  التراجع عن آخر عملية (لا يوجد)")

    def _on_undo_rename(self):
        rec = undo_manager.get_last_undoable()
        if not rec:
            QMessageBox.information(self, "لا يوجد تراجع", "لا توجد عملية سابقة يمكن التراجع عنها.")
            return

        confirm = QMessageBox.question(
            self,
            "تأكيد التراجع",
            f"هل أنت متأكد من رغبتك في التراجع عن العملية الأخيرة؟\nسيتم استعادة الأسماء السابقة لـ {len(rec.items)} ملف.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        self.undo_btn.setEnabled(False)
        self.status_changed.emit("جاري التراجع واستعادة الأسماء السابقة...", True, False)

        self.undo_worker = UndoWorker(rec, parent=self)
        self.undo_worker.progress.connect(lambda cur, tot, fname, s, f: self.progress_changed.emit(cur, tot))
        self.undo_worker.finished.connect(self._on_undo_finished)
        self.undo_worker.start()

    def _on_undo_finished(self, success: int, fail: int, errors: List[str]):
        self.progress_changed.emit(0, 0)
        self._refresh_undo_button()
        self.status_changed.emit(f"اكتمل التراجع: استعادة {success} ملف.", False, False)
        QMessageBox.information(
            self,
            "اكتمل التراجع",
            f"✓ تمت استعادة الأسماء السابقة لـ {success} ملف بنجاح."
        )
        self._start_scan()

    # ----------------------------------------------------
    # CONTEXT MENU
    # ----------------------------------------------------
    def _show_context_menu(self, pos: QPoint):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return

        item = self.table_model.item_at(index.row())
        if not item:
            return

        menu = QMenu(self)
        menu.setStyleSheet("background-color: #2B2B2B; border: 1px solid #444444; padding: 4px;")

        act_open = menu.addAction(get_icon("play", "#52C41A", 14), "تشغيل / فتح الملف")
        act_explorer = menu.addAction(get_icon("folder_open", "#0078D4", 14), "فتح موقع الملف في Explorer")
        menu.addSeparator()
        act_copy_path = menu.addAction(get_icon("file", "#AAAAAA", 14), "نسخ المسار الكامل")
        act_copy_name = menu.addAction(get_icon("file", "#AAAAAA", 14), "نسخ اسم الملف")
        menu.addSeparator()
        act_cmd = menu.addAction(get_icon("settings", "#AAAAAA", 14), "فتح موجه الأوامر CMD هنا")
        act_powershell = menu.addAction(get_icon("settings", "#60CDFF", 14), "فتح PowerShell هنا")
        menu.addSeparator()
        act_remove = menu.addAction(get_icon("cancel", "#FF4D4F", 14), "إزالة الملف من القائمة الحالية")

        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))
        if action == act_open:
            FileService.open_file(item.path)
        elif action == act_explorer:
            FileService.open_in_explorer(item.path)
        elif action == act_copy_path:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(str(item.path))
        elif action == act_copy_name:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(item.original_name)
        elif action == act_cmd:
            FileService.open_terminal(item.path.parent, "cmd")
        elif action == act_powershell:
            FileService.open_terminal(item.path.parent, "powershell")
        elif action == act_remove:
            self.table_model.remove_item_at(index.row())
            self._update_preview()
