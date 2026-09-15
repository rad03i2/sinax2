# -*- coding: utf-8 -*-
"""
SINAX Storage & Performance Chart Widgets
Custom visual components using QPainter:
- CapacityGaugeWidget: Circular Donut chart for disk/memory capacity
- RollingHistoryChart: 60-second real-time line graph for CPU/RAM/Disk IO
- CategoryBarWidget: Horizontal multi-color category segment bar
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.services.system_storage.storage_scanner import format_bytes


class CapacityGaugeWidget(QWidget):
    """Circular Donut Chart showing used vs free space with dynamic color alerts."""

    def __init__(
        self,
        title: str = "القرص C:",
        total_bytes: int = 0,
        used_bytes: int = 0,
        parent=None
    ):
        super().__init__(parent)
        self.title = title
        self.total_bytes = total_bytes
        self.used_bytes = used_bytes
        self.setMinimumSize(160, 160)

    def set_values(self, used_bytes: int, total_bytes: int, title: Optional[str] = None):
        self.used_bytes = used_bytes
        self.total_bytes = total_bytes
        if title:
            self.title = title
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        size = min(w, h) - 20
        rect = QRectF((w - size) / 2.0, (h - size) / 2.0, size, size)

        pct = (self.used_bytes / self.total_bytes * 100.0) if self.total_bytes > 0 else 0.0
        pct = min(100.0, max(0.0, pct))

        # Color based on severity
        if pct >= 88.0:
            stroke_color = QColor("#F85149")     # Red
        elif pct >= 75.0:
            stroke_color = QColor("#D29922")     # Amber / Orange
        else:
            stroke_color = QColor("#58A6FF")     # Blue

        # Draw background ring track
        pen_bg = QPen(QColor("#21262D"), 12)
        pen_bg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect, 0, 360 * 16)

        # Draw used arc
        if pct > 0:
            pen_active = QPen(stroke_color, 12)
            pen_active.setCapStyle(Qt.RoundCap)
            painter.setPen(pen_active)
            # Start angle at 90 degrees (top), sweep negative clockwise
            start_angle = 90 * 16
            span_angle = -int(pct * 360 / 100.0 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # Center Text
        painter.setPen(QPen(QColor("#F0F6FC"), 1))
        painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
        text_pct = f"{pct:.1f}%"
        painter.drawText(rect, Qt.AlignCenter, text_pct)

        # Subtext (Used / Total)
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QPen(QColor("#8B949E"), 1))
        sub_rect = rect.adjusted(0, 36, 0, 0)
        sub_text = f"{format_bytes(self.used_bytes)} / {format_bytes(self.total_bytes)}"
        painter.drawText(sub_rect, Qt.AlignCenter, sub_text)


class RollingHistoryChart(QWidget):
    """Smooth real-time rolling line chart showing the last 60 seconds of metric history."""

    def __init__(
        self,
        title: str = "استهلاك المعالج",
        unit: str = "%",
        line_color: str = "#58A6FF",
        max_val: float = 100.0,
        parent=None
    ):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.line_color = QColor(line_color)
        self.max_val = max_val
        self.history: List[float] = []
        self.current_val: float = 0.0
        self.setMinimumSize(220, 110)

    def set_data(self, history: List[float], current_val: Optional[float] = None):
        self.history = list(history)
        if current_val is not None:
            self.current_val = current_val
        elif self.history:
            self.current_val = self.history[-1]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())

        # Card container background
        painter.setBrush(QBrush(QColor("#161B22")))
        painter.setPen(QPen(QColor("#30363D"), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

        # Header Title and current value
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.setPen(QPen(QColor("#F0F6FC"), 1))
        painter.drawText(12, 20, self.title)

        val_str = f"{self.current_val:.1f} {self.unit}"
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.setPen(QPen(self.line_color, 1))
        fm = QFontMetrics(painter.font())
        val_w = fm.horizontalAdvance(val_str)
        painter.drawText(int(w - val_w - 12), 20, val_str)

        # Chart area bounds
        chart_top = 32.0
        chart_bottom = h - 12.0
        chart_left = 12.0
        chart_right = w - 12.0
        chart_w = chart_right - chart_left
        chart_h = chart_bottom - chart_top

        # Horizontal grid line at 50%
        painter.setPen(QPen(QColor("#21262D"), 1, Qt.DashLine))
        mid_y = chart_top + chart_h / 2.0
        painter.drawLine(int(chart_left), int(mid_y), int(chart_right), int(mid_y))

        if not self.history or len(self.history) < 2:
            return

        # Build path points
        points: List[QPointF] = []
        n = len(self.history)
        step_x = chart_w / max(1, n - 1)

        # Dynamic max if self.max_val is 0 (auto-scale for disk IO)
        chart_max = self.max_val
        if chart_max <= 0:
            chart_max = max(1.0, max(self.history) * 1.2)

        for i, val in enumerate(self.history):
            clamped = min(chart_max, max(0.0, val))
            px = chart_left + (i * step_x)
            py = chart_bottom - (clamped / chart_max * chart_h)
            points.append(QPointF(px, py))

        # Filled gradient area
        fill_path = QPainterPath()
        fill_path.moveTo(points[0].x(), chart_bottom)
        for pt in points:
            fill_path.lineTo(pt)
        fill_path.lineTo(points[-1].x(), chart_bottom)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, chart_top, 0, chart_bottom)
        top_col = QColor(self.line_color)
        top_col.setAlpha(60)
        bot_col = QColor(self.line_color)
        bot_col.setAlpha(0)
        grad.setColorAt(0.0, top_col)
        grad.setColorAt(1.0, bot_col)

        painter.fillPath(fill_path, QBrush(grad))

        # Draw continuous stroke line
        line_pen = QPen(self.line_color, 2)
        line_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(line_pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])


class CategoryBarWidget(QWidget):
    """Horizontal stacked bar showing categorized disk allocation percentages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories: List[Tuple[str, str, int, float, str]] = []  # (key, label_ar, size, pct, color)
        self.setMinimumHeight(44)

    def set_categories(self, categories_dict: Dict[str, Any]):
        """Accepts categories dictionary from StorageAnalysisReport."""
        self.categories.clear()
        total_size = sum(c.size for c in categories_dict.values())
        for k, v in categories_dict.items():
            if v.size > 0:
                pct = (v.size / total_size * 100.0) if total_size > 0 else 0.0
                self.categories.append((k, v.label_ar, v.size, pct, v.color))
        # Sort descending by size
        self.categories.sort(key=lambda x: x[2], reverse=True)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = float(self.width())
        bar_h = 14.0
        bar_y = 6.0

        # Background track
        painter.setBrush(QBrush(QColor("#21262D")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, int(bar_y), int(w), int(bar_h), 6, 6)

        if not self.categories:
            return

        # Stack segments
        curr_x = 0.0
        total_pct = sum(c[3] for c in self.categories)

        for idx, (k, label, sz, pct, color_hex) in enumerate(self.categories):
            seg_w = max(2.0, w * (pct / 100.0))
            painter.setBrush(QBrush(QColor(color_hex)))

            if idx == 0 and len(self.categories) == 1:
                painter.drawRoundedRect(int(curr_x), int(bar_y), int(seg_w), int(bar_h), 6, 6)
            else:
                painter.drawRect(int(curr_x), int(bar_y), int(seg_w), int(bar_h))

            curr_x += seg_w

        # Draw Legend below
        legend_y = int(bar_y + bar_h + 16)
        painter.setFont(QFont("Segoe UI", 8))
        curr_leg_x = 0

        for k, label, sz, pct, color_hex in self.categories[:6]:
            # Dot
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(curr_leg_x, legend_y - 8, 8, 8)

            # Text
            painter.setPen(QPen(QColor("#C9D1D9"), 1))
            txt = f"{label} ({pct:.1f}%)"
            painter.drawText(curr_leg_x + 12, legend_y, txt)

            fm = QFontMetrics(painter.font())
            curr_leg_x += fm.horizontalAdvance(txt) + 24
            if curr_leg_x > w - 80:
                break
