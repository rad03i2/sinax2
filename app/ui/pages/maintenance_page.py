# -*- coding: utf-8 -*-
"""
SINAX Maintenance & Repair Center Master Page (مركز الصيانة والإصلاح).
Coordinates and manages 12 specialized maintenance subpages:
0: overview (نظرة عامة)
1: doctor (طبيب SINAX)
2: cleanup (التنظيف الآمن ومراجعة التنزيلات)
3: windows_repair (إصلاح Windows: DISM & SFC)
4: storage_disk (التخزين وفحص نظام الملفات CHKDSK)
5: updates (التحديثات وإعادة التشغيل المعلقة)
6: startup (بدء التشغيل ومساعد الإقلاع النظيف)
7: network (مشاكل الشبكة)
8: apps (مشاكل التطبيقات)
9: devices (مشاكل الأجهزة)
10: reliability (السجل والموثوقية والأعطال)
11: advanced (أدوات متقدمة وسجل الصيانة)
"""

from typing import Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.navigation_controller import navigation_controller
from app.ui.icons import get_icon
from app.ui.pages.maintenance.subpages.advanced_subpage import AdvancedSubpage
from app.ui.pages.maintenance.subpages.apps_repair_subpage import AppsRepairSubpage
from app.ui.pages.maintenance.subpages.cleanup_subpage import CleanupSubpage
from app.ui.pages.maintenance.subpages.devices_repair_subpage import DevicesRepairSubpage
from app.ui.pages.maintenance.subpages.doctor_subpage import DoctorSubpage
from app.ui.pages.maintenance.subpages.network_repair_subpage import NetworkRepairSubpage
from app.ui.pages.maintenance.subpages.overview_subpage import OverviewSubpage
from app.ui.pages.maintenance.subpages.reliability_subpage import ReliabilitySubpage
from app.ui.pages.maintenance.subpages.startup_subpage import StartupSubpage
from app.ui.pages.maintenance.subpages.storage_disk_subpage import StorageDiskSubpage
from app.ui.pages.maintenance.subpages.updates_subpage import UpdatesSubpage
from app.ui.pages.maintenance.subpages.windows_repair_subpage import WindowsRepairSubpage


class QMLMaintenanceOverview(QWidget):
    navigate_requested = Signal(str)
    run_doctor_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "maintenanceController")
        self.quick_widget.setSource(get_qml_url("pages/MaintenancePage.qml"))
        layout.addWidget(self.quick_widget)
        navigation_controller.routeRequested.connect(self._on_route)

    def _on_route(self, route: str):
        if route.startswith("maintenance_"):
            sub_key = route.replace("maintenance_", "")
            self.navigate_requested.emit(sub_key)


