# -*- coding: utf-8 -*-
"""
SINAX Command Palette Dialog
Hosts CommandPalette.qml in a transparent frameless overlay dialog.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.command_palette_controller import command_palette_controller


class CommandPaletteDialog(QDialog):
    """Transparent overlay dialog hosting the QML Command Palette."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(620, 480)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._quick_widget = None

        command_palette_controller.isOpenChanged.connect(self._on_open_changed)

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
            configure_qml_engine(self._quick_widget.engine(), controller_hint="command_palette_controller")
            self._quick_widget.setSource(get_qml_url("navigation/CommandPalette.qml"))
            self._layout.addWidget(self._quick_widget)

    def _on_open_changed(self, is_open: bool):
        if is_open:
            self._ensure_quick_widget()
            if self.parent():
                parent_geo = self.parent().geometry()
                self.move(
                    parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                    parent_geo.y() + (parent_geo.height() - self.height()) // 2 - 30
                )
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            self.hide()
            if self.parent():
                self.parent().activateWindow()

    def event(self, e):
        from PySide6.QtCore import QEvent
        if e.type() == QEvent.ActivationChange:
            if not self.isActiveWindow() and command_palette_controller.isOpen:
                command_palette_controller.setOpen(False)
        return super().event(e)
