# -*- coding: utf-8 -*-
"""
SINAX QML Icon Provider
Provides on-demand Fluent UI vector icons to Qt Quick / QML via QQuickImageProvider.
Usage in QML: "image://sinax/<icon_name>[_variant]/<hex_color>/<size>"
Example: "image://sinax/folder/38BDF8/20"
Example with filled variant: "image://sinax/home_filled/38BDF8/20"
Example with RTL mirroring: "image://sinax/back/38BDF8/20?mirrored=1"
"""

from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, QColor, QImage
from app.core.icon_registry import IconService, IconRegistry


class SinaxIconProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Pixmap)

    def requestPixmap(self, id_str: str, size: QSize = None, requestedSize: QSize = None) -> QPixmap:
        """
        Parses id string format:
        <icon_name>/<color>/<size>
        Defaults: color=#CCCCCC, size=20
        Supports query parameters like ?mirrored=1
        """
        if requestedSize is None:
            requestedSize = QSize()
        if size is None:
            size = QSize()

        # Check query string for flags like mirrored
        mirrored = False
        query_parts = id_str.split("?")
        path_part = query_parts[0]
        if len(query_parts) > 1 and "mirrored=1" in query_parts[1]:
            mirrored = True

        parts = path_part.split("/")
        raw_name = parts[0] if len(parts) > 0 else "folder"

        # Check for variant suffix e.g. "home_filled" or "star_filled"
        variant = "regular"
        if raw_name.endswith("_filled"):
            icon_name = raw_name[:-7]
            variant = "filled"
        elif ":" in raw_name:
            icon_name, variant = raw_name.split(":", 1)
        else:
            icon_name = raw_name

        # Color handling (supports "#RRGGBB", "RRGGBB", or named colors)
        color_str = "#CCCCCC"
        if len(parts) > 1 and parts[1]:
            raw_c = parts[1].replace("%23", "#")
            if not raw_c.startswith("#") and len(raw_c) in (3, 6, 8):
                color_str = f"#{raw_c}"
            else:
                color_str = raw_c

        # Size handling
        icon_size = 20
        if len(parts) > 2 and parts[2].isdigit():
            icon_size = int(parts[2])
        elif requestedSize.isValid() and requestedSize.width() > 0:
            icon_size = requestedSize.width()

        pm = IconService.get_pixmap(icon_name, color_str, icon_size, variant=variant, mirrored=mirrored)
        if pm.isNull():
            pm = QPixmap(icon_size, icon_size)
            pm.fill(QColor(color_str))
        return pm

    def requestImage(self, id_str: str, size: QSize = None, requestedSize: QSize = None) -> QImage:
        pm = self.requestPixmap(id_str, size, requestedSize)
        return pm.toImage()
