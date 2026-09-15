# -*- coding: utf-8 -*-
"""
SINAX Smart Organize Page
Professional, responsive File Organization tool with 6 classification modes,
interactive pre-execution preview with editable target folders, move/copy modes,
live folder distribution summary, and 100% reliable one-click undo.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QScrollArea,
    QFileDialog, QMessageBox, QProgressBar, QAbstractItemView,
    QRadioButton, QButtonGroup, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor

from app.core.constants import APP_NAME, FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.core.config import config
from app.core.logger import get_logger
from app.core.undo_manager import undo_manager
from app.models.file_item import format_file_size
from app.services.organize_service import OrganizeService, OrganizePlan, OrganizeItem
from app.workers.organize_worker import OrganizeWorker
from app.ui.icons import get_icon

logger = get_logger("smart_organize_page")


class SmartOrganizePage(QWidget):
    """Interactive Smart File Organization Page."""

    status_changed = Signal(str, bool, bool)  # text, is_loading, is_error
    progress_changed = Signal(int, int)  # current, total
    back_to_hub_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_folder: Optional[Path] = None
        self.scanned_files: List[Path] = []
        self.current_plan: Optional[OrganizePlan] = None
        self.organize_worker: Optional[OrganizeWorker] = None
        self.setAcceptDrops(True)

        self._init_ui()

        # Load last used directory if available
        last_dir = config.get("last_opened_folder")
        if last_dir and Path(last_dir).exists():
            self.set_directory(Path(last_dir))

    def _wrap_in_scroll(self, content_widget: QWidget) -> QScrollArea:
        """Wraps a widget in a borderless, responsive QScrollArea."""
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
        # 1. TOP BAR: Folder Picker, Subfolders & Hub Navigation
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
        self.path_edit.setPlaceholderText("اختر المجلد المراد تنظيمه أو اسحبه إلى هنا...")
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

        self.subfolder_cb = QCheckBox("تضمين المجلدات الفرعية")
        self.subfolder_cb.setChecked(False)
        self.subfolder_cb.toggled.connect(self._start_scan)
        top_layout.addWidget(self.subfolder_cb)

        refresh_btn = QPushButton()
        refresh_btn.setIcon(get_icon("refresh", "#AAAAAA", 16))
        refresh_btn.setToolTip("إعادة فحص المجلد")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self._start_scan)
        top_layout.addWidget(refresh_btn)

        back_btn = QPushButton("  العودة للمركز")
        back_btn.setIcon(get_icon("arrow_back", "#AAAAAA", 16))
        back_btn.setMinimumHeight(36)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_hub_requested.emit)
        top_layout.addWidget(back_btn)

        main_layout.addWidget(top_frame)

        # ----------------------------------------------------
        # 2. MAIN SPLITTER: Preview Table & Settings Panel
        # ----------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- PREVIEW TABLE PANEL ---
        table_panel = QFrame()
        table_panel.setObjectName("tablePanel")
        table_panel.setMinimumWidth(480)
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(10, 10, 10, 10)
        table_layout.setSpacing(8)

        # Action toolbar above table
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        lbl_mode = QLabel("وضع التنظيم:")
        lbl_mode.setStyleSheet("font-size: 12px; font-weight: 600;")
        toolbar.addWidget(lbl_mode)

        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumHeight(34)
        self.mode_combo.addItem("حسب نوع وتصنيف الملفات (PDF, صور, فيديو...)", "category")
        self.mode_combo.addItem("حسب الامتداد الدقيق (PDF, DOCX, PNG...)", "extension")
        self.mode_combo.addItem("التنظيم الأكاديمي والذكي (محاضرات, واجبات, امتحانات...)", "academic")
        self.mode_combo.addItem("حسب سنة التعديل (2024, 2025...)", "year")
        self.mode_combo.addItem("حسب الشهر والسنة (2025/يناير...)", "month")
        self.mode_combo.addItem("حسب نطاق الحجم (صغيرة, متوسطة, كبيرة...)", "size")
        self.mode_combo.currentIndexChanged.connect(self._regenerate_plan)
        toolbar.addWidget(self.mode_combo, 1)

        btn_sel_all = QPushButton("تحديد الكل")
        btn_sel_all.setMinimumHeight(30)
        btn_sel_all.setCursor(Qt.PointingHandCursor)
        btn_sel_all.clicked.connect(lambda: self._select_all(True))
        toolbar.addWidget(btn_sel_all)

        btn_desel = QPushButton("إلغاء التحديد")
        btn_desel.setMinimumHeight(30)
        btn_desel.setCursor(Qt.PointingHandCursor)
        btn_desel.clicked.connect(lambda: self._select_all(False))
        toolbar.addWidget(btn_desel)

        btn_invert = QPushButton("عكس")
        btn_invert.setMinimumHeight(30)
        btn_invert.setCursor(Qt.PointingHandCursor)
        btn_invert.clicked.connect(self._invert_selection)
        toolbar.addWidget(btn_invert)

        table_layout.addLayout(toolbar)

        # Table widget
        self.table = QTableWidget(0, 6)
        self.preview_table = self.table
        self.table.setHorizontalHeaderLabels([
            "تحديد", "#", "اسم الملف", "الحجم", "المجلد المقترح (قابل للتعديل)", "المسار الجديد المعاين"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 220)
        self.table.setColumnWidth(4, 200)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().hide()
        self.table.itemChanged.connect(self._on_table_item_changed)
        table_layout.addWidget(self.table, 1)

        self.table_footer = QLabel("لا توجد ملفات محملة. اختر مجلداً للبدء.")
        self.table_footer.setStyleSheet("font-size: 11px; color: #888888; padding: 2px 4px;")
        table_layout.addWidget(self.table_footer)

        splitter.addWidget(table_panel)

        # --- SETTINGS & CONTROL PANEL ---
        settings_panel = QFrame()
        settings_panel.setObjectName("rulesPanel")
        settings_panel.setMinimumWidth(400)
        settings_outer_layout = QVBoxLayout(settings_panel)
        settings_outer_layout.setContentsMargins(0, 0, 0, 0)
        settings_outer_layout.setSpacing(0)

        # Scrollable content widget
        content_widget = QWidget()
        rules_layout = QVBoxLayout(content_widget)
        rules_layout.setContentsMargins(12, 12, 12, 12)
        rules_layout.setSpacing(12)

        # 1. Operation Options Group
        action_box = QGroupBox("طريقة التنظيم والأمان")
        act_layout = QVBoxLayout(action_box)
        act_layout.setContentsMargins(14, 22, 14, 14)
        act_layout.setSpacing(10)

        lbl_act = QLabel("نوع العملية:")
        lbl_act.setStyleSheet("font-size: 12px; font-weight: 600;")
        act_layout.addWidget(lbl_act)

        act_row = QHBoxLayout()
        self.rb_move = QRadioButton("نقل الملفات (Move)")
        self.rb_move.setChecked(True)
        self.rb_move.toggled.connect(self._regenerate_plan)
        act_row.addWidget(self.rb_move)

        self.rb_copy = QRadioButton("نسخ الملفات (Copy)")
        self.rb_copy.toggled.connect(self._regenerate_plan)
        act_row.addWidget(self.rb_copy)
        act_layout.addLayout(act_row)

        lbl_col = QLabel("عند وجود ملف بنفس الاسم:")
        lbl_col.setStyleSheet("font-size: 12px; font-weight: 600;")
        act_layout.addWidget(lbl_col)

        self.collision_combo = QComboBox()
        self.collision_combo.setMinimumHeight(34)
        self.collision_combo.addItem("إعادة تسمية ذكية تلقائياً: (1)", "rename")
        self.collision_combo.addItem("تخطي الملف المكرر", "skip")
        self.collision_combo.addItem("استبدال الملف الموجود", "overwrite")
        self.collision_combo.currentIndexChanged.connect(self._regenerate_plan)
        act_layout.addWidget(self.collision_combo)

        rules_layout.addWidget(action_box)

        # 2. Target Location Group
        dest_box = QGroupBox("المجلد الحاوي للمخرجات")
        dest_layout = QVBoxLayout(dest_box)
        dest_layout.setContentsMargins(14, 22, 14, 14)
        dest_layout.setSpacing(8)

        self.rb_dest_same = QRadioButton("التنظيم داخل نفس المجلد (مجلدات فرعية)")
        self.rb_dest_same.setChecked(True)
        self.rb_dest_same.toggled.connect(self._on_dest_mode_changed)
        dest_layout.addWidget(self.rb_dest_same)

        self.rb_dest_custom = QRadioButton("نقل/نسخ إلى مجلد خارجي مخصص:")
        self.rb_dest_custom.toggled.connect(self._on_dest_mode_changed)
        dest_layout.addWidget(self.rb_dest_custom)

        dest_row = QHBoxLayout()
        self.custom_dest_edit = QLineEdit()
        self.custom_dest_edit.setPlaceholderText("اختر مسار المجلد الخارجي...")
        self.custom_dest_edit.setMinimumHeight(34)
        self.custom_dest_edit.setEnabled(False)
        self.custom_dest_edit.textChanged.connect(self._regenerate_plan)
        dest_row.addWidget(self.custom_dest_edit, 1)

        self.btn_browse_dest = QPushButton("استعراض...")
        self.btn_browse_dest.setMinimumHeight(34)
        self.btn_browse_dest.setEnabled(False)
        self.btn_browse_dest.clicked.connect(self._on_browse_dest_dir)
        dest_row.addWidget(self.btn_browse_dest)
        dest_layout.addLayout(dest_row)

        rules_layout.addWidget(dest_box)

        # 3. Proposed Folders Distribution Summary Card
        dist_box = QGroupBox("توزيع المجلدات المقترحة")
        dist_layout = QVBoxLayout(dist_box)
        dist_layout.setContentsMargins(14, 22, 14, 14)
        dist_layout.setSpacing(8)

        self.folders_summary_lbl = QLabel("لم يتم إنشاء خطة تنظيم بعد.")
        self.folders_summary_lbl.setStyleSheet("font-size: 11px; color: #CCCCCC; line-height: 1.4;")
        self.folders_summary_lbl.setWordWrap(True)
        dist_layout.addWidget(self.folders_summary_lbl)

        rules_layout.addWidget(dist_box)

        rules_layout.addStretch(1)

        scroll_area = self._wrap_in_scroll(content_widget)
        settings_outer_layout.addWidget(scroll_area, 1)

        # 4. Pinned Bottom Execution Panel
        bottom_action_panel = QFrame()
        bottom_action_panel.setObjectName("bottomActionPanel")
        b_layout = QVBoxLayout(bottom_action_panel)
        b_layout.setContentsMargins(12, 8, 12, 12)
        b_layout.setSpacing(8)

        # Progress Section
        self.progress_box = QFrame()
        pb_layout = QVBoxLayout(self.progress_box)
        pb_layout.setContentsMargins(0, 2, 0, 2)
        pb_layout.setSpacing(6)

        self.progress_lbl = QLabel("جاري التنظيم...")
        self.progress_lbl.setStyleSheet("font-size: 11px; color: #60CDFF;")
        pb_layout.addWidget(self.progress_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        pb_layout.addWidget(self.progress_bar)
        self.progress_box.hide()
        b_layout.addWidget(self.progress_box)

        # Action Buttons
        self.execute_btn = QPushButton("  بدء التنظيم الذكي")
        self.execute_btn.setProperty("class", "PrimaryButton")
        self.execute_btn.setIcon(get_icon("play", "#FFFFFF", 16))
        self.execute_btn.setMinimumHeight(42)
        self.execute_btn.setCursor(Qt.PointingHandCursor)
        self.execute_btn.clicked.connect(self._on_execute_organize)
        b_layout.addWidget(self.execute_btn)

        self.undo_btn = QPushButton("  التراجع عن آخر عملية تنظيم")
        self.undo_btn.setIcon(get_icon("undo", "#AAAAAA", 16))
        self.undo_btn.setMinimumHeight(34)
        self.undo_btn.setCursor(Qt.PointingHandCursor)
        self.undo_btn.clicked.connect(self._on_undo_organize)
        self._refresh_undo_button()
        b_layout.addWidget(self.undo_btn)

        self.cancel_btn = QPushButton("  إلغاء العملية")
        self.cancel_btn.setProperty("class", "DangerButton")
        self.cancel_btn.setMinimumHeight(34)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._on_cancel_organize)
        self.cancel_btn.hide()
        b_layout.addWidget(self.cancel_btn)

        settings_outer_layout.addWidget(bottom_action_panel)

        splitter.addWidget(settings_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([650, 420])
        main_layout.addWidget(splitter, 1)

    # ----------------------------------------------------
    # FOLDER SCANNING & DRAG AND DROP
    # ----------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            p = Path(urls[0].toLocalFile())
            if p.is_dir():
                self.set_directory(p)
            elif p.is_file():
                self.set_directory(p.parent)

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "اختر المجلد المراد تنظيمه",
            str(self.current_folder or Path.home() / "Desktop")
        )
        if folder:
            self.set_directory(Path(folder))

    def _on_path_entered(self):
        txt = self.path_edit.text().strip()
        p = Path(txt)
        if p.exists() and p.is_dir():
            self.set_directory(p)
        else:
            QMessageBox.warning(self, "مسار غير صحيح", "المسار المدخل غير موجود أو ليس مجلداً صحيحاً.")

    def set_directory(self, folder: Path):
        self.current_folder = Path(folder).resolve()
        self.path_edit.setText(str(self.current_folder))
        config.add_recent_folder(str(self.current_folder))
        self._refresh_recent_folders()
        self._start_scan()

    def _refresh_recent_folders(self):
        self.recent_combo.blockSignals(True)
        self.recent_combo.clear()
        self.recent_combo.addItem("▼ المجلدات الأخيرة")
        recents = config.get_recent_folders()
        for r in recents:
            p = Path(r)
            self.recent_combo.addItem(f"📁 {p.name} ({p.parent})", r)
        self.recent_combo.blockSignals(False)

    def _on_recent_selected(self, index: int):
        if index <= 0:
            return
        path_str = self.recent_combo.itemData(index)
        if path_str:
            p = Path(path_str)
            if p.exists():
                self.set_directory(p)

    def _on_dest_mode_changed(self):
        is_custom = self.rb_dest_custom.isChecked()
        self.custom_dest_edit.setEnabled(is_custom)
        self.btn_browse_dest.setEnabled(is_custom)
        if is_custom and not self.custom_dest_edit.text():
            self.custom_dest_edit.setText(str(Path.home() / "Desktop" / "مجلد_منظم"))
        self._regenerate_plan()

    def _on_browse_dest_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "اختر مجلد الحفظ المنظم",
            self.custom_dest_edit.text() or str(Path.home() / "Desktop")
        )
        if folder:
            self.custom_dest_edit.setText(folder)
            self._regenerate_plan()

    def _start_scan(self):
        if not self.current_folder or not self.current_folder.exists():
            return

        self.status_changed.emit("جاري فحص المجلد وقراءة الملفات...", True, False)
        files = []
        try:
            if self.subfolder_cb.isChecked():
                files = [f for f in self.current_folder.rglob("*") if f.is_file()]
            else:
                files = [f for f in self.current_folder.glob("*") if f.is_file()]
        except Exception as e:
            logger.error(f"Error scanning folder: {e}")

        self.scanned_files = files
        self.status_changed.emit(f"تم العثور على {len(files)} ملف.", False, False)
        self._regenerate_plan()

    # ----------------------------------------------------
    # PLAN GENERATION & PREVIEW POPULATION
    # ----------------------------------------------------
    def _regenerate_plan(self):
        if not self.current_folder or not self.scanned_files:
            self.table.setRowCount(0)
            self.table_footer.setText("لا توجد ملفات محددة.")
            self.folders_summary_lbl.setText("لا توجد ملفات للتنظيم.")
            self.execute_btn.setEnabled(False)
            return

        # Determine target base dir
        if self.rb_dest_same.isChecked():
            target_base = self.current_folder
        else:
            custom_path = self.custom_dest_edit.text().strip()
            target_base = Path(custom_path) if custom_path else self.current_folder

        mode = self.mode_combo.currentData()
        action_type = "move" if self.rb_move.isChecked() else "copy"
        col_strategy = self.collision_combo.currentData()

        self.current_plan = OrganizeService.generate_plan(
            files=self.scanned_files,
            source_dir=self.current_folder,
            target_base_dir=target_base,
            mode=mode,
            action_type=action_type,
            collision_strategy=col_strategy
        )

        self._populate_table()
        self._update_summary_card()
        self.execute_btn.setEnabled(len(self.current_plan.items) > 0)

    def _populate_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        if not self.current_plan:
            self.table.blockSignals(False)
            return

        total_bytes = 0
        for idx, it in enumerate(self.current_plan.items):
            self.table.insertRow(idx)

            # 0: Checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if it.is_selected else Qt.Unchecked)
            self.table.setItem(idx, 0, chk)

            # 1: #
            it_idx = QTableWidgetItem(str(idx + 1))
            it_idx.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 1, it_idx)

            # 2: Filename + Icon
            icon_name = 'file'
            cat_color = '#888888'
            if it.category_key in FILE_CATEGORIES:
                cat_color = FILE_CATEGORIES[it.category_key].get('color', '#888888')
            icon = get_icon(it.category_key if it.category_key != 'other' else 'file', cat_color, 16)

            it_name = QTableWidgetItem(icon, it.filename)
            self.table.setItem(idx, 2, it_name)

            # 3: Size
            it_sz = QTableWidgetItem(it.formatted_size)
            it_sz.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 3, it_sz)

            # 4: Suggested Target Folder (User editable!)
            it_folder = QTableWidgetItem(it.target_folder_rel)
            it_folder.setToolTip("يمكنك النقر المزدوج لتعديل المجلد الوجهة بحرية")
            it_folder.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(idx, 4, it_folder)

            # 5: New Path Preview
            it_dest = QTableWidgetItem(str(it.target_path_abs))
            it_dest.setForeground(QColor("#60CDFF"))
            it_dest.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(idx, 5, it_dest)

            if it.is_selected:
                total_bytes += it.size_bytes

        count = len(self.current_plan.items)
        sel_count = len(self.current_plan.selected_items)
        sz_str = format_file_size(total_bytes)
        self.table_footer.setText(f"المحدد: {sel_count} من أصل {count} ملف | الحجم الإجمالي: {sz_str}")

        self.table.blockSignals(False)

    def _on_table_item_changed(self, item: QTableWidgetItem):
        if not self.current_plan or item.row() >= len(self.current_plan.items):
            return

        row = item.row()
        col = item.column()
        plan_item = self.current_plan.items[row]

        if col == 0:
            # Checkbox toggled
            plan_item.is_selected = (item.checkState() == Qt.Checked)
            self._update_summary_card()
            sel_count = len(self.current_plan.selected_items)
            self.table_footer.setText(f"المحدد للتنظيم: {sel_count} من {len(self.current_plan.items)} ملف")

        elif col == 4:
            # User edited target folder directly in table
            new_folder = item.text().strip()
            if new_folder:
                plan_item.target_folder_rel = new_folder
                plan_item.target_folder_abs = self.current_plan.target_base_dir / new_folder
                plan_item.target_path_abs = plan_item.target_folder_abs / plan_item.filename

                # Update path preview column
                dest_item = self.table.item(row, 5)
                if dest_item:
                    dest_item.setText(str(plan_item.target_path_abs))
                self._update_summary_card()

    def _select_all(self, checked: bool):
        if not self.current_plan:
            return
        self.table.blockSignals(True)
        for idx in range(self.table.rowCount()):
            it = self.table.item(idx, 0)
            if it:
                it.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self.current_plan.items[idx].is_selected = checked
        self.table.blockSignals(False)
        self._update_summary_card()

    def _invert_selection(self):
        if not self.current_plan:
            return
        self.table.blockSignals(True)
        for idx in range(self.table.rowCount()):
            it = self.table.item(idx, 0)
            if it:
                new_state = Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked
                it.setCheckState(new_state)
                self.current_plan.items[idx].is_selected = (new_state == Qt.Checked)
        self.table.blockSignals(False)
        self._update_summary_card()

    def _update_summary_card(self):
        if not self.current_plan or not self.current_plan.items:
            self.folders_summary_lbl.setText("لا توجد خطة تنظيم نشطة.")
            return

        summary = self.current_plan.folders_summary
        total_folders = len(summary)
        sel_count = len(self.current_plan.selected_items)

        lines = [
            f"<b>الملفات المحددة:</b> {sel_count} ملف",
            f"<b>المجلدات التي سيتم إنشاؤها:</b> {total_folders} مجلد فرعي",
            "<hr style='border: 0.5px solid #383838; margin: 4px 0;'>"
        ]

        for folder_name, count in sorted(summary.items(), key=lambda x: x[1], reverse=True)[:8]:
            lines.append(f"📁 <b>{folder_name}</b>: {count} ملف")

        if len(summary) > 8:
            lines.append(f"... والمزيد ({len(summary) - 8} مجلدات إضافية)")

        self.folders_summary_lbl.setText("<br>".join(lines))

    # ----------------------------------------------------
    # EXECUTION & BACKGROUND WORKER
    # ----------------------------------------------------
    def _on_execute_organize(self):
        if not self.current_plan or not self.current_plan.selected_items:
            QMessageBox.warning(self, "تنبيه", "الرجاء تحديد ملف واحد على الأقل لتنظيمه.")
            return

        action_name = "نقل" if self.current_plan.action_type == "move" else "نسخ"
        count = len(self.current_plan.selected_items)
        folders_count = len(self.current_plan.folders_summary)

        reply = QMessageBox.question(
            self,
            f"تأكيد عملية {action_name}",
            f"هل أنت متأكد من رغبتك في {action_name} {count} ملف إلى {folders_count} مجلد فرعي؟\n\n(ملاحظة: يمكنك التراجع الفوري عن هذه العملية في أي وقت بنقرة واحدة).",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        self.execute_btn.setEnabled(False)
        self.cancel_btn.show()
        self.progress_box.show()
        self.progress_bar.setValue(0)
        self.progress_lbl.setText("جاري تهيئة عملية التنظيم...")

        self.organize_worker = OrganizeWorker(self.current_plan, parent=self)
        self.organize_worker.progress_updated.connect(self._on_organize_progress)
        self.organize_worker.organize_finished.connect(self._on_organize_finished)
        self.organize_worker.organize_failed.connect(self._on_organize_failed)
        self.organize_worker.operation_canceled.connect(self._on_organize_canceled)
        self.organize_worker.start()

        self.status_changed.emit(f"جاري {action_name} الملفات وتنظيمها في الخلفية...", True, False)

    def _on_organize_progress(self, current: int, total: int, filename: str, percent: int):
        self.progress_bar.setValue(percent)
        self.progress_lbl.setText(f"معالجة {current} من {total} ({percent}%): {filename}")
        self.progress_changed.emit(current, total)

    def _on_organize_finished(self, success_count: int, fail_count: int, errors: List[str], record):
        self.execute_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress_box.hide()
        self._refresh_undo_button()

        self.status_changed.emit(f"اكتمل التنظيم: تم نقل/نسخ {success_count} ملف بنجاح.", False, False)

        msg = QMessageBox(self)
        msg.setWindowTitle("اكتمل التنظيم الذكي")
        msg.setText(f"<b>تمت عملية التنظيم بنجاح!</b><br><br>تمت معالجة: {success_count} ملف.<br>حالات الفشل: {fail_count}")
        btn_open = msg.addButton("  فتح المجلد المنظم", QMessageBox.ActionRole)
        btn_ok = msg.addButton("  تم", QMessageBox.AcceptRole)

        msg.exec()

        if msg.clickedButton() == btn_open and self.current_plan:
            target_base = str(self.current_plan.target_base_dir)
            if Path(target_base).exists():
                os.startfile(target_base)

        # Refresh folder
        self._start_scan()

    def _on_organize_failed(self, err_msg: str):
        self.execute_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress_box.hide()
        self.status_changed.emit(f"فشلت عملية التنظيم: {err_msg}", False, True)
        QMessageBox.critical(self, "خطأ في التنظيم", f"حدث خطأ أثناء التنظيم:\n\n{err_msg}")

    def _on_cancel_organize(self):
        if self.organize_worker and self.organize_worker.isRunning():
            self.progress_lbl.setText("جاري إيقاف العملية بأمان...")
            self.organize_worker.cancel()

    def _on_organize_canceled(self):
        self.execute_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress_box.hide()
        self.status_changed.emit("تم إلغاء عملية التنظيم.", False, False)
        QMessageBox.information(self, "تم الإلغاء", "تم إلغاء العملية بأمان.")

    # ----------------------------------------------------
    # UNDO ROLLBACK
    # ----------------------------------------------------
    def _refresh_undo_button(self):
        rec = undo_manager.get_last_undoable()
        if rec and rec.op_type == "organize":
            self.undo_btn.setEnabled(True)
            self.undo_btn.setText(f"  التراجع عن آخر تنظيم ({len(rec.items)} ملف)")
        else:
            self.undo_btn.setEnabled(False)
            self.undo_btn.setText("  التراجع عن آخر تنظيم")

    def _on_undo_organize(self):
        rec = undo_manager.get_last_undoable()
        if not rec or rec.op_type != "organize":
            QMessageBox.information(self, "تنبيه", "لا توجد عمليات تنظيم سابقة للتراجع عنها.")
            return

        reply = QMessageBox.question(
            self,
            "تأكيد التراجع",
            f"هل تريد التراجع عن عملية التنظيم الأخيرة وإعادة {len(rec.items)} ملف إلى مساراتها الأصلية؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        success, fail, errors = OrganizeService.undo_operation(rec)
        rec.status = "reverted"
        undo_manager.save()
        self._refresh_undo_button()

        if fail == 0:
            QMessageBox.information(self, "تم التراجع بنجاح", f"تمت استعادة كافة الملفات ({success} ملف) إلى مواقعها الأصلية بنجاح.")
        else:
            QMessageBox.warning(self, "اكتمل التراجع مع بعض التنبيهات", f"تمت استعادة {success} ملف، وتعذر استعادة {fail} ملف.")

        self._start_scan()
