# -*- coding: utf-8 -*-
"""
SINAX Restore Apps Subpage (استعادة البرامج بعد الفورمات)
Imports software backup JSON or WinGet export, displays an interactive checklist,
and launches a sequential automated re-installation queue.
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont
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

from app.services.apps_manager.backup_restore_service import BackupRestoreService
from app.ui.icons import get_icon
from app.ui.pages.apps_manager.sequential_queue_dialog import SequentialQueueDialog


class RestoreSubpage(QWidget):
    """Subpage for restoring applications from a backup file."""

    refresh_needed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._parsed_data: Dict[str, Any] = {}
        self._installable_items: List[Dict[str, Any]] = []
        self._manual_items: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top File Picker Frame
        top_frame = QFrame()
        top_frame.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        tf_layout = QVBoxLayout(top_frame)
        tf_layout.setSpacing(10)

        lbl_t = QLabel("استعادة البرامج بعد الفورمات (Restore Apps Wizard)")
        lbl_t.setStyleSheet("color: #3FB950; font-size: 16px; font-weight: bold;")
        tf_layout.addWidget(lbl_t)

        lbl_desc = QLabel("اختر ملف النسخة الاحتياطية (SINAX_Apps_Backup.json أو ملف WinGet) لإعادة تنصيب برامجك دفعة واحدة تلقائياً.")
        lbl_desc.setStyleSheet("color: #8B949E; font-size: 12px;")
        tf_layout.addWidget(lbl_desc)

        picker_row = QHBoxLayout()
        self.lbl_file_path = QLabel("لم يتم اختيار ملف بعد...")
        self.lbl_file_path.setStyleSheet("background: #0D1117; color: #8B949E; border: 1px solid #30363D; border-radius: 6px; padding: 8px 12px; font-size: 12px;")
        picker_row.addWidget(self.lbl_file_path, 1)

        btn_select_file = QPushButton("اختيار ملف النسخة الاحتياطية")
        btn_select_file.setIcon(get_icon("restore", color="#F0F6FC"))
        btn_select_file.setStyleSheet("background: #1F6FEB; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        btn_select_file.clicked.connect(self._on_choose_file)
        picker_row.addWidget(btn_select_file)

        tf_layout.addLayout(picker_row)
        main_layout.addWidget(top_frame)

        # 2. Controls & Summary Bar
        ctrl_bar = QHBoxLayout()
        self.lbl_summary = QLabel("يرجى اختيار ملف لعرض قائمة البرامج القابلة للتثبيت.")
        self.lbl_summary.setStyleSheet("color: #C9D1D9; font-size: 13px; font-weight: bold;")
        ctrl_bar.addWidget(self.lbl_summary)

        ctrl_bar.addStretch(1)

        btn_all = QPushButton("تحديد الكل")
        btn_all.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px; font-size: 11px;")
        btn_all.clicked.connect(lambda: self._set_all_checks(True))
        ctrl_bar.addWidget(btn_all)

        btn_none = QPushButton("إلغاء التحديد")
        btn_none.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px; font-size: 11px;")
        btn_none.clicked.connect(lambda: self._set_all_checks(False))
        ctrl_bar.addWidget(btn_none)

        self.btn_install = QPushButton("تثبيت البرامج المحددة الآن")
        self.btn_install.setIcon(get_icon("restore", color="#F0F6FC"))
        self.btn_install.setEnabled(False)
        self.btn_install.setStyleSheet("""
            QPushButton {
                background: #238636; color: white; border: none; border-radius: 6px;
                padding: 8px 18px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #2EA043; }
            QPushButton:disabled { background: #21262D; color: #484F58; }
        """)
        self.btn_install.clicked.connect(self._on_install_selected)
        ctrl_bar.addWidget(self.btn_install)

        main_layout.addLayout(ctrl_bar)

        # 3. Interactive Checklist Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "تثبيت",
            "اسم البرنامج",
            "الناشر",
            "معرف WinGet",
            "إمكانية الاستعادة التلقائية",
        ])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
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

    def _on_choose_file(self):
        f_path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف النسخة الاحتياطية",
            os.path.join(os.path.expanduser("~"), "Desktop"),
            "JSON Backup Files (*.json)",
        )
        if f_path:
            self.lbl_file_path.setText(f_path)
            self.lbl_file_path.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px 12px; font-size: 12px;")
            self._load_file(f_path)

    def _load_file(self, file_path: str):
        try:
            data = BackupRestoreService.inspect_backup_file(file_path)
            self._parsed_data = data
            self._installable_items = data.get("installable_items", [])
            self._manual_items = data.get("manual_items", [])

            all_items = self._installable_items + self._manual_items
            self.table.setRowCount(len(all_items))

            for r, item in enumerate(all_items):
                is_auto = item.get("installable_via_winget", False)

                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled if is_auto else Qt.NoItemFlags)
                chk.setCheckState(Qt.Checked if is_auto else Qt.Unchecked)
                self.table.setItem(r, 0, chk)

                self.table.setItem(r, 1, QTableWidgetItem(item.get("name", "-")))
                self.table.setItem(r, 2, QTableWidgetItem(item.get("publisher", "-")))
                self.table.setItem(r, 3, QTableWidgetItem(item.get("package_id") or "-"))

                st_item = QTableWidgetItem("جاهز للتثبيت التلقائي (WinGet)" if is_auto else "يتطلب تنصيباً يدوياً")
                st_item.setForeground(QColor("#3FB950") if is_auto else QColor("#D29922"))
                self.table.setItem(r, 4, st_item)

            self.lbl_summary.setText(
                f"تم التعرف على {data['total_count']} برنامجاً: "
                f"{data['installable_count']} جاهزاً للتثبيت التلقائي، "
                f"و {data['manual_count']} يتطلب تنزيل يدوي."
            )
            self.btn_install.setEnabled(len(self._installable_items) > 0)

        except Exception as e:
            QMessageBox.critical(self, "خطأ في قراءة النسخة الاحتياطية", f"تعذر قراءة محتوى الملف: {e}")

    def _set_all_checks(self, check: bool):
        for r in range(len(self._installable_items)):
            chk = self.table.item(r, 0)
            if chk:
                chk.setCheckState(Qt.Checked if check else Qt.Unchecked)

    def _on_install_selected(self):
        selected_for_install = []
        for r, item in enumerate(self._installable_items):
            chk = self.table.item(r, 0)
            if chk and chk.checkState() == Qt.Checked:
                selected_for_install.append(item)

        if not selected_for_install:
            QMessageBox.information(self, "تثبيت البرامج", "يرجى تحديد برنامج واحد على الأقل عبر مربعات الاختيار [✓].")
            return

        names_str = "\n".join(f"• {it['name']} ({it['package_id']})" for it in selected_for_install)
        reply = QMessageBox.question(
            self,
            f"تأكيد تثبيت {len(selected_for_install)} برنامجاً",
            f"سيتم تنزيل وتثبيت البرامج التالية بالتتابع عبر WinGet:\n\n{names_str}\n\nهل ترغب في بدء التثبيت؟",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            dlg = SequentialQueueDialog(
                title=f"جارٍ استعادة وتثبيت {len(selected_for_install)} برنامجاً",
                items=selected_for_install,
                task_fn=BackupRestoreService.execute_restore_queue,
                parent=self,
            )
            dlg.exec()
            self.refresh_needed.emit()
