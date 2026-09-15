# -*- coding: utf-8 -*-
"""
SINAX Wi-Fi Center Subpage (صفحة مركز ومحلل شبكات Wi-Fi)
Displays connected Wi-Fi parameters, signal meter, channel congestion analyzer,
nearby networks table, and technical Wi-Fi report exporter.
"""

from typing import List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
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

from app.services.network.network_models import NearbyWifiNetwork, WifiConnectionInfo
from app.services.network.wifi_service import WifiService
from app.ui.icons import get_icon


class WifiScanWorker(QObject):
    """Background worker for scanning Wi-Fi networks and channels."""
    finished = Signal(object, list, dict)

    def run(self):
        curr = WifiService.get_current_wifi_info()
        nets = WifiService.scan_nearby_networks()
        analysis = WifiService.analyze_channels(nets)
        self.finished.emit(curr, nets, analysis)


class WifiSubpage(QWidget):
    """Subpage for Wi-Fi management and channel analysis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self.refresh_wifi()

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
        title = QLabel("مركز وتحليل شبكات Wi-Fi")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.scan_btn = QPushButton("  مسح وتحديث الشبكات")
        self.scan_btn.setIcon(get_icon("sync", "#FFFFFF", 16))
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
        """)
        self.scan_btn.clicked.connect(self.refresh_wifi)
        top_bar.addWidget(self.scan_btn)

        self.export_btn = QPushButton("  تصدير تقرير Wi-Fi")
        self.export_btn.setIcon(get_icon("file", "#FFFFFF", 16))
        self.export_btn.setFixedHeight(36)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B;
                border: 1px solid #334155;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 500;
            }
            QPushButton:hover { background: #2D3748; }
        """)
        self.export_btn.clicked.connect(self._export_report)
        top_bar.addWidget(self.export_btn)

        layout.addLayout(top_bar)

        # 2. Current Connected Wi-Fi Card
        self.wifi_card = QFrame()
        self.wifi_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 16px;")
        card_l = QVBoxLayout(self.wifi_card)
        card_l.setSpacing(12)

        card_head = QHBoxLayout()
        self.net_name_lbl = QLabel("جاري فحص اتصال Wi-Fi...")
        self.net_name_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.net_name_lbl.setStyleSheet("color: #38BDF8;")
        card_head.addWidget(self.net_name_lbl)
        card_head.addStretch()

        self.band_badge = QLabel("2.4 GHz")
        self.band_badge.setStyleSheet("background: #334155; color: #94A3B8; border-radius: 10px; padding: 4px 12px; font-weight: bold;")
        card_head.addWidget(self.band_badge)
        card_l.addLayout(card_head)

        # Signal Progress Bar
        sig_row = QHBoxLayout()
        sig_t = QLabel("قوة الإشارة اللاسلكية:")
        sig_t.setStyleSheet("color: #94A3B8; font-size: 13px;")
        sig_row.addWidget(sig_t)

        self.sig_bar = QProgressBar()
        self.sig_bar.setFixedHeight(12)
        self.sig_bar.setRange(0, 100)
        self.sig_bar.setValue(0)
        self.sig_bar.setStyleSheet("""
            QProgressBar { background: #0F172A; border-radius: 6px; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #10B981); border-radius: 6px; }
        """)
        sig_row.addWidget(self.sig_bar, 1)

        self.sig_val_lbl = QLabel("0%")
        self.sig_val_lbl.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px;")
        sig_row.addWidget(self.sig_val_lbl)
        card_l.addLayout(sig_row)

        # Details Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(8)

        def make_kv(lbl: str):
            k = QLabel(lbl)
            k.setStyleSheet("color: #94A3B8; font-size: 12px;")
            v = QLabel("—")
            v.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 500;")
            return k, v

        self.k_bssid, self.v_bssid = make_kv("نقطة الوصول (BSSID):")
        self.k_ch, self.v_ch = make_kv("رقم القناة (Channel):")
        self.k_proto, self.v_proto = make_kv("المعيار (Protocol):")
        self.k_sec, self.v_sec = make_kv("التشفير والأمان:")
        self.k_rx, self.v_rx = make_kv("سرعة الاستقبال (Rx Rate):")
        self.k_tx, self.v_tx = make_kv("سرعة الإرسال (Tx Rate):")

        grid.addWidget(self.k_bssid, 0, 0)
        grid.addWidget(self.v_bssid, 0, 1)
        grid.addWidget(self.k_ch, 0, 2)
        grid.addWidget(self.v_ch, 0, 3)

        grid.addWidget(self.k_proto, 1, 0)
        grid.addWidget(self.v_proto, 1, 1)
        grid.addWidget(self.k_sec, 1, 2)
        grid.addWidget(self.v_sec, 1, 3)

        grid.addWidget(self.k_rx, 2, 0)
        grid.addWidget(self.v_rx, 2, 1)
        grid.addWidget(self.k_tx, 2, 2)
        grid.addWidget(self.v_tx, 2, 3)

        card_l.addLayout(grid)
        layout.addWidget(self.wifi_card)

        # 3. Channel Congestion Card
        self.channel_card = QFrame()
        self.channel_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 16px;")
        ch_layout = QVBoxLayout(self.channel_card)
        ch_layout.setSpacing(10)

        ch_title = QLabel("تحليل ازدحام القنوات وتوصيات التحسين:")
        ch_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        ch_title.setStyleSheet("color: #F8FAFC;")
        ch_layout.addWidget(ch_title)

        self.recom_lbl = QLabel("جاري تحليل توزيع الشبكات على القنوات...")
        self.recom_lbl.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.5;")
        self.recom_lbl.setWordWrap(True)
        ch_layout.addWidget(self.recom_lbl)

        layout.addWidget(self.channel_card)

        # 4. Nearby Visible Networks Table
        table_title = QLabel("الشبكات اللاسلكية المرئية القريبة:")
        table_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        table_title.setStyleSheet("color: #E2E8F0; margin-top: 6px;")
        layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "اسم الشبكة (SSID)", "قوة الإشارة", "القناة", "التردد", "الأمان والتشفير", "المعيار"
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

    def refresh_wifi(self):
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("  جاري المسح...")

        self._thread = QThread()
        self._worker = WifiScanWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_scan_finished(self, curr: Optional[WifiConnectionInfo], nets: List[NearbyWifiNetwork], analysis: dict):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("  مسح وتحديث الشبكات")

        if curr and curr.ssid:
            self.net_name_lbl.setText(f"متصل بالشبكة: {curr.ssid}")
            self.band_badge.setText(curr.band_ghz)
            self.sig_bar.setValue(curr.signal_quality_percent)
            self.sig_val_lbl.setText(f"{curr.signal_quality_percent}%")

            self.v_bssid.setText(curr.bssid or "—")
            self.v_ch.setText(str(curr.channel))
            self.v_proto.setText(curr.protocol)
            self.v_sec.setText(f"{curr.authentication} / {curr.cipher}")
            self.v_rx.setText(f"{curr.receive_rate_mbps:.0f} Mbps" if curr.receive_rate_mbps else "غير متاح")
            self.v_tx.setText(f"{curr.transmit_rate_mbps:.0f} Mbps" if curr.transmit_rate_mbps else "غير متاح")
        else:
            self.net_name_lbl.setText("محول Wi-Fi غير متصل بشبكة حالياً")
            self.band_badge.setText("غير متصل")
            self.sig_bar.setValue(0)
            self.sig_val_lbl.setText("0%")

        # Recommendations
        recoms = analysis.get("recommendations", [])
        if recoms:
            self.recom_lbl.setText("<br>".join([f"• {r}" for r in recoms]))
        else:
            self.recom_lbl.setText("لم يتم العثور على شبكات مجاورة لتحليل القنوات.")

        # Populate Table
        self.table.setRowCount(len(nets))
        for row, n in enumerate(nets):
            self.table.setItem(row, 0, QTableWidgetItem(n.ssid))
            self.table.setItem(row, 1, QTableWidgetItem(f"{n.signal_percent}%"))
            self.table.setItem(row, 2, QTableWidgetItem(str(n.channel)))
            self.table.setItem(row, 3, QTableWidgetItem(n.band_ghz))
            self.table.setItem(row, 4, QTableWidgetItem(n.security))
            self.table.setItem(row, 5, QTableWidgetItem(n.radio_type))

    def _export_report(self):
        report_text = WifiService.generate_wifi_report()
        path, _ = QFileDialog.getSaveFileName(self, "حفظ تقرير Wi-Fi", "SINAX_WiFi_Report.txt", "Text Files (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(report_text)
                QMessageBox.information(self, "نجاح التصدير", f"تم حفظ تقرير Wi-Fi الفني بنجاح في:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر حفظ التقرير: {e}")
