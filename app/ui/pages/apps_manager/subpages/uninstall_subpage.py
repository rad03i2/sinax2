# -*- coding: utf-8 -*-
"""
SINAX Batch Uninstall Subpage
Specialized subpage for batch selection and sequential uninstallation of applications
with pre-flight running process detection, system safeguards, and post-uninstall leftover prompts.
"""

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.uninstall_service import UninstallService
from app.ui.icons import get_icon
from app.ui.pages.apps_manager.sequential_queue_dialog import SequentialQueueDialog


class UninstallSubpage(QWidget):
    """Dedicated view for batch and single application uninstallation."""

    refresh_needed = Signal()
    leftover_scan_requested = Signal(object)  # InstalledApp

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._all_apps: List[InstalledApp] = []
        self._displayed_apps: List[InstalledApp] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Info Banner
        banner = QFrame()
        banner.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;")
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(8, 6, 8, 6)

        v_text = QVBoxLayout()
        lbl_t = QLabel("إلغاء التثبيت الجماعي الآمن (Sequential Batch Uninstall)")
        lbl_t.setStyleSheet("color: #F85149; font-size: 16px; font-weight: bold;")
        v_text.addWidget(lbl_t)

        lbl_desc = QLabel("حدد عدة برامج لإزالتها بالتتابع واحد تلو الآخر تلقائياً ودون تعارض في معالجات التثبيت.")
        lbl_desc.setStyleSheet("color: #8B949E; font-size: 12px;")
        v_text.addWidget(lbl_desc)
        b_layout.addLayout(v_text, 1)

        self.btn_execute_batch = QPushButton("إزالة البرامج المحددة")
        self.btn_execute_batch.setIcon(get_icon("uninstall", color="#F0F6FC"))
        self.btn_execute_batch.setStyleSheet("background: #DA3633; color: white; border: none; border-radius: 6px; padding: 10px 18px; font-weight: bold; font-size: 13px;")
        self.btn_execute_batch.clicked.connect(self._on_start_batch_uninstall)
        b_layout.addWidget(self.btn_execute_batch)

        main_layout.addWidget(banner)

        # 2. Filter Bar
        fb = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("تصفية البرامج بالاسم للبحث السريع...")
        self.search_input.setStyleSheet("background: #161B22; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px;")
        self.search_input.textChanged.connect(self._filter_list)
        fb.addWidget(self.search_input)

        btn_all = QPushButton("تحديد الكل")
        btn_all.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px;")
        btn_all.clicked.connect(lambda: self._set_all_checks(True))
        fb.addWidget(btn_all)

        btn_none = QPushButton("إلغاء التحديد")
        btn_none.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px;")
        btn_none.clicked.connect(lambda: self._set_all_checks(False))
        fb.addWidget(btn_none)

        main_layout.addLayout(fb)

        # 3. Apps Selection Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "تحديد",
            "اسم البرنامج",
            "الناشر",
            "الحجم",
            "حالة الأمان والتشغيل",
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 45)
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
        """Sets full app list and filters out protected system apps."""
        # Only show removable apps by default
        self._all_apps = [a for a in apps if not a.is_system_component and not a.is_runtime_or_driver]
        self._filter_list()

    def _filter_list(self):
        query = self.search_input.text().strip().lower()
        if query:
            self._displayed_apps = [a for a in self._all_apps if query in a.name.lower() or query in a.publisher.lower()]
        else:
            self._displayed_apps = list(self._all_apps)

        self.table.setRowCount(len(self._displayed_apps))
        for r, app in enumerate(self._displayed_apps):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Unchecked)
            self.table.setItem(r, 0, chk)

            self.table.setItem(r, 1, QTableWidgetItem(app.name))
            self.table.setItem(r, 2, QTableWidgetItem(app.publisher))
            self.table.setItem(r, 3, QTableWidgetItem(app.display_size))

            status_text = "آمن للإزالة"
            status_color = "#3FB950"
            if app.is_running:
                status_text = "يعمل حالياً (يوصى بإغلاقه)"
                status_color = "#D29922"

            st_item = QTableWidgetItem(status_text)
            st_item.setForeground(QColor(status_color))
            self.table.setItem(r, 4, st_item)

    def _set_all_checks(self, check: bool):
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked if check else Qt.Unchecked)

    def _get_checked_apps(self) -> List[InstalledApp]:
        selected = []
        for r in range(self.table.rowCount()):
            chk = self.table.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                if r < len(self._displayed_apps):
                    selected.append(self._displayed_apps[r])
        return selected

    def _on_start_batch_uninstall(self):
        selected = self._get_checked_apps()
        if not selected:
            QMessageBox.information(self, "إزالة محددة", "يرجى تحديد برنامج واحد على الأقل عبر مربعات الاختيار [✓].")
            return

        # Pre-flight Check: Running Apps
        running_apps = [a for a in selected if a.is_running]
        if running_apps:
            running_names = "\n".join(f"• {a.name}" for a in running_apps)
            reply = QMessageBox.warning(
                self,
                "تنبيه: برامج تعمل حالياً",
                f"البرامج التالية قيد التشغيل حالياً:\n\n{running_names}\n\nيوصى بإغلاقها أولاً لتفادي فشل عملية الإزالة.\nهل ترغب في المتابعة على أية حال؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # Final Confirmation
        names_list = "\n".join(f"• {a.name} ({a.display_size})" for a in selected)
        reply = QMessageBox.question(
            self,
            f"تأكيد إزالة {len(selected)} برنامجاً",
            f"سيتم تشغيل برامج الإزالة الرسمية بالتتابع للبرامج التالية:\n\n{names_list}\n\nهل ترغب في بدء عملية الإزالة؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        # Execute Sequential Queue
        dlg = SequentialQueueDialog(
            title=f"جارٍ إزالة {len(selected)} برنامجاً بالتتابع",
            items=selected,
            task_fn=UninstallService.execute_batch,
            parent=self,
        )
        dlg.exec()
        self.refresh_needed.emit()

        # Prompt for Leftovers Scan if at least one succeeded
        if dlg.report_result and hasattr(dlg.report_result, "succeeded") and dlg.report_result.succeeded:
            first_removed = selected[0]
            reply_leftover = QMessageBox.question(
                self,
                "فحص بقايا البرامج",
                "اكتملت إزالة بعض البرامج بنجاح.\n\nهل ترغب في فتح فاحص البقايا للبحث عن الملفات والمجلدات المتروكة؟",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply_leftover == QMessageBox.Yes:
                self.leftover_scan_requested.emit(first_removed)
