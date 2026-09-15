# -*- coding: utf-8 -*-
"""
SINAX System & Storage - Storage Analyzer Subpage (محلل التخزين)
Deep TreeSize-style storage analysis featuring:
- Interactive Treemap Visualizer
- Explorer Folder Tree with proportional capacity bars
- Top Largest Files (Top 10 / 50 / 100 / 500)
- Top Folders ranking
- Category, Extension, Age, and System Reserved breakdown
- Point-in-time Snapshot saving
"""

import os
import subprocess
import threading
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.system_storage.disk_health_service import DiskHealthService
from app.services.system_storage.snapshot_service import SnapshotService
from app.services.system_storage.storage_analyzer import (
    CATEGORY_CONFIG,
    StorageAnalysisReport,
    StorageAnalyzer,
)
from app.services.system_storage.storage_scanner import (
    FastStorageScanner,
    FileItem,
    FolderNode,
    ScanResult,
    ScanToken,
    format_bytes,
)
from app.ui.icons import get_icon
from app.ui.pages.system_storage.chart_widgets import CategoryBarWidget
from app.ui.pages.system_storage.treemap_widget import InteractiveTreemapWidget


class ScanWorker(QThread):
    """Worker thread running FastStorageScanner."""

    progress = Signal(dict)
    finished_scan = Signal(object)     # ScanResult
    error = Signal(str)

    def __init__(self, target_path: str, token: ScanToken, parent=None):
        super().__init__(parent)
        self.target_path = target_path
        self.token = token

    def run(self):
        try:
            scanner = FastStorageScanner()
            result = scanner.scan_path(
                root_path=self.target_path,
                progress_callback=self.progress.emit,
                token=self.token
            )
            self.finished_scan.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AnalyzerSubpage(QWidget):
    """Comprehensive disk storage analyzer and visualizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.token: Optional[ScanToken] = None
        self.worker: Optional[ScanWorker] = None
        self.current_report: Optional[StorageAnalysisReport] = None
        self._init_ui()
        self.populate_drives()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Top Controls Bar
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background: #161B22; border: 1px solid #30363D;
                border-radius: 10px; padding: 6px;
            }
        """)
        c_layout = QHBoxLayout(controls_frame)
        c_layout.setContentsMargins(12, 8, 12, 8)
        c_layout.setSpacing(10)

        lbl_target = QLabel("المسار المستهدف:")
        lbl_target.setStyleSheet("color: #C9D1D9; font-weight: bold; font-size: 12px;")
        c_layout.addWidget(lbl_target)

        self.combo_drives = QComboBox()
        self.combo_drives.setMinimumWidth(180)
        self.combo_drives.setStyleSheet("""
            QComboBox {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QComboBox::drop-down { border: none; }
        """)
        c_layout.addWidget(self.combo_drives)

        self.btn_browse = QPushButton("اختيار مجلد...")
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        self.btn_browse.clicked.connect(self._browse_folder)
        c_layout.addWidget(self.btn_browse)

        self.btn_start = QPushButton("بدء الفحص")
        self.btn_start.setIcon(get_icon("storage", color="#FFFFFF"))
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: #1F6FEB; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 6px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #388BFD; }
        """)
        self.btn_start.clicked.connect(self.start_scan)
        c_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("إلغاء")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: #DA3633; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #E5534B; }
        """)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_scan)
        c_layout.addWidget(self.btn_cancel)

        c_layout.addStretch(1)

        self.btn_save_snap = QPushButton("حفظ نقطة فحص")
        self.btn_save_snap.setIcon(get_icon("chart", color="#58A6FF"))
        self.btn_save_snap.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #58A6FF; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        self.btn_save_snap.setEnabled(False)
        self.btn_save_snap.clicked.connect(self.save_snapshot)
        c_layout.addWidget(self.btn_save_snap)

        layout.addWidget(controls_frame)

        # 2. Progress & Status
        self.status_bar_widget = QWidget()
        s_layout = QVBoxLayout(self.status_bar_widget)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(4)

        self.lbl_status = QLabel("حدد القرص أو المجلد ثم اضغط 'بدء الفحص'")
        self.lbl_status.setStyleSheet("color: #8B949E; font-size: 11px;")
        s_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 0) # indeterminate while scanning
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #21262D; border-radius: 4px; border: none; }
            QProgressBar::chunk { background: #58A6FF; border-radius: 4px; }
        """)
        self.progress_bar.setVisible(False)
        s_layout.addWidget(self.progress_bar)

        layout.addWidget(self.status_bar_widget)

        # 3. Main Views Stack / Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #30363D; background: #0D1117; border-radius: 8px; }
            QTabBar::tab {
                background: #161B22; color: #8B949E; padding: 8px 18px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                margin-right: 2px; font-weight: bold; font-size: 12px;
            }
            QTabBar::tab:selected { background: #21262D; color: #58A6FF; border-bottom: 2px solid #58A6FF; }
        """)

        # Tab 1: Treemap
        self.treemap = InteractiveTreemapWidget()
        self.tabs.addTab(self.treemap, "الخريطة التفاعلية (Treemap)")

        # Tab 2: Folder Tree
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderLabels(["المجلد / الملف", "الحجم", "الحجم الفعلي على القرص", "الملفات", "المسار"])
        self.folder_tree.setStyleSheet("""
            QTreeWidget {
                background: #161B22; color: #F0F6FC; border: none; font-size: 12px;
            }
            QHeaderView::section {
                background: #21262D; color: #8B949E; font-weight: bold; padding: 6px; border: none;
            }
        """)
        self.folder_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabs.addTab(self.folder_tree, "شجرة المجلدات (Folder Tree)")

        # Tab 3: Top Files
        self.top_files_table = QTableWidget()
        self.top_files_table.setColumnCount(5)
        self.top_files_table.setHorizontalHeaderLabels(["اسم الملف", "الحجم", "النوع", "تاريخ التعديل", "المسار الكامل"])
        self.top_files_table.setStyleSheet("""
            QTableWidget {
                background: #161B22; color: #F0F6FC; border: none; gridline-color: #21262D; font-size: 12px;
            }
            QHeaderView::section {
                background: #21262D; color: #8B949E; font-weight: bold; padding: 6px; border: none;
            }
        """)
        self.top_files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.top_files_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.top_files_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.top_files_table.customContextMenuRequested.connect(self._top_files_context_menu)
        self.tabs.addTab(self.top_files_table, "أكبر الملفات (Top Files)")

        # Tab 4: Breakdown & Stats
        self.breakdown_widget = self._create_breakdown_tab()
        self.tabs.addTab(self.breakdown_widget, "التوزيع والإحصاءات الشاملة")

        layout.addWidget(self.tabs, 1)

    def _create_breakdown_tab(self) -> QWidget:
        widget = QWidget()
        b_layout = QVBoxLayout(widget)
        b_layout.setContentsMargins(16, 16, 16, 16)
        b_layout.setSpacing(16)

        # Top stacked bar
        self.category_bar = CategoryBarWidget()
        b_layout.addWidget(self.category_bar)

        # Split into Categories table and Top Extensions table
        splitter = QSplitter(Qt.Horizontal)

        # Left: Categories
        cat_box = QFrame()
        cat_box.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 8px;")
        cb_lay = QVBoxLayout(cat_box)
        lbl_c = QLabel("توزيع الفئات الرئيسية")
        lbl_c.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_c.setStyleSheet("color: #F0F6FC; padding: 4px;")
        cb_lay.addWidget(lbl_c)

        self.table_categories = QTableWidget()
        self.table_categories.setColumnCount(4)
        self.table_categories.setHorizontalHeaderLabels(["الفئة", "الحجم", "النسبة", "العدد"])
        self.table_categories.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_categories.setStyleSheet("background: transparent; color: #F0F6FC; border: none;")
        cb_lay.addWidget(self.table_categories)
        splitter.addWidget(cat_box)

        # Right: Top Extensions
        ext_box = QFrame()
        ext_box.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 8px;")
        eb_lay = QVBoxLayout(ext_box)
        lbl_e = QLabel("أكبر الامتدادات استهلاكاً")
        lbl_e.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_e.setStyleSheet("color: #F0F6FC; padding: 4px;")
        eb_lay.addWidget(lbl_e)

        self.table_extensions = QTableWidget()
        self.table_extensions.setColumnCount(4)
        self.table_extensions.setHorizontalHeaderLabels(["الامتداد", "الحجم", "النسبة", "العدد"])
        self.table_extensions.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_extensions.setStyleSheet("background: transparent; color: #F0F6FC; border: none;")
        eb_lay.addWidget(self.table_extensions)
        splitter.addWidget(ext_box)

        b_layout.addWidget(splitter, 1)

        # Bottom System Reserved Space note
        self.lbl_reserved = QLabel("")
        self.lbl_reserved.setStyleSheet("color: #8B949E; font-size: 11px; background: #161B22; padding: 8px; border-radius: 6px;")
        self.lbl_reserved.setVisible(False)
        b_layout.addWidget(self.lbl_reserved)

        return widget

    def populate_drives(self):
        """Populate drives dropdown with active local partitions."""
        self.combo_drives.clear()
        drives = DiskHealthService.get_logical_drives()
        for d in drives:
            label = f"{d.drive_letter} ({format_bytes(d.free_bytes)} حر من {format_bytes(d.total_bytes)})"
            self.combo_drives.addItem(label, d.mount_point)

    def select_target(self, target_path: str):
        """Programmatically select target path and initiate scan."""
        norm = os.path.normpath(target_path).lower()
        matched_idx = -1
        for i in range(self.combo_drives.count()):
            val = str(self.combo_drives.itemData(i)).lower()
            if val.startswith(norm) or norm.startswith(val[:2]):
                matched_idx = i
                break

        if matched_idx >= 0:
            self.combo_drives.setCurrentIndex(matched_idx)
        else:
            self.combo_drives.addItem(target_path, target_path)
            self.combo_drives.setCurrentIndex(self.combo_drives.count() - 1)

        self.start_scan()

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر المجلد لفحص المساحة")
        if folder:
            self.combo_drives.addItem(f"مجلد: {folder}", folder)
            self.combo_drives.setCurrentIndex(self.combo_drives.count() - 1)

    def start_scan(self):
        target = self.combo_drives.currentData()
        if not target or not os.path.exists(target):
            QMessageBox.warning(self, "تنبيه", "المسار المحدد غير صالح أو غير موجود.")
            return

        self.token = ScanToken()
        self.worker = ScanWorker(target, self.token, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_scan.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_save_snap.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText(f"جارٍ فحص {target}...")
        self.worker.start()

    def cancel_scan(self):
        if self.token:
            self.token.cancel()
            self.lbl_status.setText("جارٍ إلغاء الفحص...")

    def _on_progress(self, data: dict):
        if data.get("finished"):
            return
        files = data.get("files", 0)
        folders = data.get("folders", 0)
        size = data.get("size", 0)
        curr = data.get("current_path", "")
        self.lbl_status.setText(f"تم فحص {files:,} ملف و {folders:,} مجلد ({format_bytes(size)}) - {curr[:60]}...")

    def _on_scan_finished(self, scan_result: ScanResult):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)

        if scan_result.is_cancelled:
            self.lbl_status.setText("تم إلغاء عملية الفحص.")
            return

        # Generate deep analysis report
        self.current_report = StorageAnalyzer.analyze_scan_result(scan_result)
        self.btn_save_snap.setEnabled(True)

        self.lbl_status.setText(
            f"اكتمل الفحص في {self.current_report.scan_duration:.2f} ثانية: "
            f"{self.current_report.total_files:,} ملف، {self.current_report.total_folders:,} مجلد، "
            f"الحجم الإجمالي: {format_bytes(self.current_report.total_size)}"
        )

        # 1. Update Treemap
        if scan_result.root_node:
            self.treemap.set_root_node(scan_result.root_node)

        # 2. Update Folder Tree
        self._populate_folder_tree(scan_result.root_node)

        # 3. Update Top Files
        self._populate_top_files(self.current_report.top_files)

        # 4. Update Breakdown
        self._populate_breakdown(self.current_report)

    def _on_scan_error(self, err: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"حدث خطأ أثناء الفحص: {err}")

    def _populate_folder_tree(self, root_node: Optional[FolderNode]):
        self.folder_tree.clear()
        if not root_node:
            return

        def add_node(parent_item, node: FolderNode, depth: int = 0):
            item = QTreeWidgetItem(parent_item)
            item.setText(0, node.name)
            item.setText(1, format_bytes(node.size))
            item.setText(2, format_bytes(node.allocated_size))
            item.setText(3, str(node.files_count))
            item.setText(4, node.path)

            if depth < 2:  # Populate top 2 levels immediately
                for sub in sorted(node.children, key=lambda x: x.size, reverse=True)[:30]:
                    add_node(item, sub, depth + 1)

        root_item = QTreeWidgetItem(self.folder_tree)
        root_item.setText(0, root_node.name)
        root_item.setText(1, format_bytes(root_node.size))
        root_item.setText(2, format_bytes(root_node.allocated_size))
        root_item.setText(3, str(root_node.files_count))
        root_item.setText(4, root_node.path)

        for sub in sorted(root_node.children, key=lambda x: x.size, reverse=True)[:40]:
            add_node(root_item, sub, 1)

        root_item.setExpanded(True)

    def _populate_top_files(self, files: List[FileItem]):
        self.top_files_table.setRowCount(0)
        import time
        from datetime import datetime

        self.top_files_table.setRowCount(len(files))
        for row, f in enumerate(files):
            dt_str = datetime.fromtimestamp(f.modified_time).strftime("%Y-%m-%d %H:%M")
            self.top_files_table.setItem(row, 0, QTableWidgetItem(f.name))
            self.top_files_table.setItem(row, 1, QTableWidgetItem(format_bytes(f.size)))
            self.top_files_table.setItem(row, 2, QTableWidgetItem(CATEGORY_CONFIG.get(f.category, {}).get("label_ar", f.category)))
            self.top_files_table.setItem(row, 3, QTableWidgetItem(dt_str))
            self.top_files_table.setItem(row, 4, QTableWidgetItem(f.path))

    def _populate_breakdown(self, report: StorageAnalysisReport):
        # 1. Bar
        self.category_bar.set_categories(report.categories)

        # 2. Categories Table
        self.table_categories.setRowCount(0)
        active_cats = [c for c in report.categories.values() if c.size > 0]
        active_cats.sort(key=lambda x: x.size, reverse=True)
        self.table_categories.setRowCount(len(active_cats))

        for row, c in enumerate(active_cats):
            self.table_categories.setItem(row, 0, QTableWidgetItem(c.label_ar))
            self.table_categories.setItem(row, 1, QTableWidgetItem(format_bytes(c.size)))
            self.table_categories.setItem(row, 2, QTableWidgetItem(f"{c.percentage:.1f}%"))
            self.table_categories.setItem(row, 3, QTableWidgetItem(f"{c.count:,}"))

        # 3. Extensions Table
        self.table_extensions.setRowCount(0)
        self.table_extensions.setRowCount(len(report.top_extensions))
        for row, ext in enumerate(report.top_extensions):
            self.table_extensions.setItem(row, 0, QTableWidgetItem(ext.ext))
            self.table_extensions.setItem(row, 1, QTableWidgetItem(format_bytes(ext.size)))
            self.table_extensions.setItem(row, 2, QTableWidgetItem(f"{ext.percentage:.1f}%"))
            self.table_extensions.setItem(row, 3, QTableWidgetItem(f"{ext.count:,}"))

        # 4. System Reserved info
        sr = report.system_reserved
        if sr.total_reserved_size > 0:
            parts = []
            if sr.pagefile_size > 0:
                parts.append(f"ملف التبديل (pagefile): {format_bytes(sr.pagefile_size)}")
            if sr.hiberfil_size > 0:
                parts.append(f"ملف السبات (hiberfil): {format_bytes(sr.hiberfil_size)}")
            if sr.windows_old_size > 0:
                parts.append(f"ويندوز القديم (Windows.old): {format_bytes(sr.windows_old_size)}")
            self.lbl_reserved.setText("مساحة النظام المحجوزة: " + " | ".join(parts))
            self.lbl_reserved.setVisible(True)
        else:
            self.lbl_reserved.setVisible(False)

    def _top_files_context_menu(self, pos):
        row = self.top_files_table.currentRow()
        if row < 0:
            return

        path_item = self.top_files_table.item(row, 4)
        if not path_item:
            return
        f_path = path_item.text()

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #161B22; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 16px; border-radius: 4px; }
            QMenu::item:selected { background: #1F6FEB; }
        """)

        act_open = menu.addAction("فتح في مستكشف ويندوز")
        act_copy = menu.addAction("نسخ المسار")

        action = menu.exec(self.top_files_table.mapToGlobal(pos))
        if action == act_open:
            try:
                subprocess.Popen(f'explorer /select,"{os.path.normpath(f_path)}"')
            except Exception:
                pass
        elif action == act_copy:
            QApplication.clipboard().setText(f_path)

    def save_snapshot(self):
        if not self.current_report:
            return
        snap_id = SnapshotService.save_snapshot(self.current_report)
        QMessageBox.information(
            self,
            "تم الحفظ",
            f"تم حفظ نقطة الفحص بنجاح برقم (#{snap_id}) لمتابعة تغير المساحة بمرور الوقت."
        )
