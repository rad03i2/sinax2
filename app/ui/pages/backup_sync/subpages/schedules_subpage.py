# -*- coding: utf-8 -*-
"""
SINAX Schedules & Automated Backup Subpage (النسخ المجدول).
Tracks scheduled backup plans, freshness indicators, missed backup alerts,
and integration with Windows Task Scheduler (schtasks).
"""

from pathlib import Path
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app.services.backup_sync.backup_coordinator import BackupCoordinator
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.models import BackupProfile
from app.services.backup_sync.schedule_service import ScheduleService, ScheduleStatus
from app.ui.icons import get_icon
from app.ui.pages.backup_sync.dialogs.backup_progress_dialog import BackupProgressDialog


class SchedulesSubpage(QWidget):
    """Cockpit for managing automated schedules and Windows Task Scheduler tasks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self.schedule_service = ScheduleService(self.db)
        self._statuses = []
        self._init_ui()
        self.load_schedules()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("clock", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("النسخ الاحتياطي المجدول والمهام التلقائية")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("إدارة جداول التشغيل الآلي والتكامل مع Windows Task Scheduler للعمل في الخلفية دون الحاجة لإبقاء البرنامج مفتوحاً.")
        d.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        layout.addWidget(header)

        # Schedules Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["اسم الخطة", "نوع الجدولة", "التوقيت", "آخر تشغيل", "الموعد القادم", "الحالة"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
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

        # Buttons
        b_row = QHBoxLayout()
        btn_refresh = QPushButton("تحديث")
        btn_refresh.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 16px; border-radius: 6px;")
        btn_refresh.clicked.connect(self.load_schedules)
        b_row.addWidget(btn_refresh)

        btn_win_task = QPushButton("تسجيل في مهام Windows (Task Scheduler)")
        btn_win_task.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        btn_win_task.clicked.connect(self._register_win_task)
        b_row.addWidget(btn_win_task)

        btn_run_now = QPushButton("تشغيل الخطة المحددة الآن")
        btn_run_now.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        btn_run_now.clicked.connect(self._run_selected_now)
        b_row.addWidget(btn_run_now)

        b_row.addStretch(1)
        layout.addLayout(b_row)

    def load_schedules(self):
        profiles = self.db.list_profiles()
        self._statuses = [self.schedule_service.get_profile_schedule_status(p) for p in profiles]
        self.table.setRowCount(len(self._statuses))

        for row, st in enumerate(self._statuses):
            self.table.setItem(row, 0, QTableWidgetItem(st.profile_name))
            self.table.setItem(row, 1, QTableWidgetItem(st.schedule_type))
            self.table.setItem(row, 2, QTableWidgetItem(st.schedule_time))
            self.table.setItem(row, 3, QTableWidgetItem(st.last_run_str))
            self.table.setItem(row, 4, QTableWidgetItem(st.next_run_str))

            item_fresh = QTableWidgetItem(st.freshness_ar)
            if st.freshness == "current":
                item_fresh.setForeground(Qt.GlobalColor.green)
            elif st.freshness in ("due_soon", "offline"):
                item_fresh.setForeground(Qt.GlobalColor.yellow)
            else:
                item_fresh.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 5, item_fresh)

    def _register_win_task(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._statuses):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد خطة من الجدول لتسجيلها.")
            return

        st = self._statuses[row]
        profile = self.db.get_profile(st.profile_id)
        if not profile:
            return

        ok, msg = self.schedule_service.register_windows_scheduled_task(profile)
        if ok:
            QMessageBox.information(self, "نجاح التسجيل", msg)
        else:
            QMessageBox.warning(self, "فشل التسجيل", msg)

    def _run_selected_now(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._statuses):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد خطة للتشغيل.")
            return

        st = self._statuses[row]
        profile = self.db.get_profile(st.profile_id)
        if not profile:
            return

        dlg = BackupProgressDialog(parent=self)
        coord = BackupCoordinator(self.db)

        import threading
        from PySide6.QtCore import QTimer

        is_cancelled = [False]
        dlg.cancel_requested.connect(lambda: is_cancelled.insert(0, True))

        def _worker():
            def _prog(stage, done, total, detail):
                QTimer.singleShot(0, lambda: dlg.update_progress(stage, done, total, detail))

            coord.run_backup(profile, progress_cb=_prog, cancel_check=lambda: is_cancelled[0])
            QTimer.singleShot(0, lambda: dlg.btn_cancel.setText("إغلاق"))
            QTimer.singleShot(0, self.load_schedules)

        threading.Thread(target=_worker, daemon=True).start()
        dlg.exec()
