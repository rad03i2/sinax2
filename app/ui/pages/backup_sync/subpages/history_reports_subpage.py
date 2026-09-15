# -*- coding: utf-8 -*-
"""
SINAX Backup History & Reports Subpage (سجل العمليات والتقارير).
Displays complete historical audit log of backup and sync operations,
and allows technical report generation and export in HTML and JSON formats.
"""

from pathlib import Path
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
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
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.models import BackupJob
from app.ui.icons import get_icon


class HistoryReportsSubpage(QWidget):
    """Cockpit for audit logs, job history, and report export."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self._jobs = []
        self._init_ui()
        self.load_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("history", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("سجل عمليات النسخ والتقارير الفنية")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("سجل تدقيق شامل لجميع عمليات النسخ والمزامنة والاستعادة مع إمكانية تصدير تقارير HTML و JSON مفصلة.")
        d.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        layout.addWidget(header)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["التوقيت", "نوع العملية", "الحالة", "الملفات المنسوخة", "البيانات", "التحقق"])
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
        btn_refresh.clicked.connect(self.load_history)
        b_row.addWidget(btn_refresh)

        b_row.addStretch(1)

        btn_export = QPushButton("تصدير تقرير فني (HTML)")
        btn_export.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        btn_export.clicked.connect(self._export_report)
        b_row.addWidget(btn_export)

        layout.addLayout(b_row)

    def load_history(self):
        self._jobs = self.db.list_recent_jobs(limit=100)
        self.table.setRowCount(len(self._jobs))

        for row, job in enumerate(self._jobs):
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(job.start_time))
            self.table.setItem(row, 0, QTableWidgetItem(t_str))
            self.table.setItem(row, 1, QTableWidgetItem(job.job_type))

            st_item = QTableWidgetItem(job.status.value if hasattr(job.status, "value") else str(job.status))
            if "completed" in str(job.status).lower():
                st_item.setForeground(Qt.GlobalColor.green)
            else:
                st_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 2, st_item)

            self.table.setItem(row, 3, QTableWidgetItem(str(job.files_copied + job.files_updated)))
            sz_mb = f"{job.bytes_copied / (1024**2):.1f} MB" if job.bytes_copied > 0 else "0 MB"
            self.table.setItem(row, 4, QTableWidgetItem(sz_mb))
            self.table.setItem(row, 5, QTableWidgetItem(job.verification_status))

    def _export_report(self):
        dest, _ = QFileDialog.getSaveFileName(self, "حفظ تقرير النسخ الاحتياطي", "SINAX_Backup_Report.html", "HTML Files (*.html)")
        if not dest:
            return

        rows_html = ""
        for j in self._jobs:
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(j.start_time))
            rows_html += f"<tr><td>{t_str}</td><td>{j.job_type}</td><td>{j.status}</td><td>{j.files_copied}</td><td>{j.bytes_copied/(1024**2):.1f} MB</td><td>{j.verification_status}</td></tr>"

        html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<title>تقرير النسخ الاحتياطي والمزامنة - SINAX</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0D1117; color: #C9D1D9; padding: 24px; }}
h1 {{ color: #58A6FF; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
th, td {{ border: 1px solid #30363D; padding: 10px; text-align: right; }}
th {{ background: #161B22; color: #8B949E; }}
tr:nth-child(even) {{ background: #161B22; }}
</style>
</head>
<body>
<h1>تقرير النسخ الاحتياطي والمزامنة - SINAX</h1>
<p>تاريخ التوليد: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
<table>
<tr><th>التوقيت</th><th>نوع العملية</th><th>الحالة</th><th>الملفات</th><th>الحجم</th><th>التحقق</th></tr>
{rows_html}
</table>
</body>
</html>"""
        try:
            with open(dest, "w", encoding="utf-8") as f:
                f.write(html_content)
            QMessageBox.information(self, "نجاح التصدير", f"تم تصدير التقرير الفني بنجاح إلى:\n{dest} ✓")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر حفظ التقرير: {e}")
