# -*- coding: utf-8 -*-
"""
SINAX Video Controller
Coordinates Video tools catalog, category filtering, search, hardware encoder detection,
and video metadata analysis for VideoCenterPage.qml.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, Property, Slot

from app.core.logger import get_logger
from app.core.config import config
from app.controllers.navigation_controller import navigation_controller
from app.services.video.video_registry import (
    VIDEO_CATEGORIES, VIDEO_TOOLS, VideoToolDefinition, get_video_tool_by_id
)
from app.services.video.hardware_detector import hardware_detector

logger = get_logger("video_controller")


class VideoController(QObject):
    toolsChanged = Signal()
    categoriesChanged = Signal()
    activeCategoryChanged = Signal(str)
    searchQueryChanged = Signal(str)
    selectedToolChanged = Signal(str)
    activeVideoChanged = Signal(str)
    videoMetadataChanged = Signal()
    hardwareAccelerationChanged = Signal()
    isBusyChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_category = "all"
        self._search_query = ""
        self._selected_tool_id = ""
        self._active_video_path = ""
        self._video_duration_str = ""
        self._video_resolution_str = ""
        self._video_codec = ""
        self._video_size_str = ""
        self._video_fps = 0.0
        self._is_busy = False
        self._hw_encoders = []
        self._hw_encoders_detected = False
        self._favorites: List[str] = config.get("video_favorites", [
            "batch_compress", "target_size_compress", "batch_convert",
            "fast_remux", "resize_scale", "trim_cut", "extract_audio",
            "create_gif", "batch_workflow_builder"
        ])

    def _detect_hardware_encoders(self):
        if self._hw_encoders_detected:
            return
        self._hw_encoders_detected = True
        try:
            detected = hardware_detector.detect_all()
            encoders = []
            if getattr(detected, "nvenc_available", False):
                encoders.append({"name": "NVIDIA NVENC", "badge": "فائق السرعة", "type": "nvenc"})
            if getattr(detected, "qsv_available", False):
                encoders.append({"name": "Intel QuickSync", "badge": "تسريع عتادي", "type": "qsv"})
            if getattr(detected, "amf_available", False):
                encoders.append({"name": "AMD AMF", "badge": "تسريع عتادي", "type": "amf"})
            encoders.append({"name": "المعالج البرمجي (CPU Software)", "badge": "أقصى توافق وجودة", "type": "software"})
            self._hw_encoders = encoders
        except Exception as e:
            logger.debug(f"Hardware detector exception: {e}")
            self._hw_encoders = [{"name": "المعالج البرمجي (CPU Software)", "badge": "أقصى توافق وجودة", "type": "software"}]
        self.hardwareAccelerationChanged.emit()

    @Property("QVariantList", notify=categoriesChanged)
    def categories(self) -> List[Dict[str, str]]:
        return [{"id": cat["id"], "name": cat["name_ar"]} for cat in VIDEO_CATEGORIES]

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

    @Property(str, notify=activeVideoChanged)
    def activeVideoPath(self) -> str:
        return self._active_video_path

    @Property(str, notify=videoMetadataChanged)
    def videoDurationStr(self) -> str:
        return self._video_duration_str

    @Property(str, notify=videoMetadataChanged)
    def videoResolutionStr(self) -> str:
        return self._video_resolution_str

    @Property(str, notify=videoMetadataChanged)
    def videoCodec(self) -> str:
        return self._video_codec

    @Property(str, notify=videoMetadataChanged)
    def videoSizeStr(self) -> str:
        return self._video_size_str

    @Property(float, notify=videoMetadataChanged)
    def videoFps(self) -> float:
        return self._video_fps

    @Property("QVariantList", notify=hardwareAccelerationChanged)
    def availableEncoders(self) -> List[Dict[str, str]]:
        if not self._hw_encoders_detected:
            self._detect_hardware_encoders()
        return self._hw_encoders

    @Property(str, notify=hardwareAccelerationChanged)
    def hwEncoder(self) -> str:
        if not self._hw_encoders_detected:
            self._detect_hardware_encoders()
        if self._hw_encoders:
            return self._hw_encoders[0]["name"]
        return "CPU (Software)"

    @Property(bool, notify=hardwareAccelerationChanged)
    def hasHardwareAcceleration(self) -> bool:
        return any(e.get("status") == "active" for e in self._hw_encoders)

    @Property(bool, notify=isBusyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property("QVariantList", notify=toolsChanged)
    def tools(self) -> List[Dict[str, Any]]:
        results = []
        q = self._search_query.strip().lower()

        for t in VIDEO_TOOLS:
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
        config.set("video_favorites", self._favorites)
        self.toolsChanged.emit()

    @Slot(str)
    def openTool(self, tool_id: str):
        self._selected_tool_id = tool_id
        self.selectedToolChanged.emit(tool_id)
        logger.info(f"Opening Video tool: {tool_id}")
        navigation_controller.navigateTo(f"video_{tool_id}")

    @Slot(str)
    def loadVideoFile(self, path_str: str):
        p = Path(path_str.replace("file:///", "").replace("file://", ""))
        valid_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".flv", ".ts", ".m4v"}
        if not p.exists() or p.suffix.lower() not in valid_exts:
            return

        self._active_video_path = str(p)
        self.activeVideoChanged.emit(self._active_video_path)

        size_bytes = p.stat().st_size
        if size_bytes < 1024 * 1024:
            self._video_size_str = f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            self._video_size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            self._video_size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

        # Defaults until background probe
        self._video_duration_str = "جاري الفحص..."
        self._video_resolution_str = p.suffix.upper().replace(".", "")
        self._video_codec = "H.264 / AAC"
        self._video_fps = 30.0
        self.videoMetadataChanged.emit()

        # Run background probe if FFprobe is available
        self._probe_video_async(str(p))

    def _probe_video_async(self, file_path: str):
        # Lightweight probe
        try:
            from app.services.video.video_probe_service import VideoProbeService
            info = VideoProbeService.probe_file(file_path)
            if info:
                dur = getattr(info, "duration_seconds", 0)
                mins, secs = divmod(int(dur), 60)
                hrs, mins = divmod(mins, 60)
                self._video_duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
                w, h = getattr(info, "width", 0), getattr(info, "height", 0)
                if w and h:
                    self._video_resolution_str = f"{w}x{h}"
                self._video_codec = getattr(info, "video_codec", "H.264")
                self._video_fps = getattr(info, "fps", 30.0)
                self.videoMetadataChanged.emit()
        except Exception:
            pass


video_controller = VideoController()
