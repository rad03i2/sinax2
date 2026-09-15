# -*- coding: utf-8 -*-
"""
SINAX High-Performance Installed Applications Table Model
Powers the QTableView with lazy icon loading, custom formatting, and batch selection.
"""

import os
from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import QAbstractTableModel, QFileInfo, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import QFileIconProvider

from app.services.apps_manager.app_model import InstalledApp
from app.ui.icons import get_icon


class AppsTableModel(QAbstractTableModel):
    """Table model representing a list of installed applications."""

    COL_CHECK = 0
    COL_ICON = 1
    COL_NAME = 2
    COL_PUBLISHER = 3
    COL_VERSION = 4
    COL_SIZE = 5
    COL_DATE = 6
    COL_ARCH = 7
    COL_SOURCE = 8
    COL_STATUS = 9

    COLUMN_HEADERS = [
        "",  # Checkbox
        "",  # Icon
        "اسم البرنامج",
        "الناشر",
        "الإصدار",
        "الحجم",
        "تاريخ التثبيت",
        "المعمارية",
        "المصدر",
        "الحالة",
    ]

    def __init__(self, apps: Optional[List[InstalledApp]] = None, parent=None):
        super().__init__(parent)
        self._apps: List[InstalledApp] = apps or []
        self._selected_ids: Set[str] = set()
        self._icon_cache: Dict[str, QIcon] = {}
        self._icon_provider = QFileIconProvider()
        self._default_app_icon = get_icon("file", color="#58A6FF")

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._apps)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMN_HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.COLUMN_HEADERS):
                return self.COLUMN_HEADERS[section]
        if orientation == Qt.Horizontal and role == Qt.FontRole:
            font = QFont("Segoe UI", 10)
            font.setBold(True)
            return font
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._apps)):
            return None

        app = self._apps[index.row()]
        col = index.column()

        # Checkbox column
        if col == self.COL_CHECK:
            if role == Qt.CheckStateRole:
                return Qt.Checked if app.id in self._selected_ids else Qt.Unchecked
            return None

        # Icon column
        if col == self.COL_ICON:
            if role == Qt.DecorationRole:
                return self._get_app_icon(app)
            return None

        # Display Text
        if role == Qt.DisplayRole:
            if col == self.COL_NAME:
                return app.name
            elif col == self.COL_PUBLISHER:
                return app.publisher
            elif col == self.COL_VERSION:
                return app.version
            elif col == self.COL_SIZE:
                return app.display_size
            elif col == self.COL_DATE:
                return app.formatted_install_date
            elif col == self.COL_ARCH:
                return app.architecture.upper()
            elif col == self.COL_SOURCE:
                source_map = {
                    "winget": "WinGet",
                    "store": "Microsoft Store",
                    "msi": "MSI Installer",
                    "exe": "EXE Installer",
                    "msix": "MSIX / AppX",
                }
                return source_map.get(app.source.lower(), app.source)
            elif col == self.COL_STATUS:
                status_parts = []
                if app.update_available:
                    status_parts.append(f"تحديث متاح ({app.available_version})")
                if app.is_running:
                    status_parts.append("يعمل الآن")
                if app.is_startup:
                    status_parts.append("بدء التشغيل")
                if app.is_broken:
                    status_parts.append("إدخال معطوب")
                if app.is_system_component:
                    status_parts.append("مكون نظام")
                if app.is_pinned:
                    status_parts.append("مثبت الإصدار")
                return " • ".join(status_parts) if status_parts else "مثبت"

        # Foreground Text Color
        if role == Qt.ForegroundRole:
            if col == self.COL_STATUS:
                if app.is_broken:
                    return QColor("#F85149")  # Red
                if app.update_available:
                    return QColor("#58A6FF")  # Blue
                if app.is_running:
                    return QColor("#3FB950")  # Green
                if app.is_system_component:
                    return QColor("#D29922")  # Yellow
                return QColor("#8B949E")  # Muted grey
            if col == self.COL_NAME:
                return QColor("#F0F6FC")  # Bright white
            return QColor("#C9D1D9")  # Normal light text

        # Alignment
        if role == Qt.TextAlignmentRole:
            if col in (self.COL_CHECK, self.COL_ICON, self.COL_ARCH, self.COL_SIZE):
                return Qt.AlignCenter
            return Qt.AlignRight | Qt.AlignVCenter

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid():
            return False

        if index.column() == self.COL_CHECK and role == Qt.CheckStateRole:
            app = self._apps[index.row()]
            if value == Qt.Checked:
                self._selected_ids.add(app.id)
            else:
                self._selected_ids.discard(app.id)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        default_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == self.COL_CHECK:
            return default_flags | Qt.ItemIsUserCheckable
        return default_flags

    def set_apps(self, apps: List[InstalledApp]):
        """Replaces the dataset with a new list of applications."""
        self.beginResetModel()
        self._apps = apps
        self.endResetModel()

    def get_app(self, row: int) -> Optional[InstalledApp]:
        """Returns the app at the given row index."""
        if 0 <= row < len(self._apps):
            return self._apps[row]
        return None

    def get_selected_apps(self) -> List[InstalledApp]:
        """Returns all currently checked applications."""
        return [a for a in self._apps if a.id in self._selected_ids]

    def select_all(self, select: bool = True):
        """Selects or deselects all apps in the current view."""
        self.beginResetModel()
        if select:
            self._selected_ids = {a.id for a in self._apps}
        else:
            self._selected_ids.clear()
        self.endResetModel()

    def invert_selection(self):
        """Inverts the selection status of all items."""
        self.beginResetModel()
        all_ids = {a.id for a in self._apps}
        self._selected_ids = all_ids - self._selected_ids
        self.endResetModel()

    def _get_app_icon(self, app: InstalledApp) -> QIcon:
        """Retrieves or creates a cached icon for the given application."""
        if app.id in self._icon_cache:
            return self._icon_cache[app.id]

        icon = None

        # 1. From DisplayIcon
        if app.display_icon:
            clean_path = app.display_icon.split(",")[0].strip().strip('"')
            if os.path.exists(clean_path):
                try:
                    qicon = QIcon(clean_path)
                    if not qicon.isNull():
                        icon = qicon
                    else:
                        icon = self._icon_provider.icon(QFileInfo(clean_path))
                except Exception:
                    pass

        # 2. From Main Executable
        if not icon and app.main_executable and os.path.exists(app.main_executable):
            try:
                icon = self._icon_provider.icon(QFileInfo(app.main_executable))
            except Exception:
                pass

        # 3. Fallback Fluent Vector Icon
        if not icon or icon.isNull():
            if app.source in ("store", "msix"):
                icon = get_icon("apps", color="#A371F7")
            elif app.source == "winget":
                icon = get_icon("apps", color="#58A6FF")
            elif app.source == "msi":
                icon = get_icon("file", color="#238636")
            else:
                icon = self._default_app_icon

        self._icon_cache[app.id] = icon
        return icon
