# -*- coding: utf-8 -*-
"""
SINAX Restore Subpage (استعادة الملفات والبحث في النسخ).
Allows global search across all backup snapshots, restoring individual files or full
folders with "Keep Both" collision protection, and recovering files deleted from the source.
"""

from pathlib import Path
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.models import FileVersion
from app.services.backup_sync.restore_service import RestoreService
from app.ui.icons import get_icon


class RestoreSubpage(QWidget):
    """Cockpit for file search, historical recovery, and restore operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self.restore_service = RestoreService(self.db)
        self._current_results = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("restore", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("مركز استعادة الملفات والنسخ السابقة")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("ابحث في جميع النسخ الاحتياطية واسترجع المستندات والإصدارات القديمة بأمان تام دون استبدال مفاجئ.")
        d.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        layout.addWidget(header)

        # Search Bar Row
        search_card = QFrame()
        search_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        s_lay = QHBoxLayout(search_card)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("اكتب اسم الملف أو الامتداد للبحث داخل النسخ (مثال: بحث التخرج، report.docx)...")
        self.txt_search.setStyleSheet("background-color: #0D1117; border: 1px solid #30363D; color: #F0F6FC; padding: 8px; border-radius: 6px;")
        self.txt_search.returnPressed.connect(self._do_search)
        s_lay.addWidget(self.txt_search, 1)

        btn_search = QPushButton("بحث في النسخ")
        btn_search.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        btn_search.clicked.connect(self._do_search)
        s_lay.addWidget(btn_search)

        btn_deleted = QPushButton("عرض الملفات المحذوفة من الأصل")
        btn_deleted.setStyleSheet("background-color: #21262D; color: #FBBF24; border: 1px solid #30363D; padding: 8px 14px; border-radius: 6px;")
        btn_deleted.clicked.connect(self._load_deleted_from_source)
        s_lay.addWidget(btn_deleted)

        layout.addWidget(search_card)

        # Table of results
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["اسم الملف", "المسار النسبي", "الحجم", "تاريخ النسخة", "الخطة"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
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

        # Bottom Restore Controls
        bottom_card = QFrame()
        bottom_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        b_lay = QHBoxLayout(bottom_card)

        b_lay.addWidget(QLabel("وجهة الاستعادة:"))
        self.combo_dest = QComboBox()
        self.combo_dest.addItems(["سطح المكتب (Desktop)", "مجلد مخصص...", "المكان الأصلي للملف"])
        self.combo_dest.setStyleSheet("background-color: #0D1117; color: white; padding: 6px; border-radius: 6px;")
        b_lay.addWidget(self.combo_dest)

        b_lay.addStretch(1)

        btn_restore = QPushButton("استعادة الملف المحدد")
        btn_restore.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 24px; border-radius: 6px;")
        btn_restore.clicked.connect(self._restore_selected_file)
        b_lay.addWidget(btn_restore)

        layout.addWidget(bottom_card)

    def _do_search(self):
        q = self.txt_search.text().strip()
        self._current_results = self.db.search_backup_files(q, limit=100)
        self.table.setRowCount(len(self._current_results))
        for row, item in enumerate(self._current_results):
            name = Path(item["relative_path"]).name
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(item["relative_path"]))
            sz_str = f"{item['size_bytes'] / 1024:.1f} KB" if item['size_bytes'] > 0 else "0 KB"
            self.table.setItem(row, 2, QTableWidgetItem(sz_str))
            t_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["mtime"]))
            self.table.setItem(row, 3, QTableWidgetItem(t_str))
            self.table.setItem(row, 4, QTableWidgetItem(item.get("profile_name", "-")))

    def _load_deleted_from_source(self):
        profiles = self.db.list_profiles()
        if not profiles:
            QMessageBox.information(self, "معلومات", "لا توجد خطط نسخ احتياطي مسجلة.")
            return

        deleted_list = []
        for p in profiles:
            del_files = self.restore_service.get_deleted_files_from_source(p.id)
            for df in del_files:
                deleted_list.append({
                    "relative_path": df.relative_path,
                    "size_bytes": df.size_bytes,
                    "mtime": df.mtime,
                    "stored_path": df.stored_path,
                    "profile_name": p.name,
                    "version_record": df
                })

        self._current_results = deleted_list
        self.table.setRowCount(len(deleted_list))
        for row, item in enumerate(deleted_list):
            name = Path(item["relative_path"]).name
            self.table.setItem(row, 0, QTableWidgetItem(f"⚠ {name}"))
            self.table.setItem(row, 1, QTableWidgetItem(item["relative_path"]))
            sz_str = f"{item['size_bytes'] / 1024:.1f} KB"
            self.table.setItem(row, 2, QTableWidgetItem(sz_str))
            t_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["mtime"]))
            self.table.setItem(row, 3, QTableWidgetItem(t_str))
            self.table.setItem(row, 4, QTableWidgetItem(item["profile_name"]))

        if not deleted_list:
            QMessageBox.information(self, "معلومات", "جميع الملفات الموجودة في النسخ الاحتياطية متوفرة حالياً في مساراتها الأصلية (لا توجد ملفات محذوفة).")

    def _restore_selected_file(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._current_results):
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار ملف من الجدول للاستعادة.")
            return

        item = self._current_results[row]
        # Resolve target folder
        dest_choice = self.combo_dest.currentText()
        if "سطح المكتب" in dest_choice:
            target_folder = str(Path.home() / "Desktop")
        elif "مجلد مخصص" in dest_choice:
            target_folder = QFileDialog.getExistingDirectory(self, "اختر وجهة الاستعادة")
            if not target_folder:
                return
        else:
            target_folder = str(Path.home() / "Desktop" / "SINAX_Restored")

        # Construct version
        ver = item.get("version_record")
        if not ver:
            ver = FileVersion(
                file_id=item.get("file_id", "v1"),
                snapshot_id=item.get("snapshot_id", "s1"),
                relative_path=item["relative_path"],
                size_bytes=item["size_bytes"],
                mtime=item["mtime"],
                stored_path=item["stored_path"]
            )

        ok, res_path = self.restore_service.restore_file_version(ver, target_folder, collision_policy="keep_both")
        if ok:
            QMessageBox.information(self, "نجاح الاستعادة", f"تم استعادة الملف بنجاح إلى:\n{res_path} ✓")
        else:
            QMessageBox.critical(self, "خطأ في الاستعادة", f"تعذر استعادة الملف: {res_path}")
