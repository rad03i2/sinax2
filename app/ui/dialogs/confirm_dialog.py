# -*- coding: utf-8 -*-
"""
SINAX Operation Confirmation Dialog
Displays operation summary, affected paths, sample preview, and safety warnings.
"""

from typing import List, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from app.ui.icons import get_icon

class ConfirmDialog(QDialog):
    def __init__(
        self,
        op_title: str,
        folder_path: str,
        file_count: int,
        samples: List[Tuple[str, str]],
        warning_msg: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("تأكيد تنفيذ العملية - SINAX")
        self.setMinimumWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._init_ui(op_title, folder_path, file_count, samples, warning_msg)

    def _init_ui(self, op_title, folder_path, file_count, samples, warning_msg):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header with Icon
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(get_icon("play", "#0078D4", 28).pixmap(28, 28))
        header_layout.addWidget(icon_label)

        title_container = QVBoxLayout()
        title_label = QLabel(op_title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        title_container.addWidget(title_label)

        count_label = QLabel(f"عدد الملفات المحددة للعملية: {file_count} ملف")
        count_label.setStyleSheet("font-size: 12px; color: #60CDFF;")
        title_container.addWidget(count_label)

        header_layout.addLayout(title_container)
        header_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(header_layout)

        # Warning Banner (if present)
        if warning_msg:
            warn_frame = QFrame()
            warn_frame.setStyleSheet("background-color: #3F1F1F; border: 1px solid #FF4D4F; border-radius: 6px; padding: 10px;")
            warn_layout = QHBoxLayout(warn_frame)
            warn_layout.setContentsMargins(8, 6, 8, 6)
            
            warn_icon = QLabel()
            warn_icon.setPixmap(get_icon("cancel", "#FF4D4F", 20).pixmap(20, 20))
            warn_layout.addWidget(warn_icon)
            
            warn_txt = QLabel(warning_msg)
            warn_txt.setStyleSheet("color: #FFA39E; font-size: 12px; font-weight: bold;")
            warn_txt.setWordWrap(True)
            warn_layout.addWidget(warn_txt)
            layout.addWidget(warn_frame)

        # Folder Info
        folder_label = QLabel(f"المجلد الهدف: {folder_path}")
        folder_label.setStyleSheet("font-size: 12px; color: #CCCCCC; background: #262626; padding: 8px 12px; border-radius: 4px;")
        folder_label.setWordWrap(True)
        layout.addWidget(folder_label)

        # Sample Preview box
        if samples:
            preview_title = QLabel("عينة من التغييرات المقترحة:")
            preview_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #AAAAAA;")
            layout.addWidget(preview_title)

            sample_box = QTextEdit()
            sample_box.setReadOnly(True)
            sample_box.setFixedHeight(120)
            sample_box.setStyleSheet("background-color: #1A1A1A; border: 1px solid #333333; font-family: monospace; font-size: 12px;")

            lines = []
            for orig, new_n in samples[:8]:
                lines.append(f"{orig}  ➔  {new_n}")
            if len(samples) > 8:
                lines.append(f"... والمزيد ({len(samples) - 8} ملف إضافي)")

            sample_box.setText("\n".join(lines))
            layout.addWidget(sample_box)

        # Safety Assurance Note
        safety_note = QLabel("✓ تم التحقق من الأسماء مسبقاً وتفادي التعارضات. يمكنك التراجع عن هذه العملية في أي وقت.")
        safety_note.setStyleSheet("font-size: 11px; color: #52C41A;")
        layout.addWidget(safety_note)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.cancel_btn = QPushButton("إلغاء الأمر")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton("تنفيذ العملية الآن")
        self.confirm_btn.setProperty("class", "PrimaryButton")
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)
