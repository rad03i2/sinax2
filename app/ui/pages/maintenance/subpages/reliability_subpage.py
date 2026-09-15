# -*- coding: utf-8 -*-
"""
Reliability & Crash Inspector Subpage for SINAX Maintenance & Repair Center.
Displays recent application crashes (Event ID 1000), unexpected shutdowns (Event ID 6008/41),
and inspects BSOD crash dumps from C:\\Windows\\Minidump in read-only mode.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.event_reliability_service import EventReliabilityService
from app.ui.icons import get_icon


class ReliabilitySubpage(QWidget):
    """Subpage for stability analysis, crash tracking, and BSOD dumps inspection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self.load_crash_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header with stats
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_lay.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("doctor", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(3)
        t_l = QLabel("سجل موثوقية وأعطال النظام (ماذا حدث لجهازي؟)")
        t_l.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        self.lbl_stats = QLabel("جاري قراءة سجلات الأحداث...")
        self.lbl_stats.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t_l)
        txt_col.addWidget(self.lbl_stats)
        h_lay.addLayout(txt_col, 1)

        btn_open_dumps = QPushButton("فتح مجلد تفريغ الذاكرة (Minidump)")
        btn_open_dumps.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 6px 14px; border-radius: 6px;")
        btn_open_dumps.clicked.connect(EventReliabilityService.open_minidump_folder)
        h_lay.addWidget(btn_open_dumps)

        btn_refresh = QPushButton("تحديث")
        btn_refresh.setIcon(get_icon("update", color_hex="#8B949E"))
        btn_refresh.clicked.connect(self.load_crash_data)
        h_lay.addWidget(btn_refresh)

        layout.addWidget(header)

        # Table of Crashes
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["التوقيت", "نوع الحدث", "اسم التطبيق", "الموديول المتسبب", "رمز الخطأ / التفاصيل"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setStyleSheet("""
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
        layout.addWidget(self.table, 1)

    def load_crash_data(self):
        """Fetches recent crashes and BSOD records asynchronously without blocking UI."""
        import threading
        from PySide6.QtCore import QTimer

        def _bg():
            try:
                events = EventReliabilityService.get_recent_crash_events(days=7, max_results=40)
                dumps = EventReliabilityService.get_bsod_minidump_records()

                def _update():
                    try:
                        self.lbl_stats.setText(
                            f"تم رصد: {len(events)} حالات تعطل خلال آخر 7 أيام • {len(dumps)} ملفات تفريغ شاشة زرقاء (BSOD Minidumps)"
                        )
                        self.table.setRowCount(len(events))
                        for idx, ev in enumerate(events):
                            self.table.setItem(idx, 0, QTableWidgetItem(ev.timestamp_str))
                            self.table.setItem(idx, 1, QTableWidgetItem("تعطل تطبيق" if ev.event_type == "AppCrash" else "إغلاق غير متوقع"))
                            self.table.setItem(idx, 2, QTableWidgetItem(ev.app_name))
                            self.table.setItem(idx, 3, QTableWidgetItem(ev.fault_module or "-"))
                            self.table.setItem(idx, 4, QTableWidgetItem(f"{ev.exception_code} - {ev.details}"))
                    except Exception:
                        pass
                QTimer.singleShot(0, _update)
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True).start()
