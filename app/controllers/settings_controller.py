# -*- coding: utf-8 -*-
"""
SINAX Settings Controller
Coordinates user preferences, appearance, performance tuning, update management,
and settings search for SettingsPage.qml.
"""

from typing import Any
from PySide6.QtCore import QObject, Signal, Property, Slot

from app.core.logger import get_logger
from app.core.config import config
from app.controllers.theme_controller import theme_controller
from app.services.update_service import update_service

logger = get_logger("settings_controller")


class SettingsController(QObject):
    settingsChanged = Signal()
    searchQueryChanged = Signal(str)
    statusMessageChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_query = ""
        update_service.changed.connect(self.settingsChanged)
        update_service.errorOccurred.connect(self.statusMessageChanged)
        self._load_config()

    def _load_config(self):
        self._theme = config.get("theme", "dark")
        self._animations = config.get("animations_enabled", True)
        self._confirm_dangerous = config.get("confirm_dangerous_actions", True)
        self._remember_folder = config.get("remember_last_folder", True)
        self._page_cache_size = config.get("page_cache_size", 10)
        self._toast_notifications = config.get("enable_toasts", True)
        self._worker_threads = config.get("max_worker_threads", 4)
        self._sound_effects = config.get("enable_sounds", False)
        self.settingsChanged.emit()

    @Property(str, notify=settingsChanged)
    def activeTheme(self) -> str:
        return self._theme

    @Property(str, notify=settingsChanged)
    def theme(self) -> str:
        return self._theme

    @Property(bool, notify=settingsChanged)
    def animationsEnabled(self) -> bool:
        return self._animations

    @Property(bool, notify=settingsChanged)
    def confirmDangerousActions(self) -> bool:
        return self._confirm_dangerous

    @Property(bool, notify=settingsChanged)
    def rememberLastFolder(self) -> bool:
        return self._remember_folder

    @Property(int, notify=settingsChanged)
    def pageCacheSize(self) -> int:
        return self._page_cache_size

    @Property(bool, notify=settingsChanged)
    def toastNotifications(self) -> bool:
        return self._toast_notifications

    @Property(int, notify=settingsChanged)
    def workerThreads(self) -> int:
        return self._worker_threads

    @Property(str, notify=searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @searchQuery.setter
    def searchQuery(self, q: str):
        if self._search_query != q:
            self._search_query = q
            self.searchQueryChanged.emit(q)

    # Incremental updater properties exposed to QML
    @Property(str, notify=settingsChanged)
    def currentVersion(self) -> str:
        return update_service.currentVersion

    @Property(str, notify=settingsChanged)
    def latestVersion(self) -> str:
        return update_service.latestVersion

    @Property(str, notify=settingsChanged)
    def updateStatus(self) -> str:
        return update_service.statusText

    @Property(str, notify=settingsChanged)
    def updateState(self) -> str:
        return update_service.state

    @Property(int, notify=settingsChanged)
    def updateProgress(self) -> int:
        return update_service.progress

    @Property(bool, notify=settingsChanged)
    def updateAvailable(self) -> bool:
        return update_service.updateAvailable

    @Property(bool, notify=settingsChanged)
    def updateBusy(self) -> bool:
        return update_service.busy

    @Property(str, notify=settingsChanged)
    def updateSize(self) -> str:
        return update_service.updateSize

    @Property(str, notify=settingsChanged)
    def updateReleaseNotes(self) -> str:
        return update_service.releaseNotes

    @Slot()
    def checkForUpdates(self):
        update_service.checkForUpdates()

    @Slot()
    def downloadAndInstallUpdate(self):
        update_service.downloadAndInstall()

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value: Any):
        config.set(key, value)
        self.settingsChanged.emit()

    @Slot(str, "QVariant", result="QVariant")
    def getSetting(self, key: str, default: Any = None) -> Any:
        return config.get(key, default)

    @Slot(str)
    def setTheme(self, theme_mode: str):
        if theme_mode in ["dark", "light", "system"]:
            self._theme = theme_mode
            config.set("theme", theme_mode)
            if theme_mode != "system":
                theme_controller.setDark(theme_mode == "dark")
            self.settingsChanged.emit()
            self.statusMessageChanged.emit(f"تم تغيير المظهر إلى: {theme_mode}")

    @Slot(str, bool)
    def setBoolSetting(self, key: str, value: bool):
        if key == "animations":
            self._animations = value
            config.set("animations_enabled", value)
        elif key == "confirm_dangerous":
            self._confirm_dangerous = value
            config.set("confirm_dangerous_actions", value)
        elif key == "remember_folder":
            self._remember_folder = value
            config.set("remember_last_folder", value)
        elif key == "toasts":
            self._toast_notifications = value
            config.set("enable_toasts", value)
        self.settingsChanged.emit()

    @Slot(str, int)
    def setIntSetting(self, key: str, value: int):
        if key == "page_cache":
            self._page_cache_size = value
            config.set("page_cache_size", value)
        elif key == "workers":
            self._worker_threads = value
            config.set("max_worker_threads", value)
        self.settingsChanged.emit()

    @Slot()
    def resetToDefaults(self):
        self._theme = "dark"
        self._animations = True
        self._confirm_dangerous = True
        self._remember_folder = True
        self._page_cache_size = 10
        self._toast_notifications = True
        self._worker_threads = 4
        config.set("theme", "dark")
        config.set("animations_enabled", True)
        config.set("confirm_dangerous_actions", True)
        config.set("remember_last_folder", True)
        config.set("page_cache_size", 10)
        config.set("enable_toasts", True)
        config.set("max_worker_threads", 4)
        theme_controller.setDark(True)
        self.settingsChanged.emit()
        self.statusMessageChanged.emit("تم استعادة كافة الإعدادات الافتراضية")


settings_controller = SettingsController()
