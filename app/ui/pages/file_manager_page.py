# -*- coding: utf-8 -*-
"""
SINAX File Manager Hub Page
Modern QML-powered Hub with 100% Backward Compatibility.
Displays the 7 primary File Management modules as modern Fluent cards,
with Smart Drag & Drop Resolver and Recent Folders.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.core.logger import get_logger

logger = get_logger("file_manager_page")


class FileManagerPage(QWidget):
    """Modern QML File Management Hub with direct, reliable tool routing."""

    open_tool_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._qml_signal_connected = False
        self._init_qml_ui()

    def _init_qml_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "fileManagementController")
        self.quick_widget.statusChanged.connect(self._wire_qml_signals)
        self.quick_widget.setSource(get_qml_url("pages/FileManagementPage.qml"))
        root_layout.addWidget(self.quick_widget)

        # setSource is normally synchronous for a local QML file, but also keep
        # statusChanged above so the signal is wired if loading finishes later.
        self._wire_qml_signals(self.quick_widget.status())

    def _wire_qml_signals(self, _status=None):
        if self._qml_signal_connected:
            return
        root_obj = self.quick_widget.rootObject()
        if root_obj is None:
            return
        try:
            root_obj.toolRequested.connect(self._on_qml_tool_requested)
            self._qml_signal_connected = True
            logger.info("File Management QML tool routing connected")
        except Exception as exc:
            logger.exception("Failed to connect File Management tool routing: %s", exc)

    def _on_qml_tool_requested(self, route: str):
        route = str(route or "").strip()
        if not route:
            return
        logger.info("File Management card requested route: %s", route)
        self.open_tool_requested.emit(route)
