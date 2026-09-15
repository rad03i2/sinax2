# -*- coding: utf-8 -*-
"""
SINAX Folder Synchronization Subpage (مزامنة المجلدات).
Supports One-Way, Two-Way, and Mirror sync modes.
Enforces Dry Run Preview before applying deletions and routes deleted files
safely into .sinax_sync_recycle/ with undo capabilities.
"""

from pathlib import Path
import time
import uuid

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
from app.services.backup_sync.models import ConflictResolution, SyncMode, SyncPair
from app.services.backup_sync.sync_engine import SyncEngine
from app.ui.icons import get_icon
from app.ui.pages.backup_sync.dialogs.dry_run_preview_dialog import DryRunPreviewDialog


class SyncSubpage(QWidget):
    """Cockpit for configuring and executing safe folder synchronization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self.engine = SyncEngine(self.db)
        self._init_ui()
        self.load_pairs()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header card
        header = QFrame()
        header.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        h_lay = QHBoxLayout(header)
        h_icon = QLabel()
        h_icon.setPixmap(get_icon("sync", color_hex="#38BDF8", size=36).pixmap(36, 36))
        h_lay.addWidget(h_icon)

        txt_col = QVBoxLayout()
        t = QLabel("مزامنة المجلدات الآمنة (Folder Sync)")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        d = QLabel("مزامنة اتجاهين أو مرآة مع سلة تراجع آمنة (.sinax_sync_recycle) ومعاينة إلزامية للتغييرات قبل التنفيذ.")
        d.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(d)
        h_lay.addLayout(txt_col)
        h_lay.addStretch(1)
        layout.addWidget(header)

        # Setup New Sync Pair Box
        box_pair = QFrame()
        box_pair.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        b_lay = QVBoxLayout(box_pair)
        b_lay.setSpacing(10)

        t_lbl = QLabel("إنشاء زوج مزامنة جديد:")
        t_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
        b_lay.addWidget(t_lbl)

        # Side A
        row_a = QHBoxLayout()
        self.txt_a = QLineEdit()
        self.txt_a.setPlaceholderText("المجلد الأول (الطرف A)...")
        self.txt_a.setStyleSheet("background-color: #0D1117; border: 1px solid #30363D; color: #F0F6FC; padding: 6px; border-radius: 6px;")
        row_a.addWidget(self.txt_a, 1)
        btn_a = QPushButton("استعراض A...")
        btn_a.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 6px 14px; border-radius: 6px;")
        btn_a.clicked.connect(lambda: self._browse_dir(self.txt_a))
        row_a.addWidget(btn_a)
        b_lay.addLayout(row_a)

        # Side B
        row_b = QHBoxLayout()
        self.txt_b = QLineEdit()
        self.txt_b.setPlaceholderText("المجلد الثاني (الطرف B)...")
        self.txt_b.setStyleSheet("background-color: #0D1117; border: 1px solid #30363D; color: #F0F6FC; padding: 6px; border-radius: 6px;")
        row_b.addWidget(self.txt_b, 1)
        btn_b = QPushButton("استعراض B...")
        btn_b.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 6px 14px; border-radius: 6px;")
        btn_b.clicked.connect(lambda: self._browse_dir(self.txt_b))
        row_b.addWidget(btn_b)
        b_lay.addLayout(row_b)

        # Mode Selector & Preview Button
        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(QLabel("نمط المزامنة:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["مزامنة باتجاهين (Two-Way A <-> B)", "نسخ باتجاه واحد (One-Way A -> B)", "مطابقة تامة مرآة (Mirror - مع حذف الزائد في B)"])
        self.combo_mode.setStyleSheet("background-color: #0D1117; border: 1px solid #30363D; color: #F0F6FC; padding: 6px; border-radius: 6px;")
        ctrl_row.addWidget(self.combo_mode, 1)

        btn_preview = QPushButton("معاينة المزامنة (Dry Run) وبدء التنفيذ")
        btn_preview.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        btn_preview.clicked.connect(self._run_sync_preview)
        ctrl_row.addWidget(btn_preview)
        b_lay.addLayout(ctrl_row)

        layout.addWidget(box_pair)

        # Saved Sync Pairs Table
        t_hist = QLabel("أزواج المزامنة المسجلة:")
        t_hist.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
        layout.addWidget(t_hist)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["الاسم", "الطرف A", "الطرف B", "النمط", "آخر مزامنة"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
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

    def _browse_dir(self, line_edit: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "اختر المجلد")
        if d:
            line_edit.setText(d)

    def load_pairs(self):
        pairs = self.db.list_sync_pairs()
        self.table.setRowCount(len(pairs))
        for row, p in enumerate(pairs):
            self.table.setItem(row, 0, QTableWidgetItem(p.name))
            self.table.setItem(row, 1, QTableWidgetItem(p.side_a))
            self.table.setItem(row, 2, QTableWidgetItem(p.side_b))
            self.table.setItem(row, 3, QTableWidgetItem(p.mode.value if hasattr(p.mode, "value") else str(p.mode)))
            t_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(p.last_sync_at)) if p.last_sync_at else "لم تتم بعد"
            self.table.setItem(row, 4, QTableWidgetItem(t_str))

    def _run_sync_preview(self):
        a = self.txt_a.text().strip()
        b = self.txt_b.text().strip()
        if not a or not b or not os.path.isdir(a) or not os.path.isdir(b):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مسارين صحيحين موجودين للمجلدين.")
            return

        mode_str = self.combo_mode.currentText()
        mode = SyncMode.TWO_WAY
        if "باتجاه واحد" in mode_str:
            mode = SyncMode.ONE_WAY
        elif "مرآة" in mode_str:
            mode = SyncMode.MIRROR

        pair = SyncPair(
            id=f"sync_{str(uuid.uuid4())[:8]}",
            name=f"{Path(a).name} ↔ {Path(b).name}",
            side_a=a,
            side_b=b,
            mode=mode,
            conflict_policy=ConflictResolution.KEEP_BOTH
        )
        self.db.save_sync_pair(pair)

        # Generate Dry Run
        dry_run = self.engine.generate_dry_run(pair)
        dlg = DryRunPreviewDialog(dry_run, parent=self)
        if dlg.exec() == DryRunPreviewDialog.Accepted:
            ok, msg = self.engine.execute_sync(pair, dry_run)
            if ok:
                QMessageBox.information(self, "نجاح المزامنة", msg)
            else:
                QMessageBox.critical(self, "خطأ أثناء المزامنة", msg)
            self.load_pairs()
