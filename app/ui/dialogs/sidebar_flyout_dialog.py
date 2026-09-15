# -*- coding: utf-8 -*-
"""
SINAX Sidebar Flyout Dialog
Displays the child sub-items popup when clicking a collapsed sidebar section.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.navigation_controller import navigation_controller


class SidebarFlyoutDialog(QDialog):
    """Frameless overlay dialog for collapsed sidebar accordion flyouts."""

    def __init__(self, parent=None, sidebar_widget=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(230, 320)
        self._sidebar_widget = sidebar_widget

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._quick_widget = None

        navigation_controller.openSectionChanged.connect(self._on_section_changed)
        navigation_controller.collapseChanged.connect(self._on_collapse_changed)

    def _ensure_quick_widget(self):
        if self._quick_widget is None:
            self._quick_widget = QQuickWidget(self)
            self._quick_widget.setClearColor(Qt.transparent)
            self._quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
            configure_qml_engine(self._quick_widget.engine(), controller_hint="navigation_controller")
            self._quick_widget.setSource(get_qml_url("navigation/SidebarFlyout.qml"))
            self._layout.addWidget(self._quick_widget)

    def _on_section_changed(self, section_id: str):
        if section_id and navigation_controller.isCollapsed:
            self._ensure_quick_widget()
            self._reposition()
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            self.hide()

    def _on_collapse_changed(self, is_col: bool):
        if not is_col:
            self.hide()

    def _reposition(self):
        """Positions the flyout immediately to the left of the collapsed sidebar."""
        if self._sidebar_widget and self.parent():
            sidebar_global = self._sidebar_widget.mapToGlobal(QPoint(0, 0))
            # In RTL, sidebar is on the right side; flyout appears directly to its left
            x = sidebar_global.x() - self.width() - 4
            y = max(sidebar_global.y() + 60, min(sidebar_global.y() + 100, sidebar_global.y() + self._sidebar_widget.height() - self.height() - 40))
            self.move(x, y)

    def event(self, e: QEvent) -> bool:
        # Dismiss on outside click (loss of activation)
        if e.type() == QEvent.ActivationChange:
            if not self.isActiveWindow() and navigation_controller.openSectionId:
                navigation_controller.closeSection()
        return super().event(e)
