# -*- coding: utf-8 -*-
"""
SINAX File Management Controller
Provides data models, recent folders, favorite tools, and Smart Action Resolver
for FileManagementPage.qml.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from PySide6.QtCore import QObject, Signal, Property, Slot, QUrl
from app.controllers.navigation_controller import navigation_controller
from app.core.config import config
from app.core.logger import get_logger

logger = get_logger("file_management_controller")


class FileManagementController(QObject):
    recentFoldersChanged = Signal()
    favoritesChanged = Signal()
    dropResolved = Signal(str, str, str)  # actionTitle, recommendedRoute, summaryText

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recent_folders: List[str] = []
        self._favorite_tools: List[str] = config.get("file_mgmt_favorites", ["batch_rename", "converter", "pdf_center"])
        self._init_recents()

    def _init_recents(self):
        saved = config.get("recent_folders", [])
        if not saved:
            last_f = config.get("last_folder", "")
            if last_f and Path(last_f).exists():
                saved = [last_f]
            else:
                user_home = Path.home()
                saved = [str(user_home / "Documents"), str(user_home / "Downloads")]
        self._recent_folders = [f for f in saved if Path(f).exists()][:5]

    @Property(list, notify=recentFoldersChanged)
    def recentFolders(self) -> List[str]:
        return self._recent_folders

    @Property(list, notify=favoritesChanged)
    def favoriteTools(self) -> List[str]:
        return self._favorite_tools

    @Slot(str)
    def toggleFavorite(self, tool_id: str):
        if tool_id in self._favorite_tools:
            self._favorite_tools.remove(tool_id)
        else:
            self._favorite_tools.append(tool_id)
        config.set("file_mgmt_favorites", self._favorite_tools, auto_save=True)
        self.favoritesChanged.emit()

    @Slot(str, result=bool)
    def isFavorite(self, tool_id: str) -> bool:
        return tool_id in self._favorite_tools

    @Slot(str)
    def openTool(self, tool_id: str):
        logger.info(f"Opening tool route: {tool_id}")
        navigation_controller.openRoute(tool_id)

    @Slot(list)
    def handleDrop(self, url_list: List[Any]):
        """Smart Drag & Drop Resolver analyzing paths and recommending optimal tool."""
        if not url_list:
            return

        paths = []
        for u in url_list:
            if isinstance(u, QUrl):
                p = u.toLocalFile()
            else:
                p = str(u).replace("file:///", "").replace("file://", "")
            if p:
                paths.append(Path(p))

        if not paths:
            return

        first_path = paths[0]
        # Remember last folder
        if first_path.is_dir():
            target_dir = str(first_path)
        else:
            target_dir = str(first_path.parent)

        if target_dir not in self._recent_folders:
            self._recent_folders.insert(0, target_dir)
            self._recent_folders = self._recent_folders[:5]
            config.set("recent_folders", self._recent_folders, auto_save=True)
            self.recentFoldersChanged.emit()

        # Classify by type
        if first_path.is_dir():
            self.dropResolved.emit(
                "تنظيم المجلد الذكي",
                "smart_organize",
                f"تم اكتشاف مجلد يحتوي على ملفات: '{first_path.name}'. نوصي بفرزه وتنظيمه تلقائياً."
            )
            return

        extensions = {p.suffix.lower() for p in paths if p.suffix}

        if any(ext in {".pdf"} for ext in extensions):
            self.dropResolved.emit(
                "مركز PDF الاحترافي",
                "pdf_center",
                f"تم اكتشاف {len(paths)} ملف(ات) PDF. يمكنك دمجها، ضغطها، أو تحويلها."
            )
        elif any(ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"} for ext in extensions):
            self.dropResolved.emit(
                "المحوّل الشامل للصور",
                "converter",
                f"تم اكتشاف {len(paths)} ملف صورة. نوصي بالتحويل أو الضغط الجماعي."
            )
        elif len(paths) > 3:
            self.dropResolved.emit(
                "إعادة التسمية الجماعية",
                "batch_rename",
                f"تم إسقاط {len(paths)} ملفات. يمكنك تطبيق قوالب التسمية الذكية دفعة واحدة."
            )
        else:
            self.dropResolved.emit(
                "المحوّل الشامل للملفات",
                "converter",
                f"تم إسقاط {len(paths)} ملف(ات). جاهزة للتحويل والمعالجة الفورية."
            )


# Singleton
file_management_controller = FileManagementController()
