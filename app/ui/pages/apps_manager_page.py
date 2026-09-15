# -*- coding: utf-8 -*-
"""
SINAX Apps & Programs Manager Master Page (صفحة إدارة البرامج والتطبيقات الرئيسية)
Coordinates and manages 9 specialized application subpages:
0: Overview (نظرة عامة)
1: Inventory (كل البرامج)
2: Updates (التحديثات)
3: Uninstall (إزالة البرامج)
4: Large Apps (البرامج الكبيرة)
5: Repair & Reset (الإصلاح وإعادة الضبط)
6: Leftovers (البقايا)
7: Before Format (قبل الفورمات)
8: Restore (استعادة البرامج)
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.inventory_service import InventoryService
from app.services.apps_manager.uninstall_service import UninstallService
from app.services.apps_manager.update_service import UpdateService
from app.ui.icons import get_icon
from app.ui.pages.apps_manager.sequential_queue_dialog import SequentialQueueDialog
from app.ui.pages.apps_manager.subpages.before_format_subpage import BeforeFormatSubpage
from app.ui.pages.apps_manager.subpages.inventory_subpage import InventorySubpage
from app.ui.pages.apps_manager.subpages.large_apps_subpage import LargeAppsSubpage
from app.ui.pages.apps_manager.subpages.leftovers_subpage import LeftoversSubpage
from app.ui.pages.apps_manager.subpages.overview_subpage import OverviewSubpage
from app.ui.pages.apps_manager.subpages.repair_subpage import RepairSubpage
from app.ui.pages.apps_manager.subpages.restore_subpage import RestoreSubpage
from app.ui.pages.apps_manager.subpages.uninstall_subpage import UninstallSubpage
from app.ui.pages.apps_manager.subpages.updates_subpage import UpdatesSubpage


class InventoryWorker(QObject):
    """Background inventory scanner."""
    status_msg = Signal(str)
    finished = Signal(list)

    def __init__(self, force_refresh: bool = False):
        super().__init__()
        self.force_refresh = force_refresh

    def run(self):
        apps = InventoryService.get_all_apps(
            force_refresh=self.force_refresh,
            progress_cb=lambda msg: self.status_msg.emit(msg),
        )
        self.finished.emit(apps)


class QMLAppsManagementOverview(QWidget):
    switch_subpage_requested = Signal(str)
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        from PySide6.QtQuickWidgets import QQuickWidget
        from app.core.qml_helper import configure_qml_engine, get_qml_url
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "appsController")
        self.quick_widget.setSource(get_qml_url("pages/AppsManagementPage.qml"))
        layout.addWidget(self.quick_widget)

    def update_data(self, apps):
        pass


class AppsManagerPage(QWidget):
    """Master container page for Apps & Programs Manager."""

    subpage_changed = Signal(str, str)  # (key, label_ar)
    open_startup_manager_requested = Signal()

    SUBPAGE_KEYS = [
        ("overview", "نظرة عامة", "apps"),
        ("inventory", "قائمة البرامج", "apps"),
        ("updates", "تحديث البرامج", "update"),
        ("uninstall", "إلغاء التثبيت النظيف", "delete"),
        ("large", "البرامج الضخمة", "storage"),
        ("repair", "إصلاح التثبيت", "repair"),
        ("leftovers", "بقايا البرامج المحذوفة", "leftover"),
        ("before_format", "تجهيز قبل الفورمات", "backup"),
        ("restore", "استعادة البرامج", "restore"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._is_loading = False
        self._loaded_apps: List[InstalledApp] = []
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self._buttons: Dict[str, QPushButton] = {}
        self._legacy_overview_instance = None

        self._init_ui()
        self.load_inventory(force=False)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Subpage Navigation Bar
        self.nav_bar = QWidget()
        self.nav_bar.setFixedHeight(50)
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(16, 4, 16, 4)
        nav_layout.setSpacing(6)


        for idx, (key, label, icon_name) in enumerate(self.SUBPAGE_KEYS):
            btn = QPushButton(f" {label}")
            btn.setIcon(get_icon(icon_name, color="#8B949E"))
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #8B949E;
                    border: 1px solid transparent;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: #21262D;
                    color: #F0F6FC;
                }
                QPushButton:checked {
                    background: #1F6FEB;
                    color: #FFFFFF;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(lambda checked, k=key: self.switch_subpage(k))
            nav_layout.addWidget(btn)
            self.btn_group.addButton(btn)
            self._buttons[key] = btn

        nav_layout.addStretch(1)

        # Loading indicator label
        self.lbl_nav_status = QLabel("")
        self.lbl_nav_status.setStyleSheet("color: #58A6FF; font-size: 12px;")
        nav_layout.addWidget(self.lbl_nav_status)

        main_layout.addWidget(self.nav_bar)

        # 2. Stacked Pages
        self.stack = QStackedWidget(self)
        self._subpages: Dict[int, QWidget] = {}

        # Subpage 0 is modern QML (loaded immediately)
        self.page_overview = QMLAppsManagementOverview(self)
        self.stack.addWidget(self.page_overview)
        self._subpages[0] = self.page_overview

        # Subpages 1..8: Lazy factories and lightweight placeholders
        self._factories = {
            1: self._create_inventory_subpage,
            2: self._create_updates_subpage,
            3: self._create_uninstall_subpage,
            4: self._create_large_subpage,
            5: lambda: RepairSubpage(self),
            6: self._create_leftovers_subpage,
            7: lambda: BeforeFormatSubpage(self),
            8: self._create_restore_subpage,
        }
        for _ in range(1, 9):
            self.stack.addWidget(QWidget())

        main_layout.addWidget(self.stack, 1)

        # Connect overview signals
        self.page_overview.switch_subpage_requested.connect(self.switch_subpage)
        self.page_overview.refresh_requested.connect(lambda: self.load_inventory(force=True))

        from app.ui.themes.theme_manager import theme_manager
        theme_manager.theme_changed.connect(self.apply_theme)
        self.apply_theme(theme_manager.effective_theme)

    def apply_theme(self, theme_name: str = "dark"):
        """Propagates theme across nav_bar, buttons, stack, and active subpages."""
        is_light = (theme_name == "light")
        nav_bg = "#F8FAFC" if is_light else "#0D1117"
        nav_border = "#E2E8F0" if is_light else "#21262D"
        stack_bg = "#FFFFFF" if is_light else "#0D1117"
        btn_color = "#475569" if is_light else "#8B949E"
        btn_hover_bg = "#E2E8F0" if is_light else "#21262D"
        btn_hover_color = "#0F172A" if is_light else "#F0F6FC"
        btn_checked_bg = "#0078D4" if is_light else "#1F6FEB"

        if hasattr(self, "nav_bar") and self.nav_bar is not None:
            self.nav_bar.setStyleSheet(f"background-color: {nav_bg}; border-bottom: 1px solid {nav_border};")
        if hasattr(self, "stack") and self.stack is not None:
            self.stack.setStyleSheet(f"background: {stack_bg};")

        btn_qss = f"""
            QPushButton {{
                background: transparent;
                color: {btn_color};
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {btn_hover_bg};
                color: {btn_hover_color};
            }}
            QPushButton:checked {{
                background: {btn_checked_bg};
                color: #FFFFFF;
                font-weight: bold;
            }}
        """
        for key, btn in self._buttons.items():
            btn.setStyleSheet(btn_qss)
            icon_name = next((ic for k, _, ic in self.SUBPAGE_KEYS if k == key), "apps")
            btn.setIcon(get_icon(icon_name, color=btn_color))

        for sub in self._subpages.values():
            if hasattr(sub, "apply_theme") and callable(sub.apply_theme):
                sub.apply_theme(theme_name)

    def _create_inventory_subpage(self):
        sub = InventorySubpage(self)
        sub.uninstall_single_requested.connect(self._on_single_uninstall)
        sub.batch_uninstall_requested.connect(self._on_batch_uninstall)
        sub.update_single_requested.connect(self._on_single_update)
        sub.leftover_scan_requested.connect(self._on_leftover_scan)
        sub.open_startup_manager_requested.connect(self.open_startup_manager_requested.emit)
        sub.refresh_needed.connect(lambda: self.load_inventory(force=True))
        return sub

    def _create_updates_subpage(self):
        sub = UpdatesSubpage(self)
        sub.check_updates_requested.connect(lambda: self.load_inventory(force=True))
        sub.refresh_needed.connect(lambda: self.load_inventory(force=True))
        return sub

    def _create_uninstall_subpage(self):
        sub = UninstallSubpage(self)
        sub.refresh_needed.connect(lambda: self.load_inventory(force=True))
        sub.leftover_scan_requested.connect(self._on_leftover_scan)
        return sub

    def _create_large_subpage(self):
        sub = LargeAppsSubpage(self)
        sub.uninstall_requested.connect(self._on_single_uninstall)
        return sub

    def _create_leftovers_subpage(self):
        return LeftoversSubpage(self)

    def _create_restore_subpage(self):
        sub = RestoreSubpage(self)
        sub.refresh_needed.connect(lambda: self.load_inventory(force=True))
        return sub

    _SUBPAGE_ATTRS = {
        "page_inventory": 1,
        "page_updates": 2,
        "page_uninstall": 3,
        "page_large": 4,
        "page_repair": 5,
        "page_leftovers": 6,
        "page_before_format": 7,
        "page_restore": 8,
    }

    @property
    def legacy_overview(self):
        if self._legacy_overview_instance is None:
            self._legacy_overview_instance = OverviewSubpage(self)
        return self._legacy_overview_instance

    def _ensure_subpage_loaded(self, idx: int) -> QWidget:
        if idx not in self._subpages and idx in self._factories:
            w = self._factories[idx]()
            old_w = self.stack.widget(idx)
            self.stack.removeWidget(old_w)
            old_w.deleteLater()
            self.stack.insertWidget(idx, w)
            self._subpages[idx] = w
            if self._loaded_apps and hasattr(w, "set_apps"):
                w.set_apps(self._loaded_apps)
            from app.ui.themes.theme_manager import theme_manager
            if hasattr(w, "apply_theme") and callable(w.apply_theme):
                w.apply_theme(theme_manager.effective_theme)
        return self._subpages.get(idx, self.page_overview)

    def __getattr__(self, name: str):
        if "_SUBPAGE_ATTRS" in type(self).__dict__ and name in self._SUBPAGE_ATTRS:
            idx = self._SUBPAGE_ATTRS[name]
            return self._ensure_subpage_loaded(idx)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def switch_subpage(self, key: str):
        """Switches the active subpage by key name."""
        key_to_idx = {k: i for i, (k, _, _) in enumerate(self.SUBPAGE_KEYS)}
        if key in key_to_idx:
            idx = key_to_idx[key]
            self._ensure_subpage_loaded(idx)
            self.stack.setCurrentIndex(idx)
            if key in self._buttons:
                self._buttons[key].setChecked(True)
            label = self.SUBPAGE_KEYS[idx][1]
            self.subpage_changed.emit(key, label)

    def load_inventory(self, force: bool = False):
        """Loads software inventory asynchronously in a background thread."""
        if self._is_loading:
            return
        self._is_loading = True
        self.lbl_nav_status.setText("جارٍ فحص البرامج...")

        self.worker_thread = QThread(self)
        self.worker = InventoryWorker(force_refresh=force)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.status_msg.connect(self._on_status_msg)
        self.worker.finished.connect(self._on_inventory_loaded)

        self.worker_thread.start()

    def _on_status_msg(self, msg: str):
        try:
            self.lbl_nav_status.setText(msg)
        except (RuntimeError, AttributeError):
            pass

    def _on_inventory_loaded(self, apps: List[InstalledApp]):
        self._loaded_apps = apps
        self._is_loading = False
        try:
            self.lbl_nav_status.setText("")
        except (RuntimeError, AttributeError):
            pass

        # Dispatch data to loaded subpages
        self.page_overview.update_data(apps)
        for idx, sub in self._subpages.items():
            if hasattr(sub, "set_apps"):
                try:
                    sub.set_apps(apps)
                except Exception:
                    pass

        self.worker_thread.quit()
        self.worker_thread.wait()

    def _on_single_uninstall(self, app: InstalledApp):
        reply = QMessageBox.question(
            self,
            "تأكيد إزالة البرنامج",
            f"سيتم تشغيل برنامج الإزالة الرسمي للبرنامج التالي:\n\n{app.name}\nالإصدار: {app.version}\nالناشر: {app.publisher}\n\nهل ترغب في المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            res = UninstallService.uninstall_app(app)
            if res.success:
                QMessageBox.information(self, "إلغاء التثبيت", res.message)
                self.load_inventory(force=True)
                reply_leftover = QMessageBox.question(
                    self,
                    "فحص البقايا",
                    f"تمت إزالة {app.name} بنجاح.\n\nهل ترغب في فحص البقايا المتروكة على القرص الآن؟",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply_leftover == QMessageBox.Yes:
                    self._on_leftover_scan(app)
            else:
                QMessageBox.warning(self, "فشل الإزالة", f"{res.message}\n{res.technical_details}")

    def _on_batch_uninstall(self, apps: List[InstalledApp]):
        self.switch_subpage("uninstall")
        dlg = SequentialQueueDialog(
            title=f"جارٍ إزالة {len(apps)} برنامجاً بالتتابع",
            items=apps,
            task_fn=UninstallService.execute_batch,
            parent=self,
        )
        dlg.exec()
        self.load_inventory(force=True)

    def _on_single_update(self, app: InstalledApp):
        dlg = SequentialQueueDialog(
            title=f"جارٍ تحديث: {app.name}",
            items=[app],
            task_fn=UpdateService.execute_batch_update,
            parent=self,
        )
        dlg.exec()
        self.load_inventory(force=True)

    def _on_leftover_scan(self, app: InstalledApp):
        self.switch_subpage("leftovers")
        self.page_leftovers.scan_for_app(app)
