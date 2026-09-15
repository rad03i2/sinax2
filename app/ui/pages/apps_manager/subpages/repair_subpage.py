# -*- coding: utf-8 -*-
"""
SINAX Application Repair & Reset Subpage
Handles official software repair, modifying installation components,
and resetting Windows Store/MSIX applications.
"""

import os
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
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

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.repair_service import RepairService
from app.ui.icons import get_icon


class RepairSubpage(QWidget):
    """Subpage for repairing malfunctioning software and resetting MSIX apps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._repairable_apps: List[InstalledApp] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Info Banner
        banner = QFrame()
        banner.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        b_layout = QHBoxLayout(banner)

        v_info = QVBoxLayout()
        lbl_t = QLabel("مركز الإصلاح وإعادة الضبط (App Repair & Reset)")
        lbl_t.setStyleSheet("color: #D29922; font-size: 16px; font-weight: bold;")
        v_info.addWidget(lbl_t)

        lbl_desc = QLabel(
            "يدعم ويندوز إصلاح بعض البرامج لإعادة ملفاتها التالفة، كما يدعم إعادة ضبط تطبيقات المتجر (Reset) لحالتها الأولية."
        )
        lbl_desc.setStyleSheet("color: #8B949E; font-size: 12px;")
        v_info.addWidget(lbl_desc)
        b_layout.addLayout(v_info, 1)

        btn_troubleshoot = QPushButton("مستكشف أخطاء Windows")
        btn_troubleshoot.setIcon(get_icon("repair", color="#F0F6FC"))
        btn_troubleshoot.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        btn_troubleshoot.clicked.connect(self._launch_windows_troubleshooter)
        b_layout.addWidget(btn_troubleshoot)

        main_layout.addWidget(banner)

        # 2. Table of Eligible Apps
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "اسم البرنامج",
            "الناشر",
            "نوع المثبت",
            "الإمكانيات المتاحة",
            "الإجراءات",
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
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
        self._repairable_apps = [a for a in apps if a.can_repair or a.can_reset]
        self.table.setRowCount(len(self._repairable_apps))

        for r, app in enumerate(self._repairable_apps):
            self.table.setItem(r, 0, QTableWidgetItem(app.name))
            self.table.setItem(r, 1, QTableWidgetItem(app.publisher))
            self.table.setItem(r, 2, QTableWidgetItem(app.source.upper()))

            caps = []
            if app.can_repair:
                caps.append("إصلاح الملفات (Repair)")
            if app.can_reset:
                caps.append("إعادة ضبط (Reset)")
            self.table.setItem(r, 3, QTableWidgetItem(" • ".join(caps)))

            # Actions
            act_w = QWidget()
            act_l = QHBoxLayout(act_w)
            act_l.setContentsMargins(4, 2, 4, 2)
            act_l.setSpacing(6)

            if app.can_repair:
                btn_rep = QPushButton("إصلاح")
                btn_rep.setStyleSheet("background: #D29922; color: white; border: none; border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;")
                btn_rep.clicked.connect(lambda _, a=app: self._on_repair_app(a))
                act_l.addWidget(btn_rep)

            if app.can_reset:
                btn_rst = QPushButton("إعادة ضبط")
                btn_rst.setStyleSheet("background: #21262D; color: #D29922; border: 1px solid #30363D; border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;")
                btn_rst.clicked.connect(lambda _, a=app: self._on_reset_app(a))
                act_l.addWidget(btn_rst)

            self.table.setCellWidget(r, 4, act_w)

    def _on_repair_app(self, app: InstalledApp):
        ok, msg = RepairService.repair_app(app)
        if ok:
            QMessageBox.information(self, "إصلاح البرنامج", msg)
        else:
            QMessageBox.warning(self, "فشل الإصلاح", msg)

    def _on_reset_app(self, app: InstalledApp):
        reply = QMessageBox.warning(
            self,
            "تأكيد إعادة ضبط التطبيق",
            f"⚠️ تنبيه مهم:\nإعادة ضبط التطبيق '{app.name}' ستعيد التطبيق إلى حالته الافتراضية، وقد تؤدي إلى حذف بياناته وإعداداته المحلية المخزنة.\n\nهل ترغب في الاستمرار؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok, msg = RepairService.reset_app(app)
            if ok:
                QMessageBox.information(self, "إعادة الضبط", msg)
            else:
                QMessageBox.warning(self, "فشل إعادة الضبط", msg)

    def _launch_windows_troubleshooter(self):
        try:
            os.system("start ms-settings:troubleshoot")
        except Exception:
            pass
