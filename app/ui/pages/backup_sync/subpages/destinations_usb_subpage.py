# -*- coding: utf-8 -*-
"""
SINAX Trusted Destinations & USB Subpage (الوجهات والأقراص الموثوقة).
Manages persistent device identification (Volume Serial Numbers), trusted backup drives,
auto-backup on drive connection, safe ejection, and emergency index rebuilding.
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
from app.services.backup_sync.backup_index_service import BackupIndexService
from app.services.backup_sync.device_identity_service import DeviceIdentityService
from app.services.backup_sync.usb_backup_service import UsbBackupService
from app.ui.icons import get_icon


class DestinationsUsbSubpage(QWidget):
    """Cockpit for managing external drives and destination storage health."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self.usb_service = UsbBackupService(self.db)
        self.index_service = BackupIndexService(self.db)
        self._connected_drives = []
        self._init_ui()
        self.load_drives()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("storage", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("إدارة الوجهات والأقراص الموثوقة (Trusted Backup Drives)")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("التعرف على وسائط التخزين عبر الرقم التسلسلي الفيزيائي (Volume Serial) لضمان عدم تغيير الوجهة عند تغير الأحرف.")
        d.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        layout.addWidget(header)

        # Connected Drives Table
        t_drives = QLabel("الأقراص ووحدات التخزين الخارجية المتصلة حالياً:")
        t_drives.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
        layout.addWidget(t_drives)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["الحرف", "الرقم التسلسلي (Serial)", "نظام الملفات", "المساحة الحرة", "الحجم الكلي", "الحالة الموثوقة"])
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

        # Buttons row
        b_row = QHBoxLayout()
        btn_refresh = QPushButton("تحديث قائمة الأقراص")
        btn_refresh.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 16px; border-radius: 6px;")
        btn_refresh.clicked.connect(self.load_drives)
        b_row.addWidget(btn_refresh)

        btn_trust = QPushButton("تعيين كقرص نسخ موثوق")
        btn_trust.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        btn_trust.clicked.connect(self._trust_selected_drive)
        b_row.addWidget(btn_trust)

        btn_eject = QPushButton("إخراج القرص بأمان (Safe Eject)")
        btn_eject.setStyleSheet("background-color: #21262D; color: #F87171; border: 1px solid #30363D; padding: 8px 16px; border-radius: 6px;")
        btn_eject.clicked.connect(self._eject_selected_drive)
        b_row.addWidget(btn_eject)

        b_row.addStretch(1)

        btn_rebuild = QPushButton("إعادة بناء فهرس نسخة قديمة...")
        btn_rebuild.setStyleSheet("background-color: #21262D; color: #34D399; border: 1px solid #30363D; padding: 8px 16px; border-radius: 6px;")
        btn_rebuild.clicked.connect(self._rebuild_index_from_folder)
        b_row.addWidget(btn_rebuild)

        layout.addLayout(b_row)

    def load_drives(self):
        self._connected_drives = DeviceIdentityService.list_connected_external_drives()
        self.table.setRowCount(len(self._connected_drives))
        for row, d in enumerate(self._connected_drives):
            self.table.setItem(row, 0, QTableWidgetItem(d.drive_letter))
            self.table.setItem(row, 1, QTableWidgetItem(d.volume_serial or "غير متوفر"))
            self.table.setItem(row, 2, QTableWidgetItem(d.filesystem))
            free_gb = f"{d.free_bytes / (1024**3):.1f} GB"
            total_gb = f"{d.total_bytes / (1024**3):.1f} GB"
            self.table.setItem(row, 3, QTableWidgetItem(free_gb))
            self.table.setItem(row, 4, QTableWidgetItem(total_gb))
            trusted_str = "✓ قرص موثوق" if d.is_trusted else "غير مضاف بعد"
            t_item = QTableWidgetItem(trusted_str)
            t_item.setForeground(Qt.GlobalColor.green if d.is_trusted else Qt.GlobalColor.gray)
            self.table.setItem(row, 5, t_item)

    def _trust_selected_drive(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._connected_drives):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد قرص من الجدول لتعيينه.")
            return

        drive = self._connected_drives[row]
        ok, msg = self.usb_service.pair_drive_as_trusted(drive.drive_letter)
        if ok:
            QMessageBox.information(self, "نجاح", msg)
            self.load_drives()
        else:
            QMessageBox.warning(self, "تنبيه", msg)

    def _eject_selected_drive(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._connected_drives):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد قرص لإخراجه بأمان.")
            return

        drive = self._connected_drives[row]
        ok, msg = self.usb_service.safe_eject_backup_drive(drive.drive_letter)
        if ok:
            QMessageBox.information(self, "إخراج آمن", msg)
            self.load_drives()
        else:
            QMessageBox.warning(self, "فشل الإخراج", msg)

    def _rebuild_index_from_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد النسخة الاحتياطية لإعادة فهرسته")
        if not folder:
            return

        ok, count, msg = self.index_service.rebuild_index_from_destination(folder)
        if ok:
            QMessageBox.information(self, "نجاح إعادة الفهرسة", msg)
        else:
            QMessageBox.critical(self, "خطأ", msg)
