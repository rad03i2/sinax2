# -*- coding: utf-8 -*-
"""
SINAX Converter Workspace
Full interactive workspace for batch file conversion.
Supports Drag & Drop, folders & subfolders, options panel, collision handling,
streaming progress, live speed/ETA, cancellation, and direct result opening.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame, QScrollArea,
    QFileDialog, QMessageBox, QProgressBar, QAbstractItemView,
    QRadioButton, QButtonGroup, QSlider, QSpinBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QCursor

from app.services.conversion.registry import ConversionDefinition
from app.services.conversion.dependency_manager import dependency_manager
from app.workers.conversion_worker import ConversionWorker
from app.ui.pages.converter_components.dependency_dialog import DependencyDialog
from app.services.file_service import FileService
from app.models.file_item import format_file_size
from app.core.constants import FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.core.config import config
from app.ui.icons import get_icon


class ConverterWorkspace(QWidget):
    back_requested = Signal()
    status_changed = Signal(str, bool, bool)
    progress_changed = Signal(int, int)

    def __init__(self, direction: ConversionDefinition, card_id: str = "generic", parent=None):
        super().__init__(parent)
        self.direction = direction
        self.card_id = card_id
        self.source_files: List[Path] = []
        self.worker: Optional[ConversionWorker] = None
        self._dynamic_inputs: Dict[str, Any] = {}
        self.setAcceptDrops(True)
        self._init_ui()
        from app.ui.themes.theme_manager import theme_manager
        theme_manager.theme_changed.connect(self.apply_theme)
        self.apply_theme(theme_manager.effective_theme)

    def apply_theme(self, theme_name: str):
        is_dark = (theme_name == "dark")
        title_color = "#F8FAFC" if is_dark else "#0F172A"
        if hasattr(self, "title_lbl"):
            self.title_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {title_color};")

        if hasattr(self, "btn_back"):
            back_icon_color = "#FFFFFF" if is_dark else "#1E293B"
            self.btn_back.setIcon(get_icon("back", back_icon_color, 14))

        if is_dark:
            if hasattr(self, "prog_box"):
                self.prog_box.setStyleSheet("background: #181818; border: 1px solid #333333; border-radius: 6px; padding: 8px;")
            if hasattr(self, "file_status_lbl"):
                self.file_status_lbl.setStyleSheet("font-size: 11px; color: #60CDFF;")
            if hasattr(self, "stats_lbl"):
                self.stats_lbl.setStyleSheet("font-size: 10px; color: #94A3B8;")
            if hasattr(self, "footer_lbl"):
                self.footer_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; padding: 2px;")
            if hasattr(self, "dep_banner"):
                self.dep_banner.setStyleSheet("background: #332B00; border: 1px solid #FFB900; border-radius: 6px; padding: 6px 12px;")
        else:
            if hasattr(self, "prog_box"):
                self.prog_box.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px;")
            if hasattr(self, "file_status_lbl"):
                self.file_status_lbl.setStyleSheet("font-size: 11px; color: #0284C7;")
            if hasattr(self, "stats_lbl"):
                self.stats_lbl.setStyleSheet("font-size: 10px; color: #64748B;")
            if hasattr(self, "footer_lbl"):
                self.footer_lbl.setStyleSheet("color: #64748B; font-size: 11px; padding: 2px;")
            if hasattr(self, "dep_banner"):
                self.dep_banner.setStyleSheet("background: #FEF3C7; border: 1px solid #F59E0B; border-radius: 6px; padding: 6px 12px;")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)

        # 1. Top Bar: Back Button + Title + Category Badge
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.btn_back = QPushButton("  العودة إلى قائمة التحويلات")
        self.btn_back.setIcon(get_icon("back", "#FFFFFF", 14))
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setMinimumHeight(34)
        self.btn_back.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.btn_back)

        src_up = self.direction.source_ext.upper()
        dst_up = self.direction.target_ext.upper()
        self.title_lbl = QLabel(f"تحويل {src_up} إلى {dst_up} ({self.direction.title_ar})")
        self.title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        top_bar.addWidget(self.title_lbl, 1)

        self.cat_badge = QLabel(self.direction.category.upper())
        self.cat_badge.setStyleSheet("background: #0078D4; color: #FFFFFF; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 10px;")
        top_bar.addWidget(self.cat_badge)

        layout.addLayout(top_bar)

        # 2. Dependency Warning Banner (if missing)
        self.dep_banner = QFrame()
        self.dep_banner.setStyleSheet("background: #332B00; border: 1px solid #FFB900; border-radius: 6px; padding: 6px 12px;")
        dep_layout = QHBoxLayout(self.dep_banner)
        dep_layout.setContentsMargins(8, 6, 8, 6)

        self.dep_lbl = QLabel("يتطلب هذا التحويل أداة خارجية غير مثبتة حالياً.")
        self.dep_lbl.setStyleSheet("color: #FFB900; font-weight: bold;")
        dep_layout.addWidget(self.dep_lbl, 1)

        self.btn_fix_dep = QPushButton("  إعداد وتثبيت المكوّن")
        self.btn_fix_dep.setIcon(get_icon("settings", "#000000", 14))
        self.btn_fix_dep.setCursor(Qt.PointingHandCursor)
        self.btn_fix_dep.setStyleSheet("background: #FFB900; color: #000; font-weight: bold; border-radius: 4px; padding: 4px 10px;")
        self.btn_fix_dep.clicked.connect(self._open_dep_setup)
        dep_layout.addWidget(self.btn_fix_dep)

        layout.addWidget(self.dep_banner)
        self._update_dependency_state()

        # 3. Splitter: Left Table + Right Options Panel
        split = QSplitter(Qt.Horizontal)

        # Left Panel (Files Table & Ingestion)
        left_panel = QWidget()
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0, 0, 0, 0)
        lp_layout.setSpacing(8)

        # Ingestion Toolbar
        tool_row = QHBoxLayout()
        tool_row.setSpacing(8)

        self.btn_add_files = QPushButton("  إضافة ملفات...")
        self.btn_add_files.setIcon(get_icon("file", "#FFFFFF", 14))
        self.btn_add_files.setMinimumHeight(32)
        self.btn_add_files.setCursor(Qt.PointingHandCursor)
        self.btn_add_files.clicked.connect(self._on_add_files)
        tool_row.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton("  إضافة مجلد...")
        self.btn_add_folder.setIcon(get_icon("folder", "#FFB900", 14))
        self.btn_add_folder.setMinimumHeight(32)
        self.btn_add_folder.setCursor(Qt.PointingHandCursor)
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        tool_row.addWidget(self.btn_add_folder)

        self.chk_recursive = QCheckBox("تضمين المجلدات الفرعية")
        tool_row.addWidget(self.chk_recursive)

        tool_row.addStretch(1)

        self.btn_remove = QPushButton("إزالة المحدد")
        self.btn_remove.setMinimumHeight(32)
        self.btn_remove.setCursor(Qt.PointingHandCursor)
        self.btn_remove.clicked.connect(self._on_remove_selected)
        tool_row.addWidget(self.btn_remove)

        self.btn_clear = QPushButton("مسح القائمة")
        self.btn_clear.setMinimumHeight(32)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self._on_clear_files)
        tool_row.addWidget(self.btn_clear)

        lp_layout.addLayout(tool_row)

        # Files Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "اسم الملف", "الحجم", "الحالة", "الملف الناتج"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(1, 260)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().hide()
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        lp_layout.addWidget(self.table, 1)

        # Table Footer
        self.footer_lbl = QLabel("القائمة فارغة. اسحب الملفات إلى هنا أو اضغط على 'إضافة ملفات'.")
        self.footer_lbl.setStyleSheet("color: #888888; font-size: 11px; padding: 2px;")
        lp_layout.addWidget(self.footer_lbl)

        split.addWidget(left_panel)

        # Right Panel (Options & Actions) with responsive ScrollArea
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.verticalScrollBar().setSingleStep(28)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setMinimumWidth(380)

        right_panel = QFrame()
        right_panel.setObjectName("rulesPanel")
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(14, 14, 14, 36)
        rp_layout.setSpacing(12)

        # Destination Folder Group
        dest_box = QGroupBox("مجلد الحفظ (Output Destination)")
        dest_layout = QVBoxLayout(dest_box)
        dest_layout.setContentsMargins(12, 18, 12, 12)
        dest_layout.setSpacing(8)

        self.rb_dest_same = QRadioButton("نفس مجلد الملف المصدر")
        self.rb_dest_same.setChecked(True)
        self.rb_dest_sub = QRadioButton("مجلد فرعي جديد بجانبه (Converted)")
        self.rb_dest_custom = QRadioButton("تحديد مجلد مخصص:")
        dest_layout.addWidget(self.rb_dest_same)
        dest_layout.addWidget(self.rb_dest_sub)
        dest_layout.addWidget(self.rb_dest_custom)

        custom_row = QHBoxLayout()
        self.dest_edit = QLineEdit(str(Path.home() / "Desktop"))
        self.dest_edit.setMinimumHeight(32)
        self.dest_edit.setEnabled(False)
        custom_row.addWidget(self.dest_edit, 1)

        self.btn_browse_dest = QPushButton("استعراض...")
        self.btn_browse_dest.setMinimumHeight(32)
        self.btn_browse_dest.setCursor(Qt.PointingHandCursor)
        self.btn_browse_dest.setEnabled(False)
        self.btn_browse_dest.clicked.connect(self._on_browse_dest)
        custom_row.addWidget(self.btn_browse_dest)
        dest_layout.addLayout(custom_row)

        self.rb_dest_custom.toggled.connect(lambda checked: self.dest_edit.setEnabled(checked))
        self.rb_dest_custom.toggled.connect(lambda checked: self.btn_browse_dest.setEnabled(checked))

        rp_layout.addWidget(dest_box)

        # Collision Policy Group
        col_box = QGroupBox("عند وجود ملف بنفس الاسم في الوجهة")
        col_layout = QVBoxLayout(col_box)
        col_layout.setContentsMargins(12, 18, 12, 12)

        self.col_combo = QComboBox()
        self.col_combo.setMinimumHeight(32)
        self.col_combo.addItem("إعادة تسمية ذكية تلقائياً: (1)", "rename")
        self.col_combo.addItem("تخطي الملف الموجود", "skip")
        self.col_combo.addItem("استبدال الملف الموجود", "overwrite")
        col_layout.addWidget(self.col_combo)
        rp_layout.addWidget(col_box)

        # Dynamic Options Group
        converter = self.direction.get_converter_instance()
        schema = converter.get_options_schema()
        if schema:
            opts_box = QGroupBox("خيارات التحويل المتقدمة")
            opts_layout = QVBoxLayout(opts_box)
            opts_layout.setContentsMargins(12, 18, 12, 12)
            opts_layout.setSpacing(8)

            for key, meta in schema.items():
                lbl = QLabel(meta.get("label", key) + ":")
                lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #CCCCCC;")
                opts_layout.addWidget(lbl)

                if meta.get("type") == "select":
                    cb = QComboBox()
                    cb.setMinimumHeight(30)
                    for opt in meta.get("options", []):
                        cb.addItem(opt)
                    def_val = meta.get("default")
                    if def_val:
                        cb.setCurrentText(def_val)
                    self._dynamic_inputs[key] = cb
                    opts_layout.addWidget(cb)
                elif meta.get("type") == "int":
                    sp = QSpinBox()
                    sp.setMinimumHeight(30)
                    sp.setRange(meta.get("min", 1), meta.get("max", 100))
                    sp.setValue(meta.get("default", 90))
                    self._dynamic_inputs[key] = sp
                    opts_layout.addWidget(sp)
                elif meta.get("type") == "text":
                    le = QLineEdit(meta.get("default", ""))
                    le.setMinimumHeight(30)
                    self._dynamic_inputs[key] = le
                    opts_layout.addWidget(le)

            rp_layout.addWidget(opts_box)

        # Progress Box
        self.prog_box = QFrame()
        self.prog_box.setStyleSheet("background: #181818; border: 1px solid #333; border-radius: 6px; padding: 8px;")
        pb_layout = QVBoxLayout(self.prog_box)
        pb_layout.setSpacing(6)

        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setValue(0)
        self.overall_bar.setTextVisible(True)
        pb_layout.addWidget(self.overall_bar)

        self.file_status_lbl = QLabel("جاهز للبدء.")
        self.file_status_lbl.setStyleSheet("font-size: 11px; color: #60CDFF;")
        pb_layout.addWidget(self.file_status_lbl)

        self.stats_lbl = QLabel("السرعة: -- م.ب/ث | الوقت المتبقي: --")
        self.stats_lbl.setStyleSheet("font-size: 10px; color: #888888;")
        pb_layout.addWidget(self.stats_lbl)

        self.prog_box.hide()
        rp_layout.addWidget(self.prog_box)

        rp_layout.addStretch(1)

        # Action Buttons
        self.btn_start = QPushButton("  بدء التحويل")
        self.btn_start.setProperty("class", "PrimaryButton")
        self.btn_start.setIcon(get_icon("play", "#FFFFFF", 16))
        self.btn_start.setMinimumHeight(44)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._on_start_conversion)
        rp_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("  إلغاء التحويل")
        self.btn_cancel.setProperty("class", "DangerButton")
        self.btn_cancel.setMinimumHeight(36)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._on_cancel_conversion)
        self.btn_cancel.hide()
        rp_layout.addWidget(self.btn_cancel)

        right_scroll.setWidget(right_panel)
        split.addWidget(right_scroll)
        split.setSizes([600, 400])
        layout.addWidget(split, 1)

    def _update_dependency_state(self):
        is_avail = self.direction.is_available()
        if is_avail:
            self.dep_banner.hide()
        else:
            missing = self.direction.get_missing_tools()
            missing_names = ", ".join(dependency_manager.get_tool_info(m)["name_ar"] for m in missing)
            self.dep_lbl.setText(f"يتطلب هذا التحويل توفر أداة: {missing_names}")
            self.dep_banner.show()

    def _open_dep_setup(self):
        missing = self.direction.get_missing_tools()
        if missing:
            dlg = DependencyDialog(missing[0], self)
            if dlg.exec():
                self._update_dependency_state()

    def _on_browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ")
        if folder:
            self.dest_edit.setText(folder)

    def add_files(self, paths: List[Path]):
        """Adds files matching the source extension."""
        src_ext = self.direction.source_ext.lower().lstrip('.')
        added_count = 0
        for p in paths:
            if p.is_file() and p.suffix.lower().lstrip('.') == src_ext:
                if p not in self.source_files:
                    self.source_files.append(p)
                    added_count += 1
        self._populate_table()

    def _on_add_files(self):
        ext = self.direction.source_ext.upper()
        files, _ = QFileDialog.getOpenFileNames(self, f"اختر ملفات {ext}", "", f"{ext} Files (*.{self.direction.source_ext});;All Files (*.*)")
        if files:
            self.add_files([Path(f) for f in files])

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر المجلد")
        if folder:
            p = Path(folder)
            src_ext = self.direction.source_ext.lower().lstrip('.')
            iterator = p.rglob(f"*.{src_ext}") if self.chk_recursive.isChecked() else p.glob(f"*.{src_ext}")
            files = [f for f in iterator if f.is_file()]
            self.add_files(files)

    def _on_remove_selected(self):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        for r in selected_rows:
            if 0 <= r < len(self.source_files):
                self.source_files.pop(r)
        self._populate_table()

    def _on_clear_files(self):
        self.source_files = []
        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)
        self.table.blockSignals(True)

        for idx, p in enumerate(self.source_files):
            self.table.insertRow(idx)

            # 0: #
            it_idx = QTableWidgetItem(str(idx + 1))
            it_idx.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 0, it_idx)

            # 1: Name + Icon
            ext = p.suffix.lower()
            cat_key = EXTENSION_TO_CATEGORY.get(ext, "file")
            cat_color = FILE_CATEGORIES.get(cat_key, {}).get("color", "#60CDFF")
            icon = get_icon(cat_key if cat_key != "other" else "file", cat_color, 16)
            it_name = QTableWidgetItem(icon, p.name)
            it_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(idx, 1, it_name)

            # 2: Size
            try:
                sz_str = format_file_size(p.stat().st_size)
            except Exception:
                sz_str = "0 بايت"
            it_sz = QTableWidgetItem(sz_str)
            it_sz.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(idx, 2, it_sz)

            # 3: Status
            it_st = QTableWidgetItem("جاهز")
            it_st.setTextAlignment(Qt.AlignCenter)
            it_st.setForeground(QColor("#888888"))
            self.table.setItem(idx, 3, it_st)

            # 4: Result
            it_res = QTableWidgetItem("--")
            it_res.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(idx, 4, it_res)

        self.table.blockSignals(False)
        self.footer_lbl.setText(f"إجمالي الملفات المحددة: {len(self.source_files)} ملف.")

    def _on_start_conversion(self):
        if not self.source_files:
            QMessageBox.information(self, "تنبيه", "يرجى إضافة ملفات أولاً للبدء بالتحويل.")
            return

        if not self.direction.is_available():
            self._open_dep_setup()
            return

        # Resolve output directory
        if self.rb_dest_same.isChecked():
            out_dir = self.source_files[0].parent
        elif self.rb_dest_sub.isChecked():
            out_dir = self.source_files[0].parent / "Converted"
        else:
            out_dir = Path(self.dest_edit.text().strip())

        # Resolve dynamic options
        options = {}
        for k, widget in self._dynamic_inputs.items():
            if isinstance(widget, QComboBox):
                options[k] = widget.currentText()
            elif isinstance(widget, QSpinBox):
                options[k] = widget.value()
            elif isinstance(widget, QLineEdit):
                options[k] = widget.text()

        col_policy = self.col_combo.currentData() or "rename"

        # UI State
        self.btn_start.hide()
        self.btn_cancel.show()
        self.prog_box.show()
        self.overall_bar.setValue(0)
        self.btn_add_files.setEnabled(False)
        self.btn_add_folder.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.btn_remove.setEnabled(False)

        # Launch Worker
        self.worker = ConversionWorker(
            files=self.source_files,
            direction=self.direction,
            output_dir=out_dir,
            options=options,
            collision_policy=col_policy,
            card_id=self.card_id
        )
        self.worker.overall_progress.connect(self._on_overall_progress)
        self.worker.file_progress.connect(self._on_file_progress)
        self.worker.file_status.connect(self._on_file_status)
        self.worker.stats_updated.connect(self._on_stats_updated)
        self.worker.finished_all.connect(self._on_finished_all)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.start()

    def _on_cancel_conversion(self):
        if self.worker and self.worker.isRunning():
            self.file_status_lbl.setText("جاري إلغاء العملية بأمان...")
            self.worker.cancel()

    def _on_overall_progress(self, curr: int, total: int, pct: float):
        self.overall_bar.setValue(int(pct))
        self.progress_changed.emit(curr, total)

    def _on_file_progress(self, pct: float, msg: str):
        self.file_status_lbl.setText(msg)

    def _on_file_status(self, row: int, status: str, out_path: str, err: str):
        if row < self.table.rowCount():
            it_st = self.table.item(row, 3)
            if it_st:
                it_st.setText(status)
                if status == "مكتمل":
                    it_st.setForeground(QColor("#52C41A"))
                elif status == "فشل":
                    it_st.setForeground(QColor("#FF4D4F"))
                elif status == "قيد التحويل":
                    it_st.setForeground(QColor("#60CDFF"))

            if out_path:
                it_res = self.table.item(row, 4)
                if it_res:
                    it_res.setText(out_path)
                    it_res.setForeground(QColor("#60CDFF"))

    def _on_stats_updated(self, speed: float, eta: str):
        self.stats_lbl.setText(f"السرعة: {speed:.1f} م.ب/ث | الوقت المتبقي: {eta}")

    def _on_finished_all(self, success: int, fail: int, skipped: int, failed_files: list):
        self._reset_ui_state()
        msg = f"اكتملت العملية بنجاح!\n\n✅ نجح: {success}\n"
        if skipped:
            msg += f"⚠️ تم التخطي: {skipped}\n"
        if fail:
            msg += f"❌ فشل: {fail}\n"
        QMessageBox.information(self, "اكتمل التحويل", msg)

    def _on_cancelled(self):
        self._reset_ui_state()
        QMessageBox.warning(self, "تم الإلغاء", "تم إلغاء عملية التحويل بأمان وحذف الملفات المؤقتة غير المكتملة.")

    def _reset_ui_state(self):
        self.btn_start.show()
        self.btn_cancel.hide()
        self.prog_box.hide()
        self.btn_add_files.setEnabled(True)
        self.btn_add_folder.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.btn_remove.setEnabled(True)

    def _on_item_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        res_item = self.table.item(row, 4)
        if res_item and res_item.text() and res_item.text() != "--":
            FileService.open_file(Path(res_item.text()))
        elif 0 <= row < len(self.source_files):
            FileService.open_file(self.source_files[row])

    def _show_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu(self)
        res_item = self.table.item(row, 4)
        has_out = res_item and res_item.text() and res_item.text() != "--"

        if has_out:
            act_open_res = menu.addAction("فتح الملف الناتج")
            act_open_res.triggered.connect(lambda: FileService.open_file(Path(res_item.text())))

            act_exp_res = menu.addAction("فتح مجلد النتائج")
            act_exp_res.triggered.connect(lambda: FileService.open_in_explorer(Path(res_item.text())))
            menu.addSeparator()

        if 0 <= row < len(self.source_files):
            act_src = menu.addAction("فتح الملف المصدر")
            act_src.triggered.connect(lambda: FileService.open_file(self.source_files[row]))

        menu.exec(QCursor.pos())

    # Drag and Drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = [Path(u.toLocalFile()) for u in urls]
        # Separate files and directories
        all_files = []
        for p in paths:
            if p.is_file():
                all_files.append(p)
            elif p.is_dir():
                src_ext = self.direction.source_ext.lower().lstrip('.')
                all_files.extend(list(p.glob(f"*.{src_ext}")))
        self.add_files(all_files)
