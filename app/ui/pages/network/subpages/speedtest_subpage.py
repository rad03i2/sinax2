# -*- coding: utf-8 -*-
"""
SINAX Speed Test Subpage (صفحة اختبار سرعة الإنترنت الحقيقي)
Runs real HTTPS chunked tests with live progress, Mbps/MBps conversions,
download time estimates, activity rating badges, and historical comparison table.
"""

from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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

from app.services.network.network_db import NetworkDatabase
from app.services.network.network_models import SpeedTestResult
from app.services.network.speedtest_service import SpeedTestService
from app.ui.icons import get_icon


class SpeedTestWorker(QObject):
    """Background worker for running the speed test without freezing GUI."""
    progress_msg = Signal(str)
    progress_val = Signal(int)
    live_speed = Signal(float)  # current Mbps
    finished = Signal(object)   # SpeedTestResult

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        def latency_cb(ratio: float, msg: str):
            self.progress_msg.emit(msg)
            self.progress_val.emit(int(ratio * 20))

        def download_cb(ratio: float, mbps: float):
            self.progress_msg.emit(f"اختبار سرعة التنزيل: {mbps:.1f} Mbps")
            self.progress_val.emit(20 + int(ratio * 50))
            self.live_speed.emit(mbps)

        def upload_cb(ratio: float, mbps: float):
            self.progress_msg.emit(f"اختبار سرعة الرفع: {mbps:.1f} Mbps")
            self.progress_val.emit(70 + int(ratio * 30))
            self.live_speed.emit(mbps)

        res = SpeedTestService.run_full_test(
            latency_cb=latency_cb,
            download_cb=download_cb,
            upload_cb=upload_cb,
            is_cancelled=lambda: self._cancelled
        )
        self.finished.emit(res)


