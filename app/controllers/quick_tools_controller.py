# -*- coding: utf-8 -*-
"""
SINAX Quick Tools Controller & ToolRegistryModel
Exposes ToolRegistryModel, instant search filtering, category tabs,
and workbench input/output execution for QuickToolsPage.qml.
"""

import hashlib
import base64
import urllib.parse
import uuid
from typing import Dict, List, Any, Optional
from PySide6.QtCore import (
    QObject, Signal, Property, Slot, QAbstractListModel, QModelIndex, Qt, QUrl
)
from app.services.quick_tools.registry import QuickToolRegistry, CATEGORIES
from app.core.logger import get_logger

logger = get_logger("quick_tools_controller")


class ToolItem:
    def __init__(
        self,
        tool_id: str,
        title: str,
        description: str,
        icon: str = "tools",
        category: str = "all",
        input_type: str = "text"
    ):
        self.id = tool_id
        self.title = title
        self.description = description
        self.icon = icon
        self.category = category
        self.input_type = input_type


class ToolRegistryModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    DescriptionRole = Qt.UserRole + 3
    IconRole = Qt.UserRole + 4
    CategoryRole = Qt.UserRole + 5
    InputTypeRole = Qt.UserRole + 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tools: List[ToolItem] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._tools)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._tools)):
            return None

        t = self._tools[index.row()]
        if role == self.IdRole:
            return t.id
        elif role == self.TitleRole:
            return t.title
        elif role == self.DescriptionRole:
            return t.description
        elif role == self.IconRole:
            return t.icon
        elif role == self.CategoryRole:
            return t.category
        elif role == self.InputTypeRole:
            return t.input_type
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.IdRole: b"toolId",
            self.TitleRole: b"title",
            self.DescriptionRole: b"description",
            self.IconRole: b"icon",
            self.CategoryRole: b"category",
            self.InputTypeRole: b"inputType",
        }

    def set_tools(self, tools: List[ToolItem]):
        self.beginResetModel()
        self._tools = tools
        self.endResetModel()


class QuickToolsController(QObject):
    categoryChanged = Signal(str)
    searchChanged = Signal(str)
    activeToolChanged = Signal()
    workbenchStateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = ToolRegistryModel(self)
        self._active_category = "all"
        self._search_query = ""
        self._active_tool_id = "hash_calculator"
        self._active_tool_title = "حاسبة بصمة الهاش (Hash Calculator)"
        self._workbench_input = "Hello SINAX!"
        self._workbench_output = ""
        self._is_busy = False
        self._status_message = "جاهز للتنفيذ"

        QuickToolRegistry.initialize()
        self._load_tools()
        self.executeWorkbench()

    def _load_tools(self):
        defs = QuickToolRegistry.search(self._search_query, self._active_category)
        items = [
            ToolItem(
                tool_id=d.id,
                title=d.title_ar,
                description=d.description_ar,
                icon=d.icon or "tools",
                category=d.category,
                input_type="file" if any(it.name == "FILE" for it in d.input_types) else "text"
            )
            for d in defs
        ]
        self._model.set_tools(items)

    @Property(QObject, constant=True)
    def toolModel(self) -> ToolRegistryModel:
        return self._model

    @Property(str, notify=categoryChanged)
    def activeCategory(self) -> str:
        return self._active_category

    @Property(str, notify=searchChanged)
    def searchQuery(self) -> str:
        return self._search_query

    @Property(str, notify=activeToolChanged)
    def activeToolId(self) -> str:
        return self._active_tool_id

    @Property(str, notify=activeToolChanged)
    def activeToolTitle(self) -> str:
        return self._active_tool_title

    @Property(str, notify=workbenchStateChanged)
    def workbenchInput(self) -> str:
        return self._workbench_input

    @Property(str, notify=workbenchStateChanged)
    def workbenchOutput(self) -> str:
        return self._workbench_output

    @Property(bool, notify=workbenchStateChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(str, notify=workbenchStateChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Slot(str)
    def setCategory(self, cat: str):
        if self._active_category != cat:
            self._active_category = cat
            self.categoryChanged.emit(cat)
            self._load_tools()

    @Slot(str)
    def setSearchQuery(self, query: str):
        self._search_query = query
        self.searchChanged.emit(query)
        self._load_tools()

    @Slot(str)
    def selectTool(self, tool_id: str):
        tool_def = QuickToolRegistry.get_tool(tool_id)
        if tool_def:
            self._active_tool_id = tool_id
            self._active_tool_title = tool_def.title_ar
            self.activeToolChanged.emit()
            self.executeWorkbench()

    @Slot(str)
    def setWorkbenchInput(self, text: str):
        if self._workbench_input != text:
            self._workbench_input = text
            self.workbenchStateChanged.emit()

    @Slot()
    def executeWorkbench(self):
        """Executes current tool instantly on workbenchInput."""
        text = self._workbench_input
        tool_id = self._active_tool_id

        try:
            if "hash" in tool_id or tool_id == "hash_calculator":
                raw_bytes = text.encode("utf-8")
                md5_res = hashlib.md5(raw_bytes).hexdigest()
                sha256_res = hashlib.sha256(raw_bytes).hexdigest()
                sha512_res = hashlib.sha512(raw_bytes).hexdigest()
                self._workbench_output = (
                    f"SHA-256:\n{sha256_res}\n\n"
                    f"MD5:\n{md5_res}\n\n"
                    f"SHA-512:\n{sha512_res}"
                )
            elif "base64" in tool_id or "encode" in tool_id:
                encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
                self._workbench_output = encoded
            elif "uuid" in tool_id:
                self._workbench_output = f"UUID v4:\n{str(uuid.uuid4())}\nUUID (بدون شرطات):\n{str(uuid.uuid4()).replace('-', '')}"
            elif "url" in tool_id:
                self._workbench_output = urllib.parse.quote(text)
            elif "case" in tool_id or "upper" in tool_id:
                self._workbench_output = f"UPPERCASE: {text.upper()}\nlowercase: {text.lower()}\nTitle Case: {text.title()}"
            else:
                raw_bytes = text.encode("utf-8")
                self._workbench_output = f"SHA-256:\n{hashlib.sha256(raw_bytes).hexdigest()}\nالطول: {len(text)} حرف"

            self._status_message = "تمت المعالجة بنجاح"
        except Exception as e:
            self._workbench_output = f"خطأ في المعالجة: {str(e)}"
            self._status_message = "حدث خطأ"

        self.workbenchStateChanged.emit()

    @Slot(list)
    def handleDrop(self, url_list: List[Any]):
        if not url_list:
            return
        u = url_list[0]
        if isinstance(u, QUrl):
            path_str = u.toLocalFile()
        else:
            path_str = str(u).replace("file:///", "").replace("file://", "")

        self._workbench_input = path_str
        self._workbench_output = f"مسار الملف المحدد:\n{path_str}\n\nجارٍ حساب بصمة SHA-256 للملف..."
        self.workbenchStateChanged.emit()

        # Compute hash for file
        try:
            h = hashlib.sha256()
            with open(path_str, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            self._workbench_output = (
                f"الملف: {path_str}\n"
                f"SHA-256:\n{h.hexdigest()}"
            )
            self._status_message = "تم حساب بصمة الملف بنجاح"
        except Exception as e:
            self._workbench_output = f"تعذر قراءة الملف: {e}"
            self._status_message = "خطأ في قراءة الملف"

        self.workbenchStateChanged.emit()


# Singleton
quick_tools_controller = QuickToolsController()
