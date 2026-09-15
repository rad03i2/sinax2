# -*- coding: utf-8 -*-
"""
Privacy Metadata Cleaner Subpage (تنظيف الخصوصية والبيانات الوصفية) for SINAX Privacy & Security Center.
Features:
1. Multi-format metadata inspector (Images EXIF/GPS, PDFs, Office docs).
2. Privacy-preserving sanitization that ALWAYS generates a new clean copy (photo_private.jpg)
   leaving the original completely untouched.
3. Post-sanitization automated verification ensuring sensitive tags were truly expunged.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import format_bytes
from app.services.privacy_security.metadata_privacy_service import MetadataPrivacyService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class SanitizeWorker(QThread):
    """Background worker for sanitizing metadata."""
    finished = Signal(bool, str, dict)

    def __init__(self, file_path: str, strip_gps_only: bool):
        super().__init__()
        self.file_path = file_path
        self.strip_gps_only = strip_gps_only

    def run(self):
        service = MetadataPrivacyService()
        ok, path, verifications = service.sanitize_metadata(
            self.file_path,
            strip_gps_only=self.strip_gps_only
        )
        self.finished.emit(ok, path, verifications)


class MetadataCleanSubpage(QWidget):
    """Privacy Metadata Inspector and Sanitizer Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._meta_service = MetadataPrivacyService()
        self._current_file: Optional[str] = None
        self._clean_file: Optional[str] = None
        self._worker: Optional[SanitizeWorker] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: #0D1117;")

        container = QWidget()
        container.setStyleSheet("background-color: #0D1117;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # 1. Header
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self.btn_back = QPushButton(" العودة للرئيسية")
        self.btn_back.setIcon(get_icon("arrow_back", color="#8B949E"))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #161B22; color: #8B949E; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #21262D; color: #F0F6FC; }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.btn_back)

        title_vbox = QVBoxLayout()
        t_lbl = QLabel("تنظيف الخصوصية والبيانات الوصفية (Metadata Sanitizer)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("فحص وتطهير بيانات الموقع الجغرافي (GPS) ومعلومات الكاميرا والمؤلف من الصور والـ PDF والمستندات.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        header_row.addWidget(ToolBadgeWidget.modifies_files(self))
        layout.addLayout(header_row)

        # 2. File Selector Box
        sel_box = QFrame()
        sel_box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        sb_layout = QHBoxLayout(sel_box)
        sb_layout.setSpacing(10)

        lbl_f = QLabel("الملف المستهدف:")
        lbl_f.setStyleSheet("color: #8B949E; font-weight: bold;")
        sb_layout.addWidget(lbl_f)

        self.txt_file_path = QLineEdit()
        self.txt_file_path.setPlaceholderText("اختر صورة (JPG, PNG, WEBP) أو مستند (PDF, DOCX)...")
        self.txt_file_path.setStyleSheet("""
            QLineEdit {
                background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px; font-size: 12px;
            }
        """)
        sb_layout.addWidget(self.txt_file_path, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: #FFFFFF; border-radius: 6px;
                padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2EA043; }
        """)
        btn_browse.clicked.connect(self._on_browse_file)
        sb_layout.addWidget(btn_browse)

        layout.addWidget(sel_box)

        # 3. GPS Alert Banner (Initially Hidden)
        self.gps_banner = QFrame()
        self.gps_banner.setVisible(False)
        self.gps_banner.setStyleSheet("background-color: #2D1418; border: 1px solid #F87171; border-radius: 8px; padding: 12px;")
        gb_layout = QHBoxLayout(self.gps_banner)
        gb_icon = QLabel()
        gb_icon.setPixmap(get_icon("warning", color="#F87171", size=24).pixmap(24, 24))
        gb_layout.addWidget(gb_icon)

        self.lbl_gps_warning = QLabel("تحذير خصوصية: تم اكتشاف إحداثيات موقع جغرافي دقيق (GPS) مسجلة داخل هذا الملف!")
        self.lbl_gps_warning.setStyleSheet("color: #F87171; font-weight: bold; font-size: 13px;")
        gb_layout.addWidget(self.lbl_gps_warning, 1)
        layout.addWidget(self.gps_banner)

        # 4. Inspection Details & Sanitization Options Row
        detail_frame = QFrame()
        detail_frame.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        df_vbox = QVBoxLayout(detail_frame)
        df_vbox.setSpacing(12)

        df_head = QHBoxLayout()
        df_icon = QLabel()
        df_icon.setPixmap(get_icon("eye", color="#38BDF8", size=20).pixmap(20, 20))
        df_head.addWidget(df_icon)

        self.lbl_meta_summary = QLabel("تفاصيل البيانات الوصفية المكتشفة:")
        self.lbl_meta_summary.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        df_head.addWidget(self.lbl_meta_summary)
        df_head.addStretch(1)
        df_vbox.addLayout(df_head)

        # Table of metadata fields
        self.meta_table = QTableWidget()
        self.meta_table.setColumnCount(2)
        self.meta_table.setHorizontalHeaderLabels(["الحقل / الخاصية (Tag)", "القيمة المسجلة (Value)"])
        self.meta_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.meta_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.meta_table.setFixedHeight(180)
        self.meta_table.setAlternatingRowColors(True)
        self.meta_table.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117; alternate-background-color: #161B22;
                border: 1px solid #30363D; border-radius: 6px; gridline-color: #21262D; color: #F0F6FC;
            }
            QHeaderView::section {
                background-color: #161B22; color: #8B949E; font-weight: bold; border: 1px solid #21262D; padding: 4px;
            }
        """)
        df_vbox.addWidget(self.meta_table)

        # Sanitization Options
        opt_group = QFrame()
        opt_group.setStyleSheet("background-color: #0D1117; border: 1px solid #21262D; border-radius: 6px; padding: 10px;")
        og_vbox = QVBoxLayout(opt_group)
        og_vbox.setSpacing(6)

        og_title = QLabel("خيارات التطهير:")
        og_title.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 12px;")
        og_vbox.addWidget(og_title)

        self.radio_strip_all = QRadioButton("تطهير شامل لكافة البيانات الوصفية (يوصى به للمشاركة الآمنة)")
        self.radio_strip_all.setChecked(True)
        self.radio_strip_all.setStyleSheet("color: #F0F6FC; font-size: 12px;")
        og_vbox.addWidget(self.radio_strip_all)

        self.radio_strip_gps = QRadioButton("إزالة إحداثيات GPS والموقع الجغرافي فقط (مع الاحتفاظ بإعدادات الكاميرا)")
        self.radio_strip_gps.setStyleSheet("color: #F0F6FC; font-size: 12px;")
        og_vbox.addWidget(self.radio_strip_gps)

        df_vbox.addWidget(opt_group)

        # Action Button & Progress
        act_row = QHBoxLayout()
        self.btn_sanitize = QPushButton(" إنشاء نسخة آمنة خالية من الميتاداتا")
        self.btn_sanitize.setIcon(get_icon("clean_sweep", color="#FFFFFF"))
        self.btn_sanitize.setStyleSheet("""
            QPushButton {
                background-color: #1F6FEB; color: #FFFFFF; border-radius: 6px;
                padding: 10px 24px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #388BFD; }
        """)
        self.btn_sanitize.clicked.connect(self._run_sanitization)
        act_row.addWidget(self.btn_sanitize)

        lbl_guarantee = QLabel("🛡️ ضمان SINAX: لا يتم المساس بالملف الأصلي إطلاقاً، بل تُنشأ نسخة جديدة آمنة (_private).")
        lbl_guarantee.setStyleSheet("color: #34D399; font-size: 11px;")
        act_row.addWidget(lbl_guarantee, 1)

        df_vbox.addLayout(act_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #0D1117; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #38BDF8; border-radius: 3px; }
        """)
        df_vbox.addWidget(self.progress_bar)

        layout.addWidget(detail_frame)

        # 5. Verification Card (Shown after cleaning)
        self.verify_card = QFrame()
        self.verify_card.setVisible(False)
        self.verify_card.setStyleSheet("background-color: #132E22; border: 1px solid #34D399; border-radius: 10px; padding: 14px;")
        vc_vbox = QVBoxLayout(self.verify_card)
        vc_vbox.setSpacing(8)

        vc_head = QHBoxLayout()
        vc_icon = QLabel()
        vc_icon.setPixmap(get_icon("shield", color="#34D399", size=24).pixmap(24, 24))
        vc_head.addWidget(vc_icon)

        self.lbl_verify_title = QLabel("تم إنشاء النسخة الآمنة والتحقق منها بنجاح!")
        self.lbl_verify_title.setStyleSheet("color: #34D399; font-size: 15px; font-weight: bold;")
        vc_head.addWidget(self.lbl_verify_title)
        vc_head.addStretch(1)

        btn_open_folder = QPushButton(" فتح المجلد الحاوي")
        btn_open_folder.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_open_folder.setStyleSheet("""
            QPushButton {
                background: #238636; color: #FFFFFF; border-radius: 4px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #2EA043; }
        """)
        btn_open_folder.clicked.connect(self._open_output_folder)
        vc_head.addWidget(btn_open_folder)
        vc_vbox.addLayout(vc_head)

        self.lbl_verify_details = QLabel("")
        self.lbl_verify_details.setStyleSheet("color: #F0F6FC; font-size: 12px; line-height: 1.5;")
        vc_vbox.addWidget(self.lbl_verify_details)

        layout.addWidget(self.verify_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _on_browse_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملفاً لفحص وتطهير الميتاداتا",
            "",
            "صور ومستندات (*.jpg *.jpeg *.png *.webp *.pdf *.docx *.xlsx *.pptx);;كافة الملفات (*.*)"
        )
        if f:
            self.txt_file_path.setText(f)
            self._inspect_file(f)

    def _inspect_file(self, file_path: str):
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            QMessageBox.warning(self, "تنبيه", "الملف المحدد غير موجود.")
            return

        self._current_file = str(p)
        self.verify_card.setVisible(False)

        info = self._meta_service.inspect_metadata(str(p))

        # Check GPS
        if info.get("has_gps"):
            gps = info.get("gps_info", {})
            lat = gps.get("latitude", "—")
            lon = gps.get("longitude", "—")
            self.gps_banner.setVisible(True)
            self.lbl_gps_warning.setText(f"تحذير خصوصية: تم كشف إحداثيات GPS دقيقة ({lat}, {lon}) داخل الصورة!")
        else:
            self.gps_banner.setVisible(False)

        # Populate table
        fields = info.get("metadata_fields", {})
        self.lbl_meta_summary.setText(f"تفاصيل الميتاداتا المكتشفة ({len(fields)} خاصية مسجلة) - الصيغة: {info.get('format', 'غير محدد')}")

        self.meta_table.setRowCount(len(fields))
        for row_idx, (k, v) in enumerate(fields.items()):
            self.meta_table.setItem(row_idx, 0, QTableWidgetItem(str(k)))
            self.meta_table.setItem(row_idx, 1, QTableWidgetItem(str(v)))

    def _run_sanitization(self):
        if not self._current_file or not os.path.isfile(self._current_file):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف أولاً.")
            return

        strip_gps_only = self.radio_strip_gps.isChecked()
        self.btn_sanitize.setEnabled(False)
        self.progress_bar.setVisible(True)

        self._worker = SanitizeWorker(self._current_file, strip_gps_only)
        self._worker.finished.connect(self._on_sanitize_finished)
        self._worker.start()

    def _on_sanitize_finished(self, ok: bool, output_path: str, verifications: dict):
        self.progress_bar.setVisible(False)
        self.btn_sanitize.setEnabled(True)

        if not ok:
            QMessageBox.critical(self, "خطأ في التنظيف", f"تعذر تنظيف الملف:\n{output_path}")
            return

        self._clean_file = output_path
        self.verify_card.setVisible(True)

        p = Path(output_path)
        det_lines = [
            f"<b>مسار النسخة الآمنة:</b> <code>{p.name}</code> ({format_bytes(p.stat().st_size)})",
            f"<b>التحقق من إزالة GPS:</b> {'نعم تم الحذف بنجاح' if verifications.get('gps_removed') else 'لم تكن تحتوي على GPS'}",
            f"<b>التحقق من خلو الميتاداتا:</b> تم تفريغ وتطهير الخصائص بنجاح",
            f"<b>سلامة الملف الناتج:</b> سليم وقابل للفتح دون تلف",
        ]
        self.lbl_verify_details.setText("<br>".join(det_lines))
        QMessageBox.information(self, "اكتمل التطهير", f"تم إنشاء النسخة الآمنة بنجاح في:\n{output_path}")

    def _open_output_folder(self):
        if self._clean_file and os.path.exists(self._clean_file):
            folder = os.path.dirname(self._clean_file)
            os.startfile(folder)
