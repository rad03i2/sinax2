# -*- coding: utf-8 -*-
"""
SINAX Advanced Network Tools & Diagnostic Reports Subpage (صفحة أدوات الشبكة المتقدمة والتقارير)
Provides:
1. Continuous Ping with live statistics (Min, Max, Avg, Packet Loss).
2. Visual Traceroute hop timeline runner.
3. Diagnostic common port check for local/owned hosts.
4. Technical Support Report generator with Privacy Mode and export options.
"""

import json
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.network.network_tools_service import COMMON_DIAGNOSTIC_PORTS, NetworkToolsService
from app.ui.icons import get_icon


class PingWorker(QObject):
    """Background worker for continuous ping."""
    result_ready = Signal(bool, float)

    def __init__(self, host: str):
        super().__init__()
        self.host = host

    def run_once(self):
        success, latency = NetworkToolsService.ping_single(self.host, timeout=1.2)
        self.result_ready.emit(success, latency)


class TracerouteWorker(QObject):
    """Background worker for traceroute hop tracing."""
    hop_received = Signal(int, str, float)
    finished = Signal(list)

    def __init__(self, host: str):
        super().__init__()
        self.host = host
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        hops = NetworkToolsService.traceroute_host(
            self.host,
            max_hops=15,
            hop_cb=lambda h, ip, ms: self.hop_received.emit(h, ip, ms),
            is_cancelled=lambda: self._cancelled
        )
        self.finished.emit(hops)


class PortScanWorker(QObject):
    """Background worker for diagnostic port check."""
    finished = Signal(list)

    def __init__(self, host: str):
        super().__init__()
        self.host = host

    def run(self):
        results = NetworkToolsService.scan_diagnostic_ports(self.host, timeout=1.0)
        self.finished.emit(results)


