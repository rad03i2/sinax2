# -*- coding: utf-8 -*-
"""
SINAX Application Updates Subpage
Dedicated update management center powered by WinGet CLI.
Allows discovering pending updates, upgrading single or batch apps, previewing changes, and version pinning.
"""

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
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
from app.services.apps_manager.update_service import UpdateService
from app.ui.icons import get_icon
from app.ui.pages.apps_manager.sequential_queue_dialog import SequentialQueueDialog


class UpdatesSubpage(QWidget):
    """Subpage managing software updates and version pinning."""

    check_updates_requested = Signal()
    refresh_needed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._updateable_apps: List[InstalledApp] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Control Bar
        top_bar = QFrame()
        top_bar.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(8, 6, 8, 6)
        tb_layout.setSpacing(10)

        v_info = QVBoxLayout()
        self.lbl_title = QLabel("تحديثات البرامج المتاحة")
        self.lbl_title.setStyleSheet("color: #58A6FF; font-size: 16px; font-weight: bold;")
        v_info.addWidget(self.lbl_title)

        self.lbl_count = QLabel("جاري فحص التحديثات المتاحة عبر WinGet...")
        self.lbl_count.setStyleSheet("color: #8B949E; font-size: 12px;")
        v_info.addWidget(self.lbl_count)
        tb_layout.addLayout(v_info, 1)

        self.btn_check = QPushButton("فحص التحديثات")
        self.btn_check.setIcon(get_icon("update", color="#F0F6FC"))
        self.btn_check.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        self.btn_check.clicked.connect(self.check_updates_requested.emit)
        tb_layout.addWidget(self.btn_check)

        self.btn_update_selected = QPushButton("تحديث المحدد")
        self.btn_update_selected.setStyleSheet("background: #1F6FEB; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        self.btn_update_selected.clicked.connect(self._on_update_selected)
        tb_layout.addWidget(self.btn_update_selected)

        self.btn_update_all = QPushButton("تحديث الكل")
        self.btn_update_all.setStyleSheet("background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        self.btn_update_all.clicked.connect(self._on_update_all_preview)
        tb_layout.addWidget(self.btn_update_all)

        main_layout.addWidget(top_bar)

        # 2. Updates Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "تحديد",
            "اسم البرنامج",
            "الإصدار المثبت",
            "الإصدار الجديد",
            "المصدر",
            "معرف WinGet",
            "إجراء سريع",
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 45)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0D1117; alternate-background-color: #161B22; color: #C9D1D9;
                border: 1px solid #30363D; border-radius: 10px; selection-background-color: #1F242C; font-size: 12px;
            }
            QHeaderView::section {
                background: #161B22; color: #F0F6FC; font-weight: bold;
                border: none; border-bottom: 1px solid #30363D; padding: 8px;
            }
        """)
        main_layout.addWidget(self.table, 1)

    def set_apps(self, apps: List[InstalledApp]):
        """Populates the table with apps that have updates available."""
        self._updateable_apps = [a for a in apps if a.update_available]
        self.table.setRowCount(len(self._updateable_apps))

        self.lbl_count.setText(f"يوجد {len(self._updateable_apps)} برنامجاً يتوفر له تحديثات جديدة")

        for r, app in enumerate(self._updateable_apps):
            # Checkbox item
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked)
            self.table.setItem(r, 0, chk_item)

            # Name
            self.table.setItem(r, 1, QTableWidgetItem(app.name))

            # Installed Version
            self.table.setItem(r, 2, QTableWidgetItem(app.version))

            # Available Version (Highlighted green)
            avail_item = QTableWidgetItem(app.available_version or "أحدث")
            avail_item.setForeground(QColor("#3FB950"))
            font = QFont()
            font.setBold(True)
            avail_item.setFont(font)
            self.table.setItem(r, 3, avail_item)

            # Source
            self.table.setItem(r, 4, QTableWidgetItem(app.source.upper()))

            # Package ID
            self.table.setItem(r, 5, QTableWidgetItem(app.package_id or "-"))

            # Actions widget
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(6)

            btn_one = QPushButton("تحديث")
            btn_one.setStyleSheet("background: #1F6FEB; color: white; border: none; border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;")
            btn_one.clicked.connect(lambda _, a=app: self._on_update_single(a))
            act_layout.addWidget(btn_one)

            btn_pin = QPushButton("تثبيت (Pin)" if not app.is_pinned else "فك التثبيت")
            btn_pin.setStyleSheet("background: #21262D; color: #8B949E; border: 1px solid #30363D; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
            btn_pin.clicked.connect(lambda _, a=app: self._on_toggle_pin(a))
            act_layout.addWidget(btn_pin)

            self.table.setCellWidget(r, 6, act_widget)

    def _get_checked_apps(self) -> List[InstalledApp]:
        selected = []
        for r in range(self.table.rowCount()):
            chk_item = self.table.item(r, 0)
            if chk_item and chk_item.checkState() == Qt.Checked:
                if r < len(self._updateable_apps):
                    selected.append(self._updateable_apps[r])
        return selected

    def _on_update_single(self, app: InstalledApp):
        dlg = SequentialQueueDialog(
            title=f"جارٍ تحديث: {app.name}",
            items=[app],
            task_fn=UpdateService.execute_batch_update,
            parent=self,
        )
        dlg.exec()
        self.refresh_needed.emit()

    def _on_update_selected(self):
        selected = self._get_checked_apps()
        if not selected:
            QMessageBox.information(self, "تحديث", "يرجى تحديد تطبيق واحد على الأقل عبر مربعات الاختيار.")
            return

        dlg = SequentialQueueDialog(
            title=f"جارٍ تحديث {len(selected)} برنامجاً بالتتابع",
            items=selected,
            task_fn=UpdateService.execute_batch_update,
            parent=self,
        )
        dlg.exec()
        self.refresh_needed.emit()

    def _on_update_all_preview(self):
        if not self._updateable_apps:
            QMessageBox.information(self, "تحديث الكل", "لا تتوفر أي تحديثات حالياً.")
            return

        # Preview Dialog before Update All
        preview_text = "\n".join(f"• {a.name}: من {a.version} إلى {a.available_version}" for a in self._updateable_apps)
        reply = QMessageBox.question(
            self,
            "معاينة تحديث جميع البرامج",
            f"سيتم تحديث البرامج التالية بالتتابع عبر WinGet:\n\n{preview_text}\n\nهل ترغب في بدء التحديث الآن؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            dlg = SequentialQueueDialog(
                title=f"جارٍ تحديث جميع البرامج ({len(self._updateable_apps)}) بالتتابع",
                items=self._updateable_apps,
                task_fn=UpdateService.execute_batch_update,
                parent=self,
            )
            dlg.exec()
            self.refresh_needed.emit()

    def _on_toggle_pin(self, app: InstalledApp):
        if app.is_pinned:
            UpdateService.unpin_app(app)
            QMessageBox.information(self, "تثبيت الإصدار", f"تم فك تقييد التحديثات للبرنامج {app.name}.")
        else:
            UpdateService.pin_app(app)
            QMessageBox.information(self, "تثبيت الإصدار", f"تم تثبيت إصدار البرنامج {app.name} ومنع تحديثه التلقائي.")
        self.set_apps(self._updateable_apps)
