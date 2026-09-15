# -*- coding: utf-8 -*-
"""
SINAX Installed Applications Inventory Subpage
Full interactive applications table with real-time search, multi-criteria filtering,
master-detail QSplitter, right-click context menu, and batch selection.
"""

from typing import Any, Callable, List, Optional

from PySide6.QtCore import QItemSelection, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.broken_entries_service import BrokenEntriesService
from app.services.apps_manager.inventory_service import InventoryService
from app.services.apps_manager.repair_service import RepairService
from app.services.apps_manager.uninstall_service import UninstallService
from app.ui.icons import get_icon
from app.ui.pages.apps_manager.app_detail_panel import AppDetailPanel
from app.ui.pages.apps_manager.apps_table_model import AppsTableModel


class InventorySubpage(QWidget):
    """Interactive applications inventory viewer and manager."""

    uninstall_single_requested = Signal(object)  # InstalledApp
    batch_uninstall_requested = Signal(list)  # List[InstalledApp]
    update_single_requested = Signal(object)  # InstalledApp
    leftover_scan_requested = Signal(object)  # InstalledApp
    open_startup_manager_requested = Signal()
    refresh_needed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._raw_apps: List[InstalledApp] = []
        self._filtered_apps: List[InstalledApp] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Filter and Search Bar
        filter_bar = QFrame()
        filter_bar.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 10px;")
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(8, 6, 8, 6)
        fb_layout.setSpacing(10)

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("بحث بالاسم، الناشر، أو معرف WinGet...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-size: 13px; min-width: 240px;
            }
            QLineEdit:focus { border-color: #58A6FF; }
        """)
        self.search_input.textChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.search_input)

        # Category Filter
        self.combo_category = QComboBox()
        categories = [
            ("all", "كل البرامج والتطبيقات"),
            ("desktop", "برامج سطح المكتب (Win32)"),
            ("store", "متجر مايكروسوفت (MSIX)"),
            ("updates", "يتوفر لها تحديث"),
            ("large", "برامج كبيرة الحجم (>1 GB)"),
            ("startup", "تعمل عند بدء التشغيل"),
            ("running", "تعمل حالياً"),
            ("broken", "إدخالات معطوبة في السجل"),
            ("msi", "مثبتات MSI"),
            ("exe", "مثبتات EXE"),
            ("64bit", "معمارية 64-bit"),
            ("32bit", "معمارية 32-bit"),
            ("system", "مكونات النظام والحزم"),
        ]
        for key, text in categories:
            self.combo_category.addItem(text, key)
        self.combo_category.setStyleSheet("""
            QComboBox {
                background: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-size: 12px; font-weight: bold;
            }
            QComboBox QAbstractItemView { background: #161B22; color: #F0F6FC; selection-background-color: #1F6FEB; }
        """)
        self.combo_category.currentIndexChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.combo_category)

        # Sort selector
        self.combo_sort = QComboBox()
        sort_options = [
            ("name", "فرز: الاسم أبجدياً"),
            ("size", "فرز: الحجم الأكبر أولاً"),
            ("install_date", "فرز: تاريخ التثبيت الأحدث"),
            ("publisher", "فرز: الناشر"),
            ("update", "فرز: التحديثات أولاً"),
        ]
        for key, text in sort_options:
            self.combo_sort.addItem(text, key)
        self.combo_sort.setStyleSheet("""
            QComboBox {
                background: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-size: 12px;
            }
            QComboBox QAbstractItemView { background: #161B22; color: #F0F6FC; selection-background-color: #1F6FEB; }
        """)
        self.combo_sort.currentIndexChanged.connect(self._apply_filters)
        fb_layout.addWidget(self.combo_sort)

        fb_layout.addStretch(1)

        # Batch Selection Tools
        self.btn_select_all = QPushButton("تحديد الكل")
        self.btn_select_all.setStyleSheet("background: #21262D; color: #C9D1D9; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px; font-size: 11px;")
        self.btn_select_all.clicked.connect(lambda: self.table_model.select_all(True))
        fb_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("إلغاء التحديد")
        self.btn_deselect_all.setStyleSheet("background: #21262D; color: #C9D1D9; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px; font-size: 11px;")
        self.btn_deselect_all.clicked.connect(lambda: self.table_model.select_all(False))
        fb_layout.addWidget(self.btn_deselect_all)

        self.btn_batch_uninstall = QPushButton("إزالة المحدد")
        self.btn_batch_uninstall.setIcon(get_icon("uninstall", color="#F0F6FC"))
        self.btn_batch_uninstall.setStyleSheet("background: #DA3633; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 12px;")
        self.btn_batch_uninstall.clicked.connect(self._on_batch_uninstall_clicked)
        fb_layout.addWidget(self.btn_batch_uninstall)

        main_layout.addWidget(filter_bar)

        # 2. Main Content Splitter (Table + Detail Panel)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setStyleSheet("QSplitter::handle { background: #21262D; width: 3px; }")

        # Table View
        self.table_model = AppsTableModel(parent=self)
        self.table_view = QTableView(self)
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setShowGrid(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        self.table_view.setStyleSheet("""
            QTableView {
                background: #0D1117; alternate-background-color: #161B22; color: #C9D1D9;
                border: 1px solid #30363D; border-radius: 10px; selection-background-color: #1F242C;
                selection-color: #F0F6FC; font-size: 12px;
            }
            QHeaderView::section {
                background: #161B22; color: #F0F6FC; font-weight: bold;
                border: none; border-bottom: 1px solid #30363D; padding: 8px;
            }
        """)

        # Configure column widths
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(AppsTableModel.COL_CHECK, QHeaderView.Fixed)
        self.table_view.setColumnWidth(AppsTableModel.COL_CHECK, 36)
        header.setSectionResizeMode(AppsTableModel.COL_ICON, QHeaderView.Fixed)
        self.table_view.setColumnWidth(AppsTableModel.COL_ICON, 38)
        header.setSectionResizeMode(AppsTableModel.COL_NAME, QHeaderView.Stretch)
        header.setSectionResizeMode(AppsTableModel.COL_PUBLISHER, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(AppsTableModel.COL_VERSION, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(AppsTableModel.COL_SIZE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(AppsTableModel.COL_DATE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(AppsTableModel.COL_ARCH, QHeaderView.Fixed)
        self.table_view.setColumnWidth(AppsTableModel.COL_ARCH, 55)
        header.setSectionResizeMode(AppsTableModel.COL_SOURCE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(AppsTableModel.COL_STATUS, QHeaderView.ResizeToContents)

        self.table_view.selectionModel().selectionChanged.connect(self._on_table_selection_changed)

        self.splitter.addWidget(self.table_view)

        # Detail Panel
        self.detail_panel = AppDetailPanel(self)
        self.detail_panel.setFixedWidth(360)
        self.detail_panel.uninstall_requested.connect(lambda app: self.uninstall_single_requested.emit(app))
        self.detail_panel.update_requested.connect(lambda app: self.update_single_requested.emit(app))
        self.detail_panel.repair_requested.connect(self._on_repair_app)
        self.detail_panel.reset_requested.connect(self._on_reset_app)
        self.detail_panel.leftover_scan_requested.connect(lambda app: self.leftover_scan_requested.emit(app))
        self.detail_panel.open_startup_manager_requested.connect(self.open_startup_manager_requested.emit)
        self.splitter.addWidget(self.detail_panel)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        main_layout.addWidget(self.splitter, 1)

        # Bottom Count Label
        self.lbl_count = QLabel("جاري التحميل...")
        self.lbl_count.setStyleSheet("color: #8B949E; font-size: 12px;")
        main_layout.addWidget(self.lbl_count)

    def set_apps(self, apps: List[InstalledApp]):
        """Sets the application catalog and re-evaluates filters."""
        self._raw_apps = apps
        self._apply_filters()

    def _apply_filters(self):
        query = self.search_input.text()
        cat_key = self.combo_category.currentData() or "all"
        sort_key = self.combo_sort.currentData() or "name"
        sort_desc = (sort_key == "size")

        self._filtered_apps = InventoryService.filter_apps(
            self._raw_apps,
            query=query,
            category=cat_key,
            sort_by=sort_key,
            sort_desc=sort_desc,
        )

        self.table_model.set_apps(self._filtered_apps)
        self.lbl_count.setText(f"عرض {len(self._filtered_apps)} من أصل {len(self._raw_apps)} برنامجاً")

        # Refresh detail panel with currently selected row
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            self.detail_panel.set_app(self.table_model.get_app(row))
        else:
            self.detail_panel.set_app(None)

    def _on_table_selection_changed(self, selected: QItemSelection, deselected: QItemSelection):
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            app = self.table_model.get_app(indexes[0].row())
            self.detail_panel.set_app(app)
        else:
            self.detail_panel.set_app(None)

    def _show_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return

        app = self.table_model.get_app(index.row())
        if not app:
            return

        menu = QMenu(self)
        menu.setLayoutDirection(Qt.RightToLeft)
        menu.setStyleSheet("""
            QMenu { background: #161B22; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #1F6FEB; color: white; }
            QMenu::separator { height: 1px; background: #30363D; margin: 4px 8px; }
        """)

        act_run = menu.addAction(get_icon("play", color="#238636"), "تشغيل البرنامج")
        act_run.setEnabled(bool(app.main_executable))
        act_run.triggered.connect(lambda: self.detail_panel._on_run_app())

        act_open_folder = menu.addAction(get_icon("folder", color="#58A6FF"), "فتح موقع التثبيت")
        act_open_folder.setEnabled(bool(app.install_location))
        act_open_folder.triggered.connect(lambda: self.detail_panel._on_open_folder())

        act_open_url = menu.addAction(get_icon("link", color="#8B949E"), "موقع الناشر الرسمي")
        act_open_url.setEnabled(bool(app.help_link or app.url_info_about))
        act_open_url.triggered.connect(lambda: self.detail_panel._on_open_website())

        menu.addSeparator()

        if app.update_available:
            act_up = menu.addAction(get_icon("update", color="#1F6FEB"), "تحديث البرنامج")
            act_up.triggered.connect(lambda: self.update_single_requested.emit(app))

        if app.can_repair:
            act_rep = menu.addAction(get_icon("repair", color="#D29922"), "إصلاح البرنامج")
            act_rep.triggered.connect(lambda: self._on_repair_app(app))

        if app.can_reset:
            act_rst = menu.addAction(get_icon("clean", color="#D29922"), "إعادة ضبط التطبيق (Reset)")
            act_rst.triggered.connect(lambda: self._on_reset_app(app))

        if app.is_broken:
            act_del_broken = menu.addAction(get_icon("uninstall", color="#F85149"), "تنظيف الإدخال المعطوب من السجل")
            act_del_broken.triggered.connect(lambda: self._on_remove_broken(app))

        act_leftovers = menu.addAction(get_icon("clean", color="#A371F7"), "البحث عن بقايا البرنامج")
        act_leftovers.triggered.connect(lambda: self.leftover_scan_requested.emit(app))

        menu.addSeparator()

        act_uninstall = menu.addAction(get_icon("uninstall", color="#DA3633"), "إلغاء التثبيت")
        act_uninstall.setEnabled(app.can_uninstall)
        act_uninstall.triggered.connect(lambda: self.uninstall_single_requested.emit(app))

        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def _on_repair_app(self, app: InstalledApp):
        ok, msg = RepairService.repair_app(app)
        if ok:
            QMessageBox.information(self, "إصلاح البرنامج", msg)
        else:
            QMessageBox.warning(self, "فشل الإصلاح", msg)

    def _on_reset_app(self, app: InstalledApp):
        reply = QMessageBox.warning(
            self,
            "تأكيد إعادة الضبط (Reset)",
            f"سيؤدي هذا إلى إعادة ضبط التطبيق '{app.name}' وحذف بياناته وإعداداته المحلية.\n\nهل ترغب في المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok, msg = RepairService.reset_app(app)
            if ok:
                QMessageBox.information(self, "إعادة الضبط", msg)
            else:
                QMessageBox.warning(self, "فشل إعادة الضبط", msg)

    def _on_remove_broken(self, app: InstalledApp):
        reply = QMessageBox.question(
            self,
            "تنظيف إدخال معطوب",
            f"سيتم إزالة الإدخال المعطوب للبرنامج '{app.name}' من سجل ويندوز مع حفظ نسخة احتياطية (.reg).\n\nهل ترغب في المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok, msg = BrokenEntriesService.remove_broken_entry(app)
            if ok:
                QMessageBox.information(self, "تم التنظيف", msg)
                self.refresh_needed.emit()
            else:
                QMessageBox.warning(self, "خطأ", msg)

    def _on_batch_uninstall_clicked(self):
        selected = self.table_model.get_selected_apps()
        if not selected:
            QMessageBox.information(self, "إزالة محددة", "يرجى تحديد برنامج واحد على الأقل عبر مربعات الاختيار [✓].")
            return
        self.batch_uninstall_requested.emit(selected)