class ToolsSubpage(QWidget):
    """Subpage for advanced network tools (Ping, Traceroute, Ports, Report)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)

        # Ping state
        self._ping_timer = QTimer(self)
        self._ping_timer.setInterval(1000)
        self._ping_timer.timeout.connect(self._do_ping_tick)
        self._ping_running = False
        self._ping_sent = 0
        self._ping_received = 0
        self._latencies: List[float] = []

        # Traceroute state
        self._trace_thread: Optional[QThread] = None
        self._trace_worker: Optional[TracerouteWorker] = None

        # Port scan state
        self._port_thread: Optional[QThread] = None
        self._port_worker: Optional[PortScanWorker] = None

        # Current generated report
        self._current_report: Dict[str, Any] = {}

        self._init_ui()

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
        layout.setSpacing(20)

        # Header Title
        top_bar = QHBoxLayout()
        title = QLabel("أدوات الشبكة المتقدمة والتقارير الفنية (Advanced Network Tools)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Section 1: Continuous Ping Tool
        layout.addWidget(self._build_ping_section())

        # Section 2: Traceroute Tool
        layout.addWidget(self._build_traceroute_section())

        # Section 3: Diagnostic Port Check Tool
        layout.addWidget(self._build_port_check_section())

        # Section 4: Technical Support Report Exporter
        layout.addWidget(self._build_report_section())

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    # -------------------------------------------------------------
    # 1. Ping Tool Section
    # -------------------------------------------------------------
    def _build_ping_section(self) -> QFrame:
        frame = self._create_section_frame("اختبار الاتصال المستمر (Continuous Ping)")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(12)

        ctrl_row = QHBoxLayout()
        lbl = QLabel("الهدف (Host / IP):")
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet("color: #94A3B8;")
        ctrl_row.addWidget(lbl)

        self.ping_input = QLineEdit("1.1.1.1")
        self.ping_input.setPlaceholderText("مثال: 1.1.1.1 أو google.com")
        self.ping_input.setStyleSheet(self._input_style())
        self.ping_input.setFixedWidth(220)
        ctrl_row.addWidget(self.ping_input)

        self.ping_btn = QPushButton("  بدء الفحص")
        self.ping_btn.setIcon(get_icon("speedtest", "#FFFFFF", 16))
        self.ping_btn.setStyleSheet(self._primary_button_style())
        self.ping_btn.setFixedWidth(130)
        self.ping_btn.clicked.connect(self._toggle_ping)
        ctrl_row.addWidget(self.ping_btn)

        ctrl_row.addStretch()
        fl.addLayout(ctrl_row)

        # Stats Chips
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.ping_latency_lbl = self._create_metric_chip("زمن الاستجابة الحالية", "- ms")
        self.ping_avg_lbl = self._create_metric_chip("متوسط الاستجابة", "- ms")
        self.ping_minmax_lbl = self._create_metric_chip("أدنى / أقصى", "- / - ms")
        self.ping_loss_lbl = self._create_metric_chip("نسبة الفقد (Loss)", "0%")

        stats_row.addWidget(self.ping_latency_lbl)
        stats_row.addWidget(self.ping_avg_lbl)
        stats_row.addWidget(self.ping_minmax_lbl)
        stats_row.addWidget(self.ping_loss_lbl)
        fl.addLayout(stats_row)

        # Ping Log Box
        self.ping_log = QTextEdit()
        self.ping_log.setReadOnly(True)
        self.ping_log.setFixedHeight(120)
        self.ping_log.setStyleSheet("""
            QTextEdit {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #38BDF8;
                font-family: Consolas, monospace;
                font-size: 11px;
                padding: 6px;
            }
        """)
        fl.addWidget(self.ping_log)

        return frame

    def _toggle_ping(self):
        if not self._ping_running:
            host = self.ping_input.text().strip()
            if not host:
                QMessageBox.warning(self, "خطأ", "يرجى كتابة عنوان هدف صحيح.")
                return
            self._ping_running = True
            self.ping_btn.setText("  إيقاف الفحص")
            self.ping_btn.setStyleSheet(self._danger_button_style())
            self.ping_input.setEnabled(False)
            self._ping_sent = 0
            self._ping_received = 0
            self._latencies.clear()
            self.ping_log.clear()
            self.ping_log.append(f"--- بدء فحص Ping نحو {host} كل ثانية ---")
            self._ping_timer.start()
            self._do_ping_tick()
        else:
            self._ping_running = False
            self._ping_timer.stop()
            self.ping_btn.setText("  بدء الفحص")
            self.ping_btn.setStyleSheet(self._primary_button_style())
            self.ping_input.setEnabled(True)
            self.ping_log.append("--- تم إيقاف الفحص ---")

    def _do_ping_tick(self):
        host = self.ping_input.text().strip()
        worker = PingWorker(host)
        # Run in thread or synchronously since timeout is bounded
        self._ping_sent += 1
        success, latency = NetworkToolsService.ping_single(host, timeout=1.0)
        if success:
            self._ping_received += 1
            self._latencies.append(latency)
            avg = sum(self._latencies) / len(self._latencies)
            min_lat = min(self._latencies)
            max_lat = max(self._latencies)
            self.ping_latency_lbl.findChild(QLabel, "val_lbl").setText(f"{latency} ms")
            self.ping_avg_lbl.findChild(QLabel, "val_lbl").setText(f"{avg:.1f} ms")
            self.ping_minmax_lbl.findChild(QLabel, "val_lbl").setText(f"{min_lat:.0f} / {max_lat:.0f} ms")
            self.ping_log.append(f"رد من {host}: الوقت={latency}ms")
        else:
            self.ping_latency_lbl.findChild(QLabel, "val_lbl").setText("انقطاع (Timeout)")
            self.ping_log.append(f"انقطاع الاتصال: لم يتم استلام رد من {host}")

        loss_pct = int(((self._ping_sent - self._ping_received) / self._ping_sent) * 100)
        self.ping_loss_lbl.findChild(QLabel, "val_lbl").setText(f"{loss_pct}%")

    # -------------------------------------------------------------
    # 2. Traceroute Section
    # -------------------------------------------------------------
    def _build_traceroute_section(self) -> QFrame:
        frame = self._create_section_frame("تتبع مسار الحزم (Traceroute Hop Timeline)")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(12)

        ctrl_row = QHBoxLayout()
        lbl = QLabel("الهدف (Host / IP):")
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet("color: #94A3B8;")
        ctrl_row.addWidget(lbl)

        self.trace_input = QLineEdit("google.com")
        self.trace_input.setPlaceholderText("مثال: 8.8.8.8 أو cloudflare.com")
        self.trace_input.setStyleSheet(self._input_style())
        self.trace_input.setFixedWidth(220)
        ctrl_row.addWidget(self.trace_input)

        self.trace_btn = QPushButton("  بدء التتبع")
        self.trace_btn.setIcon(get_icon("tools", "#FFFFFF", 16))
        self.trace_btn.setStyleSheet(self._primary_button_style())
        self.trace_btn.setFixedWidth(130)
        self.trace_btn.clicked.connect(self._start_traceroute)
        ctrl_row.addWidget(self.trace_btn)

        ctrl_row.addStretch()
        fl.addLayout(ctrl_row)

        self.trace_table = QTableWidget()
        self.trace_table.setColumnCount(3)
        self.trace_table.setHorizontalHeaderLabels(["رقم القفزة (Hop #)", "عنوان العقدة (Node IP)", "زمن الوصول (Latency)"])
        self.trace_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trace_table.setAlternatingRowColors(True)
        self.trace_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.trace_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.trace_table.setFixedHeight(180)
        self.trace_table.setStyleSheet(self._table_style())
        fl.addWidget(self.trace_table)

        return frame

    def _start_traceroute(self):
        host = self.trace_input.text().strip()
        if not host:
            QMessageBox.warning(self, "خطأ", "يرجى كتابة عنوان هدف صحيح.")
            return

        self.trace_btn.setEnabled(False)
        self.trace_btn.setText("  جاري التتبع...")
        self.trace_table.setRowCount(0)

        if self._trace_thread and self._trace_thread.isRunning():
            self._trace_worker.cancel()
            self._trace_thread.quit()
            self._trace_thread.wait()

        self._trace_thread = QThread()
        self._trace_worker = TracerouteWorker(host)
        self._trace_worker.moveToThread(self._trace_thread)
        self._trace_thread.started.connect(self._trace_worker.run)
        self._trace_worker.hop_received.connect(self._on_trace_hop)
        self._trace_worker.finished.connect(self._on_trace_finished)
        self._trace_worker.finished.connect(self._trace_thread.quit)
        self._trace_thread.start()

    def _on_trace_hop(self, hop_num: int, ip: str, latency: float):
        row = self.trace_table.rowCount()
        self.trace_table.insertRow(row)
        self.trace_table.setItem(row, 0, QTableWidgetItem(f"القفزة {hop_num}"))
        self.trace_table.setItem(row, 1, QTableWidgetItem(ip))
        lat_str = f"{latency:.1f} ms" if latency > 0 else "< 1 ms"
        item = QTableWidgetItem(lat_str)
        if latency > 100:
            item.setForeground(Qt.yellow)
        else:
            item.setForeground(Qt.green)
        self.trace_table.setItem(row, 2, item)

    def _on_trace_finished(self, hops: list):
        self.trace_btn.setEnabled(True)
        self.trace_btn.setText("  بدء التتبع")
        if not hops and self.trace_table.rowCount() == 0:
            row = self.trace_table.rowCount()
            self.trace_table.insertRow(row)
            self.trace_table.setItem(row, 0, QTableWidgetItem("-"))
            self.trace_table.setItem(row, 1, QTableWidgetItem("تعذر تتبع المسار أو الهدف محمي بجدار ناري"))
            self.trace_table.setItem(row, 2, QTableWidgetItem("-"))

    # -------------------------------------------------------------
    # 3. Diagnostic Port Check Section
    # -------------------------------------------------------------
    def _build_port_check_section(self) -> QFrame:
        frame = self._create_section_frame("فحص المنافذ التشخيصية القياسية (Common Diagnostic Ports)")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(12)

        ctrl_row = QHBoxLayout()
        lbl = QLabel("الجهاز المحلي (IP / Host):")
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet("color: #94A3B8;")
        ctrl_row.addWidget(lbl)

        self.port_host_input = QLineEdit("127.0.0.1")
        self.port_host_input.setPlaceholderText("مثال: 192.168.1.1 أو 127.0.0.1")
        self.port_host_input.setStyleSheet(self._input_style())
        self.port_host_input.setFixedWidth(220)
        ctrl_row.addWidget(self.port_host_input)

        self.port_scan_btn = QPushButton("  فحص المنافذ")
        self.port_scan_btn.setIcon(get_icon("connections", "#FFFFFF", 16))
        self.port_scan_btn.setStyleSheet(self._primary_button_style())
        self.port_scan_btn.setFixedWidth(130)
        self.port_scan_btn.clicked.connect(self._start_port_scan)
        ctrl_row.addWidget(self.port_scan_btn)

        note = QLabel("(فحص تشخيصي قياسي للأجهزة المملوكة لك فقط)")
        note.setFont(QFont("Segoe UI", 9))
        note.setStyleSheet("color: #64748B;")
        ctrl_row.addWidget(note)
        ctrl_row.addStretch()
        fl.addLayout(ctrl_row)

        self.ports_table = QTableWidget()
        self.ports_table.setColumnCount(4)
        self.ports_table.setHorizontalHeaderLabels(["رقم المنفذ", "الخدمة / البروتوكول", "الحالة", "زمن الاستجابة"])
        self.ports_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ports_table.setAlternatingRowColors(True)
        self.ports_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ports_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ports_table.setFixedHeight(180)
        self.ports_table.setStyleSheet(self._table_style())
        fl.addWidget(self.ports_table)

        return frame

    def _start_port_scan(self):
        host = self.port_host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "خطأ", "يرجى كتابة عنوان صحيح.")
            return

        self.port_scan_btn.setEnabled(False)
        self.port_scan_btn.setText("  جاري الفحص...")
        self.ports_table.setRowCount(0)

        if self._port_thread and self._port_thread.isRunning():
            self._port_thread.quit()
            self._port_thread.wait()

        self._port_thread = QThread()
        self._port_worker = PortScanWorker(host)
        self._port_worker.moveToThread(self._port_thread)
        self._port_thread.started.connect(self._port_worker.run)
        self._port_worker.finished.connect(self._on_port_scan_finished)
        self._port_worker.finished.connect(self._port_thread.quit)
        self._port_thread.start()

    def _on_port_scan_finished(self, results: List[Dict[str, Any]]):
        self.port_scan_btn.setEnabled(True)
        self.port_scan_btn.setText("  فحص المنافذ")

        self.ports_table.setRowCount(len(results))
        for idx, item in enumerate(results):
            port_item = QTableWidgetItem(str(item["port"]))
            serv_item = QTableWidgetItem(item["service"])
            stat_item = QTableWidgetItem(item["status"])
            lat_item = QTableWidgetItem(f"{item['latency_ms']} ms" if item["latency_ms"] > 0 else "-")

            if "مفتوح" in item["status"]:
                stat_item.setForeground(Qt.green)
            else:
                stat_item.setForeground(Qt.gray)

            self.ports_table.setItem(idx, 0, port_item)
            self.ports_table.setItem(idx, 1, serv_item)
            self.ports_table.setItem(idx, 2, stat_item)
            self.ports_table.setItem(idx, 3, lat_item)

    # -------------------------------------------------------------
    # 4. Support Report Section
    # -------------------------------------------------------------
    def _build_report_section(self) -> QFrame:
        frame = self._create_section_frame("توليد تقرير الدعم الفني للشبكة (Network Support Report)")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(12)

        top_row = QHBoxLayout()
        self.privacy_check = QCheckBox("تفعيل وضع حماية الخصوصية (إخفاء العناوين الحساسة وPublic IP)")
        self.privacy_check.setChecked(True)
        self.privacy_check.setStyleSheet("color: #F8FAFC; font-weight: bold;")
        top_row.addWidget(self.privacy_check)
        top_row.addStretch()

        self.gen_report_btn = QPushButton("  توليد التقرير الآن")
        self.gen_report_btn.setIcon(get_icon("doctor", "#FFFFFF", 16))
        self.gen_report_btn.setStyleSheet(self._primary_button_style())
        self.gen_report_btn.clicked.connect(self._generate_report)
        top_row.addWidget(self.gen_report_btn)
        fl.addLayout(top_row)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setFixedHeight(180)
        self.report_text.setStyleSheet("""
            QTextEdit {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                font-family: Consolas, monospace;
                font-size: 11px;
                padding: 10px;
            }
        """)
        fl.addWidget(self.report_text)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.copy_btn = QPushButton("  نسخ إلى الحافظة")
        self.copy_btn.setIcon(get_icon("share", "#FFFFFF", 14))
        self.copy_btn.setStyleSheet(self._secondary_button_style())
        self.copy_btn.clicked.connect(self._copy_report)
        btn_row.addWidget(self.copy_btn)

        self.save_txt_btn = QPushButton("  تصدير نصي (.txt)")
        self.save_txt_btn.setIcon(get_icon("tools", "#FFFFFF", 14))
        self.save_txt_btn.setStyleSheet(self._secondary_button_style())
        self.save_txt_btn.clicked.connect(self._export_txt)
        btn_row.addWidget(self.save_txt_btn)

        self.save_json_btn = QPushButton("  تصدير بيانات (.json)")
        self.save_json_btn.setIcon(get_icon("tools", "#FFFFFF", 14))
        self.save_json_btn.setStyleSheet(self._secondary_button_style())
        self.save_json_btn.clicked.connect(self._export_json)
        btn_row.addWidget(self.save_json_btn)

        btn_row.addStretch()
        fl.addLayout(btn_row)

        return frame

    def _generate_report(self):
        priv = self.privacy_check.isChecked()
        self._current_report = NetworkToolsService.generate_support_report(privacy_mode=priv)
        txt = NetworkToolsService.export_report_to_text(self._current_report)
        self.report_text.setText(txt)

    def _copy_report(self):
        text = self.report_text.toPlainText()
        if not text:
            QMessageBox.information(self, "تنبيه", "يرجى توليد التقرير أولاً.")
            return
        QGuiApplication.clipboard().setText(text)
        QMessageBox.information(self, "نجاح", "تم نسخ التقرير إلى الحافظة بنجاح!")

    def _export_txt(self):
        text = self.report_text.toPlainText()
        if not text:
            QMessageBox.information(self, "تنبيه", "يرجى توليد التقرير أولاً.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "حفظ تقرير الدعم الفني", "SINAX_Network_Report.txt", "Text Files (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                QMessageBox.information(self, "تم الحفظ", f"تم تصدير التقرير إلى:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر حفظ الملف: {e}")

    def _export_json(self):
        if not self._current_report:
            self._generate_report()
        path, _ = QFileDialog.getSaveFileName(self, "حفظ التقرير بصيغة JSON", "SINAX_Network_Report.json", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self._current_report, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "تم الحفظ", f"تم تصدير التقرير إلى:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر حفظ الملف: {e}")

    # -------------------------------------------------------------
    # Helpers & UI Styles
    # -------------------------------------------------------------
    def _create_section_frame(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        return frame

    def _create_metric_chip(self, title: str, default_val: str) -> QFrame:
        chip = QFrame()
        chip.setStyleSheet("""
            QFrame {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        l = QVBoxLayout(chip)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(4)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 9))
        t.setStyleSheet("color: #94A3B8;")
        l.addWidget(t)

        v = QLabel(default_val)
        v.setObjectName("val_lbl")
        v.setFont(QFont("Segoe UI", 12, QFont.Bold))
        v.setStyleSheet("color: #38BDF8;")
        l.addWidget(v)

        return chip

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                color: #F8FAFC;
                font-family: Consolas, monospace;
            }
            QLineEdit:focus { border: 1px solid #0078D4; }
        """

    def _primary_button_style(self) -> str:
        return """
            QPushButton {
                background: #0078D4;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: bold;
                height: 32px;
            }
            QPushButton:hover { background: #106EBE; }
            QPushButton:disabled { background: #334155; color: #64748B; }
        """

    def _danger_button_style(self) -> str:
        return """
            QPushButton {
                background: #EF4444;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: bold;
                height: 32px;
            }
            QPushButton:hover { background: #DC2626; }
        """

    def _secondary_button_style(self) -> str:
        return """
            QPushButton {
                background: #334155;
                color: #F8FAFC;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: bold;
                height: 32px;
            }
            QPushButton:hover { background: #475569; }
        """

    def _table_style(self) -> str:
        return """
            QTableWidget {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                gridline-color: #334155;
                selection-background-color: #0078D4;
            }
            QTableWidget::item { padding: 5px 8px; }
            QTableWidget::item:alternate { background: #131E33; }
            QHeaderView::section {
                background: #0A0F1D;
                color: #94A3B8;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #334155;
                font-weight: bold;
            }
        """
