# -*- coding: utf-8 -*-
"""
SINAX Apps Management Controller & InstalledAppsModel
Coordinates Windows installed applications inventory, WinGet updates,
uninstallation workflows, and subpage filtering for AppsManagementPage.qml.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtCore import (
    QObject, Signal, Property, Slot, QAbstractListModel, QModelIndex, Qt, QThread
)

from app.core.logger import get_logger
from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.inventory_service import InventoryService
from app.services.apps_manager.update_service import UpdateService
from app.controllers.navigation_controller import navigation_controller

logger = get_logger("apps_controller")


class InstalledAppsModel(QAbstractListModel):
    NameRole = Qt.UserRole + 1
    PublisherRole = Qt.UserRole + 2
    VersionRole = Qt.UserRole + 3
    SizeStrRole = Qt.UserRole + 4
    InstallDateRole = Qt.UserRole + 5
    SourceRole = Qt.UserRole + 6
    ArchitectureRole = Qt.UserRole + 7
    CanUninstallRole = Qt.UserRole + 8
    ConfidenceRole = Qt.UserRole + 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_apps: List[InstalledApp] = []
        self._filtered_apps: List[InstalledApp] = []
        self._filter_type = "all"  # all, large, updates, store, winget, desktop
        self._search_query = ""

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._filtered_apps)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._filtered_apps)):
            return None
        app = self._filtered_apps[index.row()]

        if role == self.NameRole or role == Qt.DisplayRole:
            return getattr(app, "display_name", getattr(app, "name", "برنامج"))
        elif role == self.PublisherRole:
            return app.publisher or "غير معروف"
        elif role == self.VersionRole:
            return getattr(app, "display_version", getattr(app, "version", "1.0"))
        elif role == self.SizeStrRole:
            return getattr(app, "size_str", getattr(app, "display_size", "—"))
        elif role == self.InstallDateRole:
            return getattr(app, "formatted_install_date", getattr(app, "install_date", "—"))
        elif role == self.SourceRole:
            return getattr(app, "source", "desktop")
        elif role == self.ArchitectureRole:
            return getattr(app, "architecture", "64-bit")
        elif role == self.CanUninstallRole:
            return bool(app.uninstall_string)
        elif role == self.ConfidenceRole:
            # high, medium, uncertain
            return "high" if app.uninstall_string else "uncertain"
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.NameRole: b"name",
            self.PublisherRole: b"publisher",
            self.VersionRole: b"version",
            self.SizeStrRole: b"sizeStr",
            self.InstallDateRole: b"installDate",
            self.SourceRole: b"source",
            self.ArchitectureRole: b"architecture",
            self.CanUninstallRole: b"canUninstall",
            self.ConfidenceRole: b"confidence",
        }

    def set_apps(self, apps: List[InstalledApp]):
        self.beginResetModel()
        self._all_apps = apps
        self._apply_filter_internal()
        self.endResetModel()

    def set_filter(self, filter_type: str, search_query: str):
        self.beginResetModel()
        self._filter_type = filter_type
        self._search_query = search_query.strip().lower()
        self._apply_filter_internal()
        self.endResetModel()

    def _apply_filter_internal(self):
        res = self._all_apps
        if self._filter_type == "large":
            # Filter apps with size > 100MB
            res = [a for a in res if getattr(a, "estimated_size_bytes", 0) > 100 * 1024 * 1024]
        elif self._filter_type == "store":
            res = [a for a in res if getattr(a, "source", "") == "uwp"]
        elif self._filter_type == "desktop":
            res = [a for a in res if getattr(a, "source", "") != "uwp"]

        if self._search_query:
            q = self._search_query
            res = [
                a for a in res
                if q in a.display_name.lower() or q in (a.publisher or "").lower()
            ]

        self._filtered_apps = res


class AppsInventoryWorker(QThread):
    appsReady = Signal(list)

    def __init__(self, force_refresh=False, parent=None):
        super().__init__(parent)
        self.force_refresh = force_refresh

    def run(self):
        try:
            apps = InventoryService.get_all_apps(force_refresh=self.force_refresh)
            self.appsReady.emit(apps)
        except Exception as e:
            logger.error(f"Error loading apps inventory: {e}")
            self.appsReady.emit([])


class AppsController(QObject):
    appsCountChanged = Signal(int)
    activeFilterChanged = Signal(str)
    searchQueryChanged = Signal(str)
    selectedAppChanged = Signal()
    isLoadingChanged = Signal(bool)
    statusMessageChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = InstalledAppsModel(self)
        self._active_filter = "all"
        self._search_query = ""
        self._is_loading = False
        self._status_message = "جاهز"
        self._selected_app_idx = -1
        self._selected_app_data: Dict[str, Any] = {}
        self._worker: Optional[AppsInventoryWorker] = None
        self._inventory_initialized = False

    @Property(QObject, constant=True)
    def appsModel(self) -> InstalledAppsModel:
        if not self._inventory_initialized:
            self._inventory_initialized = True
            self.refreshInventory(False)
        return self._model

    @Property(int, notify=appsCountChanged)
    def totalAppsCount(self) -> int:
        return len(self._model._all_apps)

    @Property(int, notify=appsCountChanged)
    def filteredAppsCount(self) -> int:
        return len(self._model._filtered_apps)

    @Property(str, notify=activeFilterChanged)
    def activeFilter(self) -> str:
        return self._active_filter

    @activeFilter.setter
    def activeFilter(self, f: str):
        if self._active_filter != f:
            self._active_filter = f
            self.activeFilterChanged.emit(f)
            self._model.set_filter(self._active_filter, self._search_query)
            self.appsCountChanged.emit(self.filteredAppsCount)

    @Property(str, notify=searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @searchQuery.setter
    def searchQuery(self, q: str):
        if self._search_query != q:
            self._search_query = q
            self.searchQueryChanged.emit(q)
            self._model.set_filter(self._active_filter, self._search_query)
            self.appsCountChanged.emit(self.filteredAppsCount)

    @Slot(str)
    def setSearchFilter(self, q: str):
        self.searchQuery = q

    @Property(str, notify=searchQueryChanged)
    def searchFilter(self) -> str:
        return self._search_query

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property("QVariantMap", notify=selectedAppChanged)
    def selectedApp(self) -> Dict[str, Any]:
        return self._selected_app_data

    @Slot(bool)
    def refreshInventory(self, force=True):
        if self._is_loading:
            return
        self._is_loading = True
        self.isLoadingChanged.emit(True)
        self._status_message = "جاري قراءة سجل البرامج المثبتة..."
        self.statusMessageChanged.emit(self._status_message)

        self._worker = AppsInventoryWorker(force_refresh=force)
        self._worker.appsReady.connect(self._on_apps_loaded)
        self._worker.start()

    def _on_apps_loaded(self, apps: list):
        self._model.set_apps(apps)
        self._is_loading = False
        self.isLoadingChanged.emit(False)
        self.appsCountChanged.emit(len(apps))
        self._status_message = f"تم تحميل {len(apps)} تطبيق مثبت"
        self.statusMessageChanged.emit(self._status_message)

    @Slot(int)
    def selectApp(self, row: int):
        if 0 <= row < len(self._model._filtered_apps):
            self._selected_app_idx = row
            app = self._model._filtered_apps[row]
            self._selected_app_data = {
                "name": app.display_name,
                "publisher": app.publisher or "غير معروف",
                "version": app.display_version or "—",
                "sizeStr": app.size_str,
                "installDate": app.install_date or "—",
                "installLocation": getattr(app, "install_location", "") or "مسار افتراضي",
                "source": getattr(app, "source", "desktop"),
                "canUninstall": bool(app.uninstall_string),
                "confidence": "high" if app.uninstall_string else "uncertain",
            }
        else:
            self._selected_app_data = {}
        self.selectedAppChanged.emit()

    @Slot(str)
    def requestUninstall(self, app_name: str):
        logger.info(f"Requested uninstall for app: {app_name}")
        navigation_controller.navigateTo("apps_uninstall")


apps_controller = AppsController()
