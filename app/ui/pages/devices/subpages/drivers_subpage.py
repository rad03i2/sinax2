# -*- coding: utf-8 -*-
"""
SINAX Drivers & Device Manager Subpage (صفحة إدارة الأجهزة والتعريفات)
Displays PnP hardware device tree categorized by device class, problem devices
filter, missing drivers with Hardware ID copy, and driver backup via pnputil.
"""

import os
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.driver_service import DriverService
from app.services.devices.hardware_models import PnpDeviceInfo
from app.ui.icons import get_icon


class BackupWorker(QThread):
    """Background worker for exporting drivers via pnputil."""
    progress = Signal(str)
    finished = Signal(dict)

    def __init__(self, dest_dir: str):
        super().__init__()
        self.dest_dir = dest_dir

    def run(self):
        res = DriverService.backup_drivers(self.dest_dir, lambda msg: self.progress.emit(msg))
        self.finished.emit(res)


class DriversSubpage(QWidget):
    """Subpage for viewing PnP hardware devices, troubleshooting drivers, and backing them up."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._tree_data: Dict[str, List[PnpDeviceInfo]] = {}
        self._problem_devices: List[PnpDeviceInfo] = []
        self._backup_worker: Optional[BackupWorker] = None
        self._init_ui()
        self.refresh_devices()

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
        title = QLabel("إدارة الأجهزة وحزم التعريفات (Drivers & Device Manager)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.btn_backup = QPushButton("  النسخ الاحتياطي للتعريفات")
        self.btn_backup.setIcon(get_icon("devices", "#FFFFFF", 16))
        self.btn_backup.setFixedHeight(34)
        self.btn_backup.setStyleSheet("""
            QPushButton {
                background: #0284C7; color: #FFFFFF; border-radius: 6px;
                padding: 0 14px; font-weight: bold;
            }
            QPushButton:hover { background: #0369A1; }
        """)
        self.btn_backup.clicked.connect(self._start_backup)
        top_bar.addWidget(self.btn_backup)

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
        self.refresh_btn.clicked.connect(self.refresh_devices)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Problem Devices Banner (if any)
        self.problem_box = QFrame()
        self.problem_box.setStyleSheet("background: #451A03; border: 1px solid #B45309; border-radius: 10px; padding: 14px 18px;")
        p_layout = QHBoxLayout(self.problem_box)
        p_icon = QLabel()
        p_icon.setPixmap(get_icon("warning", "#F59E0B", 22).pixmap(22, 22))
        p_layout.addWidget(p_icon)

        self.problem_msg_lbl = QLabel("تنبيه: تم اكتشاف أجهزة بها مشاكل أو تعريفات مفقودة.")
        self.problem_msg_lbl.setStyleSheet("color: #FEF3C7; font-weight: bold; background: transparent;")
        p_layout.addWidget(self.problem_msg_lbl, 1)

        self.btn_copy_hwid = QPushButton("نسخ معرّف العتاد للبحث")
        self.btn_copy_hwid.setFixedHeight(30)
        self.btn_copy_hwid.setStyleSheet("""
            QPushButton {
                background: #B45309; color: #FFFFFF; border-radius: 6px;
                padding: 0 12px; font-weight: bold;
            }
            QPushButton:hover { background: #92400E; }
        """)
        self.btn_copy_hwid.clicked.connect(self._copy_problem_hwid)
        p_layout.addWidget(self.btn_copy_hwid)

        self.problem_box.setVisible(False)
        layout.addWidget(self.problem_box)

        # 2. Main Device Tree
        tree_card = QFrame()
        tree_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 16px;")
        t_layout = QVBoxLayout(tree_card)
        t_layout.setSpacing(12)

        t_title = QLabel("شجرة عتاد النظام (PnP Device Tree)")
        t_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        t_title.setStyleSheet("color: #F8FAFC; background: transparent;")
        t_layout.addWidget(t_title)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["الجهاز / التصنيف", "الحالة", "الشركة المصنعة", "التعريف"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: #0F172A;
                border: 1px solid #334155;
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
            QTreeWidget::item:selected {
                background: #0078D4;
                color: #FFFFFF;
            }
        """)
        self.tree.setFixedHeight(340)
        t_layout.addWidget(self.tree)
        layout.addWidget(tree_card)

        # 3. Driver Backup Progress Frame
        self.backup_status_frame = QFrame()
        self.backup_status_frame.setStyleSheet("background: #0F172A; border: 1px solid #1E293B; border-radius: 8px; padding: 12px 16px;")
        bs_layout = QVBoxLayout(self.backup_status_frame)
        bs_layout.setSpacing(6)

        self.backup_lbl = QLabel("جاهز للنسخ الاحتياطي...")
        self.backup_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        bs_layout.addWidget(self.backup_lbl)

        self.backup_bar = QProgressBar()
        self.backup_bar.setFixedHeight(10)
        self.backup_bar.setTextVisible(False)
        self.backup_bar.setRange(0, 0)  # indeterminate while running
        self.backup_bar.setStyleSheet("QProgressBar { background: #1E293B; border-radius: 5px; } QProgressBar::chunk { background: #0284C7; }")
        self.backup_bar.setVisible(False)
        bs_layout.addWidget(self.backup_bar)

        layout.addWidget(self.backup_status_frame)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def refresh_devices(self):
        try:
            self._tree_data = DriverService.get_pnp_tree()
            self._problem_devices = DriverService.get_problem_devices()
            self._render()
        except Exception:
            pass

    def _render(self):
        # Problem box
        if self._problem_devices:
            self.problem_box.setVisible(True)
            self.problem_msg_lbl.setText(
                f"تنبيه: تم اكتشاف {len(self._problem_devices)} أجهزة بها مشاكل أو تعريفات مفقودة في مدير الأجهزة."
            )
        else:
            self.problem_box.setVisible(False)

        # Tree
        self.tree.clear()
        for cls_name, devices in sorted(self._tree_data.items()):
            parent_item = QTreeWidgetItem([f"📁 {cls_name} ({len(devices)})", "", "", ""])
            parent_item.setFont(0, QFont("Segoe UI", 10, QFont.Bold))
            parent_item.setForeground(0, Qt.white)
            self.tree.addTopLevelItem(parent_item)

            for dev in devices:
                st_text = dev.status
                if dev.is_problem:
                    st_text = f"⚠ خطأ ({dev.error_code})"
                child_item = QTreeWidgetItem([dev.name, st_text, dev.manufacturer, dev.driver_name])
                if dev.is_problem:
                    child_item.setForeground(1, Qt.red)
                else:
                    child_item.setForeground(1, Qt.green)
                parent_item.addChild(child_item)

        self.tree.expandToDepth(0)

    def _copy_problem_hwid(self):
        if not self._problem_devices:
            return
        lines = []
        for dev in self._problem_devices:
            hw_str = "\n  ".join(dev.hardware_ids) if dev.hardware_ids else dev.instance_id
            lines.append(f"[{dev.name}]\n  Class: {dev.device_class}\n  Status: {dev.status}\n  IDs:\n  {hw_str}")
        full_text = "\n\n".join(lines)
        QGuiApplication.clipboard().setText(full_text)
        QMessageBox.information(self, "تم النسخ", "تم نسخ معرّفات الأجهزة المعطوبة إلى الحافظة للبحث عنها.")

    def _start_backup(self):
        dest_dir = QFileDialog.getExistingDirectory(self, "اختر مجلد حفظ النسخة الاحتياطية للتعريفات")
        if not dest_dir:
            return

        self.btn_backup.setEnabled(False)
        self.backup_bar.setVisible(True)
        self.backup_lbl.setText(f"جاري تصدير التعريفات عبر pnputil إلى: {dest_dir} ...")

        self._backup_worker = BackupWorker(dest_dir)
        self._backup_worker.progress.connect(lambda msg: self.backup_lbl.setText(msg))
        self._backup_worker.finished.connect(self._on_backup_finished)
        self._backup_worker.start()

    def _on_backup_finished(self, res: dict):
        self.btn_backup.setEnabled(True)
        self.backup_bar.setVisible(False)
        if res.get("success"):
            self.backup_lbl.setText(f"✓ {res.get('message_ar')} ({res.get('exported_count', 0)} تعريف)")
            QMessageBox.information(
                self, "نجاح النسخ الاحتياطي",
                f"تم حفظ {res.get('exported_count', 0)} تعريف بنجاح في:\n{res.get('destination_dir')}"
            )
        else:
            self.backup_lbl.setText(f"فشل: {res.get('message_ar')}")
            QMessageBox.warning(self, "تنبيه", f"تعذر إتمام النسخ الاحتياطي:\n{res.get('message_ar')}")
