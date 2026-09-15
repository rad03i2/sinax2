# -*- coding: utf-8 -*-
"""
SINAX Navigation Controller
Coordinates routing between QML Sidebar/TopBar and MainWindow stack.
Maintains history, breadcrumb strings, search filters, and sidebar collapse states.
"""

from typing import Dict, List, Optional
from PySide6.QtCore import QObject, Signal, Property, Slot
from app.models.navigation_model import NavigationModel
from app.core.config import config
from app.core.logger import get_logger

logger = get_logger("navigation_controller")


class NavigationController(QObject):
    routeChanged = Signal(str)
    titleChanged = Signal(str)
    breadcrumbChanged = Signal(str)
    collapseChanged = Signal(bool)
    searchChanged = Signal(str)
    historyChanged = Signal()
    openSectionChanged = Signal(str)
    routeRequested = Signal(str)  # Connected to MainWindow page switcher
    pageActivated = Signal(str)   # Lifecycle: called when page becomes visible
    pageDeactivated = Signal(str) # Lifecycle: called when page is navigated away from
    pageRefreshRequested = Signal(str)

    # Route metadata mapping (Title, Parent Section Title)
    ROUTE_META = {
        "dashboard": ("الرئيسية", ""),
        "file_manager": ("إدارة الملفات", ""),
        "batch_rename": ("إعادة تسمية الملفات", "إدارة الملفات"),
        "converter": ("المحوّل الشامل", "إدارة الملفات"),
        "merge_files": ("دمج وتجميع الملفات", "إدارة الملفات"),
        "smart_organize": ("التنظيم الذكي للملفات", "إدارة الملفات"),
        "search_analysis": ("البحث والتحليل المتقدم", "إدارة الملفات"),
        "duplicate_copy": ("النسخ والنقل والتكرار", "إدارة الملفات"),
        "pdf_center": ("مركز PDF", "إدارة الملفات"),
        "multimedia": ("الوسائط المتعددة", ""),
        "image_center": ("الصور", "الوسائط المتعددة"),
        "video_center": ("الفيديو", "الوسائط المتعددة"),
        "audio_center": ("الصوت", "الوسائط المتعددة"),
        "media_tools": ("أدوات الوسائط", "الوسائط المتعددة"),
        "system_storage": ("النظام والتخزين", ""),
        "system_storage_overview": ("نظرة عامة", "النظام والتخزين"),
        "system_storage_analyzer": ("محلل التخزين", "النظام والتخزين"),
        "system_storage_cleanup": ("التنظيف الآمن", "النظام والتخزين"),
        "system_storage_health": ("صحة الأقراص", "النظام والتخزين"),
        "system_storage_performance": ("مراقبة الأداء", "النظام والتخزين"),
        "system_storage_processes": ("إدارة العمليات", "النظام والتخزين"),
        "system_storage_startup": ("بدء التشغيل", "النظام والتخزين"),
        "system_storage_device": ("مواصفات الجهاز", "النظام والتخزين"),
        "apps_manager": ("إدارة البرامج والتطبيقات", ""),
        "apps_overview": ("نظرة عامة", "إدارة البرامج والتطبيقات"),
        "apps_inventory": ("كل البرامج", "إدارة البرامج والتطبيقات"),
        "apps_updates": ("التحديثات", "إدارة البرامج والتطبيقات"),
        "apps_uninstall": ("إزالة البرامج", "إدارة البرامج والتطبيقات"),
        "apps_large": ("البرامج الكبيرة", "إدارة البرامج والتطبيقات"),
        "apps_repair": ("الإصلاح وإعادة الضبط", "إدارة البرامج والتطبيقات"),
        "apps_leftovers": ("البقايا", "إدارة البرامج والتطبيقات"),
        "apps_before_format": ("قبل الفورمات", "إدارة البرامج والتطبيقات"),
        "apps_restore": ("استعادة البرامج", "إدارة البرامج والتطبيقات"),
        "network": ("الشبكة والإنترنت", ""),
        "network_overview": ("نظرة عامة", "الشبكة والإنترنت"),
        "network_speedtest": ("اختبار السرعة", "الشبكة والإنترنت"),
        "network_doctor": ("تشخيص الاتصال", "الشبكة والإنترنت"),
        "network_wifi": ("Wi-Fi", "الشبكة والإنترنت"),
        "network_lan_devices": ("الأجهزة المحلية", "الشبكة والإنترنت"),
        "network_traffic": ("استهلاك الإنترنت", "الشبكة والإنترنت"),
        "network_connections": ("الاتصالات والمنافذ", "الشبكة والإنترنت"),
        "network_dns": ("DNS", "الشبكة والإنترنت"),
        "network_share": ("مشاركة الملفات", "الشبكة والإنترنت"),
        "network_adapters": ("معلومات الشبكة", "الشبكة والإنترنت"),
        "network_tools": ("أدوات متقدمة", "الشبكة والإنترنت"),
        "devices": ("إدارة الأجهزة والمعلومات", ""),
        "devices_overview": ("نظرة عامة", "إدارة الأجهزة والمعلومات"),
        "devices_cpu": ("المعالج", "إدارة الأجهزة والمعلومات"),
        "devices_gpu": ("كرت الشاشة", "إدارة الأجهزة والمعلومات"),
        "devices_ram": ("الذاكرة RAM", "إدارة الأجهزة والمعلومات"),
        "devices_motherboard": ("اللوحة الأم وBIOS", "إدارة الأجهزة والمعلومات"),
        "devices_storage": ("التخزين", "إدارة الأجهزة والمعلومات"),
        "devices_battery": ("البطارية والطاقة", "إدارة الأجهزة والمعلومات"),
        "devices_displays": ("الشاشات", "إدارة الأجهزة والمعلومات"),
        "devices_usb": ("USB والأجهزة", "إدارة الأجهزة والمعلومات"),
        "devices_drivers": ("التعريفات", "إدارة الأجهزة والمعلومات"),
        "devices_sensors": ("الحساسات والحرارة", "إدارة الأجهزة والمعلومات"),
        "devices_windows": ("معلومات Windows", "إدارة الأجهزة والمعلومات"),
        "devices_quick_check": ("الفحص السريع", "إدارة الأجهزة والمعلومات"),
        "devices_reports": ("التقارير والمقارنة", "إدارة الأجهزة والمعلومات"),
        "privacy_security": ("الخصوصية والأمان", ""),
        "privacy_overview": ("نظرة عامة", "الخصوصية والأمان"),
        "privacy_file_safety": ("فحص الملفات", "الخصوصية والأمان"),
        "privacy_integrity": ("سلامة الملفات", "الخصوصية والأمان"),
        "privacy_signature": ("التوقيع الرقمي", "الخصوصية والأمان"),
        "privacy_clean": ("تنظيف الخصوصية", "الخصوصية والأمان"),
        "privacy_safe_share": ("المشاركة الآمنة", "الخصوصية والأمان"),
        "privacy_vault": ("التشفير والخزنة", "الخصوصية والأمان"),
        "privacy_secure_delete": ("الحذف الآمن", "الخصوصية والأمان"),
        "privacy_file_monitor": ("مراقبة التغييرات", "الخصوصية والأمان"),
        "privacy_passwords": ("كلمات المرور", "الخصوصية والأمان"),
        "privacy_windows_security": ("حماية Windows", "الخصوصية والأمان"),
        "privacy_advanced_tools": ("أدوات متقدمة", "الخصوصية والأمان"),
        "privacy_reports": ("التقارير", "الخصوصية والأمان"),
        "maintenance": ("مركز الصيانة والإصلاح", ""),
        "maintenance_overview": ("نظرة عامة", "مركز الصيانة والإصلاح"),
        "maintenance_doctor": ("طبيب SINAX", "مركز الصيانة والإصلاح"),
        "maintenance_cleanup": ("التنظيف الآمن", "مركز الصيانة والإصلاح"),
        "maintenance_windows_repair": ("إصلاح Windows", "مركز الصيانة والإصلاح"),
        "maintenance_storage_disk": ("التخزين والقرص", "مركز الصيانة والإصلاح"),
        "maintenance_updates": ("التحديثات والإقلاع", "مركز الصيانة والإصلاح"),
        "maintenance_startup": ("بدء التشغيل", "مركز الصيانة والإصلاح"),
        "maintenance_network": ("مشاكل الشبكة", "مركز الصيانة والإصلاح"),
        "maintenance_apps": ("مشاكل التطبيقات", "مركز الصيانة والإصلاح"),
        "maintenance_devices": ("مشاكل الأجهزة", "مركز الصيانة والإصلاح"),
        "maintenance_reliability": ("السجل والموثوقية", "مركز الصيانة والإصلاح"),
        "maintenance_advanced": ("أدوات متقدمة", "مركز الصيانة والإصلاح"),
        "backup_sync": ("النسخ الاحتياطي والمزامنة", ""),
        "backup_sync_overview": ("نظرة عامة", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_wizard": ("معالج النسخ الذكي", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_quick_backup": ("احمِ ملفاتي المهمة", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_before_format": ("تجهيز قبل الفورمات", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_sync": ("المزامنة الحية", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_restore": ("استعادة الملفات", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_versions": ("سجل الإصدارات", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_health_drill": ("صحة النسخ والاستعادة", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_destinations": ("أقراص النسخ (USB)", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_schedules": ("الجدولة التلقائية", "النسخ الاحتياطي والمزامنة"),
        "backup_sync_history_reports": ("سجل العمليات والتقارير", "النسخ الاحتياطي والمزامنة"),
        "quick_tools": ("الأدوات السريعة", ""),
        "history": ("سجل العمليات", ""),
        "settings": ("الإعدادات", ""),
        "about": ("حول البرنامج", ""),
        "icon_gallery": ("معرض الأيقونات للمطورين", "أدوات المطور"),
    }

    # Default subpage mappings for parent section clicks
    SECTION_DEFAULTS = {
        "file_manager": "file_manager",
        "multimedia": "image_center",
        "system_storage": "system_storage_overview",
        "apps_manager": "apps_overview",
        "network": "network_overview",
        "devices": "devices_overview",
        "privacy_security": "privacy_overview",
        "maintenance": "maintenance_overview",
        "backup_sync": "backup_sync_overview",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_route: str = "dashboard"
        self._is_collapsed: bool = config.get("sidebar_collapsed", False)
        self._search_query: str = ""
        self._history: List[str] = ["dashboard"]
        self._history_index: int = 0
        self._model = NavigationModel(self)
        self._model.openSectionChanged.connect(self.openSectionChanged)
        if self._is_collapsed:
            self._model.close_section()

    @Property(QObject, constant=True)
    def navModel(self) -> NavigationModel:
        return self._model

    @Property(str, notify=openSectionChanged)
    def openSectionId(self) -> str:
        return self._model.current_open_section or ""

    @Slot(str)
    def toggleSection(self, section_id: str):
        """Single source of truth accordion toggle for both Expanded and Collapsed modes."""
        self._model.toggle_section(section_id)

    @Slot()
    def closeSection(self):
        """Closes any open section/flyout."""
        self._model.close_section()

    @Property(str, notify=routeChanged)
    def currentRoute(self) -> str:
        return self._current_route

    @Property(str, notify=titleChanged)
    def currentTitle(self) -> str:
        meta = self.ROUTE_META.get(self._current_route, (self._current_route, ""))
        return meta[0]

    @Property(str, notify=breadcrumbChanged)
    def currentBreadcrumb(self) -> str:
        meta = self.ROUTE_META.get(self._current_route, (self._current_route, ""))
        title, parent_title = meta[0], meta[1]
        if parent_title:
            return f"{parent_title}  ›  {title}"
        return title

    @Property(bool, notify=collapseChanged)
    def isCollapsed(self) -> bool:
        return self._is_collapsed

    @Property(str, notify=searchChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @Property(bool, notify=historyChanged)
    def canGoBack(self) -> bool:
        return self._history_index > 0

    @Property(bool, notify=historyChanged)
    def canGoForward(self) -> bool:
        return self._history_index < len(self._history) - 1

    @Slot(str)
    def openRoute(self, route_id: str):
        """Navigates to route, updates model accordion, and records history."""
        target_route = self.SECTION_DEFAULTS.get(route_id, route_id)

        # Close any open flyout in collapsed mode without expanding sidebar
        if self._is_collapsed:
            self._model.close_section()

        if target_route != self._current_route:
            # Truncate any forward history and append
            if self._history_index < len(self._history) - 1:
                self._history = self._history[:self._history_index + 1]
            self._history.append(target_route)
            self._history_index = len(self._history) - 1
            self.historyChanged.emit()

            self._set_active_route(target_route)
            self.routeRequested.emit(target_route)

    def _set_active_route(self, route_id: str):
        old_route = self._current_route
        if old_route and old_route != route_id:
            self.pageDeactivated.emit(old_route)

        self._current_route = route_id
        if not self._is_collapsed:
            self._model.expand_for_route(route_id)
        self.routeChanged.emit(route_id)
        self.titleChanged.emit(self.currentTitle)
        self.breadcrumbChanged.emit(self.currentBreadcrumb)
        self.pageActivated.emit(route_id)

    @Slot()
    def goBack(self):
        if self.canGoBack:
            self._history_index -= 1
            target = self._history[self._history_index]
            self.historyChanged.emit()
            self._set_active_route(target)
            self.routeRequested.emit(target)

    @Slot()
    def goForward(self):
        if self.canGoForward:
            self._history_index += 1
            target = self._history[self._history_index]
            self.historyChanged.emit()
            self._set_active_route(target)
            self.routeRequested.emit(target)

    @Slot()
    def toggleSidebar(self):
        self.setCollapsed(not self._is_collapsed)

    @Slot(bool)
    def setCollapsed(self, val: bool):
        changed = (self._is_collapsed != val)
        self._is_collapsed = val
        if changed:
            config.set("sidebar_collapsed", val, auto_save=True)
            self.collapseChanged.emit(val)
        if val:
            self._model.close_section()
        elif changed:
            self._model.expand_for_route(self._current_route)

    @Slot(str)
    def setSearchQuery(self, query: str):
        self._search_query = query
        self._model.filter_by_search(query)
        self.searchChanged.emit(query)

    @Slot(str)
    def copyToClipboard(self, text: str):
        from PySide6.QtGui import QGuiApplication
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setText(text)


# Global Singleton Instance
navigation_controller = NavigationController()
