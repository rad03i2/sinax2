# -*- coding: utf-8 -*-
"""
SINAX System & Storage - Process Manager & File Lock Finder Subpage (إدارة العمليات)
Full system process manager with:
- Search and filtering
- Safe termination guards for critical Windows processes
- Process details inspector (Cmdline, Parent PID, Threads)
- File Lock Finder dialog ("من يستخدم هذا الملف؟")
"""

import os
import subprocess
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.system_storage.process_service import (
    FileLockerInfo,
    ProcessDetail,
    ProcessInfo,
    ProcessService,
)
from app.services.system_storage.storage_scanner import format_bytes
from app.ui.icons import get_icon


class ProcessDetailDialog(QDialog):
    """Modal displaying deep inspection of a single process."""

    def __init__(self, detail: ProcessDetail, parent=None):
        super().__init__(parent)
        self.detail = detail
        self.setWindowTitle(f"تفاصيل العملية: {detail.name} (PID: {detail.pid})")
        self.resize(550, 420)
        self.setStyleSheet("""
            QDialog { background: #0D1117; color: #F0F6FC; }
            QLabel { color: #C9D1D9; font-size: 12px; }
            QTextEdit { background: #161B22; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; font-family: 'Consolas', monospace; font-size: 11px; }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header info
        h_frame = QFrame()
        h_frame.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        h_lay = QVBoxLayout(h_frame)
        h_lay.setSpacing(6)

        h_lay.addWidget(QLabel(f"<b>اسم العملية:</b> {self.detail.name}"))
        h_lay.addWidget(QLabel(f"<b>معرف العملية (PID):</b> {self.detail.pid} | <b>العملية الأب (PPID):</b> {self.detail.ppid} ({self.detail.parent_name})"))
        h_lay.addWidget(QLabel(f"<b>المستخدم:</b> {self.detail.username or 'غير محدد'} | <b>خيوط المعالجة:</b> {self.detail.num_threads}"))
        h_lay.addWidget(QLabel(f"<b>استهلاك الذاكرة (RSS):</b> {format_bytes(self.detail.memory_rss)}"))
        h_lay.addWidget(QLabel(f"<b>المسار التنفيذي:</b> {self.detail.exe or 'غير متوفر'}"))
        h_lay.addWidget(QLabel(f"<b>مجلد العمل:</b> {self.detail.cwd or 'غير متوفر'}"))

        layout.addWidget(h_frame)

        # Command line arguments
        layout.addWidget(QLabel("<b>سطر الأوامر والوسائط:</b>"))
        txt_cmd = QTextEdit()
        txt_cmd.setReadOnly(True)
        txt_cmd.setText(" ".join(self.detail.cmdline) if self.detail.cmdline else "غير متوفر")
        txt_cmd.setFixedHeight(80)
        layout.addWidget(txt_cmd)

        # Open files
        layout.addWidget(QLabel(f"<b>الملفات المفتوحة بواسطة العملية ({len(self.detail.open_files)}):</b>"))
        txt_files = QTextEdit()
        txt_files.setReadOnly(True)
        txt_files.setText("\n".join(self.detail.open_files) if self.detail.open_files else "لا توجد ملفات مفتوحة قابلة للقراءة")
        layout.addWidget(txt_files, 1)

        # Close button
        btn_close = QPushButton("إغلاق")
        btn_close.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignRight)


class FileLockFinderDialog(QDialog):
    """Dialog finding which process is locking a specified file or folder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("أداة كشف قفل الملفات والمجلدات - File Lock Finder")
        self.resize(650, 420)
        self.setStyleSheet("""
            QDialog { background: #0D1117; color: #F0F6FC; }
            QLineEdit { background: #161B22; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px; }
            QPushButton { background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 14px; font-weight: bold; }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        lbl_desc = QLabel("حدد الملف أو المجلد الذي يرفض الحذف أو التعديل لمعرفة العملية التي تستخدمه حالياً:")
        lbl_desc.setStyleSheet("color: #8B949E; font-size: 12px;")
        layout.addWidget(lbl_desc)

        # Input row
        row = QHBoxLayout()
        row.setSpacing(8)
        self.txt_path = QLineEdit()
        self.txt_path.setPlaceholderText("مسار الملف أو المجلد...")
        row.addWidget(self.txt_path, 1)

        btn_file = QPushButton("اختيار ملف")
        btn_file.clicked.connect(self._pick_file)
        row.addWidget(btn_file)

        btn_folder = QPushButton("اختيار مجلد")
        btn_folder.clicked.connect(self._pick_folder)
        row.addWidget(btn_folder)

        btn_find = QPushButton("كشف القفل")
        btn_find.setStyleSheet("""
            QPushButton { background: #1F6FEB; color: #FFFFFF; border: none; padding: 6px 18px; }
            QPushButton:hover { background: #388BFD; }
        """)
        btn_find.clicked.connect(self._find_lockers)
        row.addWidget(btn_find)
        layout.addLayout(row)

        # Results table
        self.table_lockers = QTableWidget()
        self.table_lockers.setColumnCount(4)
        self.table_lockers.setHorizontalHeaderLabels(["PID", "اسم البرنامج", "المستخدم", "مسار الملف المقفول"])
        self.table_lockers.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_lockers.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_lockers.setStyleSheet("background: #161B22; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px;")
        layout.addWidget(self.table_lockers, 1)

        # Actions row
        act_row = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #8B949E; font-size: 11px;")
        act_row.addWidget(self.lbl_status, 1)

        btn_kill = QPushButton("إنهاء العملية المقفلة")
        btn_kill.setStyleSheet("background: #DA3633; color: #FFFFFF; border: none;")
        btn_kill.clicked.connect(self._kill_selected_locker)
        act_row.addWidget(btn_kill)

        layout.addLayout(act_row)

    def _pick_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر الملف المقفول")
        if f:
            self.txt_path.setText(f)
            self._find_lockers()

    def _pick_folder(self):
        f = QFileDialog.getExistingDirectory(self, "اختر المجلد المقفول")
        if f:
            self.txt_path.setText(f)
            self._find_lockers()

    def _find_lockers(self):
        target = self.txt_path.text().strip()
        if not target or not os.path.exists(target):
            QMessageBox.warning(self, "تنبيه", "المسار غير موجود.")
            return

        self.lbl_status.setText("جارٍ فحص العمليات المفتوحة...")
        lockers = ProcessService.find_file_lockers(target)
        self.table_lockers.setRowCount(len(lockers))

        for r, l in enumerate(lockers):
            self.table_lockers.setItem(r, 0, QTableWidgetItem(str(l.pid)))
            self.table_lockers.setItem(r, 1, QTableWidgetItem(l.name))
            self.table_lockers.setItem(r, 2, QTableWidgetItem(l.username))
            self.table_lockers.setItem(r, 3, QTableWidgetItem(l.locked_file_path))

        if not lockers:
            self.lbl_status.setText("لم يتم العثور على أي عملية تقفل هذا الملف أو المجلد حالياً.")
        else:
            self.lbl_status.setText(f"تم العثور على {len(lockers)} عمليات تستخدم هذا الملف.")

    def _kill_selected_locker(self):
        row = self.table_lockers.currentRow()
        if row < 0:
            return
        pid = int(self.table_lockers.item(row, 0).text())
        ok, msg = ProcessService.terminate_process(pid, force=True)
        if ok:
            QMessageBox.information(self, "تم", msg)
            self._find_lockers()
        else:
            QMessageBox.warning(self, "تعذر الإنهاء", msg)


class ProcessSubpage(QWidget):
    """Full system process manager and analyzer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_processes: List[ProcessInfo] = []
        self._init_ui()
        self.refresh_processes()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Controls Bar
        bar = QFrame()
        bar.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 10px;")
        b_lay = QHBoxLayout(bar)
        b_lay.setContentsMargins(12, 8, 12, 8)
        b_lay.setSpacing(10)

        # Search filter
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("بحث بالاسم أو PID...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px;
            }
        """)
        self.txt_search.textChanged.connect(self._apply_filter)
        b_lay.addWidget(self.txt_search, 1)

        # Buttons
        btn_refresh = QPushButton("تحديث")
        btn_refresh.setIcon(get_icon("storage", color="#F0F6FC"))
        btn_refresh.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        btn_refresh.clicked.connect(self.refresh_processes)
        b_lay.addWidget(btn_refresh)

        btn_lock = QPushButton("كاشف قفل الملفات")
        btn_lock.setIcon(get_icon("search", color="#58A6FF"))
        btn_lock.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #58A6FF; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        btn_lock.clicked.connect(self._open_file_lock_dialog)
        b_lay.addWidget(btn_lock)

        btn_details = QPushButton("تفاصيل العملية")
        btn_details.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 14px;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        btn_details.clicked.connect(self._show_selected_details)
        b_lay.addWidget(btn_details)

        btn_term = QPushButton("إنهاء العملية")
        btn_term.setStyleSheet("""
            QPushButton {
                background: #DA3633; color: #FFFFFF; border: none;
                border-radius: 6px; padding: 6px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #E5534B; }
        """)
        btn_term.clicked.connect(self._terminate_selected)
        b_lay.addWidget(btn_term)

        layout.addWidget(bar)

        # 2. Process Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["PID", "اسم العملية", "الذاكرة (RAM)", "الذاكرة %", "المعالج %", "الحالة", "المستخدم"])
        self.table.setStyleSheet("""
            QTableWidget {
                background: #161B22; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 8px; gridline-color: #21262D; font-size: 12px;
            }
            QHeaderView::section {
                background: #21262D; color: #8B949E; font-weight: bold; padding: 8px; border: none;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._show_selected_details)
        layout.addWidget(self.table, 1)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #8B949E; font-size: 11px;")
        layout.addWidget(self.lbl_count)

    def refresh_processes(self):
        self.all_processes = ProcessService.list_processes()
        self._apply_filter()

    def _apply_filter(self):
        q = self.txt_search.text().strip().lower()
        if q:
            filtered = [
                p for p in self.all_processes
                if q in p.name.lower() or q in str(p.pid)
            ]
        else:
            filtered = self.all_processes

        self.table.setRowCount(len(filtered))
        for row, p in enumerate(filtered):
            # PID
            pid_item = QTableWidgetItem(str(p.pid))
            pid_item.setData(Qt.UserRole, p.pid)
            self.table.setItem(row, 0, pid_item)

            # Name
            name_text = p.name + (" (نظام)" if p.is_critical else "")
            self.table.setItem(row, 1, QTableWidgetItem(name_text))

            # Memory
            self.table.setItem(row, 2, QTableWidgetItem(p.memory_formatted))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p.memory_percent:.1f}%"))

            # CPU
            self.table.setItem(row, 4, QTableWidgetItem(f"{p.cpu_percent:.1f}%"))

            # Status
            self.table.setItem(row, 5, QTableWidgetItem(p.status_ar))

            # User
            self.table.setItem(row, 6, QTableWidgetItem(p.username))

        self.lbl_count.setText(f"إجمالي العمليات المعروضة: {len(filtered):,} عملية")

    def _get_selected_pid(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _show_selected_details(self):
        pid = self._get_selected_pid()
        if pid is None:
            return
        detail = ProcessService.get_process_detail(pid)
        if detail:
            dlg = ProcessDetailDialog(detail, self)
            dlg.exec()

    def _terminate_selected(self):
        pid = self._get_selected_pid()
        if pid is None:
            return

        proc = next((p for p in self.all_processes if p.pid == pid), None)
        name = proc.name if proc else str(pid)

        confirm = QMessageBox.question(
            self,
            "تأكيد إنهاء العملية",
            f"هل أنت متأكد من رغبتك في إغلاق العملية '{name}' (PID: {pid})؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        ok, msg = ProcessService.terminate_process(pid, force=False)
        if ok:
            QMessageBox.information(self, "نجاح", msg)
            self.refresh_processes()
        else:
            QMessageBox.warning(self, "تعذر الإنهاء", msg)

    def _open_file_lock_dialog(self):
        dlg = FileLockFinderDialog(self)
        dlg.exec()
