# -*- coding: utf-8 -*-
"""
SINAX Dry Run Preview Dialog.
Mandatory pre-execution confirmation for Mirror & Synchronization actions.
Explicitly highlights new files, updates, deletions, and conflicts.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from app.services.backup_sync.sync_engine import SyncDryRunReport
from app.ui.icons import get_icon


class DryRunPreviewDialog(QDialog):
    """Presents a transparent preview of all actions before synchronizing."""

    def __init__(self, report: SyncDryRunReport, parent=None):
        super().__init__(parent)
        self.report = report
        self.setWindowTitle("معاينة المزامنة (Dry Run Preview)")
        self.resize(750, 480)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
            QDialog {
                background-color: #0D1117;
                color: #C9D1D9;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header with counts
        header_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("sync", color_hex="#38BDF8", size=32).pixmap(32, 32))
        header_row.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        t = QLabel("مراجعة التغييرات قبل تنفيذ المزامنة")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        sub = QLabel(
            f"جديد: {len(self.report.to_copy_a_to_b)} • "
            f"محدث: {len(self.report.to_copy_b_to_a)} • "
            f"سيُحذف: {len(self.report.to_delete)} • "
            f"تعارض: {len(self.report.conflicts)}"
        )
        sub.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(sub)
        header_row.addLayout(txt_col)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        if self.report.warning_message:
            warn_lbl = QLabel(self.report.warning_message)
            warn_lbl.setWordWrap(True)
            warn_lbl.setStyleSheet("""
                background-color: #2D1A00;
                color: #FBBF24;
                border: 1px solid #78350F;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            """)
            layout.addWidget(warn_lbl)

        # Action table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["الإجراء", "المسار النسبي", "الحجم", "السبب"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
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
                font-weight: bold;
                padding: 6px;
                border: none;
            }
        """)

        all_actions = (
            self.report.to_copy_a_to_b +
            self.report.to_copy_b_to_a +
            self.report.to_delete +
            self.report.conflicts
        )
        self.table.setRowCount(len(all_actions))

        action_labels = {
            "copy_a_to_b": ("نسخ A -> B", "#38BDF8"),
            "copy_b_to_a": ("نسخ B -> A", "#34D399"),
            "delete_b": ("حذف آمن", "#F87171"),
            "conflict": ("تعارض!", "#FBBF24"),
        }

        for row, item in enumerate(all_actions):
            lbl, color = action_labels.get(item.action, (item.action, "#C9D1D9"))
            item_act = QTableWidgetItem(lbl)
            item_act.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 0, item_act)
            self.table.setItem(row, 1, QTableWidgetItem(item.relative_path))
            sz_str = f"{item.size_bytes / 1024:.1f} KB" if item.size_bytes > 0 else "-"
            self.table.setItem(row, 2, QTableWidgetItem(sz_str))
            self.table.setItem(row, 3, QTableWidgetItem(item.reason))

        layout.addWidget(self.table, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        btn_cancel = QPushButton("إلغاء المزامنة")
        btn_cancel.setStyleSheet("background-color: #21262D; color: #C9D1D9; padding: 8px 18px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("تأكيد وبدء المزامنة")
        btn_confirm.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 24px; border-radius: 6px;")
        btn_confirm.clicked.connect(self.accept)
        btn_row.addWidget(btn_confirm)

        layout.addLayout(btn_row)
