# -*- coding: utf-8 -*-
"""
SINAX Quick Backup Subpage ("احمِ ملفاتي المهمة").
One-click essential folders backup (Desktop, Documents, Pictures).
Auto-discovers external USB/HDD storage and begins protected copy instantly.
"""

from pathlib import Path
import time
import uuid

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from app.services.backup_sync.backup_coordinator import BackupCoordinator
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.device_identity_service import DeviceIdentityService
from app.services.backup_sync.known_folders_service import KnownFoldersService
from app.services.backup_sync.models import (
    BackupProfile,
    BackupType,
    IncrementalMode,
    RetentionPolicy,
    VerificationLevel,
)
from app.ui.icons import get_icon
from app.ui.pages.backup_sync.dialogs.backup_progress_dialog import BackupProgressDialog


class QuickBackupSubpage(QWidget):
    """1-click essential backup cockpit."""

    backup_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header card
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #0F172A);
                border: 1px solid #3B82F6;
                border-radius: 10px;
                padding: 18px;
            }
        """)
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("backup", color_hex="#60A5FA", size=42).pixmap(42, 42))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("حماية الملفات والمستندات الأساسية بنقرة واحدة")
        t.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("يقوم SINAX تلقائياً بتحديد سطح المكتب والمستندات والصور، ويطلب منك فقط تحديد وجهة الحفظ.")
        d.setStyleSheet("font-size: 12px; color: #93C5FD;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        layout.addWidget(header)

        # Detected Folders Card
        card_sources = QFrame()
        card_sources.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        s_lay = QVBoxLayout(card_sources)
        s_title = QLabel("المجلدات المشمولة في الحماية التلقائية:")
        s_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        s_lay.addWidget(s_title)

        important_paths = KnownFoldersService.get_important_folders_paths()
        for p in important_paths:
            row = QLabel(f"✓ {Path(p).name} ({p})")
            row.setStyleSheet("font-size: 12px; color: #34D399; padding: 2px 0;")
            s_lay.addWidget(row)
        layout.addWidget(card_sources)

        # Destination selector
        dest_card = QFrame()
        dest_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        d_lay = QVBoxLayout(dest_card)
        d_title = QLabel("اختر مسار وجهة النسخ (قرص خارجي USB/HDD أو مجلد):")
        d_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
        d_lay.addWidget(d_title)

        d_row = QHBoxLayout()
        self.txt_dest = QLineEdit()
        self.txt_dest.setPlaceholderText("اختر مسار الوجهة...")
        self.txt_dest.setStyleSheet("background-color: #0D1117; border: 1px solid #30363D; color: #F0F6FC; padding: 8px; border-radius: 6px;")

        # Auto-populate if external drive connected
        ext_drives = DeviceIdentityService.list_connected_external_drives()
        if ext_drives:
            self.txt_dest.setText(str(Path(ext_drives[0].drive_letter + "\\") / "SINAX_Backup"))

        d_row.addWidget(self.txt_dest, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 16px; border-radius: 6px;")
        btn_browse.clicked.connect(self._browse_dest)
        d_row.addWidget(btn_browse)
        d_lay.addLayout(d_row)
        layout.addWidget(dest_card)

        # Big Launch Button
        btn_launch = QPushButton("ابدأ الحماية الفورية الآن")
        btn_launch.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 30px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2EA043;
            }
        """)
        btn_launch.clicked.connect(self._run_quick_backup)
        layout.addWidget(btn_launch)

        layout.addStretch(1)

    def _browse_dest(self):
        d = QFileDialog.getExistingDirectory(self, "اختر وجهة النسخ")
        if d:
            self.txt_dest.setText(d)

    def _run_quick_backup(self):
        dest = self.txt_dest.text().strip()
        if not dest:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مسار وجهة النسخ.")
            return

        sources = KnownFoldersService.get_important_folders_paths()
        if not sources:
            QMessageBox.warning(self, "تنبيه", "تعذر اكتشاف المجلدات الأساسية للنظام.")
            return

        profile = BackupProfile(
            id=f"prof_quick_{str(uuid.uuid4())[:6]}",
            name="الحماية السريعة (المستندات وسطح المكتب والصور)",
            sources=sources,
            destination=dest,
            backup_type=BackupType.INCREMENTAL,
            incremental_mode=IncrementalMode.FAST,
            verification_level=VerificationLevel.BALANCED,
            retention=RetentionPolicy(keep_last_n=10)
        )
        self.db.save_profile(profile)

        # Launch progress dialog
        dlg = BackupProgressDialog(parent=self)
        coord = BackupCoordinator(self.db)

        import threading
        from PySide6.QtCore import QTimer

        is_cancelled = [False]
        dlg.cancel_requested.connect(lambda: is_cancelled.insert(0, True))

        def _worker():
            def _prog(stage, done, total, detail):
                QTimer.singleShot(0, lambda: dlg.update_progress(stage, done, total, detail))

            job = coord.run_backup(profile, progress_cb=_prog, cancel_check=lambda: is_cancelled[0])
            def _done():
                dlg.btn_cancel.setText("إغلاق")
                self.backup_finished.emit()
            QTimer.singleShot(0, _done)

        threading.Thread(target=_worker, daemon=True).start()
        dlg.exec()
