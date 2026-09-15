# -*- coding: utf-8 -*-
"""
SINAX Status Bar
Bottom status line displaying activity progress, current folder, and system status.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, Signal
from app.ui.icons import get_icon

class StatusBar(QFrame):
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusBarFrame")
        self.setFixedHeight(36)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(12)

        # Status icon & text
        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_icon("check", "#52C41A", 14).pixmap(14, 14))
        layout.addWidget(self.status_icon)

        self.status_label = QLabel("جاهز")
        self.status_label.setStyleSheet("font-size: 12px; color: #CCCCCC;")
        layout.addWidget(self.status_label)

        # Folder label
        self.folder_label = QLabel("")
        self.folder_label.setStyleSheet("font-size: 11px; color: #888888; font-style: italic;")
        layout.addWidget(self.folder_label)

        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Progress bar (hidden when idle)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(180, 14)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Cancel button
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.setIcon(get_icon("cancel", "#FF4D4F", 12))
        self.cancel_btn.setStyleSheet("padding: 2px 8px; font-size: 11px; background-color: #383838;")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        self.cancel_btn.hide()
        layout.addWidget(self.cancel_btn)

        # Details stats label
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-size: 11px; color: #999999;")
        layout.addWidget(self.stats_label)

    def set_status(self, message: str, is_loading: bool = False, is_error: bool = False):
        self.status_label.setText(message)
        if is_error:
            self.status_icon.setPixmap(get_icon("cancel", "#FF4D4F", 14).pixmap(14, 14))
        elif is_loading:
            self.status_icon.setPixmap(get_icon("refresh", "#60CDFF", 14).pixmap(14, 14))
        else:
            self.status_icon.setPixmap(get_icon("check", "#52C41A", 14).pixmap(14, 14))

    def set_folder(self, folder_str: str):
        if folder_str:
            self.folder_label.setText(f"المجلد: {folder_str}")
        else:
            self.folder_label.setText("")

    def set_stats(self, stats_str: str):
        self.stats_label.setText(stats_str)

    def show_progress(self, current: int, total: int, show_cancel: bool = True):
        self.progress_bar.show()
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"%p% ({current}/{total})")
        else:
            self.progress_bar.setRange(0, 0)
        
        if show_cancel:
            self.cancel_btn.show()

    def hide_progress(self):
        self.progress_bar.hide()
        self.cancel_btn.hide()
