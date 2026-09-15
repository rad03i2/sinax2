# -*- coding: utf-8 -*-
"""
SINAX Sensors & Thermals Subpage (صفحة الحساسات ودرجات الحرارة)
Displays live sensor telemetry (CPU, GPU, Storage, Motherboard),
active sensor provider badge, min/max session tracking, and an honest
transparency note on Windows sensor limitations.
"""

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
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

from app.services.devices.hardware_models import SensorItem
from app.services.devices.sensor_service import SensorService
from app.ui.icons import get_icon


class SensorsSubpage(QWidget):
    """Subpage for hardware telemetry, thermal readings, fans, and voltages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._sensors: List[SensorItem] = []
        self._timer: Optional[QTimer] = None
        self._init_ui()
        self.refresh_sensors()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_sensors)
        self._timer.start(2500)

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
        title = QLabel("الحساسات ودرجات الحرارة (Sensors & Thermals)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.lbl_provider_badge = QLabel("المزود: جاري الفحص")
        self.lbl_provider_badge.setStyleSheet("""
            background: #1E293B; color: #38BDF8; border: 1px solid #334155;
            border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: bold;
        """)
        top_bar.addWidget(self.lbl_provider_badge)

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
        self.refresh_btn.clicked.connect(self.refresh_sensors)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Sensors Table
        table_card = QFrame()
        table_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 16px;")
        t_layout = QVBoxLayout(table_card)
        t_layout.setSpacing(12)

        t_title = QLabel("قراءات الحساسات اللحظية وسجل الجلسة")
        t_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t_title.setStyleSheet("color: #F8FAFC; background: transparent;")
        t_layout.addWidget(t_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "الحساس / المكون", "التصنيف", "القراءة الحالية", "أدنى قراءة (Min)", "أعلى قراءة (Max)", "المصدر"
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
        self.table.setFixedHeight(280)
        t_layout.addWidget(self.table)
        layout.addWidget(table_card)

        # 2. Honest Transparency Disclaimer Card
        info_card = QFrame()
        info_card.setStyleSheet("background: #0F172A; border: 1px solid #1E293B; border-radius: 10px; padding: 16px;")
        info_layout = QHBoxLayout(info_card)
        info_icon = QLabel()
        info_icon.setPixmap(get_icon("info", "#38BDF8", 24).pixmap(24, 24))
        info_layout.addWidget(info_icon)

        info_text = QLabel(
            "<b>الشفافية الهندسية:</b> نظام Windows القياسي يتيح قراءة درجات حرارة وحدات التخزين (NVMe/SSD SMART) "
            "وكروت الشاشة المنفصلة (NVIDIA/AMD) مباشرة عبر واجهاتها الرسمية دون الحاجة لصلاحيات خاصة. "
            "أما حساسات أنوية المعالج (CPU Digital Thermal Sensors) ومراوح اللوحة الأم، فتحتاج أمنيًا "
            "إلى تعريفات منخفضة المستوى (Ring-0 Kernel Drivers) يمتنع SINAX عن تثبيتها التزامًا بالأمان واستقرار النظام. "
            "وعليه نلتزم بعرض القيم الحقيقية المتوفرة فقط بدون أي درجات حرارة وهمية أو مصطنعة."
        )
        info_text.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.5; background: transparent;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text, 1)
        layout.addWidget(info_card)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def refresh_sensors(self):
        try:
            self._sensors = SensorService.get_all_sensors()
            provider_name = SensorService.get_active_provider_name()
            self.lbl_provider_badge.setText(f"المزود: {provider_name}")
            self._render()
        except Exception:
            pass

    def _render(self):
        self.table.setRowCount(len(self._sensors))
        for r, s in enumerate(self._sensors):
            self.table.setItem(r, 0, QTableWidgetItem(s.name))
            self.table.setItem(r, 1, QTableWidgetItem(s.category))

            val_item = QTableWidgetItem(s.value_str)
            val_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            if s.status == "critical":
                val_item.setForeground(Qt.red)
            elif s.status == "warning":
                val_item.setForeground(Qt.yellow)
            else:
                val_item.setForeground(Qt.cyan)
            self.table.setItem(r, 2, val_item)

            min_str = f"{s.min_session_value:.0f} {s.unit}" if s.min_session_value is not None else "—"
            max_str = f"{s.max_session_value:.0f} {s.unit}" if s.max_session_value is not None else "—"
            self.table.setItem(r, 3, QTableWidgetItem(min_str))
            self.table.setItem(r, 4, QTableWidgetItem(max_str))
            self.table.setItem(r, 5, QTableWidgetItem(s.source_provider))
