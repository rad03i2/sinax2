# -*- coding: utf-8 -*-
"""
SINAX Windows & Environment Subpage (صفحة بيئة ونظام Windows)
Displays Windows edition, version, build number, installation date, uptime,
activation status, system folders, and quick shortcuts to Windows settings.
"""

from typing import Optional

from PySide6.QtCore import Qt, QTimer
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

from app.services.devices.hardware_models import WindowsDetails
from app.services.devices.windows_info_service import WindowsInfoService
from app.ui.icons import get_icon


class WindowsSubpage(QWidget):
    """Subpage for inspecting Windows operating system environment and settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._win_info: Optional[WindowsDetails] = None
        self._timer: Optional[QTimer] = None
        self._init_ui()
        self.refresh_windows()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_windows)
        self._timer.start(10000)  # update uptime every 10s

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
        title = QLabel("نظام التشغيل والبيئة (Windows Specs & Environment)")
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
        self.refresh_btn.clicked.connect(self.refresh_windows)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. OS Edition Hero Card
        os_card = QFrame()
        os_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        os_layout = QVBoxLayout(os_card)
        os_layout.setSpacing(14)

        os_head = QHBoxLayout()
        self.os_edition_lbl = QLabel("Microsoft Windows")
        self.os_edition_lbl.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self.os_edition_lbl.setStyleSheet("color: #38BDF8; background: transparent;")
        os_head.addWidget(self.os_edition_lbl)
        os_head.addStretch()

        self.activation_badge = QLabel("نشط ومفعل")
        self.activation_badge.setStyleSheet("""
            background: #10B981; color: #FFFFFF; border-radius: 6px;
            padding: 4px 12px; font-size: 11px; font-weight: bold;
        """)
        os_head.addWidget(self.activation_badge)
        os_layout.addLayout(os_head)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.lbl_ver = self._create_spec_item(grid, 0, 0, "الإصدار (Version):")
        self.lbl_build = self._create_spec_item(grid, 0, 1, "رقم البناء (OS Build):")
        self.lbl_arch = self._create_spec_item(grid, 0, 2, "معمارية النظام:")

        self.lbl_install = self._create_spec_item(grid, 1, 0, "تاريخ التثبيت:")
        self.lbl_boot = self._create_spec_item(grid, 1, 1, "آخر تشغيل:")
        self.lbl_uptime = self._create_spec_item(grid, 1, 2, "مدة التشغيل المستمرة (Uptime):")

        self.lbl_pcname = self._create_spec_item(grid, 2, 0, "اسم الكمبيوتر:")
        self.lbl_user = self._create_spec_item(grid, 2, 1, "المستخدم الحالي:")
        self.lbl_sysdir = self._create_spec_item(grid, 2, 2, "مجلد النظام:")

        os_layout.addLayout(grid)
        layout.addWidget(os_card)

        # 2. Native Windows Settings Shortcuts Card
        actions_card = QFrame()
        actions_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        act_layout = QVBoxLayout(actions_card)
        act_layout.setSpacing(12)

        act_title = QLabel("اختصارات سريعة لإعدادات Windows الرسمية")
        act_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        act_title.setStyleSheet("color: #F8FAFC; background: transparent;")
        act_layout.addWidget(act_title)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(12)

        btn_sys = QPushButton("  إعدادات النظام (System)")
        btn_sys.setIcon(get_icon("settings", "#FFFFFF", 16))
        btn_sys.setFixedHeight(36)
        btn_sys.setStyleSheet(self._action_btn_style())
        btn_sys.clicked.connect(lambda: WindowsInfoService.open_windows_settings("system"))
        btns_row.addWidget(btn_sys)

        btn_upd = QPushButton("  تحديثات Windows Update")
        btn_upd.setIcon(get_icon("devices", "#FFFFFF", 16))
        btn_upd.setFixedHeight(36)
        btn_upd.setStyleSheet(self._action_btn_style())
        btn_upd.clicked.connect(lambda: WindowsInfoService.open_windows_settings("windowsupdate"))
        btns_row.addWidget(btn_upd)

        btn_act = QPushButton("  إعدادات التنشيط (Activation)")
        btn_act.setIcon(get_icon("shield", "#FFFFFF", 16))
        btn_act.setFixedHeight(36)
        btn_act.setStyleSheet(self._action_btn_style())
        btn_act.clicked.connect(lambda: WindowsInfoService.open_windows_settings("activation"))
        btns_row.addWidget(btn_act)

        btns_row.addStretch()
        act_layout.addLayout(btns_row)
        layout.addWidget(actions_card)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _action_btn_style(self) -> str:
        return """
            QPushButton {
                background: #334155; color: #F8FAFC; border-radius: 6px;
                padding: 0 16px; font-weight: bold; border: 1px solid #475569;
            }
            QPushButton:hover { background: #475569; }
        """

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

    def refresh_windows(self):
        try:
            self._win_info = WindowsInfoService.get_windows_details()
            self._render()
        except Exception:
            pass

    def _render(self):
        if not self._win_info:
            return
        w = self._win_info
        self.os_edition_lbl.setText(w.edition)
        self.activation_badge.setText(w.activation_status)
        if "نشط" in w.activation_status or "Activated" in w.activation_status:
            self.activation_badge.setStyleSheet("background: #10B981; color: #FFFFFF; border-radius: 6px; padding: 4px 12px; font-weight: bold;")
        else:
            self.activation_badge.setStyleSheet("background: #F59E0B; color: #000000; border-radius: 6px; padding: 4px 12px; font-weight: bold;")

        self.lbl_ver.setText(w.version)
        self.lbl_build.setText(w.build)
        self.lbl_arch.setText(w.architecture)
        self.lbl_install.setText(w.install_date)
        self.lbl_boot.setText(w.last_boot)
        self.lbl_uptime.setText(w.uptime_formatted)
        self.lbl_pcname.setText(w.computer_name)
        self.lbl_user.setText(w.username)
        self.lbl_sysdir.setText(w.system_directory)
