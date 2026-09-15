# -*- coding: utf-8 -*-
"""
SINAX Physical Storage Subpage (صفحة وسائط التخزين الفيزيائية وSMART)
Displays physical NVMe/SSD/HDD disks, SMART wear indicators, temperatures,
serial privacy masking toggle, and safe read-only sequential speed benchmark.
"""

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.hardware_models import StorageDeviceInfo
from app.services.devices.storage_hardware_service import StorageHardwareService
from app.ui.icons import get_icon
from app.ui.design_system import (
    ModernCard,
    MetricCard,
    PrimaryButton,
    SecondaryButton,
    SmoothScrollArea,
    ThemeTokens,
)


class StorageSubpage(QWidget):
    """Subpage for physical disk inspection, SMART status, and safe throughput testing."""

    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._disks: List[StorageDeviceInfo] = []
        self._mask_serials = True
        self._is_testing = False
        self._init_ui()
        self.refresh_disks()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = SmoothScrollArea(self)
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
        title = QLabel("أقراص ووسائط التخزين الفيزيائية (Physical Disks & SMART)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY};")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.mask_checkbox = QCheckBox("إخفاء الأرقام التسلسلية (حماية الخصوصية)")
        self.mask_checkbox.setChecked(True)
        self.mask_checkbox.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; font-size: 11px;")
        self.mask_checkbox.toggled.connect(self._on_mask_toggled)
        top_bar.addWidget(self.mask_checkbox)

        self.refresh_btn = SecondaryButton("تحديث", icon_name="storage")
        self.refresh_btn.clicked.connect(self.refresh_disks)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Physical Disks Table
        table_card = ModernCard(
            title="الأقراص المثبتة وسلامة SMART",
            subtitle="الحالة الصحية، درجات الحرارة، واستهلاك العمر الافتراضي"
        )

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "طراز القرص (Model)", "النوع والناقل", "السعة", "الحالة الصحية",
            "الحرارة", "استهلاك العمر (Wear)", "ساعات العمل", "الرقم التسلسلي"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(180)
        table_card.add_widget(self.table)
        layout.addWidget(table_card)

        # 2. Safe Sequential Read Throughput Test Tool
        bench_card = ModernCard(
            title="فحص سرعة القراءة المتتابعة الآمن (Sequential Read Check)",
            subtitle="فحص قراءة آمن (Read-Only) بدون أي كتابة لاختبار أداء القرص وذاكرة الفلاش"
        )

        b_desc = QLabel(
            "يقوم هذا الفحص باختبار سرعة القراءة المتتابعة للقرص الأساسي بشكل آمن (Read-Only) "
            "بدون كتابة أي بايت على القرص لحماية سلامة بياناتك وذاكرة الفلاش."
        )
        b_desc.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; background: transparent; line-height: 1.4;")
        b_desc.setWordWrap(True)
        bench_card.add_widget(b_desc)

        bench_ctrl = QHBoxLayout()
        self.btn_run_bench = PrimaryButton("  بدء فحص سرعة القراءة", icon_name="play")
        self.btn_run_bench.clicked.connect(self._run_bench)
        bench_ctrl.addWidget(self.btn_run_bench)

        self.bench_res_lbl = QLabel("")
        self.bench_res_lbl.setStyleSheet(f"color: {ThemeTokens.ACCENT_LIGHT}; font-weight: bold; font-size: 13px; background: transparent;")
        bench_ctrl.addWidget(self.bench_res_lbl)
        bench_ctrl.addStretch()

        bench_card.add_layout(bench_ctrl)
        layout.addWidget(bench_card)

        # 3. System & Storage Link Card
        link_card = ModernCard()
        link_layout = QHBoxLayout()
        link_layout.setContentsMargins(14, 10, 14, 10)

        link_text = QLabel(
            "هل ترغب في تحليل مساحات الأقسام وتنظيف الملفات المؤقتة والملفات المكررة؟"
        )
        link_text.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY}; font-weight: 500; background: transparent;")
        link_layout.addWidget(link_text)
        link_layout.addStretch()

        btn_go_storage = SecondaryButton("الانتقال إلى قسم النظام والتخزين", icon_name="storage")
        btn_go_storage.clicked.connect(lambda: self.navigate_requested.emit("system_storage"))
        link_layout.addWidget(btn_go_storage)
        link_card.add_layout(link_layout)
        layout.addWidget(link_card)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def refresh_disks(self):
        try:
            self._disks = StorageHardwareService.get_physical_disks(mask_serial=self._mask_serials)
            self._render_disks()
        except Exception:
            pass

    def _on_mask_toggled(self, checked: bool):
        self._mask_serials = checked
        self.refresh_disks()

    def _render_disks(self):
        self.table.setRowCount(len(self._disks))
        for r, d in enumerate(self._disks):
            self.table.setItem(r, 0, QTableWidgetItem(d.model))
            self.table.setItem(r, 1, QTableWidgetItem(f"{d.media_type_ar} ({d.bus_type})"))
            self.table.setItem(r, 2, QTableWidgetItem(d.capacity_formatted))

            item_health = QTableWidgetItem(d.health_status_ar)
            if "سليم" in d.health_status_ar or "جيدة" in d.health_status_ar or "Healthy" in d.health_status_ar:
                item_health.setForeground(Qt.green)
            self.table.setItem(r, 3, item_health)

            temp_str = f"{d.temperature_c}°C" if d.temperature_c is not None else "غير متوفرة"
            self.table.setItem(r, 4, QTableWidgetItem(temp_str))

            wear_str = f"{d.wear_percentage}%" if d.wear_percentage is not None else "غير متوفر"
            self.table.setItem(r, 5, QTableWidgetItem(wear_str))

            hrs_str = f"{d.power_on_hours:,} س" if d.power_on_hours is not None else "غير متوفر"
            self.table.setItem(r, 6, QTableWidgetItem(hrs_str))

            self.table.setItem(r, 7, QTableWidgetItem(d.serial_number))

    def _run_bench(self):
        if self._is_testing:
            return
        self._is_testing = True
        self.btn_run_bench.setEnabled(False)
        self.bench_res_lbl.setText("جاري اختبار سرعة القراءة المتتابعة...")

        # In-process or fast call
        import threading

        def worker():
            res = StorageHardwareService.run_sequential_read_test("C:", duration_sec=3)

            def done():
                self._is_testing = False
                self.btn_run_bench.setEnabled(True)
                if res.get("passed"):
                    self.bench_res_lbl.setText(f"✓ سرعة القراءة: {res.get('speed_mb_s', 0):.1f} MB/s (C:)")
                else:
                    self.bench_res_lbl.setText(f"خطأ: {res.get('error', 'تعذر القياس')}")

            from PySide6.QtCore import QMetaObject, Qt, Q_ARG
            # Run on UI thread
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, done)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
