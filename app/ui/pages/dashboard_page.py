# -*- coding: utf-8 -*-
"""
SINAX Executive Control Dashboard (لوحة التحكم الرئيسية)
Modern QML-powered command center with 100% Backward Compatibility:
- Live CPU, RAM, and Storage vitals via QML Dashboard.qml
- 6 Essential Quick Action launch tiles
- Operations history preview
- Smart maintenance and data protection recommendations
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.navigation_controller import navigation_controller
from app.controllers.dashboard_controller import dashboard_controller
from app.ui.design_system import MetricCard, StatusBadge


class DashboardPage(QWidget):
    """Modern QML Executive Control Cockpit for SINAX with 100% Backward Compatibility."""

    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_compatibility_elements()
        self._init_qml_ui()
        QTimer.singleShot(100, self._load_async_telemetry)

    def _init_compatibility_elements(self):
        self.card_cpu = MetricCard("المعالج (CPU)", "0%", "الاستهلاك اللحظي", "performance", parent=self)
        self.card_ram = MetricCard("الذاكرة العشوائية (RAM)", "0%", "المستخدم من الإجمالي", "storage", parent=self)
        self.card_disk = MetricCard("قرص النظام الأساسي (C:)", "0%", "المساحة المتاحة", "storage", parent=self)
        self.status_badge = StatusBadge("النظام يعمل بكفاءة ✓", "success", parent=self)
        for w in [self.card_cpu, self.card_ram, self.card_disk, self.status_badge]:
            w.hide()
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def _init_qml_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "dashboardController")
        self.quick_widget.setSource(get_qml_url("pages/Dashboard.qml"))
        root_layout.addWidget(self.quick_widget)
        self.quick_widget.raise_()

        navigation_controller.routeRequested.connect(self._on_route_requested)

    def _on_route_requested(self, route: str):
        if route != "dashboard":
            self.navigate_requested.emit(route)

    def _load_async_telemetry(self):
        dashboard_controller.refreshMetrics()
