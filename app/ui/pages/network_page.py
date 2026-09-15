# -*- coding: utf-8 -*-
"""
SINAX Network & Internet Center Master Page (صفحة مركز الشبكة والإنترنت الرئيسية)
Coordinates and manages 11 specialized network subpages:
0: overview (نظرة عامة)
1: speedtest (اختبار السرعة)
2: doctor (تشخيص الاتصال)
3: wifi (Wi-Fi)
4: lan_devices (الأجهزة المحلية)
5: traffic (استهلاك الإنترنت)
6: connections (الاتصالات والمنافذ)
7: dns (DNS)
8: share (مشاركة الملفات)
9: adapters (معلومات الشبكة)
10: tools (أدوات متقدمة)
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

from app.ui.icons import get_icon
from app.ui.pages.network.subpages.adapters_subpage import AdaptersSubpage
from app.ui.pages.network.subpages.connections_subpage import ConnectionsSubpage
from app.ui.pages.network.subpages.dns_subpage import DnsSubpage
from app.ui.pages.network.subpages.doctor_subpage import DoctorSubpage
from app.ui.pages.network.subpages.lan_devices_subpage import LanDevicesSubpage
from app.ui.pages.network.subpages.overview_subpage import OverviewSubpage
from app.ui.pages.network.subpages.share_subpage import ShareSubpage
from app.ui.pages.network.subpages.speedtest_subpage import SpeedTestSubpage
from app.ui.pages.network.subpages.tools_subpage import ToolsSubpage
from app.ui.pages.network.subpages.traffic_subpage import TrafficSubpage
from app.ui.pages.network.subpages.wifi_subpage import WifiSubpage
from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url


class QMLNetworkCenterOverview(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "networkController")
        self.quick_widget.setSource(get_qml_url("pages/NetworkCenterPage.qml"))
        layout.addWidget(self.quick_widget)


class NetworkPage(QWidget):
    """Master container page for Network & Internet Center."""

    subpage_changed = Signal(str, str)  # (key, label_ar)

    SUBPAGE_KEYS = [
        ("overview", "نظرة عامة", "network"),
        ("speedtest", "اختبار السرعة", "speedtest"),
        ("doctor", "تشخيص الاتصال", "doctor"),
        ("wifi", "Wi-Fi", "wifi"),
        ("lan_devices", "الأجهزة المحلية", "devices"),
        ("traffic", "استهلاك الإنترنت", "traffic"),
        ("connections", "الاتصالات والمنافذ", "connections"),
        ("dns", "DNS", "dns"),
        ("share", "مشاركة الملفات", "share"),
        ("adapters", "معلومات الشبكة", "adapters"),
        ("tools", "أدوات متقدمة", "tools"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self._buttons: Dict[str, QPushButton] = {}
        self._legacy_overview_instance = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Subpage Navigation Bar (Scrollable for responsiveness)
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

        # Subpage 0 is modern QML (loaded immediately)
        self.page_overview = QMLNetworkCenterOverview(self)
        self.stack.addWidget(self.page_overview)
        self._subpages[0] = self.page_overview

        # Subpages 1..10: Lazy factories and lightweight placeholders
        self._factories = {
            1: lambda: SpeedTestSubpage(self),
            2: lambda: DoctorSubpage(self),
            3: lambda: WifiSubpage(self),
            4: lambda: LanDevicesSubpage(self),
            5: lambda: TrafficSubpage(self),
            6: lambda: ConnectionsSubpage(self),
            7: lambda: DnsSubpage(self),
            8: lambda: ShareSubpage(self),
            9: lambda: AdaptersSubpage(self),
            10: lambda: ToolsSubpage(self),
        }
        for _ in range(1, 11):
            self.stack.addWidget(QWidget())

        main_layout.addWidget(self.stack, 1)

        # Connect overview quick actions to subpage switching
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
        btn_checked_bg = "#E0E7FF" if is_light else "#21262D"
        btn_checked_color = "#0078D4" if is_light else "#58A6FF"
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
            icon_name = next((ic for k, _, ic in self.SUBPAGE_KEYS if k == key), "network")
            btn.setIcon(get_icon(icon_name, color=btn_color))

        for sub in self._subpages.values():
            if hasattr(sub, "apply_theme") and callable(sub.apply_theme):
                sub.apply_theme(theme_name)

    _SUBPAGE_ATTRS = {
        "page_speedtest": 1,
        "page_doctor": 2,
        "page_wifi": 3,
        "page_lan_devices": 4,
        "page_traffic": 5,
        "page_connections": 6,
        "page_dns": 7,
        "page_share": 8,
        "page_adapters": 9,
        "page_tools": 10,
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
        """Switches active subpage by key name (supports 'key' or 'network_key')."""
        clean_key = key.replace("network_", "")

        key_to_idx = {k: i for i, (k, _, _) in enumerate(self.SUBPAGE_KEYS)}
        if clean_key in key_to_idx:
            idx = key_to_idx[clean_key]
            self._ensure_subpage_loaded(idx)
            self.stack.setCurrentIndex(idx)
            if clean_key in self._buttons:
                self._buttons[clean_key].setChecked(True)
            label = self.SUBPAGE_KEYS[idx][1]
            self.subpage_changed.emit(clean_key, label)
