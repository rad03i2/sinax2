# -*- coding: utf-8 -*-
"""
SINAX Image Controller
Coordinates Image tools catalog, category filtering, search, image preview,
and interactive Before/After viewer for ImageCenterPage.qml.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, Property, Slot

from app.core.logger import get_logger
from app.core.config import config
from app.controllers.navigation_controller import navigation_controller
from app.services.image.image_registry import (
    IMAGE_TOOLS_REGISTRY, IMAGE_CATEGORIES, ImageToolDefinition, get_tool_by_id
)

logger = get_logger("image_controller")


class ImageController(QObject):
    toolsChanged = Signal()
    categoriesChanged = Signal()
    activeCategoryChanged = Signal(str)
    searchQueryChanged = Signal(str)
    selectedToolChanged = Signal(str)
    activeImageChanged = Signal(str)
    processedImageChanged = Signal(str)
    imageStatsChanged = Signal()
    isBusyChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_category = "all"
        self._search_query = ""
        self._selected_tool_id = ""
        self._active_image_path = ""
        self._processed_image_path = ""
        self._image_width = 0
        self._image_height = 0
        self._image_format = ""
        self._image_size_str = ""
        self._is_busy = False
        self._favorites: List[str] = config.get("image_favorites", [
            "batch_compress", "target_size_compress", "batch_resize",
            "batch_convert", "watermark", "batch_workflow_builder"
        ])

    @Property("QStringList", constant=True)
    def supportedFormats(self) -> List[str]:
        return ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF", "ICO"]

    @Property("QVariantList", notify=categoriesChanged)
    def categories(self) -> List[Dict[str, str]]:
        return [{"id": cat["id"], "name": cat["name_ar"]} for cat in IMAGE_CATEGORIES]

    @Property(str, notify=activeCategoryChanged)
    def activeCategory(self) -> str:
        return self._active_category

    @activeCategory.setter
    def activeCategory(self, cat: str):
        if self._active_category != cat:
            self._active_category = cat
            self.activeCategoryChanged.emit(cat)
            self.toolsChanged.emit()

    @Property(str, notify=searchQueryChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @searchQuery.setter
    def searchQuery(self, q: str):
        if self._search_query != q:
            self._search_query = q
            self.searchQueryChanged.emit(q)
            self.toolsChanged.emit()

    @Property(str, notify=selectedToolChanged)
    def selectedToolId(self) -> str:
        return self._selected_tool_id

    @Property(str, notify=activeImageChanged)
    def activeImagePath(self) -> str:
        return self._active_image_path

    @Property(str, notify=processedImageChanged)
    def processedImagePath(self) -> str:
        return self._processed_image_path

    @Property(int, notify=imageStatsChanged)
    def imageWidth(self) -> int:
        return self._image_width

    @Property(int, notify=imageStatsChanged)
    def imageHeight(self) -> int:
        return self._image_height

    @Property(str, notify=imageStatsChanged)
    def imageFormat(self) -> str:
        return self._image_format

    @Property(str, notify=imageStatsChanged)
    def imageSizeStr(self) -> str:
        return self._image_size_str

    @Property(bool, notify=isBusyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property("QVariantList", notify=toolsChanged)
    def tools(self) -> List[Dict[str, Any]]:
        results = []
        q = self._search_query.strip().lower()

        for t in IMAGE_TOOLS_REGISTRY:
            if self._active_category != "all":
                if self._active_category == "most_used":
                    if t.id not in self._favorites and t.category != "most_used":
                        continue
                elif t.category != self._active_category:
                    continue

            if q:
                match = (
                    q in t.title_ar.lower()
                    or q in t.title_en.lower()
                    or q in t.description_ar.lower()
                    or any(q in tag.lower() for tag in t.tags)
                )
                if not match:
                    continue

            results.append({
                "id": t.id,
                "title": t.title_ar,
                "titleEn": t.title_en,
                "category": t.category,
                "icon": t.icon,
                "description": t.description_ar,
                "status": getattr(t, "status", getattr(t, "badge", "جاهز")),
                "badgeText": getattr(t, "badge", "جاهز"),
                "supportsBatch": t.supports_batch,
                "isFavorite": t.id in self._favorites,
                "aiPowered": getattr(t, "ai_powered", False),
            })
        return results

    @Slot(str)
    def selectCategory(self, cat_id: str):
        self.activeCategory = cat_id

    @Slot(str)
    def setSearch(self, text: str):
        self.searchQuery = text

    @Slot(str)
    def toggleFavorite(self, tool_id: str):
        if tool_id in self._favorites:
            self._favorites.remove(tool_id)
        else:
            self._favorites.append(tool_id)
        config.set("image_favorites", self._favorites)
        self.toolsChanged.emit()

    @Slot(str)
    def openTool(self, tool_id: str):
        self._selected_tool_id = tool_id
        self.selectedToolChanged.emit(tool_id)
        logger.info(f"Opening Image tool: {tool_id}")
        navigation_controller.navigateTo(f"image_{tool_id}")

    @Slot(str)
    def loadImageFile(self, path_str: str):
        p = Path(path_str.replace("file:///", "").replace("file://", ""))
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif", ".ico"}
        if not p.exists() or p.suffix.lower() not in valid_exts:
            return

        self._active_image_path = str(p)
        self._processed_image_path = str(p)  # Default before/after to same until processed
        self.activeImageChanged.emit(self._active_image_path)
        self.processedImageChanged.emit(self._processed_image_path)

        size_bytes = p.stat().st_size
        if size_bytes < 1024 * 1024:
            self._image_size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            self._image_size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

        # Read dimensions using lightweight PIL without loading torch
        try:
            from PIL import Image
            with Image.open(str(p)) as im:
                self._image_width, self._image_height = im.size
                self._image_format = im.format or p.suffix.upper().replace(".", "")
        except Exception:
            self._image_width, self._image_height = 0, 0
            self._image_format = p.suffix.upper().replace(".", "")

        self.imageStatsChanged.emit()
        logger.info(f"Loaded Image: {p.name} ({self._image_width}x{self._image_height}, {self._image_format})")


image_controller = ImageController()
