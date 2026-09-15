# -*- coding: utf-8 -*-
"""
SINAX Dashboard Controller
Provides live system metrics, quick center tiles, and recent activity to QML Dashboard.
Manages polling lifecycles (pauses background monitoring when user navigates away).
"""

import os
import platform
from typing import Any, Dict, List
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
import psutil

from app.controllers.navigation_controller import navigation_controller
from app.core.logger import get_logger

logger = get_logger("dashboard_controller")


class DashboardController(QObject):
    metricsChanged = Signal()
    operationsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cpu_percent: float = 0.0
        self._ram_percent: float = 0.0
        self._ram_text: str = "جاري القراءة..."
        self._disk_percent: float = 0.0
        self._disk_text: str = "جاري القراءة..."
        self._backup_text: str = "محمي - النظام جاهز"
        self._windows_text: str = f"{platform.system()} {platform.release()} (Build {platform.version()})"
        self._recent_ops: List[Dict[str, Any]] = [
            {"title": "فحص سلامة الأقراص السريع", "time": "منذ 10 دقائق", "status": "مكتمل"},
            {"title": "تنظيف ذاكرة التخزين المؤقت", "time": "منذ ساعتين", "status": "مكتمل"},
            {"title": "التحقق من تسريع العتاد", "time": "عند الإقلاع", "status": "جاهز"},
        ]

        self._quick_centers = [
            {
                "id": "file_manager",
                "title": "إدارة وتنظيم الملفات",
                "desc": "إعادة التسمية الذكية، دمج الملفات، تحويل الصيغ، ومركز PDF الشامل.",
                "icon": "folder",
                "route": "file_manager"
            },
            {
                "id": "multimedia",
                "title": "مركز الوسائط المتعددة",
                "desc": "معالجة وتحسين وضغط الفيديو، استعراض الصور، وتحويل المقاطع الصوتية.",
                "icon": "video",
                "route": "video_center"
            },
            {
                "id": "system_storage",
                "title": "النظام ومحلل التخزين",
                "desc": "كشف الملفات الضخمة، تنظيف الكاش والملفات المؤقتة، وصحة الأقراص.",
                "icon": "storage",
                "route": "system_storage_overview"
            },
            {
                "id": "apps_manager",
                "title": "إدارة التطبيقات والبرامج",
                "desc": "جرد البرامج، إزالة البقايا العالقة، تحديث الحزم، وتجهيز قبل الفورمات.",
                "icon": "apps",
                "route": "apps_overview"
            },
            {
                "id": "network",
                "title": "الشبكة والإنترنت",
                "desc": "تشخيص الاتصال، قياس السرعة، مراقبة الاستهلاك، وإدارة الأجهزة المحلية.",
                "icon": "network",
                "route": "network_overview"
            },
            {
                "id": "maintenance",
                "title": "مركز الصيانة والإصلاح",
                "desc": "طبيب SINAX الشامل، إصلاح ملفات ويندوز (SFC/DISM)، وصيانة الأداء.",
                "icon": "doctor",
                "route": "maintenance_overview"
            },
        ]

        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self._poll_metrics)
        self._is_active = False

    @Property(float, notify=metricsChanged)
    def cpuPercent(self) -> float:
        return self._cpu_percent

    @Property(float, notify=metricsChanged)
    def ramPercent(self) -> float:
        return self._ram_percent

    @Property(str, notify=metricsChanged)
    def ramText(self) -> str:
        return self._ram_text

    @Property(float, notify=metricsChanged)
    def diskPercent(self) -> float:
        return self._disk_percent

    @Property(str, notify=metricsChanged)
    def diskText(self) -> str:
        return self._disk_text

    @Property(str, notify=metricsChanged)
    def backupText(self) -> str:
        return self._backup_text

    @Property(str, notify=metricsChanged)
    def windowsText(self) -> str:
        return self._windows_text

    @Property(list, notify=operationsChanged)
    def recentOperations(self) -> list:
        return self._recent_ops

    @Property(list, constant=True)
    def quickCenters(self) -> list:
        return self._quick_centers

    @Slot()
    def startMonitoring(self):
        """Called when QML Dashboard is visible."""
        if not self._is_active:
            self._is_active = True
            self._poll_metrics()
            self._timer.start()

    @Slot()
    def stopMonitoring(self):
        """Called when user navigates away from Dashboard to preserve CPU."""
        if self._is_active:
            self._is_active = False
            self._timer.stop()

    def _poll_metrics(self):
        try:
            self._cpu_percent = psutil.cpu_percent(interval=None)

            vm = psutil.virtual_memory()
            self._ram_percent = vm.percent
            used_gb = vm.used / (1024 ** 3)
            total_gb = vm.total / (1024 ** 3)
            self._ram_text = f"{used_gb:.1f} GB / {total_gb:.1f} GB"

            du = psutil.disk_usage("C:\\")
            self._disk_percent = du.percent
            free_gb = du.free / (1024 ** 3)
            tot_disk_gb = du.total / (1024 ** 3)
            self._disk_text = f"{free_gb:.1f} GB متاح من {tot_disk_gb:.1f} GB"

            self.metricsChanged.emit()
        except Exception as e:
            logger.debug(f"Metrics poll error: {e}")

    @Property(bool, notify=metricsChanged)
    def isActive(self) -> bool:
        return self._is_active

    @Property(str, notify=metricsChanged)
    def cpuUsage(self) -> str:
        return f"{int(self._cpu_percent)}%"

    @Property(str, notify=metricsChanged)
    def ramUsage(self) -> str:
        return f"{int(self._ram_percent)}%"

    @Property(str, notify=metricsChanged)
    def diskUsage(self) -> str:
        return f"{int(self._disk_percent)}%"

    @Property(str, notify=metricsChanged)
    def diskFree(self) -> str:
        return self._disk_text

    @Property(str, notify=metricsChanged)
    def statusMessage(self) -> str:
        return self._backup_text

    @Slot()
    def refreshMetrics(self):
        self._poll_metrics()

    @Slot(bool)
    def setActive(self, active: bool):
        if active:
            self.startMonitoring()
        else:
            self.stopMonitoring()

    @Slot(str)
    def openCenter(self, route: str):
        navigation_controller.openRoute(route)


# Global Singleton Instance
dashboard_controller = DashboardController()
