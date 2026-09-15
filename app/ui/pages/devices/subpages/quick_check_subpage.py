# -*- coding: utf-8 -*-
"""
SINAX Quick Hardware Check Subpage (صفحة الفحص الشامل والسريع للعتاد)
Runs a 9-stage comprehensive hardware verification pipeline and categorizes
results into Passed, Attention, and Issues without fake scores.
"""

from typing import List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.hardware_models import HardwareCheckItem
from app.services.devices.hardware_test_service import HardwareTestService
from app.ui.icons import get_icon


class HardwareCheckWorker(QThread):
    """Background worker for running the 9-stage hardware verification."""
    progress = Signal(str, int)
    finished = Signal(list)

    def run(self):
        items = HardwareTestService.run_full_check(lambda name, pct: self.progress.emit(name, pct))
        self.finished.emit(items)


class QuickCheckSubpage(QWidget):
    """Subpage for running comprehensive hardware diagnostics and viewing truthful findings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._worker: Optional[HardwareCheckWorker] = None
        self._results: List[HardwareCheckItem] = []
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
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(24, 20, 24, 24)
        self.layout.setSpacing(18)

        # Header
        top_bar = QHBoxLayout()
        title = QLabel("الفحص السريع والشامل للعتاد (Quick Hardware Doctor)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.btn_run = QPushButton("  بدء الفحص الشامل للعتاد")
        self.btn_run.setIcon(get_icon("play", "#FFFFFF", 16))
        self.btn_run.setFixedHeight(38)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background: #0078D4; color: #FFFFFF; border-radius: 6px;
                padding: 0 20px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background: #106EBE; }
            QPushButton:disabled { background: #334155; color: #64748B; }
        """)
        self.btn_run.clicked.connect(self.start_check)
        top_bar.addWidget(self.btn_run)
        self.layout.addLayout(top_bar)

        # 1. Pipeline Status Card
        self.status_card = QFrame()
        self.status_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        s_layout = QVBoxLayout(self.status_card)
        s_layout.setSpacing(10)

        s_head = QHBoxLayout()
        self.stage_lbl = QLabel("جاهز لبدء فحص عتاد ومكونات الجهاز.")
        self.stage_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.stage_lbl.setStyleSheet("color: #38BDF8; background: transparent;")
        s_head.addWidget(self.stage_lbl)
        s_head.addStretch()

        self.pct_lbl = QLabel("0%")
        self.pct_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.pct_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        s_head.addWidget(self.pct_lbl)
        s_layout.addLayout(s_head)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #0F172A; border: 1px solid #334155; border-radius: 4px; }
            QProgressBar::chunk { background: #0078D4; border-radius: 3px; }
        """)
        s_layout.addWidget(self.progress_bar)

        desc = QLabel(
            "يقوم الفحص الشامل باختبار 9 مراحل حيوية (المعالج، الذاكرة، أقراص SMART، كروت الشاشة، "
            "صحة البطارية، أخطاء مدير الأجهزة، أمان الإقلاع، سرعة القراءة، وحساسات الحرارة)."
        )
        desc.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        s_layout.addWidget(desc)
        self.layout.addWidget(self.status_card)

        # 2. Results Container
        self.results_container = QWidget()
        self.results_container.setStyleSheet("background: transparent;")
        self.res_layout = QVBoxLayout(self.results_container)
        self.res_layout.setContentsMargins(0, 0, 0, 0)
        self.res_layout.setSpacing(10)
        self.layout.addWidget(self.results_container)

        self.layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def start_check(self):
        self.btn_run.setEnabled(False)
        self.progress_bar.setValue(0)
        self.stage_lbl.setText("بدء الفحص...")
        self.pct_lbl.setText("0%")

        # Clear previous items
        while self.res_layout.count() > 0:
            child = self.res_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._worker = HardwareCheckWorker()
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, stage_name: str, pct: int):
        self.stage_lbl.setText(f"قيد الفحص: {stage_name}")
        self.progress_bar.setValue(pct)
        self.pct_lbl.setText(f"{pct}%")

    def _on_finished(self, items: List[HardwareCheckItem]):
        self.btn_run.setEnabled(True)
        self.progress_bar.setValue(100)
        self.pct_lbl.setText("100%")
        self.stage_lbl.setText("اكتمل الفحص الشامل لجميع المكونات.")
        self._results = items

        passed = [i for i in items if i.status == "passed"]
        warnings = [i for i in items if i.status == "warning"]
        attentions = [i for i in items if i.status == "attention"]

        summary_box = QFrame()
        summary_box.setStyleSheet("background: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 12px 18px;")
        sm_layout = QHBoxLayout(summary_box)
        sm_text = QLabel(
            f"<b>ملخص نتائج الفحص:</b> {len(passed)} عناصر سليمة تمامًا  |  "
            f"{len(attentions)} ملاحظات وإرشادات  |  {len(warnings)} تنبيهات تحتاج انتباهًا"
        )
        sm_text.setStyleSheet("color: #F8FAFC; background: transparent;")
        sm_layout.addWidget(sm_text)
        self.res_layout.addWidget(summary_box)

        # Render check items
        for item in items:
            card = self._create_item_card(item)
            self.res_layout.addWidget(card)

    def _create_item_card(self, item: HardwareCheckItem) -> QFrame:
        card = QFrame()
        bg_color = "#1E293B"
        border_color = "#334155"
        status_color = "#10B981"
        status_badge = "سليم (Passed)"

        if item.status == "warning":
            bg_color = "#451A03"
            border_color = "#B45309"
            status_color = "#F59E0B"
            status_badge = "تنبيه (Warning)"
        elif item.status == "attention":
            bg_color = "#1E293B"
            border_color = "#0284C7"
            status_color = "#38BDF8"
            status_badge = "ملاحظة (Note)"

        card.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 12px 16px;
            }}
        """)
        c_layout = QHBoxLayout(card)
        c_layout.setSpacing(14)

        icon_lbl = QLabel()
        icon_name = "check" if item.status == "passed" else ("warning" if item.status == "warning" else "info")
        icon_lbl.setPixmap(get_icon(icon_name, status_color, 20).pixmap(20, 20))
        c_layout.addWidget(icon_lbl)

        vbox = QVBoxLayout()
        vbox.setSpacing(4)
        title_lbl = QLabel(f"[{item.category}] {item.name}")
        title_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_lbl.setStyleSheet("color: #F8FAFC; background: transparent;")
        msg_lbl = QLabel(item.message_ar)
        msg_lbl.setStyleSheet("color: #CBD5E1; font-size: 11px; background: transparent;")
        vbox.addWidget(title_lbl)
        vbox.addWidget(msg_lbl)
        c_layout.addLayout(vbox, 1)

        badge = QLabel(status_badge)
        badge.setStyleSheet(f"""
            background: {status_color}; color: #FFFFFF; border-radius: 4px;
            padding: 3px 8px; font-size: 10px; font-weight: bold;
        """)
        c_layout.addWidget(badge)
        return card
