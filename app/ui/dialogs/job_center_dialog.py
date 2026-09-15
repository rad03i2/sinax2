# -*- coding: utf-8 -*-
"""
SINAX Job Center Dialog
Hosts JobCenter.qml in a clean slide-in overlay dialog.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.job_controller import job_controller


class JobCenterDialog(QDialog):
    """Overlay dialog hosting the QML Job Center Drawer."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(460, 600)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._quick_widget = None

    @property
    def quick_widget(self):
        self._ensure_quick_widget()
        return self._quick_widget

    @quick_widget.setter
    def quick_widget(self, val):
        self._quick_widget = val

    def _ensure_quick_widget(self):
        if self._quick_widget is None:
            self._quick_widget = QQuickWidget(self)
            self._quick_widget.setClearColor(Qt.transparent)
            self._quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
            configure_qml_engine(self._quick_widget.engine(), controller_hint="job_controller")
            self.quick_widget_source = get_qml_url("navigation/JobCenter.qml")
            self._quick_widget.setSource(self.quick_widget_source)
            self._layout.addWidget(self._quick_widget)
            root_obj = self._quick_widget.rootObject()
            if root_obj and hasattr(root_obj, "closed"):
                root_obj.closed.connect(self.hide_drawer)

    def show_drawer(self):
        self._ensure_quick_widget()
        if self.parent():
            parent_geo = self.parent().geometry()
            self.setGeometry(
                parent_geo.x() + 20,
                parent_geo.y() + 60,
                440,
                parent_geo.height() - 80
            )
        root_obj = self._quick_widget.rootObject()
        if root_obj:
            root_obj.setProperty("isOpen", True)
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_drawer(self):
        if self._quick_widget:
            root_obj = self._quick_widget.rootObject()
            if root_obj:
                root_obj.setProperty("isOpen", False)
        self.hide()
