# -*- coding: utf-8 -*-
"""
Devices Troubleshooting & Peripheral Repair Subpage for SINAX.
Detects hardware devices with error codes (yellow exclamation marks),
provides targeted services (Restart Print Spooler for stuck jobs),
and shortcuts to official Windows Sound, Bluetooth, and Device Manager tools.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.snapshot_history_service import SnapshotHistoryService
from app.services.maintenance.troubleshooter_service import TroubleshooterService
from app.ui.icons import get_icon


class DevicesRepairSubpage(QWidget):
    """Subpage for resolving printer, audio, bluetooth, and driver issues."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

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
        icon_lbl.setPixmap(get_icon("devices", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(3)
        t_l = QLabel("استكشاف وإصلاح مشكلات الأجهزة والملحقات")
        t_l.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        s_l = QLabel("حل مشاكل تعليق الطابعات، انقطاع مخارج الصوت، اقتران البلوتوث، والتعريفات التي بها أخطاء.")
        s_l.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t_l)
        txt_col.addWidget(s_l)
        h_lay.addLayout(txt_col, 1)

        btn_dev_mgr = QPushButton("فتح إدارة الأجهزة (Device Manager)")
        btn_dev_mgr.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
        btn_dev_mgr.clicked.connect(TroubleshooterService.open_device_manager)
        h_lay.addWidget(btn_dev_mgr)

        layout.addWidget(header)

        # Quick Peripheral Fixes Grid
        grid_frame = QFrame()
        grid_frame.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        grid = QGridLayout(grid_frame)
        grid.setSpacing(14)

        CARDS = [
            ("مشاكل الطابعة والطباعة", "حل مشكلة تعليق المستندات وتوقف استجابة الطابعات بإعادة تشغيل خدمة مخزن الطباعة.", "إعادة تشغيل Print Spooler", self._restart_spooler, "devices"),
            ("مشاكل مخارج الصوت", "تشخيص تعطل السماعات أو عدم التعرف على أجهزة الإخراج ومصادر الصوت.", "فتح إعدادات ومصحح الصوت", TroubleshooterService.open_audio_troubleshooter, "audio"),
            ("أجهزة البلوتوث اللاسلكية", "حل مشكلات الاقتران وانقطاع اتصال الفأرة ولوحة المفاتيح والسماعات اللاسلكية.", "فتح إعدادات Bluetooth", TroubleshooterService.open_bluetooth_settings, "wifi"),
            ("إدارة الطابعات والماسحات", "عرض قائمة الطابعات المتصلة وإلغاء أوامر الطباعة العالقة في قائمة الانتظار.", "فتح إعدادات الطابعات", TroubleshooterService.open_printers_settings, "devices"),
        ]

        for idx, (title, desc, btn_text, handler, icon_name) in enumerate(CARDS):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #161B22;
                    border: 1px solid #30363D;
                    border-radius: 8px;
                    padding: 14px;
                }
            """)
            c_lay = QVBoxLayout(card)
            c_lay.setSpacing(8)

            top_h = QHBoxLayout()
            ic = QLabel()
            ic.setPixmap(get_icon(icon_name, color_hex="#38BDF8", size=24).pixmap(24, 24))
            top_h.addWidget(ic)
            tl = QLabel(title)
            tl.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
            top_h.addWidget(tl)
            top_h.addStretch(1)
            c_lay.addLayout(top_h)

            dl = QLabel(desc)
            dl.setWordWrap(True)
            dl.setStyleSheet("font-size: 12px; color: #8B949E; line-height: 1.3;")
            c_lay.addWidget(dl, 1)

            act_btn = QPushButton(btn_text)
            act_btn.setStyleSheet("""
                QPushButton {
                    background-color: #21262D;
                    color: #F0F6FC;
                    border: 1px solid #30363D;
                    border-radius: 6px;
                    padding: 6px 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #30363D;
                    border-color: #38BDF8;
                }
            """)
            act_btn.clicked.connect(handler)
            c_lay.addWidget(act_btn)

            r = idx // 2
            c = idx % 2
            grid.addWidget(card, r, c)

        layout.addWidget(grid_frame)
        layout.addStretch(1)

    def _restart_spooler(self):
        success, msg = TroubleshooterService.restart_service("spooler")
        SnapshotHistoryService().log_maintenance_action(
            "restart_print_spooler", "إعادة تشغيل Print Spooler", "devices", "success" if success else "failed", msg
        )
        if success:
            QMessageBox.information(self, "نجاح", msg)
        else:
            QMessageBox.warning(self, "تنبيه", f"{msg}\nقد يتطلب الإجراء تشغيل البرنامج كمسؤول.")
