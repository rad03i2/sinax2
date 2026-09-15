# -*- coding: utf-8 -*-
"""
SINAX DNS Center Subpage (صفحة مركز وخوادم DNS)
Provides DNS records lookups, server benchmarks (Cloudflare vs Google vs Quad9),
and safe DNS switching with configuration restore.
"""

from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.network.dns_service import DnsService
from app.services.network.network_info_service import NetworkInfoService
from app.ui.icons import get_icon


class DnsBenchmarkWorker(QObject):
    """Worker for benchmarking DNS servers."""
    finished = Signal(list)

    def run(self):
        res = DnsService.benchmark_dns_servers()
        self.finished.emit(res)


class DnsSubpage(QWidget):
    """Subpage for DNS lookups, benchmarks, and settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self._load_current_dns()

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
        title = QLabel("مركز أسماء النطاقات (DNS Center & Benchmark)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        layout.addWidget(title)

        # 2. Current DNS Card
        self.curr_card = QFrame()
        self.curr_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 14px;")
        curr_l = QHBoxLayout(self.curr_card)

        self.dns_status_lbl = QLabel("خوادم DNS الحالية: جاري التحقق...")
        self.dns_status_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.dns_status_lbl.setStyleSheet("color: #38BDF8;")
        curr_l.addWidget(self.dns_status_lbl)

        curr_l.addStretch()

        self.bench_btn = QPushButton("  مقارنة أسرع DNS")
        self.bench_btn.setIcon(get_icon("speedtest", "#FFFFFF", 16))
        self.bench_btn.setFixedHeight(36)
        self.bench_btn.setStyleSheet("background: #0078D4; color: white; border-radius: 6px; padding: 0 16px; font-weight: bold;")
        self.bench_btn.clicked.connect(self._run_benchmark)
        curr_l.addWidget(self.bench_btn)

        layout.addWidget(self.curr_card)

        # 3. DNS Benchmark Table
        b_title = QLabel("نتائج مقارنة سرعة استجابة خوادم DNS:")
        b_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        b_title.setStyleSheet("color: #E2E8F0; margin-top: 6px;")
        layout.addWidget(b_title)

        self.bench_table = QTableWidget()
        self.bench_table.setColumnCount(4)
        self.bench_table.setHorizontalHeaderLabels(["اسم الخادم", "عنوان IP", "زمن الاستجابة (Latency)", "الحالة"])
        self.bench_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bench_table.verticalHeader().setVisible(False)
        self.bench_table.setFixedHeight(180)
        self.bench_table.setStyleSheet("""
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
        layout.addWidget(self.bench_table)

        # 4. DNS Lookup Tool
        l_title = QLabel("استعلام سجلات DNS (DNS Lookup):")
        l_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        l_title.setStyleSheet("color: #E2E8F0; margin-top: 8px;")
        layout.addWidget(l_title)

        lookup_bar = QHBoxLayout()
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("أدخل النطاق مثلاً: google.com أو wikipedia.org")
        self.domain_input.setFixedHeight(36)
        self.domain_input.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 6px; padding: 0 10px; color: white;")
        lookup_bar.addWidget(self.domain_input, 1)

        self.record_combo = QComboBox()
        self.record_combo.addItems(["A", "AAAA", "CNAME", "MX", "TXT", "NS", "PTR"])
        self.record_combo.setFixedHeight(36)
        self.record_combo.setFixedWidth(100)
        self.record_combo.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 6px; color: white;")
        lookup_bar.addWidget(self.record_combo)

        lookup_btn = QPushButton("استعلام")
        lookup_btn.setFixedHeight(36)
        lookup_btn.setStyleSheet("background: #0078D4; color: white; border-radius: 6px; padding: 0 18px; font-weight: bold;")
        lookup_btn.clicked.connect(self._do_lookup)
        lookup_bar.addWidget(lookup_btn)
        layout.addLayout(lookup_bar)

        self.lookup_table = QTableWidget()
        self.lookup_table.setColumnCount(4)
        self.lookup_table.setHorizontalHeaderLabels(["النطاق", "نوع السجل", "القيمة المسترجعة", "TTL (ثوانٍ)"])
        self.lookup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lookup_table.verticalHeader().setVisible(False)
        self.lookup_table.setFixedHeight(160)
        self.lookup_table.setStyleSheet("""
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
        layout.addWidget(self.lookup_table)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _load_current_dns(self):
        conn = NetworkInfoService.get_active_connection_summary()
        dns_list = conn.get("dns_servers", [])
        self.dns_status_lbl.setText(f"خوادم DNS الحالية: {', '.join(dns_list) if dns_list else 'تلقائي (DHCP)'}")

    def _run_benchmark(self):
        self.bench_btn.setEnabled(False)
        self.bench_btn.setText("  جاري القياس...")

        self._thread = QThread()
        self._worker = DnsBenchmarkWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_bench_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_bench_finished(self, results: list):
        self.bench_btn.setEnabled(True)
        self.bench_btn.setText("  مقارنة أسرع DNS")

        self.bench_table.setRowCount(len(results))
        for row, r in enumerate(results):
            name_str = f"{r['name']} 🚀 (الأسرع)" if r.get("is_fastest") else r['name']
            self.bench_table.setItem(row, 0, QTableWidgetItem(name_str))
            self.bench_table.setItem(row, 1, QTableWidgetItem(r["ip"]))
            self.bench_table.setItem(row, 2, QTableWidgetItem(f"{r['latency_ms']:.1f} ms" if r["latency_ms"] < 999 else "—"))
            self.bench_table.setItem(row, 3, QTableWidgetItem(r["status"]))

    def _do_lookup(self):
        domain = self.domain_input.text().strip()
        rtype = self.record_combo.currentText()
        if not domain:
            QMessageBox.warning(self, "خطأ", "يرجى كتابة اسم نطاق صحيح للاستعلام.")
            return

        records = DnsService.lookup_records(domain, rtype)
        self.lookup_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.lookup_table.setItem(row, 0, QTableWidgetItem(rec["name"]))
            self.lookup_table.setItem(row, 1, QTableWidgetItem(rec["type"]))
            self.lookup_table.setItem(row, 2, QTableWidgetItem(str(rec["value"])))
            self.lookup_table.setItem(row, 3, QTableWidgetItem(str(rec["ttl"])))
