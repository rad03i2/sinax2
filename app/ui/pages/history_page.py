# -*- coding: utf-8 -*-
"""
SINAX Operations History & Rollback Page
Displays logged file management operations and enables one-click rollbacks.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QSpacerItem, QSizePolicy, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.core.undo_manager import undo_manager, HistoryRecord
from app.services.rename_service import RenameService
from app.ui.icons import get_icon

class HistoryPage(QWidget):
    status_message = Signal(str, bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.stack = QStackedWidget(self)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.stack)

        # Page 0: Modern QML Operation History
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "historyController")
        self.quick_widget.setSource(get_qml_url("pages/OperationHistoryPage.qml"))
        self.stack.addWidget(self.quick_widget)

        # Page 1: Legacy Table Widget (for test compatibility)
        self.legacy_widget = QWidget()
        layout = QVBoxLayout(self.legacy_widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header toolbar
        head_layout = QHBoxLayout()
        title_lbl = QLabel("سجل العمليات السابقة وإمكانية التراجع")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #FFFFFF;")
        head_layout.addWidget(title_lbl)

        head_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        refresh_btn = QPushButton(" تحديث السجل")
        refresh_btn.setIcon(get_icon("refresh", "#AAAAAA", 14))
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.refresh_table)
        head_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("مسح السجل")
        clear_btn.setIcon(get_icon("cancel", "#FF4D4F", 14))
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._on_clear_history)
        head_layout.addWidget(clear_btn)

        layout.addLayout(head_layout)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "التاريخ والوقت",
            "نوع العملية",
            "عدد الملفات",
            "المجلد المستهدف",
            "الحالة والنتيجة",
            "تفاصيل العملية",
            "إجراء التراجع"
        ])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.table)
        self.refresh_table()

    def refresh_table(self):
        records = undo_manager.get_all_records()
        self.table.setRowCount(len(records))

        for row, rec in enumerate(records):
            # 0: Date
            t_item = QTableWidgetItem(rec.timestamp)
            t_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, t_item)

            # 1: Op type
            op_label = "إعادة تسمية" if rec.op_type == "rename" else rec.op_type
            op_item = QTableWidgetItem(op_label)
            op_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, op_item)

            # 2: Count
            c_item = QTableWidgetItem(str(len(rec.items)))
            c_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, c_item)

            # 3: Folder
            f_item = QTableWidgetItem(rec.folder)
            self.table.setItem(row, 3, f_item)

            # 4: Status badge
            if rec.status == "reverted":
                status_txt = "تم التراجع عنها"
                color = "#888888"
            elif rec.success:
                status_txt = "نجحت العملية"
                color = "#52C41A"
            else:
                status_txt = "فشلت جزئياً"
                color = "#FF4D4F"

            s_item = QTableWidgetItem(status_txt)
            s_item.setTextAlignment(Qt.AlignCenter)
            s_item.setForeground(Qt.GlobalColor(Qt.white))
            self.table.setItem(row, 4, s_item)

            # 5: Details
            d_item = QTableWidgetItem(rec.details)
            self.table.setItem(row, 5, d_item)

            # 6: Action button
            if rec.status == "completed" and rec.op_type == "rename":
                undo_btn = QPushButton(" تراجع")
                undo_btn.setIcon(get_icon("undo", "#60CDFF", 12))
                undo_btn.setStyleSheet("padding: 2px 10px; font-size: 11px;")
                undo_btn.setCursor(Qt.PointingHandCursor)
                undo_btn.clicked.connect(lambda _, r=rec: self._revert_record(r))
                self.table.setCellWidget(row, 6, undo_btn)
            else:
                lbl = QLabel("غير متاح")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color: #666666; font-size: 11px;")
                self.table.setCellWidget(row, 6, lbl)

    def _revert_record(self, record: HistoryRecord):
        confirm = QMessageBox.question(
            self,
            "تأكيد التراجع",
            f"هل أنت متأكد من رغبتك في التراجع عن هذه العملية؟\nسيتم استرجاع الأسماء السابقة لـ {len(record.items)} ملف.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        success, failed, errors = RenameService.undo_operation(record)
        self.refresh_table()
        if failed == 0:
            QMessageBox.information(self, "تم التراجع", f"✓ تمت استعادة {success} ملف بنجاح.")
        else:
            QMessageBox.warning(self, "تراجع جزئي", f"تمت استعادة {success} ملف، بينما تعذر استرجاع {failed} ملف.")

    def _on_clear_history(self):
        confirm = QMessageBox.question(
            self,
            "مسح سجل العمليات",
            "هل أنت متأكد من رغبتك في مسح كافة سجلات العمليات السابقة؟\nلن تتمكن من التراجع عن العمليات المسجلة بعد ذلك.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            undo_manager.clear_history()
            self.refresh_table()
