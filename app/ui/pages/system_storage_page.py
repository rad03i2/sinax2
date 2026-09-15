# -*- coding: utf-8 -*-
"""
SINAX System & Storage Master Page (صفحة النظام والتخزين الرئيسية)
Hosts and coordinates 8 specialized subpages:
0: Overview (لوحة القيادة العامة)
1: Storage Analyzer (محلل التخزين)
2: Safe Cleanup (التنظيف الآمن)
3: Disk Health & S.M.A.R.T. (صحة الأقراص)
4: Live Performance (مراقبة الأداء)
5: Process Manager (إدارة العمليات)
6: Startup Items (بدء التشغيل)
7: Device Specs & Diagnostics (مواصفات الجهاز)
"""

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.navigation_controller import navigation_controller
from app.core.module_loader import SubpageLazyRegistry
from app.ui.icons import get_icon
from app.ui.pages.system_storage.subpages.analyzer_subpage import AnalyzerSubpage
from app.ui.pages.system_storage.subpages.cleanup_subpage import CleanupSubpage
from app.ui.pages.system_storage.subpages.device_subpage import DeviceSubpage
from app.ui.pages.system_storage.subpages.health_subpage import HealthSubpage
from app.ui.pages.system_storage.subpages.overview_subpage import OverviewSubpage
from app.ui.pages.system_storage.subpages.performance_subpage import PerformanceSubpage
from app.ui.pages.system_storage.subpages.process_subpage import ProcessSubpage
from app.ui.pages.system_storage.subpages.startup_subpage import StartupSubpage


class QMLSystemStorageOverview(QWidget):
    navigate_requested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "systemStorageController")
        self.quick_widget.setSource(get_qml_url("pages/SystemStoragePage.qml"))
        layout.addWidget(self.quick_widget)
        navigation_controller.routeRequested.connect(self._on_route)

    def _on_route(self, route: str):
        if route.startswith("system_storage_"):
            sub_key = route.replace("system_storage_", "")
            self.navigate_requested.emit(sub_key, None)


class SystemStoragePage(QWidget):
    """Main System & Storage Page container."""

    subpage_changed = Signal(str, str)  # (key, label_ar)

    SUBPAGE_KEYS = [
        ("overview", "نظرة عامة", "storage"),
        ("analyzer", "محلل التخزين", "treemap"),
        ("cleanup", "التنظيف الآمن", "clean"),
        ("health", "صحة الأقراص", "storage"),
        ("performance", "مراقبة الأداء", "performance"),
        ("processes", "إدارة العمليات", "process"),
        ("startup", "بدء التشغيل", "startup"),
        ("device", "مواصفات الجهاز", "chart"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self._buttons: Dict[str, QPushButton] = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sub-navigation Bar
        nav_bar = QFrame()
        nav_bar.setFixedHeight(54)
        nav_bar.setStyleSheet("""
            QFrame {
                background: #0D1117;
                border-bottom: 1px solid #21262D;
            }
        """)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(16, 6, 16, 6)
        nav_layout.setSpacing(8)

        for idx, (key, label, icon_name) in enumerate(self.SUBPAGE_KEYS):
            btn = QPushButton(label)
            btn.setIcon(get_icon(icon_name, color="#8B949E"))
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #8B949E; border: none;
                    border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 12px;
                }
                QPushButton:hover { background: #161B22; color: #F0F6FC; }
                QPushButton:checked {
                    background: #21262D; color: #58A6FF;
                    border-bottom: 2px solid #58A6FF;
                }
            """)
            btn.clicked.connect(lambda _, k=key: self.switch_subpage(k))
            self.btn_group.addButton(btn, idx)
            self._buttons[key] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)
        main_layout.addWidget(nav_bar)

        # 2. Stacked Pages
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("background: #0D1117;")

        # Set up Subpage Lazy Registry (Loads only Overview eagerly, other 7 on demand)
        self._registry = SubpageLazyRegistry(self.stack)

        # 0: Overview (eager QML Hub)
        self._registry.register_subpage("overview", 0, lambda: QMLSystemStorageOverview(self), eager=True)
        self.overview_page = self._registry.get_or_create("overview")

        # 1..7: Lazy Subpages
        self._registry.register_subpage("analyzer", 1, lambda: AnalyzerSubpage(self))
        self._registry.register_subpage("cleanup", 2, lambda: CleanupSubpage(self))
        self._registry.register_subpage("health", 3, lambda: HealthSubpage(self))
        self._registry.register_subpage("performance", 4, lambda: PerformanceSubpage(self))
        self._registry.register_subpage("process", 5, lambda: ProcessSubpage(self))
        self._registry.register_subpage("startup", 6, lambda: StartupSubpage(self))
        self._registry.register_subpage("device", 7, lambda: DeviceSubpage(self))

        # Connect inter-subpage signals
        self.overview_page.navigate_requested.connect(self._on_navigate_requested)

        main_layout.addWidget(self.stack, 1)

    def __getattr__(self, name: str):
        if name.endswith("_page"):
            key = name.replace("_page", "")
            widget = self._registry.get_or_create(key)
            if widget is not None:
                return widget
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def switch_subpage(self, key: str, param: Optional[Any] = None):
        """Switch active subpage by key and optional param."""
        widget = self._registry.switch_to(key)

        if key in self._buttons:
            self._buttons[key].setChecked(True)

        label_ar = next((l for k, l, _ in self.SUBPAGE_KEYS if k == key), "النظام والتخزين")
        self.subpage_changed.emit(key, label_ar)

        # If parameter was passed (e.g. drive letter to analyzer)
        if key == "analyzer" and param and widget is not None:
            widget.select_target(str(param))

    def _on_navigate_requested(self, subpage_key: str, param: Optional[Any]):
        self.switch_subpage(subpage_key, param)
