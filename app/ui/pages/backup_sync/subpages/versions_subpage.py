# -*- coding: utf-8 -*-
"""
SINAX Versions & Timeline Subpage (سجل الإصدارات والخط الزمني).
Displays chronological file revision history, snapshot timeline points,
and provides one-click restoration to previous dates with file diffing.
"""

from pathlib import Path
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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
from app.services.backup_sync.models import FileVersion
from app.services.backup_sync.restore_service import RestoreService
from app.ui.icons import get_icon


class VersionsSubpage(QWidget):
    """Cockpit for browsing file versions and snapshot points."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self.restore_service = RestoreService(self.db)
        self._current_versions = []
        self._init_ui()
        self.load_profiles()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("clock", color_hex="#A78BFA", size=36).pixmap(36, 36))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("سجل الإصدارات والخط الزمني (Version History)")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("استعراض نقاط الاستعادة السابقة واسترجاع أي ملف كما كان في تاريخ أو ساعة معينة.")
        d.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        layout.addWidget(header)

        # Profile selector row
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("خطة النسخ الاحتياطي:"))
        self.combo_profile = QComboBox()
        self.combo_profile.setStyleSheet("background-color: #161B22; color: #F0F6FC; border: 1px solid #30363D; padding: 6px; border-radius: 6px;")
        self.combo_profile.currentIndexChanged.connect(self._on_profile_changed)
        sel_row.addWidget(self.combo_profile, 1)

        btn_refresh = QPushButton("تحديث")
        btn_refresh.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 6px 14px; border-radius: 6px;")
        btn_refresh.clicked.connect(self.load_profiles)
        sel_row.addWidget(btn_refresh)
        layout.addLayout(sel_row)

        # Versions Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["الملف", "المسار النسبي", "الإصدار", "التاريخ والوقت", "الحجم"])
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

        # Action button
        b_row = QHBoxLayout()
        b_row.addStretch(1)

        btn_restore = QPushButton("استعادة هذا الإصدار إلى سطح المكتب")
        btn_restore.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        btn_restore.clicked.connect(self._restore_version)
        b_row.addWidget(btn_restore)

        layout.addLayout(b_row)

    def load_profiles(self):
        profiles = self.db.list_profiles()
        self.combo_profile.clear()
        for p in profiles:
            self.combo_profile.addItem(p.name, p.id)
        self._on_profile_changed()

    def _on_profile_changed(self):
        profile_id = self.combo_profile.currentData()
        if not profile_id:
            self.table.setRowCount(0)
            return

        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM file_versions 
                WHERE profile_id = ?
                ORDER BY mtime DESC LIMIT 200
            """, (profile_id,)).fetchall()

        self._current_versions = [
            FileVersion(
                file_id=r["file_id"], snapshot_id=r["snapshot_id"],
                relative_path=r["relative_path"], size_bytes=r["size_bytes"],
                mtime=r["mtime"], sha256=r["sha256"], version_number=r["version_number"],
                stored_path=r["stored_path"]
            ) for r in rows
        ]

        self.table.setRowCount(len(self._current_versions))
        for row, v in enumerate(self._current_versions):
            self.table.setItem(row, 0, QTableWidgetItem(Path(v.relative_path).name))
            self.table.setItem(row, 1, QTableWidgetItem(v.relative_path))
            self.table.setItem(row, 2, QTableWidgetItem(f"v{v.version_number}"))
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v.mtime))
            self.table.setItem(row, 3, QTableWidgetItem(t_str))
            sz_str = f"{v.size_bytes / 1024:.1f} KB" if v.size_bytes > 0 else "0 KB"
            self.table.setItem(row, 4, QTableWidgetItem(sz_str))

    def _restore_version(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._current_versions):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد إصدار من الجدول للاستعادة.")
            return

        ver = self._current_versions[row]
        target_folder = str(Path.home() / "Desktop")
        ok, res_path = self.restore_service.restore_file_version(ver, target_folder, collision_policy="keep_both")
        if ok:
            QMessageBox.information(self, "نجاح الاستعادة", f"تم استعادة الإصدار المحدد بنجاح إلى:\n{res_path} ✓")
        else:
            QMessageBox.critical(self, "خطأ في الاستعادة", f"تعذر الاستعادة: {res_path}")
