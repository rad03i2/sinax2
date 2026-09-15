# -*- coding: utf-8 -*-
"""
Windows Repair Subpage for SINAX Maintenance & Repair Center.
Implements the official Microsoft Servicing & System Integrity Pipeline:
- DISM CheckHealth, ScanHealth, and RestoreHealth (with ISO source support)
- SFC VerifyOnly (inspection) and SFC Scannow (repair)
- CBS Log Analyzer (extracts repaired/corrupted system files from CBS.log)
- DISM Log viewer
"""

import threading
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.log_analyzer_service import LogAnalyzerService
from app.services.maintenance.snapshot_history_service import SnapshotHistoryService
from app.services.maintenance.windows_repair_service import WindowsRepairService
from app.ui.icons import get_icon


class RepairWorkerSignals(QObject):
    progress = Signal(int, str)
    finished = Signal(dict)
    log_line = Signal(str)


class WindowsRepairSubpage(QWidget):
    """Orchestrates official DISM and SFC operations with CBS log insights."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        tabs = QTabWidget(self)
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363D;
                background-color: #0D1117;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #161B22;
                color: #8B949E;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #21262D;
                color: #38BDF8;
                border-bottom: 2px solid #38BDF8;
            }
        """)

        # Tab 1: Repair Wizard
        self.tab_wizard = QWidget()
        self._init_wizard_tab()
        tabs.addTab(self.tab_wizard, "معالج إصلاح ملفات وصورة Windows")

        # Tab 2: CBS Log Analyzer
        self.tab_cbs = QWidget()
        self._init_cbs_tab()
        tabs.addTab(self.tab_cbs, "تحليل سجل SFC و CBS")

        main_layout.addWidget(tabs)

    def _init_wizard_tab(self):
        layout = QVBoxLayout(self.tab_wizard)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Guidance banner
        guide = QFrame()
        guide.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        g_layout = QHBoxLayout(guide)
        g_icon = QLabel()
        g_icon.setPixmap(get_icon("doctor", color_hex="#38BDF8", size=32).pixmap(32, 32))
        g_layout.addWidget(g_icon)

        g_txt = QLabel(
            "تسلسل الإصلاح الرسمي الموصى به من Microsoft:\n"
            "1. فحص سلامة مستودع المكونات (DISM CheckHealth).\n"
            "2. إذا وجد تلف، تشغيل DISM RestoreHealth لإصلاح صورة النظام.\n"
            "3. تشغيل SFC Scannow لفحص واستبدال ملفات النظام المتضررة بنسخ سليمة."
        )
        g_txt.setStyleSheet("font-size: 12px; color: #C9D1D9; line-height: 1.4;")
        g_layout.addWidget(g_txt, 1)
        layout.addWidget(guide)

        # Action Buttons Row
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_dism_check = QPushButton("1. فحص DISM السريع")
        self.btn_dism_check.clicked.connect(self._run_dism_check)
        btn_bar.addWidget(self.btn_dism_check)

        self.btn_sfc_verify = QPushButton("2. تحقق SFC (بدون تعديل)")
        self.btn_sfc_verify.clicked.connect(self._run_sfc_verify)
        btn_bar.addWidget(self.btn_sfc_verify)

        self.btn_sfc_scan = QPushButton("3. إصلاح SFC Scannow")
        self.btn_sfc_scan.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold;")
        self.btn_sfc_scan.clicked.connect(self._run_sfc_scan)
        btn_bar.addWidget(self.btn_sfc_scan)

        self.btn_dism_restore = QPushButton("4. إصلاح صورة DISM")
        self.btn_dism_restore.setStyleSheet("background-color: #B45309; color: white; font-weight: bold;")
        self.btn_dism_restore.clicked.connect(self._run_dism_restore)
        btn_bar.addWidget(self.btn_dism_restore)

        layout.addLayout(btn_bar)

        # Progress bar
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 100)
        self.pbar.setValue(0)
        self.pbar.setVisible(False)
        self.pbar.setStyleSheet("""
            QProgressBar {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                height: 10px;
                text-align: center;
                color: #FFFFFF;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.pbar)

        # Live Output Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 12px;
                color: #58A6FF;
                padding: 10px;
            }
        """)
        self.console.setText("جاهز لتشغيل الفحص أو الإصلاح المطلوب. انقر على أي زر أعلاه للبدء...")
        layout.addWidget(self.console, 1)

    def _init_cbs_tab(self):
        layout = QVBoxLayout(self.tab_cbs)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_r = QHBoxLayout()
        t_l = QLabel("أحدث العمليات المسجلة في سجل Windows CBS (مرشحة لأوامر SFC [SR]):")
        t_l.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
        top_r.addWidget(t_l)
        top_r.addStretch(1)

        btn_load_cbs = QPushButton("تحديث قراءة السجل")
        btn_load_cbs.setIcon(get_icon("update", color_hex="#8B949E"))
        btn_load_cbs.clicked.connect(self._load_cbs_entries)
        top_r.addWidget(btn_load_cbs)
        layout.addLayout(top_r)

        self.cbs_table = QTableWidget()
        self.cbs_table.setColumnCount(4)
        self.cbs_table.setHorizontalHeaderLabels(["التوقيت", "الحالة", "الملف المتأثر", "التفاصيل المسجلة"])
        self.cbs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cbs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cbs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cbs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.cbs_table.setStyleSheet("""
            QTableWidget {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                gridline-color: #21262D;
                color: #C9D1D9;
            }
            QHeaderView::section {
                background-color: #0D1117;
                color: #8B949E;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.cbs_table, 1)

    def _run_dism_check(self):
        self.console.append("\n[+] تشغيل DISM /CheckHealth...")
        res = WindowsRepairService.run_dism_check_health()
        self.console.append(f"النتيجة: {res.get('message_ar', '')}")
        SnapshotHistoryService().log_maintenance_action(
            "dism_check_health", "فحص DISM CheckHealth", "windows_repair", res.get("status", "unknown"), res.get("message_ar", "")
        )

    def _run_sfc_verify(self):
        self._start_task(
            "sfc_verify",
            "تحقق SFC VerifyOnly",
            lambda cb: WindowsRepairService.run_sfc_verify_only(progress_cb=cb)
        )

    def _run_sfc_scan(self):
        self._start_task(
            "sfc_scannow",
            "إصلاح ملفات النظام SFC Scannow",
            lambda cb: WindowsRepairService.run_sfc_scannow(progress_cb=cb)
        )

    def _run_dism_restore(self):
        self._start_task(
            "dism_restore",
            "إصلاح مستودع المكونات DISM RestoreHealth",
            lambda cb: WindowsRepairService.run_dism_restore_health(progress_cb=cb)
        )

    def _start_task(self, action_id: str, action_title: str, task_func):
        self.pbar.setVisible(True)
        self.pbar.setValue(0)
        self.console.append(f"\n[+] جارٍ بدء: {action_title}...")

        signals = RepairWorkerSignals()
        signals.progress.connect(lambda p, s: (self.pbar.setValue(p), self.console.append(s)))
        signals.finished.connect(lambda r: self._on_task_finished(action_id, action_title, r))

        def worker():
            try:
                res = task_func(lambda pct, msg: signals.progress.emit(pct, msg))
                signals.finished.emit(res)
            except Exception as e:
                signals.finished.emit({"status": "error", "message_ar": str(e)})

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_task_finished(self, action_id: str, action_title: str, result: dict):
        self.pbar.setVisible(False)
        msg = result.get("message_ar", "اكتمل الإجراء.")
        self.console.append(f"[✓] النتيجة: {msg}")
        SnapshotHistoryService().log_maintenance_action(
            action_id, action_title, "windows_repair", result.get("status", "completed"), msg
        )

    def _load_cbs_entries(self):
        entries = LogAnalyzerService.get_sfc_cbs_entries(max_entries=30)
        self.cbs_table.setRowCount(len(entries))
        for idx, item in enumerate(entries):
            self.cbs_table.setItem(idx, 0, QTableWidgetItem(item.timestamp_str))
            self.cbs_table.setItem(idx, 1, QTableWidgetItem(item.status))
            self.cbs_table.setItem(idx, 2, QTableWidgetItem(item.file_path))
            self.cbs_table.setItem(idx, 3, QTableWidgetItem(item.details))
