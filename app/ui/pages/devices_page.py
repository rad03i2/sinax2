# -*- coding: utf-8 -*-
"""
SINAX Devices & Hardware Center Master Page (صفحة مركز الأجهزة ومعلومات الحاسوب الرئيسية)
Coordinates and manages 14 specialized hardware subpages:
0: overview (نظرة عامة)
1: cpu (المعالج)
2: gpu (كرت الشاشة)
3: ram (الذاكرة RAM)
4: motherboard (اللوحة الأم وBIOS)
5: storage (التخزين الفيزيائي)
6: battery (البطارية والطاقة)
7: displays (الشاشات وEDID)
8: usb (USB والأجهزة الملحقة)
9: drivers (التعريفات ومدير الأجهزة)
10: sensors (الحساسات والحرارة)
11: windows (معلومات Windows)
12: quick_check (الفحص السريع والشامل)
13: reports (التقارير ولقطات العتاد)
"""

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.navigation_controller import navigation_controller
from app.core.module_loader import SubpageLazyRegistry
from app.ui.icons import get_icon
from app.ui.pages.devices.subpages.battery_subpage import BatterySubpage
from app.ui.pages.devices.subpages.cpu_subpage import CpuSubpage
from app.ui.pages.devices.subpages.displays_subpage import DisplaysSubpage
from app.ui.pages.devices.subpages.drivers_subpage import DriversSubpage
from app.ui.pages.devices.subpages.gpu_subpage import GpuSubpage
from app.ui.pages.devices.subpages.motherboard_subpage import MotherboardSubpage
from app.ui.pages.devices.subpages.overview_subpage import OverviewSubpage
from app.ui.pages.devices.subpages.quick_check_subpage import QuickCheckSubpage
from app.ui.pages.devices.subpages.ram_subpage import RamSubpage
from app.ui.pages.devices.subpages.reports_subpage import ReportsSubpage
from app.ui.pages.devices.subpages.sensors_subpage import SensorsSubpage
from app.ui.pages.devices.subpages.storage_subpage import StorageSubpage
from app.ui.pages.devices.subpages.usb_subpage import UsbSubpage
from app.ui.pages.devices.subpages.windows_subpage import WindowsSubpage


class QMLDevicesOverview(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "devicesController")
        self.quick_widget.setSource(get_qml_url("pages/DevicesPage.qml"))
        layout.addWidget(self.quick_widget)
        navigation_controller.routeRequested.connect(self._on_route)

    def _on_route(self, route: str):
        if route.startswith("devices_"):
            sub_key = route.replace("devices_", "")
            self.navigate_requested.emit(sub_key)


class DevicesPage(QWidget):
    """Master container page for Devices & Hardware Center."""

    subpage_changed = Signal(str, str)  # (key, label_ar)
    external_navigate_requested = Signal(str)  # e.g. navigate to 'system_storage'

    SUBPAGE_KEYS = [
        ("overview", "نظرة عامة", "devices"),
        ("cpu", "المعالج", "cpu"),
        ("gpu", "كرت الشاشة", "gpu"),
        ("ram", "الذاكرة RAM", "ram"),
        ("motherboard", "اللوحة الأم وBIOS", "devices"),
        ("storage", "التخزين", "storage"),
        ("battery", "البطارية والطاقة", "devices"),
        ("displays", "الشاشات", "devices"),
        ("usb", "USB والأجهزة", "devices"),
        ("drivers", "التعريفات", "devices"),
        ("sensors", "الحساسات والحرارة", "devices"),
        ("windows", "معلومات Windows", "devices"),
        ("quick_check", "الفحص السريع", "doctor"),
        ("reports", "التقارير والمقارنة", "devices"),
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

        # Set up Subpage Lazy Registry (Loads only Overview eagerly, other 13 on demand)
        self._registry = SubpageLazyRegistry(self.stack)

        # 0: Overview (eager QML Hub)
        self._registry.register_subpage("overview", 0, lambda: QMLDevicesOverview(self), eager=True)
        self.page_overview = self._registry.get_or_create("overview")

        # 1..13: Lazy Subpages
        self._registry.register_subpage("cpu", 1, lambda: CpuSubpage(self))
        self._registry.register_subpage("gpu", 2, lambda: GpuSubpage(self))
        self._registry.register_subpage("ram", 3, lambda: RamSubpage(self))
        self._registry.register_subpage("motherboard", 4, lambda: MotherboardSubpage(self))
        self._registry.register_subpage("storage", 5, self._create_storage_subpage)
        self._registry.register_subpage("battery", 6, lambda: BatterySubpage(self))
        self._registry.register_subpage("displays", 7, lambda: DisplaysSubpage(self))
        self._registry.register_subpage("usb", 8, lambda: UsbSubpage(self))
        self._registry.register_subpage("drivers", 9, lambda: DriversSubpage(self))
        self._registry.register_subpage("sensors", 10, lambda: SensorsSubpage(self))
        self._registry.register_subpage("windows", 11, lambda: WindowsSubpage(self))
        self._registry.register_subpage("quick_check", 12, lambda: QuickCheckSubpage(self))
        self._registry.register_subpage("reports", 13, lambda: ReportsSubpage(self))

        main_layout.addWidget(self.stack, 1)

        # Connect internal navigation signals
        self.page_overview.navigate_requested.connect(self.switch_subpage)

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
            icon_name = next((ic for k, _, ic in self.SUBPAGE_KEYS if k == key), "devices")
            btn.setIcon(get_icon(icon_name, color=btn_color))

        if hasattr(self, "_registry") and self._registry is not None:
            for sub in self._registry._instances.values():
                if hasattr(sub, "apply_theme") and callable(sub.apply_theme):
                    sub.apply_theme(theme_name)

    def _create_storage_subpage(self) -> StorageSubpage:
        sub = StorageSubpage(self)
        sub.navigate_requested.connect(self.external_navigate_requested.emit)
        return sub

    def __getattr__(self, name: str):
        if name.startswith("page_"):
            key = name[5:]
            widget = self._registry.get_or_create(key)
            if widget is not None:
                if hasattr(widget, "apply_theme") and callable(widget.apply_theme):
                    from app.ui.themes.theme_manager import theme_manager
                    widget.apply_theme(theme_manager.effective_theme)
                return widget
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def switch_subpage(self, key: str):
        """Switches active subpage by key name (supports 'key' or 'devices_key')."""
        clean_key = key.replace("devices_", "")

        key_to_idx = {k: i for i, (k, _, _) in enumerate(self.SUBPAGE_KEYS)}
        if clean_key in key_to_idx:
            idx = key_to_idx[clean_key]
            sub = self._registry.switch_to(clean_key)
            if sub and hasattr(sub, "apply_theme") and callable(sub.apply_theme):
                from app.ui.themes.theme_manager import theme_manager
                sub.apply_theme(theme_manager.effective_theme)
            if clean_key in self._buttons:
                self._buttons[clean_key].setChecked(True)
            label = self.SUBPAGE_KEYS[idx][1]
            self.subpage_changed.emit(clean_key, label)
