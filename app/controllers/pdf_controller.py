# -*- coding: utf-8 -*-
"""
SINAX PDF Controller
Coordinates PDF tools catalog, category filtering, search, file dropping,
and thumbnail preview models for PdfCenterPage.qml.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, Property, Slot
import shutil

from app.core.logger import get_logger
from app.core.config import config
from app.controllers.navigation_controller import navigation_controller
from app.services.pdf.pdf_registry import (
    PDF_TOOLS_REGISTRY, PDF_CATEGORIES, PDFToolDefinition, get_tool_by_id
)

logger = get_logger("pdf_controller")


class PDFController(QObject):
    toolsChanged = Signal()
    categoriesChanged = Signal()
    activeCategoryChanged = Signal(str)
    searchQueryChanged = Signal(str)
    selectedToolChanged = Signal(str)
    activeFileChanged = Signal(str)
    pageCountChanged = Signal(int)
    fileSizeStrChanged = Signal(str)
    isBusyChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_category = "all"
        self._search_query = ""
        self._selected_tool_id = ""
        self._active_file_path = ""
        self._page_count = 0
        self._file_size_str = ""
        self._is_busy = False
        self._favorites: List[str] = config.get("pdf_favorites", ["merge", "compress", "split", "extract_pages", "protect"])

    @Property("QVariantList", notify=categoriesChanged)
    def categories(self) -> List[Dict[str, str]]:
        return [{"id": cat_id, "name": name} for cat_id, name in PDF_CATEGORIES]

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

    @Property(str, notify=activeFileChanged)
    def activeFilePath(self) -> str:
        return self._active_file_path

    @Property(int, notify=pageCountChanged)
    def pageCount(self) -> int:
        return self._page_count

    @Property(str, notify=fileSizeStrChanged)
    def fileSizeStr(self) -> str:
        return self._file_size_str

    @Property(bool, notify=isBusyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(int, notify=isBusyChanged)
    def progress(self) -> int:
        return 0

    @Property("QVariantList", notify=toolsChanged)
    def tools(self) -> List[Dict[str, Any]]:
        results = []
        q = self._search_query.strip().lower()

        for t in PDF_TOOLS_REGISTRY:
            # 1. Category Filter
            if self._active_category != "all":
                if self._active_category == "most_used":
                    if t.id not in self._favorites and t.category != "most_used":
                        continue
                elif t.category != self._active_category:
                    continue

            # 2. Search Filter
            if q:
                match = (
                    q in t.title_ar.lower()
                    or q in t.title_en.lower()
                    or q in t.description_ar.lower()
                    or any(q in tag.lower() for tag in t.tags)
                )
                if not match:
                    continue

            # 3. Check dependency status truthfully
            status = t.status
            if t.required_engine == "tesseract":
                has_tess = shutil.which("tesseract") is not None
                if not has_tess:
                    status = "needs_dep"
            elif t.required_engine == "qpdf":
                has_qpdf = shutil.which("qpdf") is not None
                if not has_qpdf:
                    status = "needs_dep"

            results.append({
                "id": t.id,
                "title": t.title_ar,
                "titleEn": t.title_en,
                "category": t.category,
                "icon": t.icon,
                "description": t.description_ar,
                "status": status,
                "supportsBatch": t.supports_batch,
                "isFavorite": t.id in self._favorites,
                "requiredEngine": t.required_engine,
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
        config.set("pdf_favorites", self._favorites)
        self.toolsChanged.emit()

    @Slot(str)
    def openTool(self, tool_id: str):
        self._selected_tool_id = tool_id
        self.selectedToolChanged.emit(tool_id)
        logger.info(f"Opening PDF tool: {tool_id}")
        navigation_controller.navigateTo(f"pdf_{tool_id}")

    @Slot(str)
    def loadPdfFile(self, path_str: str):
        p = Path(path_str.replace("file:///", "").replace("file://", ""))
        if not p.exists() or p.suffix.lower() != ".pdf":
            return

        self._active_file_path = str(p)
        self.activeFileChanged.emit(self._active_file_path)

        # Quick size formatting
        size_bytes = p.stat().st_size
        if size_bytes < 1024 * 1024:
            self._file_size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            self._file_size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        self.fileSizeStrChanged.emit(self._file_size_str)

        # Quick page count detection via lightweight pypdf or PyMuPDF if available
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            self._page_count = len(reader.pages)
        except Exception:
            try:
                import fitz
                doc = fitz.open(str(p))
                self._page_count = len(doc)
                doc.close()
            except Exception:
                self._page_count = 1

        self.pageCountChanged.emit(self._page_count)
        logger.info(f"Loaded PDF: {p.name} ({self._page_count} pages, {self._file_size_str})")


pdf_controller = PDFController()
