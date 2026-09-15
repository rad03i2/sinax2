# -*- coding: utf-8 -*-
"""
SINAX Large Applications Subpage
Identifies and ranks disk space consuming applications with threshold filters (>10GB, >5GB, >1GB, >500MB, >100MB).
"""

import os
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
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

from app.services.apps_manager.app_model import InstalledApp, format_bytes
from app.ui.icons import get_icon


class LargeAppsSubpage(QWidget):
    """Subpage displaying space-consuming software."""

    uninstall_requested = Signal(object)  # InstalledApp

    THRESHOLDS = [
        ("all", "الكل", 0),
        ("100mb", "> 100 MB", 100 * 1024 * 1024),
        ("500mb", "> 500 MB", 500 * 1024 * 1024),
        ("1gb", "> 1 GB", 1024 * 1024 * 1024),
        ("5gb", "> 5 GB", 5 * 1024 * 1024 * 1024),
        ("10gb", "> 10 GB", 10 * 1024 * 1024 * 1024),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._all_apps: List[InstalledApp] = []
        self._current_threshold_bytes: int = 1024 * 1024 * 1024  # Default > 1GB
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Bar with Filter Chips
        top_bar = QFrame()
        top_bar.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(8, 6, 8, 6)
        tb_layout.setSpacing(10)

        v_text = QVBoxLayout()
        self.lbl_title = QLabel("البرامج الأكثر استهلاكاً لمساحة التخزين")
        self.lbl_title.setStyleSheet("color: #F0883E; font-size: 16px; font-weight: bold;")
        v_text.addWidget(self.lbl_title)

        self.lbl_total_large = QLabel("الحجم الإجمالي للبرامج الكبيرة: 0 GB")
        self.lbl_total_large.setStyleSheet("color: #8B949E; font-size: 12px;")
        v_text.addWidget(self.lbl_total_large)
        tb_layout.addLayout(v_text, 1)

        # Filter Chips
        self.btn_group = QButtonGroup(self)
        for key, text, b_val in self.THRESHOLDS:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setChecked(key == "1gb")
            btn.setStyleSheet("""
                QPushButton {
                    background: #21262D; color: #8B949E; border: 1px solid #30363D;
                    border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: bold;
                }
                QPushButton:hover { background: #30363D; color: #F0F6FC; }
                QPushButton:checked { background: #1F6FEB; color: white; border-color: #1F6FEB; }
            """)
            btn.clicked.connect(lambda _, val=b_val: self._on_threshold_changed(val))
            self.btn_group.addButton(btn)
            tb_layout.addWidget(btn)

        main_layout.addWidget(top_bar)

        # 2. Ranked Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "الترتيب",
            "اسم البرنامج",
            "الناشر",
            "الحجم المستهلك",
            "إجراء سريع",
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 60)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0D1117; alternate-background-color: #161B22; color: #C9D1D9;
                border: 1px solid #30363D; border-radius: 10px; font-size: 12px;
            }
            QHeaderView::section {
                background: #161B22; color: #F0F6FC; font-weight: bold;
                border: none; border-bottom: 1px solid #30363D; padding: 8px;
            }
        """)
        main_layout.addWidget(self.table, 1)

    def set_apps(self, apps: List[InstalledApp]):
        self._all_apps = sorted(apps, key=lambda a: a.effective_size_bytes, reverse=True)
        self._refresh_table()

    def _on_threshold_changed(self, threshold_bytes: int):
        self._current_threshold_bytes = threshold_bytes
        self._refresh_table()

    def _refresh_table(self):
        filtered = [a for a in self._all_apps if a.effective_size_bytes >= self._current_threshold_bytes]
        total_sz = sum(a.effective_size_bytes for a in filtered)
        self.lbl_total_large.setText(f"إجمالي استهلاك {len(filtered)} برنامجاً: {format_bytes(total_sz)}")

        self.table.setRowCount(len(filtered))
        for r, app in enumerate(filtered):
            # Rank item
            rank_item = QTableWidgetItem(f"#{r + 1}")
            rank_item.setTextAlignment(Qt.AlignCenter)
            rank_item.setForeground(QColor("#8B949E"))
            self.table.setItem(r, 0, rank_item)

            self.table.setItem(r, 1, QTableWidgetItem(app.name))
            self.table.setItem(r, 2, QTableWidgetItem(app.publisher))

            # Size item with colored badge
            sz_item = QTableWidgetItem(app.display_size)
            sz_item.setForeground(QColor("#F0883E") if app.effective_size_bytes >= (5 * 1024**3) else QColor("#58A6FF"))
            font = QFont()
            font.setBold(True)
            sz_item.setFont(font)
            self.table.setItem(r, 3, sz_item)

            # Actions
            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(4, 2, 4, 2)
            act_l.setSpacing(6)

            if app.install_location and os.path.exists(app.install_location):
                btn_loc = QPushButton("فتح المسار")
                btn_loc.setStyleSheet("background: #21262D; color: #C9D1D9; border: 1px solid #30363D; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
                btn_loc.clicked.connect(lambda _, p=app.install_location: os.startfile(p))
                act_l.addWidget(btn_loc)

            btn_un = QPushButton("إزالة")
            btn_un.setStyleSheet("background: #DA3633; color: white; border: none; border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;")
            btn_un.clicked.connect(lambda _, a=app: self.uninstall_requested.emit(a))
            act_l.addWidget(btn_un)

            self.table.setCellWidget(r, 4, act_w)
