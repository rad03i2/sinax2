# -*- coding: utf-8 -*-
"""
SINAX Network Doctor Subpage (صفحة طبيب تشخيص وإصلاح الاتصال)
Provides 5-stage visual diagnostic workflow, pinpointed root cause analysis,
and 1-click safe repairs (Flush DNS, DHCP Renew, Adapter Restart, Winsock Reset).
"""

from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.network.doctor_service import NetworkDoctorService
from app.services.network.network_models import DoctorDiagnosticReport
from app.ui.icons import get_icon


class DoctorWorker(QObject):
    """Background worker for executing the 5-stage diagnostic pipeline."""
    stage_update = Signal(int, int, str)
    finished = Signal(object)

    def run(self):
        def cb(step: int, total: int, msg: str):
            self.stage_update.emit(step, total, msg)

        report = NetworkDoctorService.run_full_diagnosis(progress_cb=cb)
        self.finished.emit(report)


class DoctorSubpage(QWidget):
    """Subpage for diagnosing network bottlenecks and 1-click repairs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._thread: Optional[QThread] = None
        self._worker: Optional[DoctorWorker] = None
        self._stage_cards = []
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
        layout.setSpacing(16)

        # 1. Header Bar
        top_bar = QHBoxLayout()
        title = QLabel("طبيب تشخيص وإصلاح الاتصال (Network Doctor)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.diagnose_btn = QPushButton("  فحص وتشخيص الآن")
        self.diagnose_btn.setIcon(get_icon("doctor", "#FFFFFF", 18))
        self.diagnose_btn.setFixedHeight(40)
        self.diagnose_btn.setStyleSheet("""
            QPushButton {
                background: #0078D4;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 0 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #106EBE; }
            QPushButton:disabled { background: #334155; color: #64748B; }
        """)
        self.diagnose_btn.clicked.connect(self._run_diagnosis)
        top_bar.addWidget(self.diagnose_btn)
        layout.addLayout(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 5)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #1E293B; border-radius: 3px; }
            QProgressBar::chunk { background: #10B981; border-radius: 3px; }
        """)
        layout.addWidget(self.progress_bar)

        # 2. Root Cause Result Card
        self.result_card = QFrame()
        self.result_card.setStyleSheet("""
            QFrame {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        res_layout = QVBoxLayout(self.result_card)
        res_layout.setSpacing(8)

        self.result_status = QLabel("جاهز لبدء التشخيص الشامل")
        self.result_status.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.result_status.setStyleSheet("color: #38BDF8;")
        res_layout.addWidget(self.result_status)

        self.result_desc = QLabel("يقوم طبيب الشبكة بفحص 5 مراحل متتالية: كرت الشبكة، عنوان IP واكتشاف APIPA، استجابة الراوتر، دقة DNS، واتصال HTTPS.")
        self.result_desc.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.5;")
        self.result_desc.setWordWrap(True)
        res_layout.addWidget(self.result_desc)

        layout.addWidget(self.result_card)

        # 3. Stages Visual Timeline (5 Cards)
        stages_title = QLabel("مراحل مسار فحص الاتصال الخمس:")
        stages_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        stages_title.setStyleSheet("color: #E2E8F0; margin-top: 6px;")
        layout.addWidget(stages_title)

        stage_defs = [
            ("محول الشبكة (Network Adapter)", "التأكد من تشغيل كرت Wi-Fi أو Ethernet وتوصيله"),
            ("تكوين عنوان IP و DHCP", "التحقق من الحصول على IP صالح وكشف أخطاء APIPA (169.254.x.x)"),
            ("بوابة الاتصال بالراوتر (Gateway)", "فحص الاتصال الداخلي بالراوتر المنزلي أو المكتبي"),
            ("نظام أسماء النطاقات (DNS Lookup)", "فحص سرعة استجابة خوادم DNS في حل عناوين الويب"),
            ("اتصال الويب الآمن (HTTPS)", "فحص تبادل حزم البيانات مع خوادم الويب العالمية"),
        ]

        self._stage_cards = []
        for name, desc in stage_defs:
            card = self._create_stage_card(name, desc)
            self._stage_cards.append(card)
            layout.addWidget(card)

        # 4. Safe Sequential Repairs Wizard
        repairs_title = QLabel("أدوات الإصلاح السريع بنقرة واحدة (Safe 1-Click Fixes):")
        repairs_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        repairs_title.setStyleSheet("color: #E2E8F0; margin-top: 10px;")
        layout.addWidget(repairs_title)

        repairs_box = QHBoxLayout()
        repairs_box.setSpacing(10)

        def make_repair_btn(title: str, sub: str, callback, color: str = "#0078D4"):
            btn = QPushButton(f"  {title}")
            btn.setIcon(get_icon("repair", "#FFFFFF", 16))
            btn.setFixedHeight(46)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    color: #FFFFFF;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: #2D3748;
                    border-color: {color};
                }}
            """)
            btn.clicked.connect(callback)
            return btn

        repairs_box.addWidget(make_repair_btn("مسح DNS Cache", "آمن وفوري", self._do_flush_dns, "#10B981"))
        repairs_box.addWidget(make_repair_btn("تجديد عنوان IP (DHCP)", "إعادة طلب IP", self._do_renew_dhcp, "#38BDF8"))
        repairs_box.addWidget(make_repair_btn("إعادة تشغيل كرت الشبكة", "يتطلب موافقة", self._do_restart_adapter, "#F59E0B"))
        repairs_box.addWidget(make_repair_btn("إعادة ضبط Winsock", "إصلاح متقدم", self._do_winsock_reset, "#EF4444"))

        layout.addLayout(repairs_box)
        layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_stage_card(self, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        h = QHBoxLayout(card)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setObjectName("StageIcon")
        icon_lbl.setPixmap(get_icon("network", "#64748B", 20).pixmap(20, 20))
        h.addWidget(icon_lbl)

        info_l = QVBoxLayout()
        info_l.setSpacing(2)

        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t_lbl.setStyleSheet("color: #FFFFFF;")
        info_l.addWidget(t_lbl)

        d_lbl = QLabel(desc)
        d_lbl.setObjectName("StageDesc")
        d_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        info_l.addWidget(d_lbl)

        h.addLayout(info_l, 1)

        badge = QLabel("في الانتظار")
        badge.setObjectName("StageBadge")
        badge.setStyleSheet("""
            background: #334155;
            color: #94A3B8;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: bold;
        """)
        h.addWidget(badge)

        return card

    def _run_diagnosis(self):
        self.diagnose_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.result_status.setText("جاري فحص مسار الشبكة خطوة بخطوة...")
        self.result_status.setStyleSheet("color: #F59E0B;")

        for card in self._stage_cards:
            b = card.findChild(QLabel, "StageBadge")
            if b:
                b.setText("جاري الفحص...")
                b.setStyleSheet("background: rgba(245, 158, 11, 0.2); color: #F59E0B; border-radius: 6px; padding: 4px 10px; font-weight: bold;")

        self._thread = QThread()
        self._worker = DoctorWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.stage_update.connect(self._on_stage_update)
        self._worker.finished.connect(self._on_diagnosis_finished)

        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_stage_update(self, step: int, total: int, msg: str):
        self.progress_bar.setValue(step)
        self.result_desc.setText(msg)

    def _on_diagnosis_finished(self, report: DoctorDiagnosticReport):
        self.diagnose_btn.setEnabled(True)
        self.progress_bar.setValue(5)

        if report.overall_health == "healthy":
            self.result_status.setText("الاتصال سليم ومستقر تماماً ✓")
            self.result_status.setStyleSheet("color: #10B981;")
        elif report.overall_health == "warning":
            self.result_status.setText("تحذير: توجد مشكلة أو بطء في مسار الاتصال ⚠️")
            self.result_status.setStyleSheet("color: #F59E0B;")
        else:
            self.result_status.setText("تنبيه: انقطاع في مسار الاتصال ✗")
            self.result_status.setStyleSheet("color: #EF4444;")

        self.result_desc.setText(f"<b>السبب الجذري:</b> {report.root_cause_ar}<br><b>الإجراء المقترح:</b> {report.recommended_action_ar}")

        # Update stage cards
        for i, st in enumerate(report.stages):
            if i < len(self._stage_cards):
                card = self._stage_cards[i]
                b = card.findChild(QLabel, "StageBadge")
                d = card.findChild(QLabel, "StageDesc")
                ic = card.findChild(QLabel, "StageIcon")

                if d:
                    d.setText(st.summary)

                if st.status == "passed":
                    if b:
                        b.setText("سليم ✓")
                        b.setStyleSheet("background: rgba(16, 185, 129, 0.2); color: #10B981; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
                    if ic:
                        ic.setPixmap(get_icon("network", "#10B981", 20).pixmap(20, 20))
                else:
                    if b:
                        b.setText("عطل ✗" if st.status == "failed" else "تحذير ⚠️")
                        b.setStyleSheet("background: rgba(239, 68, 68, 0.2); color: #EF4444; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
                    if ic:
                        ic.setPixmap(get_icon("doctor", "#EF4444", 20).pixmap(20, 20))

    # Repair Handlers
    def _do_flush_dns(self):
        ok, msg = NetworkDoctorService.repair_flush_dns()
        QMessageBox.information(self, "مسح DNS Cache", msg)

    def _do_renew_dhcp(self):
        reply = QMessageBox.question(
            self,
            "تأكيد تجديد DHCP",
            "سيتم تحرير عنوان IP وطلب عنوان جديد من الراوتر. قد ينقطع الاتصال لثوانٍ معدودة.\nهل ترغب بالمتابعة؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok, msg = NetworkDoctorService.repair_renew_dhcp()
            QMessageBox.information(self, "تجديد DHCP", msg)

    def _do_restart_adapter(self):
        reply = QMessageBox.question(
            self,
            "تأكيد إعادة تشغيل المحول",
            "سيتم إيقاف كرت الشبكة وإعادة تشغيله فوراً لحل مشاكل التجمد.\nهل ترغب بالمتابعة؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok, msg = NetworkDoctorService.repair_restart_adapter()
            QMessageBox.information(self, "إعادة تشغيل المحول", msg)

    def _do_winsock_reset(self):
        reply = QMessageBox.question(
            self,
            "تأكيد إعادة ضبط Winsock",
            "هذا إصلاح متقدم لإعادة كتالوج مقابس الشبكة لحالته النظيفة الأصلية.\nقد يتطلب ذلك إعادة تشغيل ويندوز لتثبيت الإعدادات.\nهل أنت متأكد؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok, msg = NetworkDoctorService.repair_winsock_reset()
            QMessageBox.information(self, "إعادة ضبط Winsock", msg)
