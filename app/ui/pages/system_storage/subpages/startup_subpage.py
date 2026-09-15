# -*- coding: utf-8 -*-
"""
SINAX System & Storage - Startup Items Manager Subpage (إدارة بدء التشغيل)
Safely enables and disables Windows startup programs using:
- Official StartupApproved binary registry flags (non-destructive)
- Broken entry detection (missing target executables)
- Automatic snapshot backup to JSON
"""

import os
import subprocess
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from app.services.system_storage.startup_service import StartupItem, StartupService
from app.ui.icons import get_icon


class StartupSubpage(QWidget):
    """Windows Startup items management tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_items: List[StartupItem] = []
        self._init_ui()
        self.refresh_items()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Controls Bar
        bar = QFrame()
        bar.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 10px;")
        b_lay = QHBoxLayout(bar)
        b_lay.setContentsMargins(12, 8, 12, 8)
        b_lay.setSpacing(12)

        # Stats summary label
        self.lbl_stats = QLabel("جارٍ قراءة عناصر الإقلاع...")
        self.lbl_stats.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 12px;")
        b_lay.addWidget(self.lbl_stats, 1)

        # Filter dropdown
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["عرض كافة العناصر", "المفعلة فقط", "المعطلة فقط", "العناصر التالفة فقط"])
        self.combo_filter.setStyleSheet("""
            QComboBox {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QComboBox::drop-down { border: none; }
        """)
        self.combo_filter.currentIndexChanged.connect(self._apply_filter)
        b_lay.addWidget(self.combo_filter)

        btn_backup = QPushButton("أخذ نسخة احتياطية (JSON)")
        btn_backup.setIcon(get_icon("chart", color="#58A6FF"))
        btn_backup.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #58A6FF; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        btn_backup.clicked.connect(self._manual_backup)
        b_lay.addWidget(btn_backup)

        btn_refresh = QPushButton("تحديث")
        btn_refresh.setIcon(get_icon("storage", color="#F0F6FC"))
        btn_refresh.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; }
        """)
        btn_refresh.clicked.connect(self.refresh_items)
        b_lay.addWidget(btn_refresh)

        layout.addWidget(bar)

        # 2. Startup Items Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["التشغيل التلقائي", "اسم التطبيق", "الحالة", "الموقع", "الأمر / المسار التنفيذي"])
        self.table.setStyleSheet("""
            QTableWidget {
                background: #161B22; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 8px; gridline-color: #21262D; font-size: 12px;
            }
            QHeaderView::section {
                background: #21262D; color: #8B949E; font-weight: bold; padding: 8px; border: none;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

    def refresh_items(self):
        self.all_items = StartupService.list_startup_items()
        self._apply_filter()

    def _apply_filter(self):
        idx = self.combo_filter.currentIndex()
        if idx == 1:
            filtered = [it for it in self.all_items if it.is_enabled]
        elif idx == 2:
            filtered = [it for it in self.all_items if not it.is_enabled]
        elif idx == 3:
            filtered = [it for it in self.all_items if it.is_broken]
        else:
            filtered = self.all_items

        tot = len(self.all_items)
        en_c = sum(1 for it in self.all_items if it.is_enabled)
        br_c = sum(1 for it in self.all_items if it.is_broken)
        self.lbl_stats.setText(
            f"إجمالي عناصر الإقلاع: {tot} | المفعلة: <b style='color:#3FB950;'>{en_c}</b> | التالفة: <b style='color:#F85149;'>{br_c}</b>"
        )

        self.table.setRowCount(len(filtered))
        for row, it in enumerate(filtered):
            # Toggle Checkbox
            chk = QCheckBox("مفعل" if it.is_enabled else "معطل")
            chk.setChecked(it.is_enabled)
            chk.setStyleSheet("color: #F0F6FC;")
            chk.stateChanged.connect(lambda state, item=it: self._on_toggle(item, state))

            c_widget = QWidget()
            c_lay = QHBoxLayout(c_widget)
            c_lay.setContentsMargins(8, 0, 8, 0)
            c_lay.setAlignment(Qt.AlignCenter)
            c_lay.addWidget(chk)
            self.table.setCellWidget(row, 0, c_widget)

            # Name
            self.table.setItem(row, 1, QTableWidgetItem(it.name))

            # Status Badge
            if it.is_broken:
                b_text, b_col, b_bg = "مسار تالف / غير موجود", "#F85149", "rgba(248, 81, 73, 0.15)"
            elif it.is_enabled:
                b_text, b_col, b_bg = "يعمل مع الإقلاع", "#3FB950", "rgba(63, 185, 80, 0.15)"
            else:
                b_text, b_col, b_bg = "معطل", "#8B949E", "rgba(139, 148, 158, 0.15)"

            b_lbl = QLabel(b_text)
            b_lbl.setStyleSheet(f"""
                background: {b_bg}; color: {b_col};
                border: 1px solid {b_col}44; border-radius: 4px;
                padding: 2px 8px; font-weight: bold; font-size: 10px;
            """)
            b_widget = QWidget()
            b_lay_cell = QHBoxLayout(b_widget)
            b_lay_cell.setContentsMargins(4, 0, 4, 0)
            b_lay_cell.setAlignment(Qt.AlignCenter)
            b_lay_cell.addWidget(b_lbl)
            self.table.setCellWidget(row, 2, b_widget)

            # Location
            self.table.setItem(row, 3, QTableWidgetItem(it.location_label_ar))

            # Command / Path
            self.table.setItem(row, 4, QTableWidgetItem(it.command))

    def _on_toggle(self, item: StartupItem, state: int):
        enable = (state == Qt.Checked.value or state == 2)
        ok, msg = StartupService.toggle_item(item, enable)
        if not ok:
            QMessageBox.warning(self, "خطأ", msg)
        self.refresh_items()

    def _manual_backup(self):
        try:
            b_path = StartupService.backup_startup_state()
            QMessageBox.information(
                self,
                "تمت النسخة الاحتياطية",
                f"تم حفظ نسخة احتياطية من كافة إعدادات بدء التشغيل في الملف:\n{b_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"تعذر إنشاء النسخة الاحتياطية: {e}")
