# -*- coding: utf-8 -*-
"""
SINAX Quick About Controller
Coordinates the Quick About Popup identity window.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot, QUrl
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

    @Property(str, constant=True)
    def developerPhotoUrl(self) -> str:
        """Return a real file:// URL for the bundled developer photo.

        QML relative paths are fragile after PyInstaller moves application data
        below its runtime directory.  Resolve the image in Python so the same QML
        works both from source and from the packaged Windows build.
        """
        candidates = []

        frozen_root = getattr(sys, "_MEIPASS", None)
        if frozen_root:
            candidates.append(
                Path(frozen_root) / "resources" / "images" / "about" / "radwan_profile.png"
            )

        candidates.append(
            Path(__file__).resolve().parents[2]
            / "resources"
            / "images"
            / "about"
            / "radwan_profile.png"
        )

        for photo_path in candidates:
            try:
                if photo_path.is_file():
                    return QUrl.fromLocalFile(str(photo_path.resolve())).toString()
            except OSError:
                continue

        return ""

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