class MaintenancePage(QWidget):
    """Master container page for SINAX Maintenance & Repair Center."""

    subpage_changed = Signal(str, str) # (clean_key, label_ar)
    external_navigate_requested = Signal(str)

    SUBPAGE_KEYS = [
        ("overview", "نظرة عامة", "doctor"),
        ("doctor", "طبيب SINAX", "doctor"),
        ("cleanup", "التنظيف الآمن", "clean"),
        ("windows_repair", "إصلاح Windows", "tools"),
        ("storage_disk", "التخزين والقرص", "storage"),
        ("updates", "التحديثات والإقلاع", "update"),
        ("startup", "بدء التشغيل", "startup"),
        ("network", "مشاكل الشبكة", "network"),
        ("apps", "مشاكل التطبيقات", "apps"),
        ("devices", "مشاكل الأجهزة", "devices"),
        ("reliability", "السجل والموثوقية", "doctor"),
        ("advanced", "أدوات متقدمة", "tools"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self._buttons: Dict[str, QPushButton] = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Subpage Navigation Bar (Scrollable horizontally)
        self.nav_scroll = QScrollArea(self)
        self.nav_scroll.setFixedHeight(54)
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setFrameShape(QFrame.NoFrame)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        nav_bar = QWidget()
        nav_bar.setStyleSheet("background: transparent;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(16, 6, 16, 6)
        nav_layout.setSpacing(6)

        for idx, (key, label, icon_name) in enumerate(self.SUBPAGE_KEYS):
            btn = QPushButton(f" {label}")
            btn.setIcon(get_icon(icon_name, color="#8B949E"))
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda _, k=key: self.switch_subpage(k))
            self.btn_group.addButton(btn, idx)
            self._buttons[key] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)
        self.nav_scroll.setWidget(nav_bar)
        main_layout.addWidget(self.nav_scroll)

        # 2. Stacked Pages
        self.stack = QStackedWidget(self)
        self._subpages: Dict[int, QWidget] = {}

        # Subpage 0 is modern QML Hub (loaded immediately)
        self.page_overview = QMLMaintenanceOverview(self)
        self.stack.addWidget(self.page_overview)
        self._subpages[0] = self.page_overview

        # Subpages 1..11: Lazy factories and lightweight placeholders
        self._factories = {
            1: lambda: DoctorSubpage(self),
            2: lambda: CleanupSubpage(self),
            3: lambda: WindowsRepairSubpage(self),
            4: lambda: StorageDiskSubpage(self),
            5: lambda: UpdatesSubpage(self),
            6: lambda: StartupSubpage(self),
            7: lambda: NetworkRepairSubpage(self),
            8: lambda: AppsRepairSubpage(self),
            9: lambda: DevicesRepairSubpage(self),
            10: lambda: ReliabilitySubpage(self),
            11: lambda: AdvancedSubpage(self),
        }
        for _ in range(1, 12):
            self.stack.addWidget(QWidget())

        main_layout.addWidget(self.stack, 1)

        # Connect internal signals
        self.page_overview.navigate_requested.connect(self.switch_subpage)
        self.page_overview.run_doctor_requested.connect(lambda: self.switch_subpage("doctor"))

        from app.ui.themes.theme_manager import theme_manager
        theme_manager.theme_changed.connect(self.apply_theme)
        self.apply_theme(theme_manager.effective_theme)

    def apply_theme(self, theme_name: str = "dark"):
        """Propagates theme across nav_scroll, buttons, stack, and active subpages."""
        is_light = (theme_name == "light")
        bg_color = "#F8FAFC" if is_light else "#0D1117"
        border_color = "#E2E8F0" if is_light else "#21262D"
        stack_bg = "#FFFFFF" if is_light else "#0D1117"
        btn_color = "#475569" if is_light else "#8B949E"
        btn_hover_bg = "#E2E8F0" if is_light else "#161B22"
        btn_hover_color = "#0F172A" if is_light else "#F0F6FC"
        btn_checked_bg = "#E0F2FE" if is_light else "#21262D"
        btn_checked_color = "#0284C7" if is_light else "#38BDF8"
        scrollbar_handle = "#CBD5E1" if is_light else "#334155"

        if hasattr(self, "nav_scroll") and self.nav_scroll is not None:
            self.nav_scroll.setStyleSheet(f"""
                QScrollArea {{
                    background: {bg_color};
                    border-bottom: 1px solid {border_color};
                }}
                QScrollBar:horizontal {{
                    height: 4px;
                    background: {bg_color};
                }}
                QScrollBar::handle:horizontal {{
                    background: {scrollbar_handle};
                    border-radius: 2px;
                }}
            """)
        if hasattr(self, "stack") and self.stack is not None:
            self.stack.setStyleSheet(f"background: {stack_bg};")

        btn_qss = f"""
            QPushButton {{
                background: transparent;
                color: {btn_color};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {btn_hover_bg};
                color: {btn_hover_color};
            }}
            QPushButton:checked {{
                background: {btn_checked_bg};
                color: {btn_checked_color};
                border-bottom: 2px solid {btn_checked_color};
            }}
        """
        for key, btn in self._buttons.items():
            btn.setStyleSheet(btn_qss)
            icon_name = next((ic for k, _, ic in self.SUBPAGE_KEYS if k == key), "doctor")
            btn.setIcon(get_icon(icon_name, color=btn_color))

        for sub in self._subpages.values():
            if hasattr(sub, "apply_theme") and callable(sub.apply_theme):
                sub.apply_theme(theme_name)

    _SUBPAGE_ATTRS = {
        "page_doctor": 1,
        "page_cleanup": 2,
        "page_windows_repair": 3,
        "page_storage_disk": 4,
        "page_updates": 5,
        "page_startup": 6,
        "page_network": 7,
        "page_apps": 8,
        "page_devices": 9,
        "page_reliability": 10,
        "page_advanced": 11,
    }

    def _ensure_subpage_loaded(self, idx: int) -> QWidget:
        if idx not in self._subpages and idx in self._factories:
            w = self._factories[idx]()
            old_w = self.stack.widget(idx)
            self.stack.removeWidget(old_w)
            old_w.deleteLater()
            self.stack.insertWidget(idx, w)
            self._subpages[idx] = w
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
        """Switches active subpage by key name (supports 'key' or 'maintenance_key')."""
        clean_key = key.replace("maintenance_", "")
        key_to_idx = {k: i for i, (k, _, _) in enumerate(self.SUBPAGE_KEYS)}
        if clean_key in key_to_idx:
            idx = key_to_idx[clean_key]
            self._ensure_subpage_loaded(idx)
            self.stack.setCurrentIndex(idx)
            if clean_key in self._buttons:
                self._buttons[clean_key].setChecked(True)
            label = self.SUBPAGE_KEYS[idx][1]
            self.subpage_changed.emit(clean_key, label)
