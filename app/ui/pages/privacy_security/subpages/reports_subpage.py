# -*- coding: utf-8 -*-
"""
Privacy & Security Reports Subpage (تقارير الأمان والخصوصية) for SINAX Privacy & Security Center.
Features:
1. Multi-format audit report exporter (HTML, JSON, TXT, CSV).
2. Privacy Mode toggle that masks username, hostname, IP, and personal paths.
3. Security Activity and Audit Log viewer with real database records.
4. Comprehensive privacy posture health summary.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.privacy_security.privacy_db import PrivacyDatabase
from app.services.privacy_security.privacy_report_service import PrivacyReportService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class ReportsSubpage(QWidget):
    """Privacy Audit & Reporting Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._report_service = PrivacyReportService()
        self._db = PrivacyDatabase()
        self._last_exported_file: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: #0D1117;")

        container = QWidget()
        container.setStyleSheet("background-color: #0D1117;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # 1. Header
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self.btn_back = QPushButton(" العودة للرئيسية")
        self.btn_back.setIcon(get_icon("arrow_back", color="#8B949E"))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #161B22; color: #8B949E; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #21262D; color: #F0F6FC; }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.btn_back)

        title_vbox = QVBoxLayout()
        t_lbl = QLabel("تقارير الأمان وسجل التدقيق (Privacy Reports & Audit)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("تصدير تقارير التدقيق الأمني بصيغ متعددة مع نمط حجب البيانات الحساسة (Privacy Mode) ومراجعة سجل الأحداث.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        layout.addLayout(header_row)

        # 2. Privacy Mode Card
        pm_card = QFrame()
        pm_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        pm_vbox = QVBoxLayout(pm_card)
        pm_vbox.setSpacing(8)

        pm_top = QHBoxLayout()
        pm_icon = QLabel()
        pm_icon.setPixmap(get_icon("shield", color="#38BDF8", size=22).pixmap(22, 22))
        pm_top.addWidget(pm_icon)

        pm_title = QLabel("نمط الخصوصية التلقائي (Privacy Mode)")
        pm_title.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        pm_top.addWidget(pm_title)
        pm_top.addStretch(1)

        self.chk_privacy_mode = QCheckBox("تفعيل حجب البيانات الحساسة (موصى به)")
        self.chk_privacy_mode.setChecked(True)
        self.chk_privacy_mode.setStyleSheet("color: #34D399; font-weight: bold; font-size: 12px;")
        pm_top.addWidget(self.chk_privacy_mode)
        pm_vbox.addLayout(pm_top)

        pm_desc = QLabel(
            "عند تفعيل هذا النمط، يتم حجب اسم المستخدم، اسم الجهاز، عناوين IP، والمسارات الشخصية تلقائياً "
            "في أي تقرير يتم تصديره، مما يتيح لك مشاركة التقرير مع جهات الدعم أو التدقيق الخارجي دون القلق من تسريب بياناتك."
        )
        pm_desc.setWordWrap(True)
        pm_desc.setStyleSheet("color: #8B949E; font-size: 12px; line-height: 1.5;")
        pm_vbox.addWidget(pm_desc)

        layout.addWidget(pm_card)

        # 3. Export Buttons Card
        exp_card = QFrame()
        exp_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        ec_vbox = QVBoxLayout(exp_card)
        ec_vbox.setSpacing(12)

        ec_t = QLabel("تصدير تقرير التدقيق الشامل:")
        ec_t.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px;")
        ec_vbox.addWidget(ec_t)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        # HTML
        btn_html = QPushButton(" تصدير تقرير HTML متجاوب")
        btn_html.setIcon(get_icon("globe", color="#FFFFFF"))
        btn_html.setStyleSheet("""
            QPushButton {
                background: #1F6FEB; color: #FFFFFF; border-radius: 6px; padding: 10px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #388BFD; }
        """)
        btn_html.clicked.connect(lambda: self._export_report("html", "SINAX_Privacy_Audit.html", "ملف HTML (*.html)"))
        btn_row.addWidget(btn_html)

        # JSON
        btn_json = QPushButton(" تصدير كائن JSON للمطورين")
        btn_json.setIcon(get_icon("document", color="#FFFFFF"))
        btn_json.setStyleSheet("""
            QPushButton {
                background: #238636; color: #FFFFFF; border-radius: 6px; padding: 10px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #2EA043; }
        """)
        btn_json.clicked.connect(lambda: self._export_report("json", "SINAX_Privacy_Audit.json", "ملف JSON (*.json)"))
        btn_row.addWidget(btn_json)

        # CSV
        btn_csv = QPushButton(" تصدير جدول CSV")
        btn_csv.setIcon(get_icon("download", color="#38BDF8"))
        btn_csv.setStyleSheet("""
            QPushButton {
                background: #1E293B; color: #38BDF8; border: 1px solid #38BDF8;
                border-radius: 6px; padding: 10px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #38BDF8; color: #0D1117; }
        """)
        btn_csv.clicked.connect(lambda: self._export_report("csv", "SINAX_Privacy_Audit.csv", "ملف CSV (*.csv)"))
        btn_row.addWidget(btn_csv)

        # TXT
        btn_txt = QPushButton(" تصدير نص TXT")
        btn_txt.setIcon(get_icon("report", color="#F0F6FC"))
        btn_txt.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 10px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; }
        """)
        btn_txt.clicked.connect(lambda: self._export_report("txt", "SINAX_Privacy_Audit.txt", "ملف نصي (*.txt)"))
        btn_row.addWidget(btn_txt)

        ec_vbox.addLayout(btn_row)
        layout.addWidget(exp_card)

        # 4. Audit Log Viewer Table
        log_card = QFrame()
        log_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        lc_vbox = QVBoxLayout(log_card)
        lc_vbox.setSpacing(10)

        lc_head = QHBoxLayout()
        lc_head.setSpacing(8)

        lc_icon = QLabel()
        lc_icon.setPixmap(get_icon("report", color="#38BDF8", size=20).pixmap(20, 20))
        lc_head.addWidget(lc_icon)

        self.lbl_log_title = QLabel("سجل العمليات والأحداث الأمنية المسجلة (Audit Logs):")
        self.lbl_log_title.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px;")
        lc_head.addWidget(self.lbl_log_title)
        lc_head.addStretch(1)

        btn_refresh = QPushButton("تحديث السجل")
        btn_refresh.setIcon(get_icon("refresh", color="#8B949E"))
        btn_refresh.setStyleSheet("background: #21262D; color: #8B949E; border: 1px solid #30363D; border-radius: 4px; padding: 4px 10px; font-size: 11px;")
        btn_refresh.clicked.connect(self._load_events_log)
        lc_head.addWidget(btn_refresh)
        lc_vbox.addLayout(lc_head)

        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(4)
        self.table_logs.setHorizontalHeaderLabels(["التاريخ والوقت", "نوع العملية", "الحالة", "المسار والهدف"])
        self.table_logs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_logs.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_logs.setAlternatingRowColors(True)
        self.table_logs.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117; alternate-background-color: #161B22;
                border: 1px solid #30363D; border-radius: 6px; gridline-color: #21262D; color: #F0F6FC;
            }
            QHeaderView::section {
                background-color: #161B22; color: #8B949E; font-weight: bold; border: 1px solid #21262D; padding: 6px;
            }
        """)
        lc_vbox.addWidget(self.table_logs)

        layout.addWidget(log_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._load_events_log()

    def _export_report(self, fmt: str, default_name: str, file_filter: str):
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            f"تصدير تقرير الخصوصية ({fmt.upper()})",
            default_name,
            file_filter
        )
        if not save_path:
            return

        pm = self.chk_privacy_mode.isChecked()
        ok, msg = self._report_service.export_report(save_path, fmt=fmt, apply_privacy_mode=pm)

        if ok:
            self._last_exported_file = save_path
            reply = QMessageBox.information(
                self,
                "تم تصدير التقرير",
                f"تم تصدير التقرير بنجاح!\n\nالملف:\n{save_path}\n\nهل ترغب في فتح المجلد الحاوي؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                os.startfile(os.path.dirname(save_path))
        else:
            QMessageBox.critical(self, "فشل التصدير", msg)

    def _load_events_log(self):
        events = self._db.get_recent_events(limit=100)
        self.table_logs.setRowCount(len(events))

        for idx, ev in enumerate(events):
            ts = ev.get("timestamp", "—")
            et = ev.get("event_type", "—")
            st = ev.get("status", "—")
            tgt = ev.get("target_path", "—")

            self.table_logs.setItem(idx, 0, QTableWidgetItem(ts))

            it_et = QTableWidgetItem(et)
            it_et.setForeground(QColor("#38BDF8"))
            self.table_logs.setItem(idx, 1, it_et)

            it_st = QTableWidgetItem(st)
            if "SUCCESS" in st:
                it_st.setForeground(QColor("#34D399"))
            elif "FAIL" in st:
                it_st.setForeground(QColor("#F87171"))
            else:
                it_st.setForeground(QColor("#FBBF24"))
            self.table_logs.setItem(idx, 2, it_st)

            it_tgt = QTableWidgetItem(tgt)
            it_tgt.setToolTip(tgt)
            self.table_logs.setItem(idx, 3, it_tgt)
