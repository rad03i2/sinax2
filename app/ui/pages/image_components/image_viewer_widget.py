# -*- coding: utf-8 -*-
"""
SINAX Interactive Image Viewer & Before/After Comparison Widget
Provides high-DPI image preview, interactive zoom & pan,
and a split-view slider comparing original vs processed images.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSlider, QSizePolicy
)
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen, QImage, QWheelEvent, QMouseEvent

from app.services.image.image_utils import format_size


class SplitComparisonCanvas(QWidget):
    """Canvas widget supporting interactive split-view comparison with a draggable divider."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap_before: Optional[QPixmap] = None
        self.pixmap_after: Optional[QPixmap] = None
        self.split_position: float = 0.5  # 0.0 to 1.0
        self.zoom_factor: float = 1.0
        self.pan_offset = QPoint(0, 0)
        self._dragging_split = False
        self._dragging_pan = False
        self._last_mouse_pos = QPoint()
        self.setMouseTracking(True)
        self.setCursor(Qt.ArrowCursor)

    def set_images(self, before_path: Optional[Path], after_path: Optional[Path] = None):
        """Loads pixmaps for before and after views."""
        self.pixmap_before = QPixmap(str(before_path)) if before_path and Path(before_path).exists() else None
        self.pixmap_after = QPixmap(str(after_path)) if after_path and Path(after_path).exists() else None
        self.pan_offset = QPoint(0, 0)
        self.zoom_factor = 1.0
        self.update()

    def zoom_in(self):
        self.zoom_factor = min(5.0, self.zoom_factor * 1.25)
        self.update()

    def zoom_out(self):
        self.zoom_factor = max(0.2, self.zoom_factor / 1.25)
        self.update()

    def reset_view(self):
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        self.split_position = 0.5
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Background grid pattern
        painter.fillRect(self.rect(), QColor("#181818"))

        if not self.pixmap_before and not self.pixmap_after:
            painter.setPen(QColor("#777777"))
            painter.drawText(self.rect(), Qt.AlignCenter, "اختر صورة لمعاينتها هنا")
            return

        ref_pix = self.pixmap_after or self.pixmap_before
        if not ref_pix or ref_pix.isNull():
            return

        w, h = self.width(), self.height()
        scaled_w = int(ref_pix.width() * self.zoom_factor)
        scaled_h = int(ref_pix.height() * self.zoom_factor)

        # Fit calculation
        fit_scale = min(w / ref_pix.width(), h / ref_pix.height(), 1.0) * self.zoom_factor
        draw_w = int(ref_pix.width() * fit_scale)
        draw_h = int(ref_pix.height() * fit_scale)

        draw_x = (w - draw_w) // 2 + self.pan_offset.x()
        draw_y = (h - draw_h) // 2 + self.pan_offset.y()
        target_rect = QRect(draw_x, draw_y, draw_w, draw_h)

        split_x = int(w * self.split_position)

        # Draw "After" (Processed) image
        active_after = self.pixmap_after or self.pixmap_before
        if active_after:
            painter.drawPixmap(target_rect, active_after)

        # Draw "Before" (Original) image clipped to left side if both exist
        if self.pixmap_before and self.pixmap_after:
            painter.save()
            painter.setClipRect(0, 0, split_x, h)
            painter.drawPixmap(target_rect, self.pixmap_before)
            painter.restore()

            # Draw divider line
            painter.setPen(QPen(QColor("#60CDFF"), 2))
            painter.drawLine(split_x, 0, split_x, h)

            # Draw Labels
            painter.setPen(QColor("#FFFFFF"))
            painter.fillRect(10, 10, 75, 24, QColor(0, 0, 0, 160))
            painter.drawText(16, 26, "الأصل (قبل)")

            painter.fillRect(w - 85, 10, 75, 24, QColor(0, 0, 0, 160))
            painter.drawText(w - 75, 26, "النتيجة (بعد)")

    def mousePressEvent(self, event: QMouseEvent):
        split_x = int(self.width() * self.split_position)
        if abs(event.pos().x() - split_x) <= 10 and self.pixmap_after:
            self._dragging_split = True
        elif event.button() == Qt.LeftButton:
            self._dragging_pan = True
            self._last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        split_x = int(self.width() * self.split_position)
        if self.pixmap_after and abs(event.pos().x() - split_x) <= 10:
            self.setCursor(Qt.SplitHCursor)
        elif not self._dragging_pan:
            self.setCursor(Qt.ArrowCursor)

        if self._dragging_split:
            self.split_position = max(0.05, min(0.95, event.pos().x() / self.width()))
            self.update()
        elif self._dragging_pan:
            delta = event.pos() - self._last_mouse_pos
            self.pan_offset += delta
            self._last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging_split = False
        self._dragging_pan = False
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()