class SpeedTestSubpage(QWidget):
    """Subpage for executing and visualizing speed tests."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._thread: Optional[QThread] = None
        self._worker: Optional[SpeedTestWorker] = None
        self._init_ui()
        self._load_history()

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
        top_bar = QHBoxLayout()
        title = QLabel("اختبار سرعة الإنترنت الحقيقي (SINAX Speed Test)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # 2. Main Speed Gauge Card
        self.gauge_card = QFrame()
        self.gauge_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)
        gauge_layout = QVBoxLayout(self.gauge_card)
        gauge_layout.setContentsMargins(24, 24, 24, 24)
        gauge_layout.setSpacing(14)
        gauge_layout.setAlignment(Qt.AlignCenter)

        self.speed_number = QLabel("0.0")
        self.speed_number.setFont(QFont("Segoe UI", 48, QFont.Bold))
        self.speed_number.setAlignment(Qt.AlignCenter)
        self.speed_number.setStyleSheet("color: #38BDF8;")
        gauge_layout.addWidget(self.speed_number)

        self.speed_unit = QLabel("Mbps (ميغابت في الثانية)")
        self.speed_unit.setFont(QFont("Segoe UI", 12))
        self.speed_unit.setAlignment(Qt.AlignCenter)
        self.speed_unit.setStyleSheet("color: #94A3B8;")
        gauge_layout.addWidget(self.speed_unit)

        self.status_msg = QLabel("اضغط على زر (بدء الاختبار) للقياس الحقيقي المباشر")
        self.status_msg.setFont(QFont("Segoe UI", 12))
        self.status_msg.setAlignment(Qt.AlignCenter)
        self.status_msg.setStyleSheet("color: #E2E8F0;")
        gauge_layout.addWidget(self.status_msg)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #334155;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: #0078D4;
                border-radius: 4px;
            }
        """)
        gauge_layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        self.start_btn = QPushButton("  بدء اختبار السرعة الآن")
        self.start_btn.setIcon(get_icon("speedtest", "#FFFFFF", 18))
        self.start_btn.setFixedHeight(44)
        self.start_btn.setFixedWidth(240)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #0078D4;
                color: #FFFFFF;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #106EBE; }
            QPushButton:disabled { background: #334155; color: #64748B; }
        """)
        self.start_btn.clicked.connect(self._start_speed_test)
        btn_row.addWidget(self.start_btn)
        gauge_layout.addLayout(btn_row)

        layout.addWidget(self.gauge_card)

        # 3. Final Metric Tiles (Download, Upload, Ping, Jitter, Loss)
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(12)

        self.card_dl = self._create_metric_card("سرعة التنزيل (Download)", "— Mbps", "— MB/s", "#38BDF8")
        self.card_ul = self._create_metric_card("سرعة الرفع (Upload)", "— Mbps", "— MB/s", "#A855F7")
        self.card_ping = self._create_metric_card("زمن الاستجابة (Ping)", "— ms", "الحد الأدنى: —", "#10B981")
        self.card_jitter = self._create_metric_card("التقلب (Jitter)", "— ms", "فقد الحزم: 0%", "#F59E0B")

        metrics_grid.addWidget(self.card_dl, 0, 0)
        metrics_grid.addWidget(self.card_ul, 0, 1)
        metrics_grid.addWidget(self.card_ping, 0, 2)
        metrics_grid.addWidget(self.card_jitter, 0, 3)
        layout.addLayout(metrics_grid)

        # 4. Ratings & Download Estimator Card
        self.estimator_card = QFrame()
        self.estimator_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 14px;")
        est_layout = QVBoxLayout(self.estimator_card)

        est_title = QLabel("تقدير زمن تحميل الملفات الشائعة وتقييم الاتصال:")
        est_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        est_title.setStyleSheet("color: #F8FAFC;")
        est_layout.addWidget(est_title)

        self.est_details = QLabel("أجرِ اختبار السرعة لعرض الوقت التقديري لتنزيل ملفات 5GB و 10GB وتقييم جودة الألعاب والبث بدقة.")
        self.est_details.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.6;")
        self.est_details.setWordWrap(True)
        est_layout.addWidget(self.est_details)
        layout.addWidget(self.estimator_card)

        # 5. Speed History Table
        hist_title = QLabel("سجل الاختبارات السابقة")
        hist_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        hist_title.setStyleSheet("color: #E2E8F0; margin-top: 8px;")
        layout.addWidget(hist_title)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "التاريخ والوقت", "التنزيل (Mbps)", "الرفع (Mbps)", "Ping (ms)", "Jitter (ms)", "فقد الحزم", "المزود"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setFixedHeight(180)
        self.history_table.setStyleSheet("""
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
        layout.addWidget(self.history_table)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_metric_card(self, title: str, main_val: str, sub_val: str, border_col: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background: #1E293B;
                border: 1px solid #334155;
                border-right: 4px solid {border_col};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        l = QVBoxLayout(f)
        l.setSpacing(4)
        l.setContentsMargins(10, 8, 10, 8)

        t = QLabel(title)
        t.setStyleSheet("color: #94A3B8; font-size: 12px;")
        l.addWidget(t)

        m = QLabel(main_val)
        m.setObjectName("MainVal")
        m.setFont(QFont("Segoe UI", 16, QFont.Bold))
        m.setStyleSheet("color: #FFFFFF;")
        l.addWidget(m)

        s = QLabel(sub_val)
        s.setObjectName("SubVal")
        s.setStyleSheet("color: #64748B; font-size: 11px;")
        l.addWidget(s)
        return f

    def _start_speed_test(self):
        self.start_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.speed_number.setText("0.0")

        self._thread = QThread()
        self._worker = SpeedTestWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress_msg.connect(self.status_msg.setText)
        self._worker.progress_val.connect(self.progress_bar.setValue)
        self._worker.live_speed.connect(lambda v: self.speed_number.setText(f"{v:.1f}"))
        self._worker.finished.connect(self._on_speed_test_finished)

        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_speed_test_finished(self, result: Optional[SpeedTestResult]):
        self.start_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_msg.setText("اكتمل اختبار السرعة بنجاح ✓")

        if not result:
            self.status_msg.setText("تعذر إتمام الاختبار. تحقق من اتصالك بالإنترنت.")
            return

        self.speed_number.setText(f"{result.download_mbps:.1f}")

        # Update cards
        dl_card_m = self.card_dl.findChild(QLabel, "MainVal")
        dl_card_s = self.card_dl.findChild(QLabel, "SubVal")
        if dl_card_m and dl_card_s:
            dl_card_m.setText(f"{result.download_mbps:.1f} Mbps")
            dl_card_s.setText(f"≈ {result.download_mbyte_s:.2f} MB/s")

        ul_card_m = self.card_ul.findChild(QLabel, "MainVal")
        ul_card_s = self.card_ul.findChild(QLabel, "SubVal")
        if ul_card_m and ul_card_s:
            ul_card_m.setText(f"{result.upload_mbps:.1f} Mbps")
            ul_card_s.setText(f"≈ {result.upload_mbyte_s:.2f} MB/s")

        p_m = self.card_ping.findChild(QLabel, "MainVal")
        if p_m:
            p_m.setText(f"{result.ping_ms:.1f} ms")

        j_m = self.card_jitter.findChild(QLabel, "MainVal")
        j_s = self.card_jitter.findChild(QLabel, "SubVal")
        if j_m and j_s:
            j_m.setText(f"{result.jitter_ms:.1f} ms")
            j_s.setText(f"فقد الحزم: {result.packet_loss_percent:.0f}%")

        # Ratings & Download Estimator
        t10 = result.estimate_download_time_str(10.0)
        t50 = result.estimate_download_time_str(50.0)
        ratings = result.get_service_rating()
        rat_str = " • ".join([f"{k}: <b>{v}</b>" for k, v in ratings.items()])

        self.est_details.setText(
            f"• التقدير الواقعي للتنزيل: ملف 10 GB يستغرق <b>{t10}</b> | ملف 50 GB يستغرق <b>{t50}</b>.<br>"
            f"• تقييم الأنشطة: {rat_str}"
        )

        self._load_history()

    def _load_history(self):
        """Populates the history table from SQLite database."""
        tests = NetworkDatabase.get_recent_speed_tests(limit=15)
        self.history_table.setRowCount(len(tests))
        for row, t in enumerate(tests):
            ts_str = t.timestamp.strftime("%Y-%m-%d %H:%M")
            self.history_table.setItem(row, 0, QTableWidgetItem(ts_str))
            self.history_table.setItem(row, 1, QTableWidgetItem(f"{t.download_mbps:.1f}"))
            self.history_table.setItem(row, 2, QTableWidgetItem(f"{t.upload_mbps:.1f}"))
            self.history_table.setItem(row, 3, QTableWidgetItem(f"{t.ping_ms:.1f}"))
            self.history_table.setItem(row, 4, QTableWidgetItem(f"{t.jitter_ms:.1f}"))
            self.history_table.setItem(row, 5, QTableWidgetItem(f"{t.packet_loss_percent:.0f}%"))
            self.history_table.setItem(row, 6, QTableWidgetItem(t.provider_name or "Cloudflare"))
