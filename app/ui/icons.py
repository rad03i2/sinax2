# -*- coding: utf-8 -*-
"""
SINAX Icon Generator & Bridge
Delegates all icon requests to the centralized IconService (Microsoft Fluent UI System Icons).
Retains create_sinax_logo for custom branding rendering.
"""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF
from app.core.icon_registry import IconService


def create_sinax_logo(size: int = 64) -> QIcon:
    """Renders the official SINAX hexagonal tech logo with gradient-like modern styling."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw rounded hexagon background
    center = size / 2.0
    radius = size * 0.44

    path = QPainterPath()
    import math
    for i in range(6):
        angle_rad = math.radians(60 * i - 30)
        x = center + radius * math.cos(angle_rad)
        y = center + radius * math.sin(angle_rad)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()

    painter.setPen(QPen(QColor("#0078D4"), 2.5))
    painter.setBrush(QBrush(QColor("#005A9E")))
    painter.drawPath(path)

    # Draw modern "S" monogram inside
    s_pen = QPen(QColor("#FFFFFF"), size * 0.12, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(s_pen)
    
    spath = QPainterPath()
    spath.moveTo(center + size * 0.14, center - size * 0.18)
    spath.lineTo(center - size * 0.10, center - size * 0.18)
    spath.lineTo(center - size * 0.10, center - size * 0.02)
    spath.lineTo(center + size * 0.10, center + size * 0.02)
    spath.lineTo(center + size * 0.10, center + size * 0.18)
    spath.lineTo(center - size * 0.14, center + size * 0.18)
    painter.drawPath(spath)

    painter.end()
    return QIcon(pixmap)


def get_icon(name: str, color_hex: str = "#0078D4", size: int = 32, color: str = None) -> QIcon:
    """Provides a modern Fluent UI icon based on semantic name from centralized IconService."""
    if color is not None:
        color_hex = color

    if name == "logo":
        return create_sinax_logo(size)

    return IconService.get_qicon(name, color_hex, size)
