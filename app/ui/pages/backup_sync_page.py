# -*- coding: utf-8 -*-
"""
SINAX Backup & Sync Center Master Page (مركز النسخ الاحتياطي والمزامنة).
Coordinates and manages 11 specialized subpages:
0: overview (نظرة عامة والداشبورد)
1: wizard (معالج إنشاء خطة النسخ الاحتياطي)
2: quick_backup (احمِ ملفاتي المهمة بنقرة واحدة)
3: before_format (تجهيز وحفظ البيانات قبل الفورمات)
4: sync (مزامنة المجلدات وسلة التراجع)
5: restore (استعادة الملفات والبحث الشامل)
6: versions (سجل الإصدارات والخط الزمني)
7: health_drill (صحة النسخ واختبار الاستعادة العشوائي)
8: destinations (الوجهات والأقراص الموثوقة)
9: schedules (النسخ المجدول ومهام Windows)
10: history_reports (سجل العمليات وتصدير التقارير)
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
from app.core.module_loader import SubpageLazyRegistry
from app.ui.icons import get_icon
from app.ui.pages.backup_sync.subpages.before_format_subpage import BeforeFormatSubpage
from app.ui.pages.backup_sync.subpages.destinations_usb_subpage import DestinationsUsbSubpage
from app.ui.pages.backup_sync.subpages.health_drill_subpage import HealthDrillSubpage
from app.ui.pages.backup_sync.subpages.history_reports_subpage import HistoryReportsSubpage
from app.ui.pages.backup_sync.subpages.overview_subpage import OverviewSubpage
from app.ui.pages.backup_sync.subpages.quick_backup_subpage import QuickBackupSubpage
from app.ui.pages.backup_sync.subpages.restore_subpage import RestoreSubpage
from app.ui.pages.backup_sync.subpages.schedules_subpage import SchedulesSubpage
from app.ui.pages.backup_sync.subpages.sync_subpage import SyncSubpage
from app.ui.pages.backup_sync.subpages.versions_subpage import VersionsSubpage
from app.ui.pages.backup_sync.subpages.wizard_subpage import WizardSubpage


class QMLBackupSyncOverview(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "backupSyncController")
        self.quick_widget.setSource(get_qml_url("pages/BackupSyncPage.qml"))
        layout.addWidget(self.quick_widget)
        navigation_controller.routeRequested.connect(self._on_route)

    def refresh_telemetry(self):
        pass

    def _on_route(self, route: str):
        if route.startswith("backup_sync_"):
            sub_key = route.replace("backup_sync_", "")
            self.navigate_requested.emit(sub_key)


class BackupSyncPage(QWidget):
    """Master container page for SINAX Backup & Sync Center."""

    subpage_changed = Signal(str, str)  # (clean_key, label_ar)
    external_navigate_requested = Signal(str)

    SUBPAGE_KEYS = [
        ("overview", "نظرة عامة", "backup"),
        ("wizard", "معالج النسخ", "tools"),
        ("quick_backup", "النسخ السريع", "clean"),
        ("before_format", "قبل الفورمات", "system"),
        ("sync", "مزامنة المجلدات", "sync"),
        ("restore", "استعادة الملفات", "restore"),
        ("versions", "سجل الإصدارات", "clock"),
        ("health_drill", "صحة واختبار النسخ", "doctor"),
        ("destinations", "الوجهات والأقراص", "storage"),
        ("schedules", "النسخ المجدول", "clock"),
        ("history_reports", "السجل والتقارير", "history"),
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

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(14, 6, 14, 6)
        nav_layout.setSpacing(6)
        nav_layout.setAlignment(Qt.AlignLeft)

        for key, label_ar, icon_name in self.SUBPAGE_KEYS:
            btn = QPushButton(label_ar)
            btn.setCheckable(True)
            btn.setIcon(get_icon(icon_name, color="#8B949E", size=16))
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked=False, k=key: self.switch_subpage(k))
            self.btn_group.addButton(btn)
            self._buttons[key] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)
        self.nav_scroll.setWidget(nav_widget)
        main_layout.addWidget(self.nav_scroll)

        # 2. Main Subpages Stack
        self.stack = QStackedWidget(self)

        # Set up Subpage Lazy Registry (Loads only Overview eagerly, other 10 on demand)
        self._registry = SubpageLazyRegistry(self.stack)

        # 0: Overview (eager QML Hub)
        self._registry.register_subpage("overview", 0, lambda: QMLBackupSyncOverview(), eager=True)
        self.sub_overview = self._registry.get_or_create("overview")
        self.sub_overview.navigate_requested.connect(self._handle_internal_navigation)

        # 1..10: Lazy Subpages
        self._registry.register_subpage("wizard", 1, self._create_wizard_subpage)
        self._registry.register_subpage("quick_backup", 2, self._create_quick_backup_subpage)
        self._registry.register_subpage("before_format", 3, lambda: BeforeFormatSubpage())
        self._registry.register_subpage("sync", 4, lambda: SyncSubpage())
        self._registry.register_subpage("restore", 5, lambda: RestoreSubpage())
        self._registry.register_subpage("versions", 6, lambda: VersionsSubpage())
        self._registry.register_subpage("health_drill", 7, lambda: HealthDrillSubpage())
        self._registry.register_subpage("destinations", 8, lambda: DestinationsUsbSubpage())
        self._registry.register_subpage("schedules", 9, lambda: SchedulesSubpage())
        self._registry.register_subpage("history_reports", 10, lambda: HistoryReportsSubpage())

        main_layout.addWidget(self.stack, 1)

        # Default to overview
        self.switch_subpage("overview")

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
        btn_hover_bg = "#E2E8F0" if is_light else "rgba(255, 255, 255, 0.04)"
        btn_hover_color = "#0F172A" if is_light else "#F0F6FC"
        btn_checked_bg = "#E0F2FE" if is_light else "rgba(56, 189, 248, 0.08)"
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
            self.stack.setStyleSheet(f"background-color: {stack_bg};")

        btn_qss = f"""
            QPushButton {{
                background: transparent;
                color: {btn_color};
                border: none;
                border-bottom: 2px solid transparent;
                border-radius: 0px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                color: {btn_hover_color};
                background: {btn_hover_bg};
            }}
            QPushButton:checked {{
                color: {btn_checked_color};
                border-bottom: 2px solid {btn_checked_color};
                font-weight: bold;
                background: {btn_checked_bg};
            }}
        """
        for key, btn in self._buttons.items():
            btn.setStyleSheet(btn_qss)
            icon_name = next((ic for k, _, ic in self.SUBPAGE_KEYS if k == key), "backup")
            btn.setIcon(get_icon(icon_name, color=btn_color, size=16))

        if hasattr(self, "_registry") and self._registry is not None:
            for sub in self._registry._instances.values():
                if hasattr(sub, "apply_theme") and callable(sub.apply_theme):
                    sub.apply_theme(theme_name)

    def _create_wizard_subpage(self) -> WizardSubpage:
        wiz = WizardSubpage()
        wiz.backup_finished.connect(self.sub_overview.refresh_telemetry)
        return wiz

    def _create_quick_backup_subpage(self) -> QuickBackupSubpage:
        qb = QuickBackupSubpage()
        qb.backup_finished.connect(self.sub_overview.refresh_telemetry)
        return qb

    def __getattr__(self, name: str):
        if name.startswith("sub_"):
            key = name[4:]
            widget = self._registry.get_or_create(key)
            if widget is not None:
                if hasattr(widget, "apply_theme") and callable(widget.apply_theme):
                    from app.ui.themes.theme_manager import theme_manager
                    widget.apply_theme(theme_manager.effective_theme)
                return widget
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def switch_subpage(self, key: str):
        """Switches visible subpage by string key and updates button check state."""
        key_clean = key.lower().replace("backup_sync_", "").strip()
        index = -1
        label = "نظرة عامة"
        for i, (k, l, _) in enumerate(self.SUBPAGE_KEYS):
            if k == key_clean:
                index = i
                label = l
                break

        if index >= 0:
            sub = self._registry.switch_to(key_clean)
            if sub and hasattr(sub, "apply_theme") and callable(sub.apply_theme):
                from app.ui.themes.theme_manager import theme_manager
                sub.apply_theme(theme_manager.effective_theme)
            btn = self._buttons.get(key_clean)
            if btn and not btn.isChecked():
                btn.setChecked(True)
            self.subpage_changed.emit(key_clean, label)

    def _handle_internal_navigation(self, route_key: str):
        if route_key.startswith("backup_sync_"):
            clean = route_key[len("backup_sync_"):]
            self.switch_subpage(clean)
        else:
            self.external_navigate_requested.emit(route_key)

