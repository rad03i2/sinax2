# -*- coding: utf-8 -*-
"""
SINAX LAN Devices Subpage (صفحة الأجهزة المحلية على الشبكة)
Discovers devices via Windows Neighbor Cache and light subnet sweep,
displays MAC vendors, First/Last Seen dates, and opens router gateway page.
"""

from typing import List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.network.lan_discovery_service import LanDevice, LanDiscoveryService
from app.ui.icons import get_icon


class LanScanWorker(QObject):
    """Background worker for subnet sweep without GUI lag."""
    progress = Signal(float, str)
    finished = Signal(list)

    def __init__(self, active_scan: bool = False):
        super().__init__()
        self.active_scan = active_scan
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if self.active_scan:
            devs = LanDiscoveryService.scan_local_subnet(
                progress_cb=lambda r, m: self.progress.emit(r, m),
                is_cancelled=lambda: self._cancelled
            )
        else:
            devs = LanDiscoveryService.get_neighbor_devices()
        self.finished.emit(devs)


class LanDevicesSubpage(QWidget):
    """Subpage for viewing and managing LAN devices."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._thread: Optional[QThread] = None
        self._worker: Optional[LanScanWorker] = None
        self._init_ui()
        self.refresh_devices(active=False)

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

        # 1. Header Toolbar
        top_bar = QHBoxLayout()
        title = QLabel("الأجهزة المتصلة بالشبكة المحلية (LAN Devices)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.scan_btn = QPushButton("  فحص موسع للشبكة")
        self.scan_btn.setIcon(get_icon("devices", "#FFFFFF", 16))
        self.scan_btn.setFixedHeight(36)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background: #0078D4;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 0 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #106EBE; }
            QPushButton:disabled { background: #334155; color: #64748B; }
        """)
        self.scan_btn.clicked.connect(lambda: self.refresh_devices(active=True))
        top_bar.addWidget(self.scan_btn)

        self.router_btn = QPushButton("  فتح صفحة الراوتر")
        self.router_btn.setIcon(get_icon("network", "#FFFFFF", 16))
        self.router_btn.setFixedHeight(36)
        self.router_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                border: 1px solid #334155;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 500;
            }
            QPushButton:hover { background: #2D3748; border-color: #0078D4; }
        """)
        self.router_btn.clicked.connect(self._open_router)
        top_bar.addWidget(self.router_btn)

        layout.addLayout(top_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #1E293B; border-radius: 2px; }
            QProgressBar::chunk { background: #0078D4; border-radius: 2px; }
        """)
        layout.addWidget(self.progress_bar)

        # 2. Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        def make_stat_card(title: str, val_str: str, col: str):
            f = QFrame()
            f.setStyleSheet(f"""
                QFrame {{
                    background: #1E293B;
                    border: 1px solid #334155;
                    border-top: 3px solid {col};
                    border-radius: 8px;
                    padding: 10px 14px;
                }}
            """)
            vl = QVBoxLayout(f)
            vl.setSpacing(2)
            t = QLabel(title)
            t.setStyleSheet("color: #94A3B8; font-size: 12px;")
            vl.addWidget(t)
            v = QLabel(val_str)
            v.setObjectName("Val")
            v.setFont(QFont("Segoe UI", 16, QFont.Bold))
            v.setStyleSheet("color: #FFFFFF;")
            vl.addWidget(v)
            return f

        self.card_total = make_stat_card("إجمالي الأجهزة المكتشفة", "0", "#0078D4")
        self.card_status = make_stat_card("حالة المسح", "سريع (Cache)", "#10B981")
        stats_row.addWidget(self.card_total)
        stats_row.addWidget(self.card_status)
        layout.addLayout(stats_row)

        # 3. Table of devices
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "عنوان IP", "عنوان MAC العتادي", "الشركة المصنعة / الجهاز", "الحالة", "أول ظهور"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(340)
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

    def refresh_devices(self, active: bool = False):
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("  جاري الفحص...")
        self.progress_bar.setValue(20 if active else 60)

        self._thread = QThread()
        self._worker = LanScanWorker(active_scan=active)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda r, m: self.progress_bar.setValue(int(r * 100)))
        self._worker.finished.connect(self._on_devices_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_devices_loaded(self, devices: List[LanDevice]):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("  فحص موسع للشبكة")
        self.progress_bar.setValue(100)

        tot = self.card_total.findChild(QLabel, "Val")
        if tot:
            tot.setText(str(len(devices)))

        self.table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            self.table.setItem(row, 0, QTableWidgetItem(d.ip_address))
            self.table.setItem(row, 1, QTableWidgetItem(d.mac_address))
            self.table.setItem(row, 2, QTableWidgetItem(d.vendor))
            self.table.setItem(row, 3, QTableWidgetItem(d.state))
            self.table.setItem(row, 4, QTableWidgetItem(d.first_seen))

    def _open_router(self):
        ok = LanDiscoveryService.open_router_page()
        if not ok:
            QMessageBox.warning(self, "تنبيه", "تعذر تحديد عنوان IP لبوابة الراوتر.")