class ImageViewerWidget(QFrame):
    """Composite preview widget with zoom controls, split comparison, and metrics display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #202020;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Toolbar: Zoom buttons + Reset + Mode
        tb_layout = QHBoxLayout()
        tb_layout.setSpacing(8)

        self.info_lbl = QLabel("معاينة الصورة")
        self.info_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #FFFFFF;")
        tb_layout.addWidget(self.info_lbl)
        tb_layout.addStretch(1)

        btn_style = """
            QPushButton {
                background-color: #2D2D2D;
                color: #E0E0E0;
                border: 1px solid #3E3E3E;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0078D4;
                border-color: #0078D4;
                color: #FFFFFF;
            }
        """

        btn_zoom_in = QPushButton("➕ تكبير")
        btn_zoom_in.setStyleSheet(btn_style)
        btn_zoom_in.clicked.connect(lambda: self.canvas.zoom_in())
        tb_layout.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("➖ تصغير")
        btn_zoom_out.setStyleSheet(btn_style)
        btn_zoom_out.clicked.connect(lambda: self.canvas.zoom_out())
        tb_layout.addWidget(btn_zoom_out)

        btn_reset = QPushButton("↺ إعادة ضبط")
        btn_reset.setStyleSheet(btn_style)
        btn_reset.clicked.connect(lambda: self.canvas.reset_view())
        tb_layout.addWidget(btn_reset)

        layout.addLayout(tb_layout)

        # Main Canvas
        self.canvas = SplitComparisonCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, 1)

        # Metrics bar
        self.metrics_bar = QFrame()
        self.metrics_bar.setStyleSheet("background-color: #1A1A1A; border-radius: 6px; padding: 4px;")
        mb_layout = QHBoxLayout(self.metrics_bar)
        mb_layout.setContentsMargins(10, 4, 10, 4)

        self.metrics_lbl = QLabel("الأبعاد: -- × --  |  الحجم: --")
        self.metrics_lbl.setStyleSheet("font-size: 11px; color: #AAAAAA;")
        mb_layout.addWidget(self.metrics_lbl)
        mb_layout.addStretch(1)

        self.savings_lbl = QLabel("")
        self.savings_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #6CCB5F;")
        mb_layout.addWidget(self.savings_lbl)

        layout.addWidget(self.metrics_bar)

    def load_image(self, path: Path):
        """Loads a single image for preview."""
        p = Path(path)
        if not p.exists():
            return

        self.canvas.set_images(p, None)
        size_str = format_size(p.stat().st_size)
        
        # Read dimensions
        try:
            from PIL import Image
            with Image.open(p) as img:
                w, h = img.size
                fmt = img.format or p.suffix.upper()
                self.metrics_lbl.setText(f"الصيغة: {fmt}  |  الأبعاد: {w} × {h} px  |  الحجم: {size_str}")
        except Exception:
            self.metrics_lbl.setText(f"الحجم: {size_str}")

        self.savings_lbl.setText("")
        self.info_lbl.setText(p.name)

    def set_comparison(self, before_path: Path, after_path: Path):
        """Loads both original and processed image for split comparison."""
        b_p = Path(before_path)
        a_p = Path(after_path)
        if not b_p.exists() or not a_p.exists():
            return

        self.canvas.set_images(b_p, a_p)

        b_size = b_p.stat().st_size
        a_size = a_p.stat().st_size
        diff = b_size - a_size
        pct = (diff / b_size * 100.0) if b_size > 0 else 0

        self.metrics_lbl.setText(
            f"قبل: {format_size(b_size)}  ←  بعد: {format_size(a_size)}"
        )
        if diff > 0:
            self.savings_lbl.setText(f"توفير: {format_size(diff)} ({pct:.1f}%) 📉")
        else:
            self.savings_lbl.setText("الحجم لم يتغير")

        self.info_lbl.setText(f"مقارنة: {b_p.name}")
