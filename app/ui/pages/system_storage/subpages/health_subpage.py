# -*- coding: utf-8 -*-
"""
SINAX System & Storage - Drive Health & S.M.A.R.T. Subpage (صحة الأقراص)
Provides hardware disk specifications, S.M.A.R.T. reliability indicators,
and live I/O activity rates with honest, non-fabricated metrics.
"""

from typing import List, Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.system_storage.disk_health_service import (
    DiskHealthService,
    LogicalDriveInfo,
    PhysicalDiskInfo,
)
from app.services.system_storage.storage_scanner import format_bytes
from app.ui.icons import get_icon


class DiskCard(QFrame):
    """Card displaying a physical disk's hardware specs and S.M.A.R.T. indicators."""

    def __init__(self, disk: PhysicalDiskInfo, parent=None):
        super().__init__(parent)
        self.disk = disk
        self.setStyleSheet("""
            QFrame {
                background: #161B22; border: 1px solid #30363D;
                border-radius: 12px; padding: 16px;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header: Icon + Name + Health Status Badge
        header = QHBoxLayout()
        header.setSpacing(12)

        ico = QLabel()
        ico.setPixmap(get_icon("storage", color="#58A6FF").pixmap(28, 28))
        header.addWidget(ico)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl_name = QLabel(self.disk.name)
        lbl_name.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_name.setStyleSheet("color: #F0F6FC;")
        lbl_sub = QLabel(f"{self.disk.media_type_ar} ({self.disk.bus_type}) - السعة: {self.disk.size_formatted}")
        lbl_sub.setStyleSheet("color: #8B949E; font-size: 11px;")
        title_col.addWidget(lbl_name)
        title_col.addWidget(lbl_sub)
        header.addLayout(title_col, 1)

        # Health Badge
        badge_text = self.disk.health_status_ar
        is_healthy = self.disk.health_status.lower() == "healthy"
        badge_bg = "rgba(63, 185, 80, 0.15)" if is_healthy else "rgba(248, 81, 73, 0.15)"
        badge_fg = "#3FB950" if is_healthy else "#F85149"
        badge_border = "rgba(63, 185, 80, 0.3)" if is_healthy else "rgba(248, 81, 73, 0.3)"

        badge = QLabel(badge_text)
        badge.setStyleSheet(f"""
            background: {badge_bg}; color: {badge_fg};
            border: 1px solid {badge_border}; border-radius: 6px;
            padding: 4px 12px; font-weight: bold; font-size: 11px;
        """)
        header.addWidget(badge)
        layout.addLayout(header)

        # Grid of SMART metrics
        grid = QGridLayout()
        grid.setSpacing(10)

        # Temp
        temp_str = f"{self.disk.temperature_celsius} °C" if self.disk.temperature_celsius is not None else "غير متوفرة"
        grid.addWidget(self._make_stat_box("درجة الحرارة", temp_str, "#F4A261" if self.disk.temperature_celsius else "#8B949E"), 0, 0)

        # Wear
        wear_str = f"{self.disk.wear_percentage}%" if self.disk.wear_percentage is not None else "غير متوفرة"
        grid.addWidget(self._make_stat_box("نسبة الاهتراء (Wear)", wear_str, "#58A6FF" if self.disk.wear_percentage is not None else "#8B949E"), 0, 1)

        # Power on hours
        hours_str = f"{self.disk.power_on_hours:,} ساعة" if self.disk.power_on_hours is not None else "غير متوفرة"
        grid.addWidget(self._make_stat_box("ساعات التشغيل الكلية", hours_str, "#C9D1D9"), 0, 2)

        # Read/Write errors
        err_str = "0"
        if self.disk.read_errors_total is not None or self.disk.write_errors_total is not None:
            r = self.disk.read_errors_total or 0
            w = self.disk.write_errors_total or 0
            err_str = f"قراءة: {r} / كتابة: {w}"
        grid.addWidget(self._make_stat_box("أخطاء القراءة/الكتابة", err_str, "#3FB950" if err_str == "0" else "#F85149"), 0, 3)

        layout.addLayout(grid)

        # Footer note if smart unavailable
        if not self.disk.smart_available:
            note = QLabel(self.disk.smart_note_ar or "مؤشرات S.M.A.R.T. التفصيلية تتطلب تشغيل البرنامج بصلاحيات مسؤول.")
            note.setStyleSheet("color: #8B949E; font-size: 11px; padding: 4px;")
            layout.addWidget(note)

    def _make_stat_box(self, label: str, val: str, color: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet("background: #0D1117; border: 1px solid #21262D; border-radius: 8px; padding: 8px;")
        l = QVBoxLayout(f)
        l.setContentsMargins(8, 6, 8, 6)
        l.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8B949E; font-size: 10px;")
        v = QLabel(val)
        v.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
        l.addWidget(lbl)
        l.addWidget(v)
        return f


class HealthSubpage(QWidget):
    """Subpage displaying physical disks health and real-time disk transfer speeds."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_health()

        # Real-time disk I/O update timer (every 1.5 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_io_rate)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Top Bar: Real-time IO speed & Refresh
        top_bar = QFrame()
        top_bar.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(16, 10, 16, 10)
        tb_lay.setSpacing(16)

        self.lbl_read = QLabel("القراءة الحالية: 0.0 MB/s")
        self.lbl_read.setStyleSheet("color: #58A6FF; font-size: 13px; font-weight: bold;")
        tb_lay.addWidget(self.lbl_read)

        self.lbl_write = QLabel("الكتابة الحالية: 0.0 MB/s")
        self.lbl_write.setStyleSheet("color: #3FB950; font-size: 13px; font-weight: bold;")
        tb_lay.addWidget(self.lbl_write)

        tb_lay.addStretch(1)

        btn_refresh = QPushButton("تحديث البيانات")
        btn_refresh.setIcon(get_icon("storage", color="#F0F6FC"))
        btn_refresh.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        btn_refresh.clicked.connect(self.refresh_health)
        tb_lay.addWidget(btn_refresh)

        main_layout.addWidget(top_bar)

        # Scroll area for physical disks cards
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(14)
        self.cards_layout.addStretch(1)

        scroll.setWidget(self.cards_widget)
        main_layout.addWidget(scroll, 1)

    def refresh_health(self):
        # Clear existing cards
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        disks = DiskHealthService.get_physical_disks()
        for idx, d in enumerate(disks):
            card = DiskCard(d, self)
            self.cards_layout.insertWidget(idx, card)

    def _update_io_rate(self):
        rates = DiskHealthService.get_live_io_rates()
        r_mb = rates.get("read_mb_s", 0.0)
        w_mb = rates.get("write_mb_s", 0.0)
        self.lbl_read.setText(f"القراءة الحالية: {r_mb:.1f} MB/s")
        self.lbl_write.setText(f"الكتابة الحالية: {w_mb:.1f} MB/s")

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "timer") and not self.timer.isActive():
            self.timer.start(1500)
            self._update_io_rate()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
