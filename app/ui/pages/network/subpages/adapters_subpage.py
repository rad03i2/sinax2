# -*- coding: utf-8 -*-
"""
SINAX Network Adapters & Routing Subpage (صفحة محولات الشبكة وجداول التوجيه)
Displays network interfaces, hardware details, MTU, packet throughput stats,
firewall profile status, proxy configuration, and IPv4 routing table.
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
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

from app.services.network.adapter_service import AdapterService
from app.services.network.network_models import AdapterStatistics, NetworkAdapterInfo
from app.ui.icons import get_icon


class AdaptersLoadWorker(QObject):
    """Background worker for loading adapter metrics, routing, firewall, and proxy."""
    finished = Signal(dict)

    def run(self):
        try:
            adapters = AdapterService.get_all_adapters()
            stats = AdapterService.get_adapter_statistics()
            routes = AdapterService.get_routing_table()
            firewall = AdapterService.get_firewall_status()
            proxy = AdapterService.get_proxy_info()
            data = {
                "adapters": adapters,
                "stats": stats,
                "routes": routes,
                "firewall": firewall,
                "proxy": proxy,
            }
        except Exception:
            data = {
                "adapters": [],
                "stats": [],
                "routes": [],
                "firewall": {"Domain": False, "Private": False, "Public": False},
                "proxy": {"enabled": False, "server": "غير متوفر", "type": "Direct"},
            }
        self.finished.emit(data)


class AdaptersSubpage(QWidget):
    """Subpage for viewing network adapters, statistics, firewall, and routing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._thread: Optional[QThread] = None
        self._worker: Optional[AdaptersLoadWorker] = None
        self._init_ui()
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
        layout.setSpacing(18)

        # 1. Header Toolbar
        top_bar = QHBoxLayout()
        title = QLabel("محولات الشبكة وجداول التوجيه (Adapters & Routing)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.refresh_btn = QPushButton("  تحديث البيانات")
        self.refresh_btn.setIcon(get_icon("adapters", "#FFFFFF", 16))
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setStyleSheet("""
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
        self.refresh_btn.clicked.connect(self.refresh_data)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 2. Status Cards Row (Firewall, Proxy, Default Gateway)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        # Firewall Card
        self.firewall_card = self._create_card("جدار حماية ويندوز (Firewall)", [
            ("شبكة النطاق (Domain):", "جاري التحقق..."),
            ("الشبكة الخاصة (Private):", "جاري التحقق..."),
            ("الشبكة العامة (Public):", "جاري التحقق..."),
        ])
        cards_layout.addWidget(self.firewall_card)

        # Proxy Card
        self.proxy_card = self._create_card("إعدادات الوكيل (Proxy)", [
            ("حالة الخادم الوكيل:", "جاري الفحص..."),
            ("نوع الاتصال:", "جاري الفحص..."),
            ("عنوان الوكيل:", "جاري الفحص..."),
        ])
        cards_layout.addWidget(self.proxy_card)

        # Default Route Card
        self.route_card = self._create_card("المسار الافتراضي (Default Route)", [
            ("البوابة الافتراضية:", "جاري البحث..."),
            ("واجهة الخروج:", "جاري البحث..."),
            ("أولوية المسار (Metric):", "جاري البحث..."),
        ])
        cards_layout.addWidget(self.route_card)

        layout.addLayout(cards_layout)

        # 3. Adapters List Table
        adapters_header = QLabel("المحولات وكرتات الشبكة المثبتة")
        adapters_header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        adapters_header.setStyleSheet("color: #93C5FD; margin-top: 10px;")
        layout.addWidget(adapters_header)

        self.adapters_table = QTableWidget()
        self.adapters_table.setColumnCount(8)
        self.adapters_table.setHorizontalHeaderLabels([
            "اسم الواجهة", "وصف الشريحة", "النوع", "عنوان MAC",
            "عنوان IPv4", "بوابة الراوتر", "خوادم DNS", "الحالة"
        ])
        self._style_table(self.adapters_table)
        self.adapters_table.setMinimumHeight(200)
        layout.addWidget(self.adapters_table)

        # 4. Packet & Error Statistics Table
        stats_header = QLabel("إحصاءات الحزم والبيانات المتبادلة (Packet Statistics)")
        stats_header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        stats_header.setStyleSheet("color: #93C5FD; margin-top: 10px;")
        layout.addWidget(stats_header)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(7)
        self.stats_table.setHorizontalHeaderLabels([
            "اسم المحول", "البيانات المستلمة", "البيانات المرسلة",
            "حزم مستلمة مهملة", "حزم مرسلة مهملة", "أخطاء الاستلام", "أخطاء الإرسال"
        ])
        self._style_table(self.stats_table)
        self.stats_table.setMinimumHeight(170)
        layout.addWidget(self.stats_table)

        # 5. IPv4 Routing Table
        routes_header = QLabel("جدول توجيه الحزم (IPv4 Routing Table)")
        routes_header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        routes_header.setStyleSheet("color: #93C5FD; margin-top: 10px;")
        layout.addWidget(routes_header)

        self.routes_table = QTableWidget()
        self.routes_table.setColumnCount(5)
        self.routes_table.setHorizontalHeaderLabels([
            "شبكة الوجهة (Destination)", "القفزة التالية (Next Hop)",
            "محول الواجهة", "المقياس (Metric)", "نوع المسار"
        ])
        self._style_table(self.routes_table)
        self.routes_table.setMinimumHeight(220)
        layout.addWidget(self.routes_table)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_card(self, title: str, rows: List[tuple]) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)

        head = QLabel(title)
        head.setFont(QFont("Segoe UI", 11, QFont.Bold))
        head.setStyleSheet("color: #38BDF8;")
        card_layout.addWidget(head)

        card._val_labels = []
        for label_text, default_val in rows:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet("color: #94A3B8;")
            val = QLabel(default_val)
            val.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val.setStyleSheet("color: #F8FAFC;")
            val.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            card_layout.addLayout(row)
            card._val_labels.append(val)

        return card

    def _style_table(self, table: QTableWidget):
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setStyleSheet("""
            QTableWidget {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                gridline-color: #334155;
                selection-background-color: #0078D4;
            }
            QTableWidget::item {
                padding: 6px 10px;
            }
            QTableWidget::item:alternate {
                background: #0F172A;
            }
            QHeaderView::section {
                background: #0F172A;
                color: #94A3B8;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #334155;
                font-weight: bold;
            }
        """)

    def refresh_data(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("  جاري التحديث...")

        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

        self._thread = QThread()
        self._worker = AdaptersLoadWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_data_loaded(self, data: Dict[str, Any]):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("  تحديث البيانات")

        # 1. Update Firewall Card
        fw = data.get("firewall", {})
        dom_on = fw.get("Domain", False)
        priv_on = fw.get("Private", False)
        pub_on = fw.get("Public", False)
        if hasattr(self.firewall_card, "_val_labels") and len(self.firewall_card._val_labels) >= 3:
            self._set_status_label(self.firewall_card._val_labels[0], "مفعل ✓" if dom_on else "معطل ✗", dom_on)
            self._set_status_label(self.firewall_card._val_labels[1], "مفعل ✓" if priv_on else "معطل ✗", priv_on)
            self._set_status_label(self.firewall_card._val_labels[2], "مفعل ✓" if pub_on else "معطل ✗", pub_on)

        # 2. Update Proxy Card
        px = data.get("proxy", {})
        px_on = px.get("enabled", False)
        if hasattr(self.proxy_card, "_val_labels") and len(self.proxy_card._val_labels) >= 3:
            self._set_status_label(self.proxy_card._val_labels[0], "نشط (Manual)" if px_on else "معطل (Direct)", not px_on)
            self.proxy_card._val_labels[1].setText(px.get("type", "Direct"))
            self.proxy_card._val_labels[2].setText(px.get("server", "اتصال مباشر"))

        # 3. Update Default Route Card & Routes Table
        routes = data.get("routes", [])
        def_route = next((r for r in routes if r.get("is_default")), None)
        if hasattr(self.route_card, "_val_labels") and len(self.route_card._val_labels) >= 3:
            if def_route:
                self.route_card._val_labels[0].setText(def_route.get("next_hop") or "غير محدد")
                self.route_card._val_labels[1].setText(def_route.get("interface") or "غير محدد")
                self.route_card._val_labels[2].setText(str(def_route.get("metric", 0)))
            else:
                self.route_card._val_labels[0].setText("غير متوفر")
                self.route_card._val_labels[1].setText("غير متوفر")
                self.route_card._val_labels[2].setText("-")

        # Populate Routes Table
        self.routes_table.setRowCount(len(routes))
        for row_idx, r in enumerate(routes):
            is_def = r.get("is_default", False)
            dest_item = QTableWidgetItem(r.get("destination", ""))
            nh_item = QTableWidgetItem(r.get("next_hop", ""))
            if_item = QTableWidgetItem(r.get("interface", ""))
            met_item = QTableWidgetItem(str(r.get("metric", 0)))
            type_item = QTableWidgetItem("افتراضي (Default Gateway) ★" if is_def else "مسار محلي")

            if is_def:
                dest_item.setForeground(Qt.yellow)
                type_item.setForeground(Qt.yellow)

            self.routes_table.setItem(row_idx, 0, dest_item)
            self.routes_table.setItem(row_idx, 1, nh_item)
            self.routes_table.setItem(row_idx, 2, if_item)
            self.routes_table.setItem(row_idx, 3, met_item)
            self.routes_table.setItem(row_idx, 4, type_item)

        # 4. Populate Adapters Table
        adapters: List[NetworkAdapterInfo] = data.get("adapters", [])
        self.adapters_table.setRowCount(len(adapters))
        for row_idx, a in enumerate(adapters):
            name_item = QTableWidgetItem(a.name)
            desc_item = QTableWidgetItem(a.description)
            atype = "لاسلكي (Wi-Fi)" if a.is_wireless else ("افتراضي (Virtual)" if a.is_virtual else ("VPN" if a.is_vpn else "إيثرنت (Ethernet)"))
            type_item = QTableWidgetItem(atype)
            mac_item = QTableWidgetItem(a.mac_address)
            ip_item = QTableWidgetItem(a.ipv4_address or "غير متوفر")
            gw_item = QTableWidgetItem(a.ipv4_gateway or "-")
            dns_item = QTableWidgetItem(", ".join(a.dns_servers) if a.dns_servers else "-")
            st_item = QTableWidgetItem(a.status)

            if a.status == "متصل":
                st_item.setForeground(Qt.green)
            else:
                st_item.setForeground(Qt.gray)

            self.adapters_table.setItem(row_idx, 0, name_item)
            self.adapters_table.setItem(row_idx, 1, desc_item)
            self.adapters_table.setItem(row_idx, 2, type_item)
            self.adapters_table.setItem(row_idx, 3, mac_item)
            self.adapters_table.setItem(row_idx, 4, ip_item)
            self.adapters_table.setItem(row_idx, 5, gw_item)
            self.adapters_table.setItem(row_idx, 6, dns_item)
            self.adapters_table.setItem(row_idx, 7, st_item)

        # 5. Populate Stats Table
        stats: List[AdapterStatistics] = data.get("stats", [])
        self.stats_table.setRowCount(len(stats))
        for row_idx, s in enumerate(stats):
            name_item = QTableWidgetItem(s.name)
            rx_item = QTableWidgetItem(self._format_bytes(s.bytes_received))
            tx_item = QTableWidgetItem(self._format_bytes(s.bytes_sent))
            disc_in = QTableWidgetItem(str(s.discards_in))
            disc_out = QTableWidgetItem(str(s.discards_out))
            err_in = QTableWidgetItem(str(s.errors_in))
            err_out = QTableWidgetItem(str(s.errors_out))

            if s.errors_in > 0:
                err_in.setForeground(Qt.red)
            if s.errors_out > 0:
                err_out.setForeground(Qt.red)

            self.stats_table.setItem(row_idx, 0, name_item)
            self.stats_table.setItem(row_idx, 1, rx_item)
            self.stats_table.setItem(row_idx, 2, tx_item)
            self.stats_table.setItem(row_idx, 3, disc_in)
            self.stats_table.setItem(row_idx, 4, disc_out)
            self.stats_table.setItem(row_idx, 5, err_in)
            self.stats_table.setItem(row_idx, 6, err_out)

    def _set_status_label(self, label: QLabel, text: str, is_good: bool):
        label.setText(text)
        if is_good:
            label.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            label.setStyleSheet("color: #EF4444; font-weight: bold;")

    def _format_bytes(self, num_bytes: int) -> str:
        if num_bytes >= 1024 * 1024 * 1024:
            return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"
        if num_bytes >= 1024 * 1024:
            return f"{num_bytes / (1024 * 1024):.2f} MB"
        if num_bytes >= 1024:
            return f"{num_bytes / 1024:.1f} KB"
        return f"{num_bytes} B"
