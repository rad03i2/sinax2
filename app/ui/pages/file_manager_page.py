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
from app.controllers.navigation_controller import navigation_controller


class FileManagerPage(QWidget):
    """Modern QML File Management Hub with 100% backward compatibility."""

    open_tool_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_qml_ui()

    def _init_qml_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "fileManagementController")
        self.quick_widget.setSource(get_qml_url("pages/FileManagementPage.qml"))
        root_layout.addWidget(self.quick_widget)

        navigation_controller.routeRequested.connect(self._on_route_requested)

    def _on_route_requested(self, route: str):
        if route != "file_manager":
            self.open_tool_requested.emit(route)
