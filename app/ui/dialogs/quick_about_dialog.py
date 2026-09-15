# -*- coding: utf-8 -*-
"""
SINAX Quick About Dialog
Hosts QuickAboutPopup.qml in a transparent frameless centered dialog.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.quick_about_controller import quick_about_controller


class QuickAboutDialog(QDialog):
    """Transparent overlay dialog hosting the QML Quick About Popup."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(420, 380)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._quick_widget = None

        quick_about_controller.isOpenChanged.connect(self._on_open_changed)

    def _ensure_quick_widget(self):
        if self._quick_widget is None:
            self._quick_widget = QQuickWidget(self)
            self._quick_widget.setClearColor(Qt.transparent)
            self._quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
            configure_qml_engine(self._quick_widget.engine(), controller_hint="quick_about_controller")
            self._quick_widget.setSource(get_qml_url("dialogs/QuickAboutPopup.qml"))
            self._layout.addWidget(self._quick_widget)

    def _on_open_changed(self, is_open: bool):
        if is_open:
            self._ensure_quick_widget()
            if self.parent():
                parent_geo = self.parent().geometry()
                self.move(
                    parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                    parent_geo.y() + (parent_geo.height() - self.height()) // 2
                )
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            self.hide()

    def event(self, e: QEvent) -> bool:
        # Dismiss on outside click (losing activation)
        if e.type() == QEvent.ActivationChange:
            if not self.isActiveWindow() and quick_about_controller.isOpen:
                quick_about_controller.setOpen(False)
        return super().event(e)
