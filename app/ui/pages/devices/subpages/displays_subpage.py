# -*- coding: utf-8 -*-
"""
SINAX Displays & EDID Subpage (صفحة الشاشات ومعلومات اللوحة)
Displays visual multi-monitor spatial arrangement map, EDID panel details,
panel manufacturer, product code, refresh rates, DPI scaling, and HDR support.
"""

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.display_service import DisplayService
from app.services.devices.hardware_models import MonitorDetails
from app.ui.icons import get_icon


class MonitorVisualMap(QWidget):
    """Visual mini-canvas rendering connected monitors and their relative positions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.setStyleSheet("background: #0F172A; border-radius: 8px; border: 1px solid #1E293B;")
        self._monitors: List[MonitorDetails] = []

    def set_monitors(self, monitors: List[MonitorDetails]):
        self._monitors = monitors
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self._monitors:
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignCenter, "لا توجد شاشات مكتشفة")
            return

        w = self.width()
        h = self.height()
        count = len(self._monitors)
        box_w = min(140, int((w - 40) / max(1, count) - 15))
        box_h = 75

        start_x = int((w - (count * box_w + (count - 1) * 15)) / 2)
        y = int((h - box_h) / 2)

        for i, mon in enumerate(self._monitors):
            x = start_x + i * (box_w + 15)

            # Draw monitor box
            fill_color = QColor("#1E293B") if not mon.is_primary else QColor("#0284C7")
            painter.setBrush(fill_color)
            painter.setPen(QPen(QColor("#38BDF8") if mon.is_primary else QColor("#334155"), 2))
            painter.drawRoundedRect(x, y, box_w, box_h, 6, 6)

            # Draw monitor stand
            painter.setBrush(QColor("#475569"))
            painter.setPen(Qt.NoPen)
            painter.drawRect(x + box_w // 2 - 8, y + box_h, 16, 10)
            painter.drawRoundedRect(x + box_w // 2 - 20, y + box_h + 8, 40, 4, 2, 2)

            # Draw text
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(x, y + 22, box_w, 20, Qt.AlignCenter, f"شاشة {mon.display_index}")

            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(x, y + 42, box_w, 16, Qt.AlignCenter, mon.resolution)

            if mon.is_primary:
                painter.setPen(QColor("#FEF08A"))
                painter.drawText(x, y + 56, box_w, 14, Qt.AlignCenter, "(الأساسية)")


class DisplaysSubpage(QWidget):
    """Subpage for viewing connected displays and EDID specifications."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._monitors: List[MonitorDetails] = []
        self._init_ui()
        self.refresh_monitors()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)

        # Header
        top_bar = QHBoxLayout()
        title = QLabel("الشاشات ومواصفات العرض (Displays & EDID)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.refresh_btn = QPushButton("  تحديث")
        self.refresh_btn.setIcon(get_icon("devices", "#FFFFFF", 16))
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #334155; color: #F8FAFC; border-radius: 6px;
                padding: 0 14px; font-weight: bold; border: 1px solid #475569;
            }
            QPushButton:hover { background: #475569; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_monitors)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Visual Arrangement Canvas Card
        map_card = QFrame()
        map_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        m_layout = QVBoxLayout(map_card)
        m_layout.setSpacing(12)

        m_title = QLabel("مخطط الشاشات المتصلة (Display Arrangement)")
        m_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        m_title.setStyleSheet("color: #38BDF8; background: transparent;")
        m_layout.addWidget(m_title)

        self.visual_map = MonitorVisualMap()
        m_layout.addWidget(self.visual_map)
        layout.addWidget(map_card)

        # 2. Detailed Displays Table
        table_card = QFrame()
        table_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 16px;")
        t_layout = QVBoxLayout(table_card)
        t_layout.setSpacing(12)

        t_title = QLabel("المواصفات الفنية للوحات العرض (EDID Parameters)")
        t_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t_title.setStyleSheet("color: #F8FAFC; background: transparent;")
        t_layout.addWidget(t_title)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "الشاشة", "الاسم واللوحة (EDID)", "الدقة", "التردد", "التحجيم (DPI)", "الاتجاه", "سنة الصنع", "الرقم التسلسلي"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0F172A;
                border: 1px solid #334155;
                gridline-color: #1E293B;
                color: #F8FAFC;
                border-radius: 6px;
            }
            QHeaderView::section {
                background: #1E293B;
                color: #CBD5E1;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #334155;
            }
        """)
        self.table.setFixedHeight(180)
        t_layout.addWidget(self.table)
        layout.addWidget(table_card)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def refresh_monitors(self):
        try:
            self._monitors = DisplayService.get_monitors()
            self._render()
        except Exception:
            pass

    def _render(self):
        self.visual_map.set_monitors(self._monitors)
        self.table.setRowCount(len(self._monitors))

        for r, m in enumerate(self._monitors):
            prim_tag = " [أساسية]" if m.is_primary else ""
            self.table.setItem(r, 0, QTableWidgetItem(f"شاشة {m.display_index}{prim_tag}"))
            self.table.setItem(r, 1, QTableWidgetItem(f"{m.manufacturer} ({m.product_code})"))
            self.table.setItem(r, 2, QTableWidgetItem(m.resolution))
            self.table.setItem(r, 3, QTableWidgetItem(f"{m.refresh_rate_hz:.0f} Hz"))
            self.table.setItem(r, 4, QTableWidgetItem(f"{m.scaling_dpi_percent}%"))
            self.table.setItem(r, 5, QTableWidgetItem(m.orientation))

            yr_str = str(m.manufacture_year) if m.manufacture_year else "غير متوفر"
            self.table.setItem(r, 6, QTableWidgetItem(yr_str))
            self.table.setItem(r, 7, QTableWidgetItem(m.serial_number))
