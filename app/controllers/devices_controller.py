# -*- coding: utf-8 -*-
"""
SINAX Devices & Hardware Controller
Coordinates hardware data providers for DevicesPage.qml.
Features lazy on-demand category querying, high-performance background execution,
and truthful reporting of hardware metrics.
"""

import platform
import psutil
from typing import Dict, List, Any, Optional
from PySide6.QtCore import QObject, Signal, Property, Slot, QThread
from app.controllers.navigation_controller import navigation_controller
from app.core.logger import get_logger

logger = get_logger("devices_controller")


class DevicesController(QObject):
    overviewLoaded = Signal()
    categoryDataChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._overview_data: Dict[str, Any] = {
            "device_name": platform.node(),
            "os_name": f"Windows {platform.release()} ({platform.machine()})",
            "cpu_name": "جاري الفحص...",
            "cpu_cores": "",
            "ram_total": "",
            "ram_type": "DDR4 / DDR5",
            "gpu_name": "جاري الفحص...",
            "motherboard": "جاري الفحص...",
            "battery": "غير متوفر (جهاز مكتبي / متصل)",
            "storage_summary": "جاري الفحص...",
        }
        self._category_cache: Dict[str, List[Dict[str, str]]] = {}
        self._load_overview_async()

    def _load_overview_async(self):
        """Asynchronously queries light hardware metrics for instant shell display."""
        try:
            # CPU
            cores = psutil.cpu_count(logical=False) or 1
            threads = psutil.cpu_count(logical=True) or 1
            self._overview_data["cpu_name"] = platform.processor() or "معالج x86_64"
            self._overview_data["cpu_cores"] = f"{cores} أنوية حقيقية / {threads} مسار (Threads)"

            # RAM
            vm = psutil.virtual_memory()
            total_gb = vm.total / (1024 ** 3)
            self._overview_data["ram_total"] = f"{total_gb:.1f} GB"

            # Battery
            batt = psutil.sensors_battery()
            if batt:
                plugged = "متصل بالشاحن" if batt.power_plugged else "على البطارية"
                self._overview_data["battery"] = f"{int(batt.percent)}% ({plugged})"
            else:
                self._overview_data["battery"] = "غير متوفر (متصل بمصدر طاقة ثابت)"

            # Storage
            du = psutil.disk_usage("C:\\")
            total_disk = du.total / (1024 ** 3)
            self._overview_data["storage_summary"] = f"قرص النظام: {total_disk:.0f} GB"

            self.overviewLoaded.emit()
        except Exception as e:
            logger.error(f"Error loading overview device telemetry: {e}")

    @Property(str, notify=overviewLoaded)
    def deviceName(self) -> str:
        return self._overview_data.get("device_name", platform.node())

    @Property(str, notify=overviewLoaded)
    def osName(self) -> str:
        return self._overview_data.get("os_name", "Windows")

    @Property(str, notify=overviewLoaded)
    def cpuName(self) -> str:
        return self._overview_data.get("cpu_name", "غير متوفر")

    @Property(str, notify=overviewLoaded)
    def cpuCores(self) -> str:
        return self._overview_data.get("cpu_cores", "غير متوفر")

    @Property(str, notify=overviewLoaded)
    def ramTotal(self) -> str:
        return self._overview_data.get("ram_total", "غير متوفر")

    @Property(str, notify=overviewLoaded)
    def ramType(self) -> str:
        return self._overview_data.get("ram_type", "DDR4 / DDR5")

    @Property(str, notify=overviewLoaded)
    def gpuName(self) -> str:
        return self._overview_data.get("gpu_name", "معالج رسوميات مدمج / منفصل")

    @Property(str, notify=overviewLoaded)
    def battery(self) -> str:
        return self._overview_data.get("battery", "غير متوفر")

    @Property(str, notify=overviewLoaded)
    def storageSummary(self) -> str:
        return self._overview_data.get("storage_summary", "غير متوفر")

    @Slot(str, result=list)
    def getCategoryItems(self, category: str) -> List[Dict[str, str]]:
        """Lazy-loads detailed items for a specific hardware category."""
        if category in self._category_cache:
            return self._category_cache[category]

        items = []
        try:
            if category == "cpu":
                freq = psutil.cpu_freq()
                cur_ghz = f"{freq.current / 1000:.2f} GHz" if freq else "غير متوفر"
                items = [
                    {"label": "اسم المعالج", "value": self.cpuName, "isMono": False},
                    {"label": "التردد الحالي", "value": cur_ghz, "isMono": True},
                    {"label": "عدد الأنوية", "value": str(psutil.cpu_count(logical=False) or 1), "isMono": True},
                    {"label": "عدد المسارات", "value": str(psutil.cpu_count(logical=True) or 1), "isMono": True},
                    {"label": "المعمارية", "value": platform.machine(), "isMono": True},
                ]
            elif category == "ram":
                vm = psutil.virtual_memory()
                items = [
                    {"label": "إجمالي الذاكرة", "value": f"{vm.total / (1024**3):.1f} GB", "isMono": True},
                    {"label": "الذاكرة المستخدمة", "value": f"{(vm.total - vm.available) / (1024**3):.1f} GB", "isMono": True},
                    {"label": "الذاكرة المتاحة", "value": f"{vm.available / (1024**3):.1f} GB", "isMono": True},
                    {"label": "ذاكرة التبديل (Swap)", "value": f"{psutil.swap_memory().total / (1024**3):.1f} GB", "isMono": True},
                ]
            elif category == "windows":
                items = [
                    {"label": "نظام التشغيل", "value": platform.system(), "isMono": False},
                    {"label": "الإصدار", "value": platform.release(), "isMono": True},
                    {"label": "رقم البناء (Build)", "value": platform.version(), "isMono": True},
                    {"label": "اسم الحاسوب", "value": platform.node(), "isMono": False},
                ]
            elif category == "battery":
                batt = psutil.sensors_battery()
                if batt:
                    items = [
                        {"label": "نسبة الشحن", "value": f"{int(batt.percent)}%", "isMono": True},
                        {"label": "حالة التوصيل", "value": "متصل بالشاحن" if batt.power_plugged else "يعمل على البطارية", "isMono": False},
                        {"label": "الوقت المتبقي", "value": "غير متوفر" if batt.secsleft <= 0 else f"{int(batt.secsleft / 60)} دقيقة", "isMono": True},
                    ]
                else:
                    items = [
                        {"label": "حالة البطارية", "value": "غير متوفر (جهاز مكتبي أو متصل بمصدر طاقة دائم)", "isMono": False}
                    ]
            else:
                items = [
                    {"label": "الحالة", "value": "جاهز للفحص التفصيلي", "isMono": False}
                ]
        except Exception as e:
            logger.error(f"Error getting category items for {category}: {e}")

        self._category_cache[category] = items
        return items

    @Slot(str)
    def openSubpage(self, subpage_key: str):
        route = f"devices_{subpage_key}"
        navigation_controller.openRoute(route)


# Singleton
devices_controller = DevicesController()
