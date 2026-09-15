# -*- coding: utf-8 -*-
"""
SINAX Devices & Hardware Dashboard Subpage (لوحة القيادة ونظرة عامة على العتاد)
Hero computer card, real-time core metrics, hardware specifications summary,
and quick hardware action shortcuts.
"""

from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.hardware_models import SystemSummary
from app.services.devices.hardware_report_service import HardwareReportService
from app.ui.icons import get_icon
from app.ui.design_system import (
    ModernCard,
    MetricCard,
    InfoRow,
    StatusBadge,
    PrimaryButton,
    SecondaryButton,
    SmoothScrollArea,
    ThemeTokens,
)


class OverviewWorker(QObject):
    """Background worker for loading system summary."""
    finished = Signal(object)

    def run(self):
        summary = HardwareReportService.get_system_summary()
        self.finished.emit(summary)


class OverviewSubpage(QWidget):
    """Devices & Hardware Center central overview subpage."""

    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._thread: Optional[QThread] = None
        self._worker: Optional[OverviewWorker] = None
        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = SmoothScrollArea(self)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)

        # 1. Header Toolbar
        top_bar = QHBoxLayout()
        title = QLabel("نظرة عامة على عتاد الجهاز ومواصفاته")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY};")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.refresh_btn = PrimaryButton("تحديث البيانات", "devices")
        self.refresh_btn.clicked.connect(self.refresh_data)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 2. Hero ModernCard: "هذا الكمبيوتر"
        self.hero_card = ModernCard()
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(16)

        hero_top = QHBoxLayout()
        self.lbl_device_title = QLabel("جاري فحص مواصفات الجهاز...")
        self.lbl_device_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.lbl_device_title.setStyleSheet(f"color: {ThemeTokens.ACCENT_LIGHT};")
        hero_top.addWidget(self.lbl_device_title)
        hero_top.addStretch()

        self.lbl_device_type = StatusBadge("نوع الجهاز", "info")
        hero_top.addWidget(self.lbl_device_type)
        hero_layout.addLayout(hero_top)

        # Specs grid inside hero card using borderless InfoRows
        specs_grid = QGridLayout()
        specs_grid.setHorizontalSpacing(24)
        specs_grid.setVerticalSpacing(8)

        self.row_os = InfoRow("نظام التشغيل", "جاري القراءة...", "windows")
        self.row_cpu = InfoRow("المعالج", "جاري القراءة...", "performance")
        self.row_ram = InfoRow("الذاكرة (RAM)", "جاري القراءة...", "storage")
        self.row_gpu = InfoRow("كرت الشاشة", "جاري القراءة...", "chart")
        self.row_storage = InfoRow("التخزين الأساسي", "جاري القراءة...", "storage")
        self.row_board = InfoRow("اللوحة والـ BIOS", "جاري القراءة...", "devices")

        specs_grid.addWidget(self.row_os, 0, 0)
        specs_grid.addWidget(self.row_cpu, 0, 1)
        specs_grid.addWidget(self.row_ram, 1, 0)
        specs_grid.addWidget(self.row_gpu, 1, 1)
        specs_grid.addWidget(self.row_storage, 2, 0)
        specs_grid.addWidget(self.row_board, 2, 1)
        hero_layout.addLayout(specs_grid)

        layout.addWidget(self.hero_card)

        # 3. Core Metric Cards Row
        tiles_layout = QHBoxLayout()
        tiles_layout.setSpacing(12)

        self.tile_cpu = MetricCard("المعالج (CPU)", "—", "اسم المعالج", "performance", ThemeTokens.ACCENT_LIGHT)
        self.tile_ram = MetricCard("الذاكرة (RAM)", "—", "السعة الإجمالية", "storage", ThemeTokens.SUCCESS)
        self.tile_storage = MetricCard("حالة التخزين", "سليم ✓", "الأقراص الموصلة", "storage", "#818CF8")
        self.tile_battery = MetricCard("البطارية والطاقة", "—", "مصدر الطاقة", "startup", ThemeTokens.WARNING)
        self.tile_temp = MetricCard("حرارة المعالج", "غير متوفرة", "قراءات الحساسات", "doctor", "#F472B6")

        tiles_layout.addWidget(self.tile_cpu)
        tiles_layout.addWidget(self.tile_ram)
        tiles_layout.addWidget(self.tile_storage)
        tiles_layout.addWidget(self.tile_battery)
        tiles_layout.addWidget(self.tile_temp)
        layout.addLayout(tiles_layout)

        # 4. Quick Actions Row
        actions_title = QLabel("الانتقال السريع إلى أقسام العتاد")
        actions_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        actions_title.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY}; margin-top: 10px;")
        layout.addWidget(actions_title)

        act_layout = QHBoxLayout()
        act_layout.setSpacing(12)

        def make_btn(text: str, icon_name: str, target: str):
            btn = SecondaryButton(text, icon_name)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda: self.navigate_requested.emit(target))
            return btn

        act_layout.addWidget(make_btn("تفاصيل المعالج والضغط", "performance", "cpu"))
        act_layout.addWidget(make_btn("كرت الشاشة وVRAM", "chart", "gpu"))
        act_layout.addWidget(make_btn("الذاكرة ومنافذ الرام", "storage", "ram"))
        act_layout.addWidget(make_btn("الفحص السريع للجهاز", "speedtest", "quick_check"))
        act_layout.addWidget(make_btn("تصدير تقرير العتاد", "backup", "reports"))
        layout.addLayout(act_layout)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def refresh_data(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("  جاري القراءة...")

        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

        self._thread = QThread()
        self._worker = OverviewWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_summary_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_summary_loaded(self, s: SystemSummary):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  تحديث البيانات")

        # Hero Card updates
        brand_model = f"{s.manufacturer} {s.model}".strip()
        self.lbl_device_title.setText(brand_model if brand_model else "جهاز كمبيوتر شخصي")
        self.lbl_device_type.set_status("info", s.device_type)

        self.row_os.set_value(f"{s.os_name} ({s.os_arch}) - Build {s.os_build}")
        self.row_cpu.set_value(s.cpu_name)
        self.row_ram.set_value(s.ram_summary)
        self.row_gpu.set_value(s.primary_gpu)
        self.row_storage.set_value(s.primary_storage)
        self.row_board.set_value(f"{s.motherboard} | BIOS: {s.bios_version}")

        # Tile updates
        self.tile_cpu.set_value(s.cpu_name[:22] + ("..." if len(s.cpu_name) > 22 else ""))
        self.tile_ram.set_value(f"{s.ram_total_gb} GB")
        if s.has_battery and s.battery_percent is not None:
            self.tile_battery.set_value(f"{s.battery_percent}%", s.battery_status_ar)
        else:
            self.tile_battery.set_value("تيار مباشر", "موصول بالشاحن")

        temp_str = f"{s.cpu_temp_c:.0f}°C" if s.cpu_temp_c is not None else "غير متوفرة"
        self.tile_temp.set_value(temp_str)

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(500)
        super().closeEvent(event)


