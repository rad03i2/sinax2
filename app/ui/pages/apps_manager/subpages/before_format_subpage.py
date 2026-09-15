# -*- coding: utf-8 -*-
"""
SINAX Before Format Subpage (تجهيز البرامج قبل الفورمات)
Wizard exporting installed software list into JSON, native WinGet export, HTML, and CSV reports.
"""

import os
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.backup_restore_service import BackupRestoreService
from app.ui.icons import get_icon


class BeforeFormatSubpage(QWidget):
    """Wizard for exporting software inventory before formatting the PC."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._all_apps: List[InstalledApp] = []
        self._exported_files: Dict[str, str] = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(16)

        # 1. Hero Wizard Card
        hero = QFrame()
        hero.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1F242C, stop:1 #161B22);
                border: 1px solid #30363D; border-radius: 12px; padding: 18px;
            }
        """)
        h_layout = QVBoxLayout(hero)
        h_layout.setSpacing(10)

        t_lbl = QLabel("تجهيز البرامج قبل الفورمات (Before Format Wizard)")
        t_lbl.setStyleSheet("color: #58A6FF; font-size: 18px; font-weight: bold;")
        h_layout.addWidget(t_lbl)

        d_lbl = QLabel(
            "تتيح لك هذه الأداة تصدير قائمة بكافة البرامج المثبتة على جهازك ومصادر تنصيبها، "
            "بحيث تستطيع استعادتها وتثبيتها بنقرة واحدة بعد إعادة تثبيت نظام ويندوز!"
        )
        d_lbl.setStyleSheet("color: #C9D1D9; font-size: 13px; line-height: 1.5;")
        d_lbl.setWordWrap(True)
        h_layout.addWidget(d_lbl)

        # Disclaimer alert box
        disc_frame = QFrame()
        disc_frame.setStyleSheet("background: #1C2128; border-right: 4px solid #F0883E; border-radius: 6px; padding: 10px;")
        disc_layout = QHBoxLayout(disc_frame)
        lbl_warn = QLabel("⚠️ توضيح تقني: تحفظ هذه الميزة قائمة البرامج ومعرفات تثبيتها الرسمية (مثل WinGet ومواقع المطورين) وليست نسخة احتياطية من ملفات وإعدادات البرامج الداخلية.")
        lbl_warn.setStyleSheet("color: #F0883E; font-size: 12px; font-weight: bold;")
        lbl_warn.setWordWrap(True)
        disc_layout.addWidget(lbl_warn)
        h_layout.addWidget(disc_frame)

        vbox.addWidget(hero)

        # 2. Stats & Destination Frame
        step_frame = QFrame()
        step_frame.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        sf_layout = QVBoxLayout(step_frame)
        sf_layout.setSpacing(12)

        lbl_step_title = QLabel("ملخص حزمة البرامج الجاهزة للتصدير")
        lbl_step_title.setStyleSheet("color: #F0F6FC; font-size: 15px; font-weight: bold;")
        sf_layout.addWidget(lbl_step_title)

        self.lbl_summary_text = QLabel("جاري حصر البرامج...")
        self.lbl_summary_text.setStyleSheet("color: #8B949E; font-size: 13px;")
        sf_layout.addWidget(self.lbl_summary_text)

        # Export folder selection
        f_row = QHBoxLayout()
        self.lbl_dest_path = QLabel(os.path.join(os.path.expanduser("~"), "Desktop"))
        self.lbl_dest_path.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px 12px; font-size: 12px;")
        f_row.addWidget(self.lbl_dest_path, 1)

        btn_browse = QPushButton("تغيير المجلد (فلاشة / قرص آخر)")
        btn_browse.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px 14px; font-weight: bold;")
        btn_browse.clicked.connect(self._on_browse_dest)
        f_row.addWidget(btn_browse)
        sf_layout.addLayout(f_row)

        # Main Export Button
        self.btn_export = QPushButton("حفظ حزمة البرامج قبل الفورمات الآن")
        self.btn_export.setIcon(get_icon("backup", color="#F0F6FC"))
        self.btn_export.setStyleSheet("""
            QPushButton {
                background: #238636; color: white; border: none; border-radius: 8px;
                padding: 12px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #2EA043; }
        """)
        self.btn_export.clicked.connect(self._on_export)
        sf_layout.addWidget(self.btn_export, 0, Qt.AlignCenter)

        vbox.addWidget(step_frame)

        # 3. Exported Files Display Card
        self.results_frame = QFrame()
        self.results_frame.setVisible(False)
        self.results_frame.setStyleSheet("background: #161B22; border: 1px solid #3FB950; border-radius: 10px; padding: 16px;")
        rf_layout = QVBoxLayout(self.results_frame)
        rf_layout.setSpacing(10)

        lbl_res_title = QLabel("✅ تم حفظ حزمة برامجك بنجاح!")
        lbl_res_title.setStyleSheet("color: #3FB950; font-size: 15px; font-weight: bold;")
        rf_layout.addWidget(lbl_res_title)

        self.res_content_layout = QVBoxLayout()
        rf_layout.addLayout(self.res_content_layout)

        btn_open_folder = QPushButton("فتح مجلد الحفظ")
        btn_open_folder.setStyleSheet("background: #1F6FEB; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        btn_open_folder.clicked.connect(self._open_destination_folder)
        rf_layout.addWidget(btn_open_folder, 0, Qt.AlignLeft)

        vbox.addWidget(self.results_frame)
        vbox.addStretch(1)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def set_apps(self, apps: List[InstalledApp]):
        self._all_apps = apps
        winget_count = sum(1 for a in apps if a.package_id and not a.package_id.startswith("ARP\\"))
        manual_count = len(apps) - winget_count

        self.lbl_summary_text.setText(
            f"• إجمالي البرامج المكتشفة: {len(apps)} برنامجاً\n"
            f"• برامج تدعم التثبيت التلقائي عبر WinGet: {winget_count} برنامجاً\n"
            f"• برامج تتطلب روابط تحميل وتثبيت يدوي: {manual_count} برنامجاً\n\n"
            f"سيتم إنشاء 4 ملفات: ملف الاستعادة الذكي (JSON)، ملف WinGet الرسمي، تقرير HTML للطباعة، وجدول إكسل (CSV)."
        )

    def _on_browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد الحفظ (يوصى باختيار فلاشة USB أو قرص آخر غير C:)")
        if folder:
            self.lbl_dest_path.setText(folder)

    def _on_export(self):
        dest_dir = self.lbl_dest_path.text().strip()
        if not dest_dir or not os.path.exists(dest_dir):
            QMessageBox.warning(self, "خطأ", "مجلد الحفظ غير موجود.")
            return

        try:
            self._exported_files = BackupRestoreService.export_backup_bundle(self._all_apps, dest_dir)
            self._display_exported_files()
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", f"حدث خطأ أثناء حفظ الملفات: {e}")

    def _display_exported_files(self):
        while self.res_content_layout.count() > 0:
            item = self.res_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        file_descs = {
            "json": "ملف استعادة SINAX الذكي (يستخدم لإعادة التثبيت التلقائي بعد الفورمات)",
            "winget": "ملف تصدير WinGet الرسمي (winget import)",
            "html": "تقرير تفاعلي مستقل يمكنك فتحه في المتصفح أو طباعته",
            "csv": "جدول بيانات إكسل CSV",
        }

        for key, path in self._exported_files.items():
            row = QHBoxLayout()
            lbl_f = QLabel(f"• {os.path.basename(path)}: {file_descs.get(key, '')}")
            lbl_f.setStyleSheet("color: #C9D1D9; font-size: 12px;")
            row.addWidget(lbl_f, 1)

            btn_open = QPushButton("عرض")
            btn_open.setStyleSheet("background: #21262D; color: #58A6FF; border: 1px solid #30363D; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            btn_open.clicked.connect(lambda _, p=path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            row.addWidget(btn_open)

            self.res_content_layout.addLayout(row)

        self.results_frame.setVisible(True)

    def _open_destination_folder(self):
        dest_dir = self.lbl_dest_path.text().strip()
        if os.path.exists(dest_dir):
            os.startfile(dest_dir)
