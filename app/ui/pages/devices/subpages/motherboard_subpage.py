# -*- coding: utf-8 -*-
"""
SINAX Motherboard & BIOS Subpage (صفحة اللوحة الأم وBIOS)
Displays motherboard specifications, firmware release, UEFI vs Legacy boot mode,
Secure Boot status, and TPM (Trusted Platform Module) version & security readiness.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.hardware_models import BiosInfo, MotherboardInfo
from app.services.devices.motherboard_bios_service import MotherboardBiosService
from app.ui.icons import get_icon


class MotherboardSubpage(QWidget):
    """Subpage for viewing motherboard hardware and BIOS/UEFI firmware capabilities."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._mb_info: Optional[MotherboardInfo] = None
        self._bios_info: Optional[BiosInfo] = None
        self._init_ui()
        self.refresh_data()

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
        title = QLabel("اللوحة الأم والبرامج الثابتة (Motherboard & BIOS)")
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
        self.refresh_btn.clicked.connect(self.refresh_data)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Motherboard Card
        mb_card = QFrame()
        mb_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        mb_layout = QVBoxLayout(mb_card)
        mb_layout.setSpacing(14)

        mb_title = QLabel("معلومات اللوحة الأم (Motherboard / BaseBoard)")
        mb_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        mb_title.setStyleSheet("color: #38BDF8; background: transparent;")
        mb_layout.addWidget(mb_title)

        grid_mb = QGridLayout()
        grid_mb.setSpacing(12)
        self.lbl_mb_manuf = self._create_spec_item(grid_mb, 0, 0, "الشركة المصنعة:")
        self.lbl_mb_prod = self._create_spec_item(grid_mb, 0, 1, "طراز اللوحة (Model):")
        self.lbl_mb_ver = self._create_spec_item(grid_mb, 0, 2, "إصدار العتاد:")
        self.lbl_mb_serial = self._create_spec_item(grid_mb, 1, 0, "الرقم التسلسلي (Serial):")
        self.lbl_mb_sku = self._create_spec_item(grid_mb, 1, 1, "معرّف النظام (SKU):")
        mb_layout.addLayout(grid_mb)
        layout.addWidget(mb_card)

        # 2. BIOS / UEFI Card
        bios_card = QFrame()
        bios_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        bios_layout = QVBoxLayout(bios_card)
        bios_layout.setSpacing(14)

        bios_title = QLabel("البرامج الثابتة ونظام الإقلاع (BIOS / UEFI Firmware)")
        bios_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        bios_title.setStyleSheet("color: #38BDF8; background: transparent;")
        bios_layout.addWidget(bios_title)

        grid_bios = QGridLayout()
        grid_bios.setSpacing(12)
        self.lbl_bios_vendor = self._create_spec_item(grid_bios, 0, 0, "مطور الـ BIOS:")
        self.lbl_bios_ver = self._create_spec_item(grid_bios, 0, 1, "إصدار BIOS:")
        self.lbl_bios_date = self._create_spec_item(grid_bios, 0, 2, "تاريخ الإصدار:")
        self.lbl_smbios_ver = self._create_spec_item(grid_bios, 1, 0, "إصدار SMBIOS:")
        bios_layout.addLayout(grid_bios)
        layout.addWidget(bios_card)

        # 3. Security & Modern Boot Environment
        sec_card = QFrame()
        sec_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        sec_layout = QVBoxLayout(sec_card)
        sec_layout.setSpacing(14)

        sec_title = QLabel("أمان الإقلاع والعتاد (Boot & Hardware Security)")
        sec_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        sec_title.setStyleSheet("color: #38BDF8; background: transparent;")
        sec_layout.addWidget(sec_title)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(14)

        self.box_boot_mode = self._create_status_box("نمط الإقلاع (Boot Mode)", "UEFI", "#10B981")
        self.box_secure_boot = self._create_status_box("الإقلاع الآمن (Secure Boot)", "مفعل", "#10B981")
        self.box_tpm = self._create_status_box("شريحة الأمان (TPM 2.0)", "نشطة وجاهزة", "#10B981")

        badges_row.addWidget(self.box_boot_mode)
        badges_row.addWidget(self.box_secure_boot)
        badges_row.addWidget(self.box_tpm)
        sec_layout.addLayout(badges_row)

        layout.addWidget(sec_card)
        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_spec_item(self, grid: QGridLayout, row: int, col: int, label_text: str) -> QLabel:
        box = QVBoxLayout()
        box.setSpacing(4)
        t_lbl = QLabel(label_text)
        t_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        val_lbl = QLabel("—")
        val_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        val_lbl.setStyleSheet("color: #F8FAFC; background: transparent;")
        box.addWidget(t_lbl)
        box.addWidget(val_lbl)
        grid.addLayout(box, row, col)
        return val_lbl

    def _create_status_box(self, title: str, val: str, color_hex: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        vbox = QVBoxLayout(frame)
        vbox.setSpacing(6)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        lbl_v = QLabel(val)
        lbl_v.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_v.setStyleSheet(f"color: {color_hex}; background: transparent;")
        vbox.addWidget(lbl_t)
        vbox.addWidget(lbl_v)
        frame.val_label = lbl_v  # type: ignore
        return frame

    def refresh_data(self):
        try:
            self._mb_info = MotherboardBiosService.get_motherboard_info()
            self._bios_info = MotherboardBiosService.get_bios_info()
            self._render()
        except Exception:
            pass

    def _render(self):
        if self._mb_info:
            self.lbl_mb_manuf.setText(self._mb_info.manufacturer)
            self.lbl_mb_prod.setText(self._mb_info.product)
            self.lbl_mb_ver.setText(self._mb_info.version)
            self.lbl_mb_serial.setText(self._mb_info.serial_number)
            self.lbl_mb_sku.setText(self._mb_info.system_sku)

        if self._bios_info:
            self.lbl_bios_vendor.setText(self._bios_info.manufacturer)
            self.lbl_bios_ver.setText(self._bios_info.version)
            self.lbl_bios_date.setText(self._bios_info.release_date)
            self.lbl_smbios_ver.setText(self._bios_info.smbios_version)

            self.box_boot_mode.val_label.setText(self._bios_info.bios_mode)  # type: ignore
            self.box_secure_boot.val_label.setText(self._bios_info.secure_boot)  # type: ignore
            if "مفعل" in self._bios_info.secure_boot:
                self.box_secure_boot.val_label.setStyleSheet("color: #10B981; font-weight: bold;")  # type: ignore
            else:
                self.box_secure_boot.val_label.setStyleSheet("color: #F59E0B; font-weight: bold;")  # type: ignore

            self.box_tpm.val_label.setText(self._bios_info.tpm_status_ar)  # type: ignore
            if self._bios_info.tpm_detected:
                self.box_tpm.val_label.setStyleSheet("color: #10B981; font-weight: bold;")  # type: ignore
            else:
                self.box_tpm.val_label.setStyleSheet("color: #94A3B8; font-weight: bold;")  # type: ignore
