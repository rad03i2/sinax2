# -*- coding: utf-8 -*-
"""
SINAX Dependency Helper Dialog
Guides users to configure or install required external tools (FFmpeg, LibreOffice, 7-Zip, etc.)
using winget commands, official downloads, or custom local executable paths.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QFrame, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from app.services.conversion.dependency_manager import dependency_manager, TOOL_METADATA
from app.ui.icons import get_icon


class DependencyDialog(QDialog):
    def __init__(self, tool_id: str, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.tool_info = dependency_manager.get_tool_info(tool_id)
        self.setWindowTitle(f"إعداد المكوّن: {self.tool_info['name_ar']}")
        self.setMinimumWidth(540)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Title
        title_lbl = QLabel(f"المكوّن المطلوب: {self.tool_info['name_ar']}")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #60CDFF;")
        layout.addWidget(title_lbl)

        # Description
        desc_lbl = QLabel(self.tool_info['description_ar'])
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 12px; color: #CCCCCC; line-height: 1.4;")
        layout.addWidget(desc_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333333; max-height: 1px;")
        layout.addWidget(sep)

        # Option 1: Winget command
        if self.tool_info.get("winget"):
            w_title = QLabel("1. التثبيت السريع عبر موجه الأوامر (Windows Package Manager):")
            w_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
            layout.addWidget(w_title)

            w_row = QHBoxLayout()
            w_edit = QLineEdit(self.tool_info["winget"])
            w_edit.setReadOnly(True)
            w_edit.setStyleSheet("background: #1A1A1A; border: 1px solid #333; padding: 6px; font-family: Consolas; color: #52C41A;")
            w_row.addWidget(w_edit, 1)

            btn_copy = QPushButton("نسخ الأمر")
            btn_copy.setCursor(Qt.PointingHandCursor)
            btn_copy.clicked.connect(lambda: self._copy_text(self.tool_info["winget"]))
            w_row.addWidget(btn_copy)
            layout.addLayout(w_row)

        # Option 2: Download Website
        if self.tool_info.get("url"):
            w2_title = QLabel("2. التنزيل اليدوي من الموقع الرسمي:")
            w2_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
            layout.addWidget(w2_title)

            btn_url = QPushButton("  فتح صفحة التنزيل الرسمية في المتصفح")
            btn_url.setIcon(get_icon("link", "#FFFFFF", 14))
            btn_url.setCursor(Qt.PointingHandCursor)
            btn_url.setStyleSheet("text-align: right; padding: 6px 12px;")
            btn_url.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.tool_info["url"])))
            layout.addWidget(btn_url)

        # Option 3: Custom path browse
        p_title = QLabel("3. إذا كان البرنامج مثبتاً بالفعل، حدد مسار الملف التنفيذي (.exe):")
        p_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(p_title)

        p_row = QHBoxLayout()
        self.path_edit = QLineEdit(self.tool_info.get("path") or "")
        self.path_edit.setPlaceholderText("اختر مسار الملف التنفيذي...")
        p_row.addWidget(self.path_edit, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self._on_browse_exe)
        p_row.addWidget(btn_browse)
        layout.addLayout(p_row)

        # Dialog Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        btn_save = QPushButton("حفظ وإعادة الفحص")
        btn_save.setProperty("class", "PrimaryButton")
        btn_save.setMinimumHeight(32)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        btn_close = QPushButton("إغلاق")
        btn_close.setMinimumHeight(32)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _copy_text(self, txt: str):
        QApplication.clipboard().setText(txt)
        QMessageBox.information(self, "تم النسخ", "تم نسخ أمر التثبيت إلى الحافظة. افتح PowerShell أو Terminal والصقه لتثبيته فوراً.")

    def _on_browse_exe(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر الملف التنفيذي", "", "Executable Files (*.exe);;All Files (*.*)")
        if f:
            self.path_edit.setText(f)

    def _on_save(self):
        val = self.path_edit.text().strip()
        if val:
            if dependency_manager.set_custom_path(self.tool_id, val):
                QMessageBox.information(self, "نجاح", "تم حفظ وتفعيل مسار المكوّن بنجاح!")
                self.accept()
                return
            else:
                QMessageBox.warning(self, "خطأ", "المسار المحدد غير موجود أو ليس ملفاً صالحاً.")
                return
        dependency_manager.refresh()
        self.accept()
