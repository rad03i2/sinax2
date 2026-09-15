# -*- coding: utf-8 -*-
"""
SINAX Quick About Controller
Coordinates the Quick About Popup identity window.
"""

from PySide6.QtCore import QObject, Signal, Property, Slot
from app.core.constants import APP_NAME, APP_TAGLINE_AR, APP_VERSION, DEVELOPER_NAME


class QuickAboutController(QObject):
    isOpenChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_open: bool = False

    @Property(bool, notify=isOpenChanged)
    def isOpen(self) -> bool:
        return self._is_open

    @Property(str, constant=True)
    def appName(self) -> str:
        return APP_NAME

    @Property(str, constant=True)
    def appSubtitle(self) -> str:
        return APP_TAGLINE_AR

    @Property(str, constant=True)
    def appVersion(self) -> str:
        return APP_VERSION

    @Property(str, constant=True)
    def developerName(self) -> str:
        return DEVELOPER_NAME

    @Slot()
    def toggle(self):
        self.setOpen(not self._is_open)

    @Slot(bool)
    def setOpen(self, open_state: bool):
        if self._is_open != open_state:
            self._is_open = open_state
            self.isOpenChanged.emit(open_state)


# Global Singleton Instance
quick_about_controller = QuickAboutController()
