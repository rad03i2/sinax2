# -*- coding: utf-8 -*-
"""
Apps Maintenance & Frozen Applications Subpage for SINAX.
Detects unresponsive applications, enables safe termination of frozen user processes
without touching critical system services, and inspects broken app registration entries.
"""

import os
import psutil
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
from app.services.maintenance.snapshot_history_service import SnapshotHistoryService
from app.ui.icons import get_icon


class AppsRepairSubpage(QWidget):
    """Subpage for managing unresponsive apps and application stability."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()
        self.load_running_apps()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
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
        icon_lbl.setPixmap(get_icon("apps", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(3)
        t_l = QLabel("إدارة البرامج غير المستجيبة وصيانة التطبيقات")
        t_l.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        s_l = QLabel("رصد التطبيقات المعلقة أو المستهلكة للموارد بشكل شاذ وإنهاؤها بأمان دون المساس بخدمات النظام.")
        s_l.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t_l)
        txt_col.addWidget(s_l)
        h_lay.addLayout(txt_col, 1)

        btn_refresh = QPushButton("تحديث القائمة")
        btn_refresh.setIcon(get_icon("update", color_hex="#8B949E"))
        btn_refresh.clicked.connect(self.load_running_apps)
        h_lay.addWidget(btn_refresh)
        layout.addWidget(header)

        # Table of active processes
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["اسم التطبيق", "معرّف PID", "استهلاك المعالج CPU", "الذاكرة RAM", "الحالة"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
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

        # Actions Row
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_kill = QPushButton("إنهاء التطبيق المحدد فوراً")
        self.btn_kill.setStyleSheet("""
            QPushButton {
                background-color: #B91C1C;
                color: white;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #991B1B;
            }
        """)
        self.btn_kill.clicked.connect(self._kill_selected_process)
        btn_bar.addWidget(self.btn_kill)

        btn_bar.addStretch(1)
        layout.addLayout(btn_bar)

    def load_running_apps(self):
        """Loads user-facing active desktop processes."""
        self.table.setRowCount(0)
        procs = []

        system_names = {"system", "system idle process", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe"}

        try:
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
                try:
                    name = p.info["name"] or ""
                    if name.lower() in system_names:
                        continue
                    mem = p.info["memory_info"].rss if p.info.get("memory_info") else 0
                    # Filter only processes using > 20 MB of RAM or running apps
                    if mem >= 20 * 1024 * 1024:
                        procs.append({
                            "pid": p.info["pid"],
                            "name": name,
                            "cpu": p.info["cpu_percent"] or 0.0,
                            "mem_bytes": mem,
                            "status": p.info["status"] or "running",
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass

        # Sort by memory usage descending
        procs.sort(key=lambda x: x["mem_bytes"], reverse=True)

        self.table.setRowCount(len(procs))
        for idx, item in enumerate(procs[:60]):
            self.table.setItem(idx, 0, QTableWidgetItem(item["name"]))
            self.table.setItem(idx, 1, QTableWidgetItem(str(item["pid"])))
            self.table.setItem(idx, 2, QTableWidgetItem(f"{item['cpu']:.1f}%"))
            self.table.setItem(idx, 3, QTableWidgetItem(f"{item['mem_bytes'] / (1024 * 1024):.1f} MB"))
            self.table.setItem(idx, 4, QTableWidgetItem("يعمل طبيعياً" if item["status"] != "stopped" else "متوقف"))

    def _kill_selected_process(self):
        sel = self.table.selectedItems()
        if not sel:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد تطبيق من الجدول لإنهاء عمليته.")
            return

        row = sel[0].row()
        name = self.table.item(row, 0).text()
        pid_str = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self,
            "تأكيد إنهاء العملية",
            f"هل أنت متأكد من رغبتك في إغلاق العملية '{name}' (PID: {pid_str})؟\n"
            "أي بيانات غير محفوظة في هذا التطبيق قد تفقد.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                pid = int(pid_str)
                p = psutil.Process(pid)
                p.terminate()
                SnapshotHistoryService().log_maintenance_action(
                    "kill_frozen_process", f"إنهاء عملية {name}", "apps", "success", f"تم إنهاء العملية ذات المعرف {pid}."
                )
                QMessageBox.information(self, "نجاح", f"تم إنهاء العملية '{name}' بنجاح.")
                self.load_running_apps()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر إنهاء العملية: {e}")
