# -*- coding: utf-8 -*-
"""
SINAX USB & Peripherals Subpage (صفحة منافذ USB والملحقات المتصلة)
Displays connected USB devices, VID/PID vendor codes, filter chips,
safe USB device eject, and hardware ID copying.
"""

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.hardware_models import UsbDeviceInfo
from app.services.devices.usb_service import UsbService
from app.ui.icons import get_icon


class UsbSubpage(QWidget):
    """Subpage for managing USB peripherals and safely ejecting removable media."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._devices: List[UsbDeviceInfo] = []
        self._filter_mode = "connected"  # "connected", "all", "problems"
        self._init_ui()
        self.refresh_usb()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)

        # Header
        top_bar = QHBoxLayout()
        title = QLabel("منافذ USB والأجهزة الملحقة (USB Peripherals)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.refresh_btn = QPushButton("  تحديث")
        self.refresh_btn.setIcon(get_icon("devices", "#FFFFFF", 16))
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #334155; color: #F8FAFC; border-radius: 6px;
                padding: 0 14px; font-weight: bold; border: 1px solid #475569;
            }
            QPushButton:hover { background: #475569; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_usb)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Filter Chips & Actions
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(12)

        lbl_filt = QLabel("عرض الأجهزة:")
        lbl_filt.setStyleSheet("color: #94A3B8; font-weight: bold;")
        ctrl_bar.addWidget(lbl_filt)

        self.btn_filter_connected = QPushButton("المتصلة فقط")
        self.btn_filter_connected.setCheckable(True)
        self.btn_filter_connected.setChecked(True)
        self.btn_filter_connected.setFixedHeight(30)
        self.btn_filter_connected.setStyleSheet(self._btn_style(True))
        self.btn_filter_connected.clicked.connect(lambda: self._set_filter("connected"))
        ctrl_bar.addWidget(self.btn_filter_connected)

        self.btn_filter_all = QPushButton("جميع الأجهزة المسجلة")
        self.btn_filter_all.setCheckable(True)
        self.btn_filter_all.setFixedHeight(30)
        self.btn_filter_all.setStyleSheet(self._btn_style(False))
        self.btn_filter_all.clicked.connect(lambda: self._set_filter("all"))
        ctrl_bar.addWidget(self.btn_filter_all)

        self.btn_filter_prob = QPushButton("الأجهزة التي بها مشاكل")
        self.btn_filter_prob.setCheckable(True)
        self.btn_filter_prob.setFixedHeight(30)
        self.btn_filter_prob.setStyleSheet(self._btn_style(False))
        self.btn_filter_prob.clicked.connect(lambda: self._set_filter("problems"))
        ctrl_bar.addWidget(self.btn_filter_prob)

        ctrl_bar.addStretch()

        self.btn_copy_hwid = QPushButton("  نسخ VID/PID")
        self.btn_copy_hwid.setIcon(get_icon("copy", "#FFFFFF", 14))
        self.btn_copy_hwid.setFixedHeight(32)
        self.btn_copy_hwid.setStyleSheet("""
            QPushButton {
                background: #334155; color: #F8FAFC; border-radius: 6px;
                padding: 0 12px; font-weight: bold; border: 1px solid #475569;
            }
            QPushButton:hover { background: #475569; }
        """)
        self.btn_copy_hwid.clicked.connect(self._copy_selected_id)
        ctrl_bar.addWidget(self.btn_copy_hwid)

        self.btn_eject = QPushButton("  إخراج آمن (Safe Eject)")
        self.btn_eject.setIcon(get_icon("devices", "#FFFFFF", 14))
        self.btn_eject.setFixedHeight(32)
        self.btn_eject.setStyleSheet("""
            QPushButton {
                background: #E11D48; color: #FFFFFF; border-radius: 6px;
                padding: 0 12px; font-weight: bold;
            }
            QPushButton:hover { background: #BE123C; }
        """)
        self.btn_eject.clicked.connect(self._eject_selected)
        ctrl_bar.addWidget(self.btn_eject)

        layout.addLayout(ctrl_bar)

        # 2. USB Devices Table
        table_card = QFrame()
        table_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 16px;")
        t_layout = QVBoxLayout(table_card)
        t_layout.setSpacing(12)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "اسم الجهاز (Device Name)", "التصنيف", "الحالة", "الشركة المصنعة", "معرّف العتاد (VID/PID)", "قابل للإزالة"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0F172A;
                border: 1px solid #334155;
                gridline-color: #1E293B;
                color: #F8FAFC;
                border-radius: 6px;
            }
            QHeaderView::section {
                background: #1E293B;
                color: #CBD5E1;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #334155;
            }
        """)
        self.table.setFixedHeight(360)
        t_layout.addWidget(self.table)
        layout.addWidget(table_card)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _btn_style(self, active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background: #0078D4; color: #FFFFFF; border-radius: 15px;
                    padding: 0 14px; font-weight: bold; border: none;
                }
            """
        return """
            QPushButton {
                background: #1E293B; color: #94A3B8; border-radius: 15px;
                padding: 0 14px; border: 1px solid #334155;
            }
            QPushButton:hover { background: #334155; color: #F8FAFC; }
        """

    def _set_filter(self, mode: str):
        self._filter_mode = mode
        self.btn_filter_connected.setChecked(mode == "connected")
        self.btn_filter_connected.setStyleSheet(self._btn_style(mode == "connected"))
        self.btn_filter_all.setChecked(mode == "all")
        self.btn_filter_all.setStyleSheet(self._btn_style(mode == "all"))
        self.btn_filter_prob.setChecked(mode == "problems")
        self.btn_filter_prob.setStyleSheet(self._btn_style(mode == "problems"))
        self.refresh_usb()

    def refresh_usb(self):
        try:
            conn = (self._filter_mode != "all")
            prob = (self._filter_mode == "problems")
            self._devices = UsbService.get_usb_devices(only_connected=conn, only_problems=prob)
            self._render()
        except Exception:
            pass

    def _render(self):
        self.table.setRowCount(len(self._devices))
        for r, dev in enumerate(self._devices):
            self.table.setItem(r, 0, QTableWidgetItem(dev.name))
            self.table.setItem(r, 1, QTableWidgetItem(dev.device_class))

            st_item = QTableWidgetItem(dev.status)
            if dev.status == "OK":
                st_item.setForeground(Qt.green)
            else:
                st_item.setForeground(Qt.red)
            self.table.setItem(r, 2, st_item)

            self.table.setItem(r, 3, QTableWidgetItem(dev.manufacturer))
            self.table.setItem(r, 4, QTableWidgetItem(f"{dev.vendor_id}:{dev.product_id}"))
            rem_str = "نعم (قابل للإخراج)" if dev.is_removable_storage else "لا (مثبت)"
            self.table.setItem(r, 5, QTableWidgetItem(rem_str))

    def _copy_selected_id(self):
        r = self.table.currentRow()
        if 0 <= r < len(self._devices):
            dev = self._devices[r]
            text = f"VID_{dev.vendor_id}&PID_{dev.product_id}\nInstance: {dev.instance_id}"
            QGuiApplication.clipboard().setText(text)
            QMessageBox.information(self, "تم النسخ", f"تم نسخ معرّف الجهاز إلى الحافظة:\n{dev.name}")

    def _eject_selected(self):
        r = self.table.currentRow()
        if 0 <= r < len(self._devices):
            dev = self._devices[r]
            res = UsbService.eject_usb_device(dev.instance_id)
            if res.get("success"):
                QMessageBox.information(self, "إخراج آمن", f"✓ {res.get('message_ar')}")
                self.refresh_usb()
            else:
                QMessageBox.warning(self, "فشل الإخراج", f"تعذر إخراج الجهاز:\n{res.get('message_ar')}")
