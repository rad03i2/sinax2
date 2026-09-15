# -*- coding: utf-8 -*-
"""
Storage & Disk Maintenance Subpage for SINAX.
Combines low-storage diagnosis with structured Windows CHKDSK file system inspection.
Provides read-only scanning and scheduled boot repair with explicit user confirmation.
"""

import threading
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.chkdsk_service import ChkdskService
from app.services.maintenance.safe_cleanup_orchestrator import SafeCleanupOrchestrator
from app.services.maintenance.snapshot_history_service import SnapshotHistoryService
from app.ui.icons import get_icon


class ChkdskSignals(QObject):
    progress = Signal(str)
    finished = Signal(dict)


class StorageDiskSubpage(QWidget):
    """Subpage for file system integrity checking and storage health."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Overview Card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        c_lay = QHBoxLayout(card)
        c_lay.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("storage", color_hex="#38BDF8", size=36).pixmap(36, 36))
        c_lay.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(3)
        t_l = QLabel("فحص سلامة نظام الملفات (CHKDSK)")
        t_l.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        s_l = QLabel("فحص بنية جداول نظام الملفات واكتشاف أي تلف في الفهارس دون الحاجة لفصل القرص.")
        s_l.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t_l)
        txt_col.addWidget(s_l)
        c_lay.addLayout(txt_col, 1)

        # Drive selector
        c_lay.addWidget(QLabel("القرص:"))
        self.drive_combo = QComboBox()
        self.drive_combo.addItems(["C:", "D:", "E:"])
        self.drive_combo.setStyleSheet("""
            QComboBox {
                background-color: #21262D;
                color: #F0F6FC;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: bold;
            }
        """)
        c_lay.addWidget(self.drive_combo)

        layout.addWidget(card)

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(12)

        self.btn_scan = QPushButton("فحص نظام الملفات (قراءة فقط)")
        self.btn_scan.setIcon(get_icon("search", color_hex="#FFFFFF"))
        self.btn_scan.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        self.btn_scan.clicked.connect(self._run_chkdsk_scan)
        btn_bar.addWidget(self.btn_scan)

        self.btn_repair = QPushButton("جدولة الإصلاح عند إعادة التشغيل")
        self.btn_repair.setIcon(get_icon("clean", color_hex="#FFFFFF"))
        self.btn_repair.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #FBBF24;
                border: 1px solid #B45309;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363D;
            }
        """)
        self.btn_repair.clicked.connect(self._schedule_chkdsk_repair)
        btn_bar.addWidget(self.btn_repair)

        btn_bar.addStretch(1)
        layout.addLayout(btn_bar)

        # Progress / Indicator
        self.pbar = QProgressBar()
        self.pbar.setRange(0, 0) # Indeterminate
        self.pbar.setVisible(False)
        self.pbar.setStyleSheet("""
            QProgressBar {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.pbar)

        # Results Panel
        self.results_box = QTextEdit()
        self.results_box.setReadOnly(True)
        self.results_box.setStyleSheet("""
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
        self.results_box.setText("انقر على 'فحص نظام الملفات' لبدء فحص مباشر بدون تعديل...")
        layout.addWidget(self.results_box, 1)

    def _run_chkdsk_scan(self):
        drive = self.drive_combo.currentText()
        self.btn_scan.setEnabled(False)
        self.pbar.setVisible(True)
        self.results_box.setText(f"[+] بدء فحص نظام الملفات على القرص {drive}...\n")

        signals = ChkdskSignals()
        signals.progress.connect(lambda msg: self.results_box.append(msg))
        signals.finished.connect(self._on_scan_finished)

        def worker():
            res = ChkdskService.run_chkdsk_scan_only(
                drive_letter=drive,
                progress_cb=lambda m: signals.progress.emit(m),
            )
            signals.finished.emit(res)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_scan_finished(self, result: dict):
        self.pbar.setVisible(False)
        self.btn_scan.setEnabled(True)

        msg = result.get("message_ar", "اكتمل الفحص.")
        fs = result.get("file_system", "NTFS")
        bad = result.get("bad_sectors_kb", 0)

        self.results_box.append(f"\n======================================")
        self.results_box.append(f"نظام الملفات: {fs}")
        self.results_box.append(f"القطاعات التالفة: {bad} KB")
        self.results_box.append(f"النتيجة: {msg}")
        self.results_box.append(f"======================================\n")

        SnapshotHistoryService().log_maintenance_action(
            "chkdsk_scan", f"فحص CHKDSK للقرص {self.drive_combo.currentText()}", "storage_disk", "completed", msg
        )

    def _schedule_chkdsk_repair(self):
        drive = self.drive_combo.currentText()
        reply = QMessageBox.question(
            self,
            "تأكيد جدولة الفحص",
            f"هل ترغب بجدولة فحص وإصلاح القرص {drive} عند إعادة تشغيل Windows القادمة؟\n"
            "سيتطلب هذا بعض الوقت أثناء عملية الإقلاع لإصلاح أي أخطاء ملفات.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            res = ChkdskService.schedule_chkdsk_repair_on_reboot(drive)
            self.results_box.append(f"\n[+] {res.get('message_ar', '')}\n")
            SnapshotHistoryService().log_maintenance_action(
                "chkdsk_schedule", f"جدولة CHKDSK /F للقرص {drive}", "storage_disk", "scheduled", res.get("message_ar", "")
            )
            QMessageBox.information(self, "نتيجة الجدولة", res.get("message_ar", ""))
