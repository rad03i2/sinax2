# -*- coding: utf-8 -*-
"""
SINAX System & Storage - Live Performance Subpage (مراقبة الأداء)
Real-time system health and resource consumption monitor:
- 60-second rolling charts for CPU, RAM, and Disk I/O
- Core architecture & clock frequencies
- Top resource consumer tables (CPU & RAM)
"""

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.system_storage.performance_service import PerformanceService, PerformanceSnapshot
from app.services.system_storage.storage_scanner import format_bytes
from app.ui.pages.system_storage.chart_widgets import RollingHistoryChart


class PerformanceSubpage(QWidget):
    """Real-time performance monitoring dashboard."""

    inspect_process_requested = Signal(int)  # Emits PID to inspect in Process tab

    def __init__(self, parent=None):
        super().__init__(parent)
        self.perf_service = PerformanceService(history_len=60)
        self._init_ui()

        # 1-second polling timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._sample_and_update)

        # Initial sample
        self._sample_and_update()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        # 1. Rolling Charts Row (CPU, RAM, Disk)
        charts_row = QHBoxLayout()
        charts_row.setSpacing(12)

        self.chart_cpu = RollingHistoryChart(
            title="استهلاك المعالج (CPU)",
            unit="%",
            line_color="#58A6FF",
            max_val=100.0,
            parent=self
        )
        self.chart_cpu.setFixedHeight(160)
        charts_row.addWidget(self.chart_cpu)

        self.chart_ram = RollingHistoryChart(
            title="استهلاك الذاكرة (RAM)",
            unit="%",
            line_color="#BC8CFF",
            max_val=100.0,
            parent=self
        )
        self.chart_ram.setFixedHeight(160)
        charts_row.addWidget(self.chart_ram)

        self.chart_disk = RollingHistoryChart(
            title="حركة القرص (Disk I/O)",
            unit="MB/s",
            line_color="#3FB950",
            max_val=0.0,  # dynamic scale
            parent=self
        )
        self.chart_disk.setFixedHeight(160)
        charts_row.addWidget(self.chart_disk)

        content_layout.addLayout(charts_row)

        # 2. Key Hardware Spec Badges
        specs_row = QHBoxLayout()
        specs_row.setSpacing(12)

        self.lbl_cpu_specs = QLabel("الأنوية: - | التردد: -")
        self.lbl_cpu_specs.setStyleSheet("color: #8B949E; font-size: 11px; background: #161B22; padding: 8px 12px; border-radius: 6px; border: 1px solid #30363D;")
        specs_row.addWidget(self.lbl_cpu_specs)

        self.lbl_ram_specs = QLabel("الذاكرة: -")
        self.lbl_ram_specs.setStyleSheet("color: #8B949E; font-size: 11px; background: #161B22; padding: 8px 12px; border-radius: 6px; border: 1px solid #30363D;")
        specs_row.addWidget(self.lbl_ram_specs)

        self.lbl_swap_specs = QLabel("ملف التبديل (Swap): -")
        self.lbl_swap_specs.setStyleSheet("color: #8B949E; font-size: 11px; background: #161B22; padding: 8px 12px; border-radius: 6px; border: 1px solid #30363D;")
        specs_row.addWidget(self.lbl_swap_specs)

        content_layout.addLayout(specs_row)

        # 3. Top Resource Consumers Row
        tables_row = QHBoxLayout()
        tables_row.setSpacing(14)

        # Top CPU
        cpu_box = QFrame()
        cpu_box.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 8px;")
        cpu_lay = QVBoxLayout(cpu_box)
        lbl_top_c = QLabel("أعلى العمليات استهلاكاً للمعالج")
        lbl_top_c.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_top_c.setStyleSheet("color: #58A6FF; padding: 4px;")
        cpu_lay.addWidget(lbl_top_c)

        self.table_top_cpu = QTableWidget()
        self.table_top_cpu.setColumnCount(4)
        self.table_top_cpu.setHorizontalHeaderLabels(["PID", "العملية", "المعالج %", "الذاكرة"])
        self.table_top_cpu.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_top_cpu.setStyleSheet("background: transparent; color: #F0F6FC; border: none; font-size: 11px;")
        self.table_top_cpu.setFixedHeight(180)
        cpu_lay.addWidget(self.table_top_cpu)
        tables_row.addWidget(cpu_box)

        # Top RAM
        ram_box = QFrame()
        ram_box.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 8px;")
        ram_lay = QVBoxLayout(ram_box)
        lbl_top_r = QLabel("أعلى العمليات استهلاكاً للذاكرة")
        lbl_top_r.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_top_r.setStyleSheet("color: #BC8CFF; padding: 4px;")
        ram_lay.addWidget(lbl_top_r)

        self.table_top_ram = QTableWidget()
        self.table_top_ram.setColumnCount(4)
        self.table_top_ram.setHorizontalHeaderLabels(["PID", "العملية", "الذاكرة", "النسبة %"])
        self.table_top_ram.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_top_ram.setStyleSheet("background: transparent; color: #F0F6FC; border: none; font-size: 11px;")
        self.table_top_ram.setFixedHeight(180)
        ram_lay.addWidget(self.table_top_ram)
        tables_row.addWidget(ram_box)

        content_layout.addLayout(tables_row)
        content_layout.addStretch(1)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _sample_and_update(self):
        snapshot = self.perf_service.sample()
        history = self.perf_service.get_history()

        # Update charts
        self.chart_cpu.set_data(history["cpu"], snapshot.cpu_percent)
        self.chart_ram.set_data(history["ram"], snapshot.ram_percent)

        tot_io = snapshot.disk_read_mb_s + snapshot.disk_write_mb_s
        io_history = [
            r + w for r, w in zip(history["disk_read"], history["disk_write"])
        ]
        self.chart_disk.set_data(io_history, tot_io)

        # Update spec labels
        self.lbl_cpu_specs.setText(
            f"الأنوية: {snapshot.cpu_cores_physical} فيزيائية / {snapshot.cpu_cores_logical} منطقية | التردد: {snapshot.cpu_freq_current:.0f} MHz"
        )
        self.lbl_ram_specs.setText(
            f"الذاكرة: مستخدم {format_bytes(snapshot.ram_used)} من {format_bytes(snapshot.ram_total)} ({snapshot.ram_percent:.1f}%)"
        )
        self.lbl_swap_specs.setText(
            f"ملف التبديل: مستخدم {format_bytes(snapshot.swap_used)} من {format_bytes(snapshot.swap_total)} ({snapshot.swap_percent:.1f}%)"
        )

        # Populate top CPU table
        self.table_top_cpu.setRowCount(len(snapshot.top_cpu_processes))
        for r, p in enumerate(snapshot.top_cpu_processes):
            self.table_top_cpu.setItem(r, 0, QTableWidgetItem(str(p.pid)))
            self.table_top_cpu.setItem(r, 1, QTableWidgetItem(p.name))
            self.table_top_cpu.setItem(r, 2, QTableWidgetItem(f"{p.cpu_percent:.1f}%"))
            self.table_top_cpu.setItem(r, 3, QTableWidgetItem(p.memory_formatted))

        # Populate top RAM table
        self.table_top_ram.setRowCount(len(snapshot.top_mem_processes))
        for r, p in enumerate(snapshot.top_mem_processes):
            self.table_top_ram.setItem(r, 0, QTableWidgetItem(str(p.pid)))
            self.table_top_ram.setItem(r, 1, QTableWidgetItem(p.name))
            self.table_top_ram.setItem(r, 2, QTableWidgetItem(p.memory_formatted))
            self.table_top_ram.setItem(r, 3, QTableWidgetItem(f"{p.memory_percent:.1f}%"))

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "timer") and not self.timer.isActive():
            self.timer.start(1000)
            self._sample_and_update()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
