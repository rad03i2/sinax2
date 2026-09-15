# -*- coding: utf-8 -*-
"""
SINAX About Dialog
About window detailing program version, identity, and features.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from app.ui.icons import create_sinax_logo
from app.core.constants import APP_NAME, APP_NAME_AR, APP_VERSION, APP_TAGLINE_AR, APP_COPYRIGHT

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"حول {APP_NAME} - {APP_NAME_AR}")
        self.setFixedSize(480, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 20)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        # Logo
        logo_lbl = QLabel()
        logo_lbl.setPixmap(create_sinax_logo(64).pixmap(64, 64))
        logo_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_lbl)

        # Title
        title = QLabel(f"{APP_NAME}  |  {APP_NAME_AR}")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #60CDFF;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version_lbl = QLabel(f"الإصدار {APP_VERSION} (إصدار الإنتاج الرسمي)")
        version_lbl.setStyleSheet("font-size: 12px; color: #AAAAAA;")
        version_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_lbl)

        tagline = QLabel(APP_TAGLINE_AR)
        tagline.setStyleSheet("font-size: 13px; font-weight: bold; color: #E0E0E0;")
        tagline.setAlignment(Qt.AlignCenter)
        layout.addWidget(tagline)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #383838; max-height: 1px;")
        layout.addWidget(sep)

        # Description
        desc = QLabel(
            "برنامج متكامل وعالي الأداء لإدارة وتنظيم الحاسوب والملفات في بيئة Windows.\n"
            "تم بناؤه وفق أعلى معايير الأمان المتقدم، حيث يوفر معاينة مسبقة كاملة، "
            "وحماية تامة ضد تكرار الأسماء أو الكتابة فوق الملفات، مع سجل تراجع فوري (Undo) لجميع العمليات."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("font-size: 12px; color: #B0B0B0; line-height: 1.6;")
        layout.addWidget(desc)

        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Copyright
        copy_lbl = QLabel(APP_COPYRIGHT)
        copy_lbl.setStyleSheet("font-size: 11px; color: #666666;")
        copy_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(copy_lbl)

        # OK button
        ok_btn = QPushButton("إغلاق")
        ok_btn.setProperty("class", "PrimaryButton")
        ok_btn.setFixedWidth(120)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        
        btn_container = QHBoxLayout()
        btn_container.setAlignment(Qt.AlignCenter)
        btn_container.addWidget(ok_btn)
        layout.addLayout(btn_container)
