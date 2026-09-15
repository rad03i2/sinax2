# -*- coding: utf-8 -*-
"""
SINAX Backup Progress Dialog.
Non-blocking modal displaying the active stage (Preflight, Scanning, Copying, Verifying),
current file name, progress bar, transferred bytes, and cancel control.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)
from app.ui.icons import get_icon


class BackupProgressDialog(QDialog):
    """Progress dialog for active backup and restore jobs."""

    cancel_requested = Signal()

    def __init__(self, title: str = "جاري تنفيذ النسخ الاحتياطي...", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(560, 240)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0D1117;
                color: #C9D1D9;
            }
        """)
        self._init_ui(title)

    def _init_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header with icon
        h_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("backup", color_hex="#38BDF8", size=32).pixmap(32, 32))
        h_row.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        self.lbl_stage = QLabel("جاري التحضير...")
        self.lbl_stage.setStyleSheet("font-size: 12px; color: #38BDF8;")
        txt_col.addWidget(self.lbl_title)
        txt_col.addWidget(self.lbl_stage)
        h_row.addLayout(txt_col)
        h_row.addStretch(1)
        layout.addLayout(h_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 9px;
                text-align: center;
                color: #F0F6FC;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #238636;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Current file / detail
        self.lbl_detail = QLabel("جاري فحص الملفات...")
        self.lbl_detail.setStyleSheet("font-size: 12px; color: #8B949E;")
        layout.addWidget(self.lbl_detail)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_cancel = QPushButton("إلغاء العملية")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #F85149;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B62324;
                color: white;
            }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

    def update_progress(self, stage: str, done: int, total: int, detail: str):
        stage_names = {
            "preflight": "فحص سلامة القرص والمساحة",
            "scanning": "مسح وفحص المجلدات المصدرية",
            "copying": "نسخ الملفات والمستندات",
            "verifying": "التحقق وتوليد ملف البيان (Manifest)",
            "completed": "اكتملت العملية بنجاح ✓"
        }
        self.lbl_stage.setText(stage_names.get(stage, stage))
        self.lbl_detail.setText(detail)

        if total > 0:
            pct = int((done / total) * 100)
            self.progress_bar.setValue(min(100, pct))
        else:
            self.progress_bar.setValue(0)

        if stage == "completed":
            self.btn_cancel.setText("إغلاق")
            self.btn_cancel.setStyleSheet("background-color: #238636; color: white; border-radius: 6px; padding: 6px 16px;")

    def _on_cancel(self):
        if self.btn_cancel.text() == "إغلاق":
            self.accept()
        else:
            self.lbl_stage.setText("جاري الإلغاء بأمان...")
            self.cancel_requested.emit()
