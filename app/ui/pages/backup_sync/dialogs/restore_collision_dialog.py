# -*- coding: utf-8 -*-
"""
SINAX Restore Collision Dialog.
Prompts the user when a restored file already exists at the destination.
Defaults to "Keep Both" to prevent unintentional overwriting.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from app.ui.icons import get_icon


class RestoreCollisionDialog(QDialog):
    """Safe collision handling modal during restore."""

    def __init__(self, filename: str, destination_path: str, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.destination_path = destination_path
        self.selected_policy = "keep_both"
        self.setWindowTitle("تعارض استعادة الملف (File Already Exists)")
        self.setFixedSize(520, 220)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
            QDialog {
                background-color: #0D1117;
                color: #C9D1D9;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        h_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("warning", color_hex="#38BDF8", size=32).pixmap(32, 32))
        h_row.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        t = QLabel("الملف موجود بالفعل في مسار الاستعادة!")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        sub = QLabel(f"الملف: {self.filename}\nالمسار: {self.destination_path}")
        sub.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(sub)
        h_row.addLayout(txt_col)
        h_row.addStretch(1)
        layout.addLayout(h_row)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_both = QPushButton("الاحتفاظ بالاثنين (موصى به)")
        btn_both.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 14px; border-radius: 6px;")
        btn_both.clicked.connect(lambda: self._select_and_close("keep_both"))
        btn_row.addWidget(btn_both)

        btn_replace = QPushButton("استبدال الملف")
        btn_replace.setStyleSheet("background-color: #21262D; color: #F87171; border: 1px solid #30363D; padding: 8px 14px; border-radius: 6px;")
        btn_replace.clicked.connect(lambda: self._select_and_close("replace"))
        btn_row.addWidget(btn_replace)

        btn_skip = QPushButton("تخطي")
        btn_skip.setStyleSheet("background-color: #21262D; color: #8B949E; padding: 8px 14px; border-radius: 6px;")
        btn_skip.clicked.connect(lambda: self._select_and_close("skip"))
        btn_row.addWidget(btn_skip)

        layout.addLayout(btn_row)

    def _select_and_close(self, policy: str):
        self.selected_policy = policy
        self.accept()
