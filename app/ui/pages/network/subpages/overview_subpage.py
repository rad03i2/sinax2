# -*- coding: utf-8 -*-
"""
SINAX Network Overview Subpage (لوحة القيادة المركزية ونظرة عامة على الشبكة)
Displays live connection state card, metrics tiles (Download, Upload, Ping, Jitter, Loss),
smart recommendations, and quick actions toolbar.
"""

from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont
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

from app.services.network.network_info_service import NetworkInfoService
from app.services.network.traffic_service import TrafficService
from app.ui.icons import get_icon


class OverviewWorker(QObject):
    """Background worker fetching connection overview."""
    finished = Signal(dict)

    def run(self):
        data = NetworkInfoService.get_active_connection_summary()
        pub = NetworkInfoService.fetch_public_ip()
        data["public_ip"] = pub.ipv4 or "غير متوفر"
        data["isp_name"] = pub.isp_name or "مزود خدمة محلي"
        self.finished.emit(data)


class OverviewSubpage(QWidget):
    """Network central dashboard subpage."""

    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

        # Refresh timer for live speeds
        self._traffic_timer = QTimer(self)
        self._traffic_timer.setInterval(1000)
        self._traffic_timer.timeout.connect(self._update_live_traffic)
        self._traffic_timer.start()

        self.refresh_data()

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
        top_title = QLabel("لوحة تحكم الشبكة والإنترنت")
        top_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        top_title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(top_title)

        top_bar.addStretch()

        self.refresh_btn = QPushButton("  تحديث البيانات")
        self.refresh_btn.setIcon(get_icon("sync", "#FFFFFF", 16))
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #0078D4;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #106EBE; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)
        top_bar.addWidget(self.refresh_btn)

        layout.addLayout(top_bar)

        # 2. Hero Status Card
        self.hero_card = QFrame()
        self.hero_card.setObjectName("HeroCard")
        self.hero_card.setStyleSheet("""
            QFrame#HeroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E293B, stop:1 #0F172A);
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        hero_layout.setSpacing(12)

        # Status badge row
        badge_row = QHBoxLayout()
        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_icon("network", "#10B981", 24).pixmap(24, 24))
        badge_row.addWidget(self.status_icon)

        self.status_label = QLabel("جاري التحقق من الاتصال...")
        self.status_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.status_label.setStyleSheet("color: #10B981;")
        badge_row.addWidget(self.status_label)

        badge_row.addStretch()

        self.type_badge = QLabel("Wi-Fi")
        self.type_badge.setStyleSheet("""
            background: rgba(0, 120, 212, 0.2);
            color: #60A5FA;
            border: 1px solid #0078D4;
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: bold;
        """)
        badge_row.addWidget(self.type_badge)
        hero_layout.addLayout(badge_row)

        # Info parameters grid
        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(24)
        info_grid.setVerticalSpacing(8)

        def make_kv(lbl: str, val: str):
            k_lbl = QLabel(lbl)
            k_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 500;")
            v_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            return k_lbl, v_lbl

        self.lbl_ssid_k, self.lbl_ssid_v = make_kv("اسم الشبكة (SSID):", "—")
        self.lbl_ip_k, self.lbl_ip_v = make_kv("عنوان IPv4 المحلي:", "—")
        self.lbl_gw_k, self.lbl_gw_v = make_kv("البوابة (Router Gateway):", "—")
        self.lbl_dns_k, self.lbl_dns_v = make_kv("خوادم DNS:", "—")
        self.lbl_link_k, self.lbl_link_v = make_kv("سرعة الربط (Link Speed):", "—")
        self.lbl_signal_k, self.lbl_signal_v = make_kv("قوة الإشارة (Signal):", "—")
        self.lbl_pub_k, self.lbl_pub_v = make_kv("عنوان IP العام (Public IP):", "—")
        self.lbl_isp_k, self.lbl_isp_v = make_kv("مزود الإنترنت (ISP):", "—")

        info_grid.addWidget(self.lbl_ssid_k, 0, 0)
        info_grid.addWidget(self.lbl_ssid_v, 0, 1)
        info_grid.addWidget(self.lbl_ip_k, 0, 2)
        info_grid.addWidget(self.lbl_ip_v, 0, 3)

        info_grid.addWidget(self.lbl_gw_k, 1, 0)
        info_grid.addWidget(self.lbl_gw_v, 1, 1)
        info_grid.addWidget(self.lbl_dns_k, 1, 2)
        info_grid.addWidget(self.lbl_dns_v, 1, 3)

        info_grid.addWidget(self.lbl_link_k, 2, 0)
        info_grid.addWidget(self.lbl_link_v, 2, 1)
        info_grid.addWidget(self.lbl_signal_k, 2, 2)
        info_grid.addWidget(self.lbl_signal_v, 2, 3)

        info_grid.addWidget(self.lbl_pub_k, 3, 0)
        info_grid.addWidget(self.lbl_pub_v, 3, 1)
        info_grid.addWidget(self.lbl_isp_k, 3, 2)
        info_grid.addWidget(self.lbl_isp_v, 3, 3)

        hero_layout.addLayout(info_grid)
        layout.addWidget(self.hero_card)

        # 3. Metrics Tiles Grid
        sec_label = QLabel("المؤشرات الحية والسرعة اللحظية")
        sec_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        sec_label.setStyleSheet("color: #E2E8F0; margin-top: 6px;")
        layout.addWidget(sec_label)

        tiles_grid = QGridLayout()
        tiles_grid.setSpacing(12)

        self.tile_down = self._create_tile("التنزيل المباشر", "0.0 MB/s", "#0078D4", "traffic")
        self.tile_up = self._create_tile("الرفع المباشر", "0.0 MB/s", "#8B5CF6", "traffic")
        self.tile_ping = self._create_tile("زمن الاستجابة (Ping)", "— ms", "#10B981", "speedtest")
        self.tile_wifi = self._create_tile("إشارة اللاسلكي", "— %", "#F59E0B", "wifi")

        tiles_grid.addWidget(self.tile_down, 0, 0)
        tiles_grid.addWidget(self.tile_up, 0, 1)
        tiles_grid.addWidget(self.tile_ping, 0, 2)
        tiles_grid.addWidget(self.tile_wifi, 0, 3)

        layout.addLayout(tiles_grid)

        # 4. Quick Actions Toolbar
        actions_label = QLabel("إجراءات الشبكة السريعة")
        actions_label.setFont(QFont("Segoe UI", 13, QFont.Bold))
        actions_label.setStyleSheet("color: #E2E8F0; margin-top: 8px;")
        layout.addWidget(actions_label)

        actions_bar = QHBoxLayout()
        actions_bar.setSpacing(10)

        def make_action_btn(title: str, icon_name: str, target: str):
            btn = QPushButton(f"  {title}")
            btn.setIcon(get_icon(icon_name, "#FFFFFF", 16))
            btn.setFixedHeight(40)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    background: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    color: #E2E8F0;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #2D3748;
                    border-color: #0078D4;
                    color: #FFFFFF;
                }
            """)
            btn.clicked.connect(lambda: self.navigate_requested.emit(target))
            return btn

        actions_bar.addWidget(make_action_btn("اختبار السرعة الحقيقي", "speedtest", "speedtest"))
        actions_bar.addWidget(make_action_btn("طبيب تشخيص الأعطال", "doctor", "doctor"))
        actions_bar.addWidget(make_action_btn("محلل قنوات Wi-Fi", "wifi", "wifi"))
        actions_bar.addWidget(make_action_btn("مشاركة SINAX Share", "share", "share"))

        layout.addLayout(actions_bar)
        layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_tile(self, title: str, value: str, color_hex: str, icon_name: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: #1E293B;
                border: 1px solid #334155;
                border-top: 3px solid {color_hex};
                border-radius: 8px;
            }}
        """)
        l = QVBoxLayout(frame)
        l.setContentsMargins(14, 12, 14, 12)
        l.setSpacing(6)

        header = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(get_icon(icon_name, color_hex, 16).pixmap(16, 16))
        header.addWidget(ic)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #94A3B8; font-size: 12px;")
        header.addWidget(lbl_t)
        header.addStretch()
        l.addLayout(header)

        lbl_v = QLabel(value)
        lbl_v.setObjectName("ValLabel")
        lbl_v.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_v.setStyleSheet("color: #FFFFFF;")
        l.addWidget(lbl_v)

        return frame

    def refresh_data(self):
        """Launches worker to refresh network status."""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("  جاري التحديث...")

        self._thread = QThread()
        self._worker = OverviewWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_data_loaded(self, data: dict):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  تحديث البيانات")

        is_conn = data.get("connected", False)
        self.status_label.setText(data.get("internet_status", "متصل"))
        if is_conn:
            self.status_label.setStyleSheet("color: #10B981;")
            self.status_icon.setPixmap(get_icon("network", "#10B981", 24).pixmap(24, 24))
        else:
            self.status_label.setStyleSheet("color: #EF4444;")
            self.status_icon.setPixmap(get_icon("network", "#EF4444", 24).pixmap(24, 24))

        self.type_badge.setText(data.get("connection_type", "Ethernet"))
        self.lbl_ssid_v.setText(data.get("wifi_ssid") or "شبكة سلكية / غير متاح")
        self.lbl_ip_v.setText(data.get("ipv4", "غير متوفر"))
        self.lbl_gw_v.setText(data.get("gateway", "غير متوفر"))
        self.lbl_dns_v.setText(", ".join(data.get("dns_servers", [])) or "تلقائي")

        link_spd = data.get("link_speed_mbps", 0)
        self.lbl_link_v.setText(f"{link_spd} Mbps" if link_spd else "غير متوفر")

        sig = data.get("wifi_signal_percent", 0)
        self.lbl_signal_v.setText(f"{sig}%" if sig else "اتصال سلكي (100%)")

        self.lbl_pub_v.setText(data.get("public_ip", "غير متوفر"))
        self.lbl_isp_v.setText(data.get("isp_name", "غير متوفر"))

        # Update Wi-Fi tile
        tile_val = self.tile_wifi.findChild(QLabel, "ValLabel")
        if tile_val:
            tile_val.setText(f"{sig}%" if sig else "سلكي")

    def _update_live_traffic(self):
        """Samples instant bandwidth metrics and updates tiles."""
        metrics = TrafficService.sample_live_bandwidth()
        down_mb_s = metrics["download_mb_s"]
        up_mb_s = metrics["upload_mb_s"]

        lbl_down = self.tile_down.findChild(QLabel, "ValLabel")
        if lbl_down:
            lbl_down.setText(f"{down_mb_s:.2f} MB/s")

        lbl_up = self.tile_up.findChild(QLabel, "ValLabel")
        if lbl_up:
            lbl_up.setText(f"{up_mb_s:.2f} MB/s")
