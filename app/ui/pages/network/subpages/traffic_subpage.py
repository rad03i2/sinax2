# -*- coding: utf-8 -*-
"""
SINAX Traffic & Bandwidth Subpage (صفحة استهلاك الإنترنت وحركة البيانات)
Visualizes live bandwidth speeds, session peak rates, and total consumption per network interface.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.network.traffic_service import TrafficService
from app.ui.icons import get_icon


class TrafficSubpage(QWidget):
    """Subpage for bandwidth monitoring and data usage breakdown."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_traffic)
        self._timer.start()

        self._refresh_traffic()

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
        layout.setSpacing(16)

        # 1. Header
        title = QLabel("مراقبة حركة واستهلاك الإنترنت (Traffic & Bandwidth)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        layout.addWidget(title)

        # 2. Live Speed Cards Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        def make_card(title: str, color: str):
            f = QFrame()
            f.setStyleSheet(f"""
                QFrame {{
                    background: #1E293B;
                    border: 1px solid #334155;
                    border-top: 3px solid {color};
                    border-radius: 8px;
                    padding: 14px;
                }}
            """)
            vl = QVBoxLayout(f)
            vl.setSpacing(4)
            t = QLabel(title)
            t.setStyleSheet("color: #94A3B8; font-size: 12px;")
            vl.addWidget(t)

            val = QLabel("0.0 MB/s")
            val.setObjectName("Val")
            val.setFont(QFont("Segoe UI", 20, QFont.Bold))
            val.setStyleSheet("color: #FFFFFF;")
            vl.addWidget(val)

            sub = QLabel("0.0 Mbps")
            sub.setObjectName("Sub")
            sub.setStyleSheet("color: #64748B; font-size: 12px;")
            vl.addWidget(sub)
            return f

        self.c_down = make_card("سرعة التنزيل الحالية (Download)", "#38BDF8")
        self.c_up = make_card("سرعة الرفع الحالية (Upload)", "#A855F7")
        self.c_down_peak = make_card("أعلى سرعة تنزيل بالجلسة (Peak)", "#10B981")
        self.c_up_peak = make_card("أعلى سرعة رفع بالجلسة (Peak)", "#F59E0B")

        grid.addWidget(self.c_down, 0, 0)
        grid.addWidget(self.c_up, 0, 1)
        grid.addWidget(self.c_down_peak, 1, 0)
        grid.addWidget(self.c_up_peak, 1, 1)
        layout.addLayout(grid)

        # 3. Adapter Consumption Table
        sec_title = QLabel("إجمالي استهلاك البيانات لكل كرت شبكة:")
        sec_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        sec_title.setStyleSheet("color: #E2E8F0; margin-top: 8px;")
        layout.addWidget(sec_title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "اسم المحول (Interface)", "البيانات المستلمة (GB)", "البيانات المرسلة (GB)", "إجمالي الاستهلاك (GB)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(220)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #FFFFFF;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background: #0F172A;
                color: #94A3B8;
                border: none;
                padding: 6px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _refresh_traffic(self):
        metrics = TrafficService.sample_live_bandwidth()

        # Update download
        d_val = self.c_down.findChild(QLabel, "Val")
        d_sub = self.c_down.findChild(QLabel, "Sub")
        if d_val and d_sub:
            d_val.setText(f"{metrics['download_mb_s']:.2f} MB/s")
            d_sub.setText(f"{metrics['download_mbps']:.1f} Mbps")

        # Update upload
        u_val = self.c_up.findChild(QLabel, "Val")
        u_sub = self.c_up.findChild(QLabel, "Sub")
        if u_val and u_sub:
            u_val.setText(f"{metrics['upload_mb_s']:.2f} MB/s")
            u_sub.setText(f"{metrics['upload_mbps']:.1f} Mbps")

        # Update peaks
        dp_val = self.c_down_peak.findChild(QLabel, "Val")
        if dp_val:
            dp_val.setText(f"{metrics['peak_download_mbps'] / 8.0:.2f} MB/s")

        up_val = self.c_up_peak.findChild(QLabel, "Val")
        if up_val:
            up_val.setText(f"{metrics['peak_upload_mbps'] / 8.0:.2f} MB/s")

        # Update adapters table
        per_nic = TrafficService.get_per_adapter_consumption()
        self.table.setRowCount(len(per_nic))
        for row, (nic, vals) in enumerate(per_nic.items()):
            self.table.setItem(row, 0, QTableWidgetItem(nic))
            self.table.setItem(row, 1, QTableWidgetItem(f"{vals['recv_gb']:.2f} GB"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{vals['sent_gb']:.2f} GB"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{vals['total_gb']:.2f} GB"))
