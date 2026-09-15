# -*- coding: utf-8 -*-
"""
SINAX System & Storage Controller
Exposes live hardware vitals, DriveModel, and storage analysis hooks
for SystemStoragePage.qml. Pauses polling when page is inactive.
"""

import shutil
import psutil
from typing import Dict, List, Any, Optional
from PySide6.QtCore import (
    QObject, Signal, Property, Slot, QTimer, QAbstractListModel, QModelIndex, Qt
)
from app.controllers.navigation_controller import navigation_controller
from app.core.logger import get_logger

logger = get_logger("system_storage_controller")


class DriveItem:
    def __init__(
        self,
        letter: str,
        label: str = "",
        filesystem: str = "NTFS",
        total_gb: float = 0.0,
        used_gb: float = 0.0,
        free_gb: float = 0.0,
        percent: float = 0.0,
        drive_type: str = "SSD",
        health: str = "جيد جداً"
    ):
        self.letter = letter
        self.label = label if label else f"قرص محلي ({letter})"
        self.filesystem = filesystem
        self.total_gb = total_gb
        self.used_gb = used_gb
        self.free_gb = free_gb
        self.percent = percent
        self.drive_type = drive_type
        self.health = health


class DriveModel(QAbstractListModel):
    LetterRole = Qt.UserRole + 1
    LabelRole = Qt.UserRole + 2
    FilesystemRole = Qt.UserRole + 3
    TotalGbRole = Qt.UserRole + 4
    UsedGbRole = Qt.UserRole + 5
    FreeGbRole = Qt.UserRole + 6
    PercentRole = Qt.UserRole + 7
    DriveTypeRole = Qt.UserRole + 8
    HealthRole = Qt.UserRole + 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drives: List[DriveItem] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._drives)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._drives)):
            return None

        d = self._drives[index.row()]
        if role == self.LetterRole:
            return d.letter
        elif role == self.LabelRole:
            return d.label
        elif role == self.FilesystemRole:
            return d.filesystem
        elif role == self.TotalGbRole:
            return f"{d.total_gb:.1f} GB"
        elif role == self.UsedGbRole:
            return f"{d.used_gb:.1f} GB"
        elif role == self.FreeGbRole:
            return f"{d.free_gb:.1f} GB"
        elif role == self.PercentRole:
            return int(d.percent)
        elif role == self.DriveTypeRole:
            return d.drive_type
        elif role == self.HealthRole:
            return d.health
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.LetterRole: b"letter",
            self.LabelRole: b"label",
            self.FilesystemRole: b"filesystem",
            self.TotalGbRole: b"totalGb",
            self.UsedGbRole: b"usedGb",
            self.FreeGbRole: b"freeGb",
            self.PercentRole: b"percent",
            self.DriveTypeRole: b"driveType",
            self.HealthRole: b"health",
        }

    def update_drives(self, drives: List[DriveItem]):
        self.beginResetModel()
        self._drives = drives
        self.endResetModel()


class SystemStorageController(QObject):
    vitalsChanged = Signal()
    breakdownChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drive_model = DriveModel(self)
        self._cpu_percent = 0.0
        self._ram_percent = 0.0
        self._ram_used_gb = 0.0
        self._ram_total_gb = 0.0
        self._disk_c_percent = 0.0
        self._disk_c_free_gb = 0.0

        # Storage Breakdown percentages (System, Apps, Docs, Media, Temp)
        self._breakdown = {
            "system": 35,
            "apps": 25,
            "documents": 15,
            "media": 15,
            "temp": 10
        }

        # Polling timer (throttled to 1000ms)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._poll_vitals)

        # Connect to navigation lifecycle
        navigation_controller.pageActivated.connect(self._on_page_activated)
        navigation_controller.pageDeactivated.connect(self._on_page_deactivated)
        self._drives_scanned = False

    @Property(QObject, constant=True)
    def driveModel(self) -> DriveModel:
        if not self._drives_scanned:
            self._drives_scanned = True
            self._refresh_drives()
        return self._drive_model

    @Property(int, notify=vitalsChanged)
    def cpuPercent(self) -> int:
        return int(self._cpu_percent)

    @Property(int, notify=vitalsChanged)
    def ramPercent(self) -> int:
        return int(self._ram_percent)

    @Property(str, notify=vitalsChanged)
    def ramText(self) -> str:
        return f"{self._ram_used_gb:.1f} / {self._ram_total_gb:.1f} GB"

    @Property(int, notify=vitalsChanged)
    def diskCPercent(self) -> int:
        return int(self._disk_c_percent)

    @Property(str, notify=vitalsChanged)
    def diskCFreeText(self) -> str:
        return f"{self._disk_c_free_gb:.1f} GB متاح"

    @Property(int, notify=breakdownChanged)
    def breakdownSystem(self) -> int:
        return self._breakdown["system"]

    @Property(int, notify=breakdownChanged)
    def breakdownApps(self) -> int:
        return self._breakdown["apps"]

    @Property(int, notify=breakdownChanged)
    def breakdownDocs(self) -> int:
        return self._breakdown["documents"]

    @Property(int, notify=breakdownChanged)
    def breakdownMedia(self) -> int:
        return self._breakdown["media"]

    @Property(int, notify=breakdownChanged)
    def breakdownTemp(self) -> int:
        return self._breakdown["temp"]

    def _on_page_activated(self, route: str):
        if route.startswith("system_storage"):
            if not self._timer.isActive():
                self._timer.start()
                self._poll_vitals()

    def _on_page_deactivated(self, route: str):
        if route.startswith("system_storage"):
            self._timer.stop()

    def _poll_vitals(self):
        try:
            self._cpu_percent = psutil.cpu_percent()
            vm = psutil.virtual_memory()
            self._ram_percent = vm.percent
            self._ram_used_gb = (vm.total - vm.available) / (1024 ** 3)
            self._ram_total_gb = vm.total / (1024 ** 3)

            # Disk C
            du = shutil.disk_usage("C:\\")
            self._disk_c_percent = (du.used / du.total) * 100
            self._disk_c_free_gb = du.free / (1024 ** 3)

            self.vitalsChanged.emit()
        except Exception as e:
            logger.error(f"Error polling system storage vitals: {e}")

    def _refresh_drives(self):
        drives = []
        try:
            for part in psutil.disk_partitions(all=False):
                if "cdrom" in part.opts or not part.fstype:
                    continue
                try:
                    usage = shutil.disk_usage(part.mountpoint)
                    total_gb = usage.total / (1024 ** 3)
                    used_gb = usage.used / (1024 ** 3)
                    free_gb = usage.free / (1024 ** 3)
                    pct = (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    drive_letter = part.mountpoint.rstrip("\\")
                    drives.append(DriveItem(
                        letter=drive_letter,
                        label=f"قرص ({drive_letter})",
                        filesystem=part.fstype,
                        total_gb=total_gb,
                        used_gb=used_gb,
                        free_gb=free_gb,
                        percent=pct,
                        drive_type="SSD" if "c:" in drive_letter.lower() else "HDD",
                        health="جيد جداً"
                    ))
                except (PermissionError, OSError):
                    continue
        except Exception as e:
            logger.error(f"Error scanning partitions: {e}")

        if not drives:
            drives.append(DriveItem(letter="C:", label="قرص النظام (C:)", total_gb=512, used_gb=320, free_gb=192, percent=62.5))

        self._drive_model.update_drives(drives)

    @Slot(str)
    def openSubpage(self, subpage_key: str):
        route = f"system_storage_{subpage_key}"
        navigation_controller.openRoute(route)


# Singleton
system_storage_controller = SystemStorageController()
