# -*- coding: utf-8 -*-
"""
SINAX Conflict Resolution Dialog.
Displays side-by-side file details and comparison for conflicting files,
prompting the user to select the appropriate resolution.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from app.services.backup_sync.conflict_service import ConflictService
from app.services.backup_sync.models import ConflictResolution
from app.ui.icons import get_icon


class ConflictResolutionDialog(QDialog):
    """Interactive conflict resolution modal."""

    def __init__(self, path_a: str, path_b: str, parent=None):
        super().__init__(parent)
        self.path_a = path_a
        self.path_b = path_b
        self.selected_resolution: ConflictResolution = ConflictResolution.KEEP_BOTH
        self.setWindowTitle("حل تعارض الملفات (Sync Conflict)")
        self.resize(700, 420)
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

        info = ConflictService.get_conflict_diff_summary(self.path_a, self.path_b)

        # Header
        h_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("warning", color_hex="#FBBF24", size=32).pixmap(32, 32))
        h_row.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        t = QLabel("تم اكتشاف تعارض في تعديل الملف على كلا الطرفين")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        sub = QLabel("تم تعديل الملف في كلا الموقعين بشكل مستقل. يرجى اختيار الإجراء المطلوب:")
        sub.setStyleSheet("font-size: 12px; color: #8B949E;")
        txt_col.addWidget(t)
        txt_col.addWidget(sub)
        h_row.addLayout(txt_col)
        h_row.addStretch(1)
        layout.addLayout(h_row)

        # Side-by-side comparison cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        # Card A
        card_a = QFrame()
        card_a.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        lay_a = QVBoxLayout(card_a)
        lay_a.addWidget(QLabel("الطرف الأول (A)"))
        lay_a.addWidget(QLabel(f"المسار: {self.path_a}"))
        lay_a.addWidget(QLabel(f"الحجم: {info['size_a'] / 1024:.1f} KB"))
        cards_row.addWidget(card_a)

        # Card B
        card_b = QFrame()
        card_b.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        lay_b = QVBoxLayout(card_b)
        lay_b.addWidget(QLabel("الطرف الثاني (B)"))
        lay_b.addWidget(QLabel(f"المسار: {self.path_b}"))
        lay_b.addWidget(QLabel(f"الحجم: {info['size_b'] / 1024:.1f} KB"))
        cards_row.addWidget(card_b)

        layout.addLayout(cards_row)

        # Text Diff Preview if applicable
        if info.get("is_text") and info.get("text_diff_sample"):
            diff_box = QTextEdit()
            diff_box.setReadOnly(True)
            diff_box.setFixedHeight(120)
            diff_box.setText(info["text_diff_sample"])
            diff_box.setStyleSheet("background-color: #030712; color: #38BDF8; font-family: Consolas; font-size: 11px;")
            layout.addWidget(diff_box)

        # Resolution Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_both = QPushButton("الاحتفاظ بالاثنين معاً (موصى به)")
        btn_both.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 14px; border-radius: 6px;")
        btn_both.clicked.connect(lambda: self._set_and_accept(ConflictResolution.KEEP_BOTH))
        btn_row.addWidget(btn_both)

        btn_a = QPushButton("اعتماد نسخة (A)")
        btn_a.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 14px; border-radius: 6px;")
        btn_a.clicked.connect(lambda: self._set_and_accept(ConflictResolution.KEEP_A))
        btn_row.addWidget(btn_a)

        btn_b = QPushButton("اعتماد نسخة (B)")
        btn_b.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 14px; border-radius: 6px;")
        btn_b.clicked.connect(lambda: self._set_and_accept(ConflictResolution.KEEP_B))
        btn_row.addWidget(btn_b)

        btn_skip = QPushButton("تخطي")
        btn_skip.setStyleSheet("background-color: #21262D; color: #8B949E; padding: 8px 14px; border-radius: 6px;")
        btn_skip.clicked.connect(lambda: self._set_and_accept(ConflictResolution.SKIP))
        btn_row.addWidget(btn_skip)

        layout.addLayout(btn_row)

    def _set_and_accept(self, res: ConflictResolution):
        self.selected_resolution = res
        self.accept()
