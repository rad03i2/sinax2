# -*- coding: utf-8 -*-
"""
SINAX Sequential Batch Queue Execution Modal Dialog
Executes batch operations (Uninstall, Update, Restore) strictly sequentially in a background thread.
"""

from typing import Any, Callable, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from app.ui.icons import get_icon


class QueueWorker(QObject):
    """Executes a worker function in background thread."""
    progress = Signal(int, int, str, str)  # current, total, name, msg
    item_finished = Signal(int, bool, bool, str)  # index, success, restart_req, msg
    finished = Signal(object)  # report

    def __init__(self, task_fn: Callable, items: List[Any]):
        super().__init__()
        self.task_fn = task_fn
        self.items = items
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        def cancel_check():
            return self._cancelled

        def prog_cb(curr, total, item, msg):
            name = getattr(item, "name", str(item))
            self.progress.emit(curr, total, name, msg)

        try:
            report = self.task_fn(self.items, prog_cb, cancel_check)
            self.finished.emit(report)
        except Exception as e:
            self.finished.emit(e)


class SequentialQueueDialog(QDialog):
    """Non-blocking modal showing sequential progress for batch operations."""

    def __init__(self, title: str, items: List[Any], task_fn: Callable, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(680, 520)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.title_text = title
        self.items = items
        self.task_fn = task_fn
        self.report_result = None

        self._init_ui()
        self._start_worker()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        self.setStyleSheet("background: #0D1117; color: #C9D1D9;")

        # Header Frame
        hdr = QFrame()
        hdr.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;")
        hdr_layout = QVBoxLayout(hdr)

        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setStyleSheet("color: #58A6FF; font-size: 16px; font-weight: bold;")
        hdr_layout.addWidget(self.lbl_title)

        self.lbl_status = QLabel(f"تم جدولة {len(self.items)} عملية متتابعة...")
        self.lbl_status.setStyleSheet("color: #8B949E; font-size: 12px;")
        hdr_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.items))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #21262D; border: 1px solid #30363D; border-radius: 6px;
                text-align: center; color: #F0F6FC; font-weight: bold; height: 22px;
            }
            QProgressBar::chunk { background: #1F6FEB; border-radius: 5px; }
        """)
        hdr_layout.addWidget(self.progress_bar)
        layout.addWidget(hdr)

        # Queue Items Table
        self.table = QTableWidget(len(self.items), 3)
        self.table.setHorizontalHeaderLabels(["البرنامج", "الحالة", "التفاصيل"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background: #161B22; border: 1px solid #30363D; border-radius: 8px; gridline-color: #21262D; }
            QHeaderView::section { background: #21262D; color: #F0F6FC; font-weight: bold; padding: 6px; border: none; }
        """)

        for r, item in enumerate(self.items):
            name = getattr(item, "name", str(item))
            self.table.setItem(r, 0, QTableWidgetItem(name))
            item_status = QTableWidgetItem("في الانتظار")
            item_status.setForeground(QColor("#8B949E"))
            self.table.setItem(r, 1, item_status)
            self.table.setItem(r, 2, QTableWidgetItem("-"))

        layout.addWidget(self.table, 1)

        # Log Output (Collapsible/Small)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFixedHeight(90)
        self.log_edit.setStyleSheet("background: #0D1117; border: 1px solid #30363D; border-radius: 6px; color: #8B949E; font-family: Consolas, monospace; font-size: 11px;")
        layout.addWidget(self.log_edit)

        # Buttons Bar
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("إلغاء المتبقي")
        self.btn_cancel.setStyleSheet("background: #21262D; color: #F85149; border: 1px solid #30363D; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        self.btn_cancel.clicked.connect(self._on_cancel)

        self.btn_close = QPushButton("إغلاق")
        self.btn_close.setEnabled(False)
        self.btn_close.setStyleSheet("background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
        self.btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)

    def _start_worker(self):
        self.thread = QThread(self)
        self.worker = QueueWorker(self.task_fn, self.items)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)

        self.thread.start()

    def _on_progress(self, curr: int, total: int, name: str, msg: str):
        self.progress_bar.setValue(curr)
        self.lbl_status.setText(f"({curr} من {total}) {msg}")
        self.log_edit.append(f"[{curr}/{total}] {name}: {msg}")

        # Update row in table
        row = curr - 1
        if 0 <= row < self.table.rowCount():
            st_item = self.table.item(row, 1)
            if st_item:
                st_item.setText("جارٍ التنفيذ...")
                st_item.setForeground(QColor("#58A6FF"))
            msg_item = self.table.item(row, 2)
            if msg_item:
                msg_item.setText(msg)

    def _on_finished(self, report):
        self.report_result = report
        self.btn_cancel.setEnabled(False)
        self.btn_close.setEnabled(True)
        self.lbl_status.setText("اكتملت جميع العمليات في القائمة.")

        # Update table rows from report if available
        if hasattr(report, "succeeded"):
            suc_names = {r.app_name: r for r in report.succeeded}
            fail_names = {r.app_name: r for r in report.failed}
            skip_names = {r.app_name: r for r in report.skipped}

            for r in range(self.table.rowCount()):
                name = self.table.item(r, 0).text()
                st_item = self.table.item(r, 1)
                msg_item = self.table.item(r, 2)
                if name in suc_names:
                    res = suc_names[name]
                    if getattr(res, "restart_required", False):
                        st_item.setText("⚠️ يتطلب إعادة تشغيل")
                        st_item.setForeground(QColor("#D29922"))
                    else:
                        st_item.setText("✅ اكتملت بنجاح")
                        st_item.setForeground(QColor("#3FB950"))
                    msg_item.setText(res.message)
                elif name in fail_names:
                    res = fail_names[name]
                    st_item.setText("❌ فشلت")
                    st_item.setForeground(QColor("#F85149"))
                    msg_item.setText(res.message)
                elif name in skip_names:
                    st_item.setText("⏭️ تم التخطي")
                    st_item.setForeground(QColor("#8B949E"))

        if hasattr(report, "restart_required") and report.restart_required:
            self.lbl_status.setText("تحتاج بعض التغييرات إلى إعادة تشغيل Windows لتكتمل بنجاح.")

        self.thread.quit()
        self.thread.wait()

    def _on_cancel(self):
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText("جارٍ إيقاف العمليات المتبقية...")
        self.worker.cancel()
