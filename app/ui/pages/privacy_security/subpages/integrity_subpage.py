# -*- coding: utf-8 -*-
"""
File Integrity Subpage (سلامة الملفات والمانيفست) for SINAX Privacy & Security Center.
Features:
1. Folder Manifest Generator: Builds SHA-256 baselines (SINAX_integrity_manifest.json).
2. Folder Manifest Verifier: Compares current state vs manifest (Unchanged, Modified, Missing, New).
3. Instant Single File Hash Verifier: Compares calculated digest against expected value.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import format_bytes
from app.services.privacy_security.integrity_service import IntegrityDiff, IntegrityService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class ManifestBuilderWorker(QThread):
    """Background worker for hashing entire folder and writing manifest."""
    progress_updated = Signal(float, str)
    finished_building = Signal(bool, str, int)

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        ok, path, count = IntegrityService.create_folder_manifest(
            self.folder_path,
            progress_cb=lambda p, msg: self.progress_updated.emit(p, msg),
            cancel_check=lambda: self._cancelled,
        )
        self.finished_building.emit(ok, path, count)


class ManifestVerifierWorker(QThread):
    """Background worker for verifying directory state against manifest."""
    progress_updated = Signal(float, str)
    finished_verifying = Signal(bool, str, object)

    def __init__(self, folder_path: str, manifest_path: Optional[str] = None):
        super().__init__()
        self.folder_path = folder_path
        self.manifest_path = manifest_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        ok, msg, diff = IntegrityService.verify_folder_manifest(
            self.folder_path,
            manifest_file_path=self.manifest_path,
            progress_cb=lambda p, msg: self.progress_updated.emit(p, msg),
            cancel_check=lambda: self._cancelled,
        )
        self.finished_verifying.emit(ok, msg, diff)


class IntegritySubpage(QWidget):
    """File and Directory Integrity Verification Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_worker: Optional[ManifestBuilderWorker] = None
        self._verify_worker: Optional[ManifestVerifierWorker] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

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
        t_lbl = QLabel("سلامة الملفات والمانيفست (File Integrity & Manifest)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("إنشاء وتدقيق مانيفست البصمات الرقمية (SHA-256) للمجلدات لكشف أي تعديل أو عبث غير مرخص بالملفات.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        main_layout.addLayout(header_row)

        # Tabs
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363D; background-color: #0D1117; border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #161B22; color: #8B949E; padding: 8px 16px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                font-weight: bold; font-size: 13px; margin-left: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0D1117; color: #38BDF8;
                border: 1px solid #30363D; border-bottom: 1px solid #0D1117;
            }
            QTabBar::tab:hover:!selected { background-color: #21262D; color: #F0F6FC; }
        """)

        tab_create = self._build_create_manifest_tab()
        tab_verify = self._build_verify_manifest_tab()
        tab_single = self._build_single_hash_tab()

        self.tabs.addTab(tab_create, "إنشاء مانيفست لمجلد (Create Manifest)")
        self.tabs.addTab(tab_verify, "تدقيق ومطابقة المانيفست (Verify Manifest)")
        self.tabs.addTab(tab_single, "مطابقة هاش لملف منفرد (Single File Match)")

        main_layout.addWidget(self.tabs, 1)

    # -------------------------------------------------------------
    # Tab 1: Create Manifest
    # -------------------------------------------------------------
    def _build_create_manifest_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Folder picker
        box = QFrame()
        box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        b_layout = QVBoxLayout(box)
        b_layout.setSpacing(10)

        b_title = QLabel("اختر المجلد المراد توليد مانيفست البصمات له:")
        b_title.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px;")
        b_layout.addWidget(b_title)

        row = QHBoxLayout()
        self.txt_create_dir = QLineEdit()
        self.txt_create_dir.setPlaceholderText("حدد مسار المجلد...")
        self.txt_create_dir.setStyleSheet("""
            QLineEdit {
                background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px; font-size: 12px;
            }
        """)
        row.addWidget(self.txt_create_dir, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #30363D; }
        """)
        btn_browse.clicked.connect(self._on_browse_create_dir)
        row.addWidget(btn_browse)

        self.btn_build_manifest = QPushButton(" توليد المانيفست الآن")
        self.btn_build_manifest.setIcon(get_icon("hash", color="#FFFFFF"))
        self.btn_build_manifest.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: #FFFFFF; border-radius: 6px;
                padding: 8px 20px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #2EA043; }
        """)
        self.btn_build_manifest.clicked.connect(self._start_build_manifest)
        row.addWidget(self.btn_build_manifest)
        b_layout.addLayout(row)

        layout.addWidget(box)

        # Progress bar
        self.build_progress = QProgressBar()
        self.build_progress.setRange(0, 100)
        self.build_progress.setValue(0)
        self.build_progress.setFixedHeight(6)
        self.build_progress.setVisible(False)
        self.build_progress.setStyleSheet("""
            QProgressBar { background-color: #161B22; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #38BDF8; border-radius: 3px; }
        """)
        layout.addWidget(self.build_progress)

        self.lbl_build_status = QLabel("")
        self.lbl_build_status.setStyleSheet("color: #8B949E; font-size: 12px;")
        layout.addWidget(self.lbl_build_status)

        # Info card
        info_card = QFrame()
        info_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        i_vbox = QVBoxLayout(info_card)
        i_title = QLabel("كيف يعمل مانيفست البصمات (SINAX_integrity_manifest.json)؟")
        i_title.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 13px;")
        i_vbox.addWidget(i_title)

        i_desc = QLabel(
            "• يقوم النظام بحساب بصمة SHA-256 لكل ملف داخل المجلد ويسجل الحجم والمسار النسبي وتاريخ التعديل.<br>"
            "• يتم حفظ الملف بصيغة JSON المعيارية داخل جذر المجلد باسم <code>SINAX_integrity_manifest.json</code>.<br>"
            "• يمكنك الاحتفاظ بهذه النسخة أو تدقيق المجلد لاحقاً للتأكد التام من عدم حدوث أي تغييرات أو تلف بالملفات."
        )
        i_desc.setWordWrap(True)
        i_desc.setStyleSheet("color: #8B949E; font-size: 12px; line-height: 1.5;")
        i_vbox.addWidget(i_desc)

        layout.addWidget(info_card)
        layout.addStretch(1)
        return widget

    def _on_browse_create_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلداً لإنشاء المانيفست")
        if folder:
            self.txt_create_dir.setText(folder)

    def _start_build_manifest(self):
        target = self.txt_create_dir.text().strip()
        if not target or not os.path.isdir(target):
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار مجلد صالح أولاً.")
            return

        self.btn_build_manifest.setEnabled(False)
        self.btn_build_manifest.setText("جاري التوليد...")
        self.build_progress.setVisible(True)
        self.build_progress.setValue(0)
        self.lbl_build_status.setText("بدء حساب بصمات الملفات...")

        self._build_worker = ManifestBuilderWorker(target)
        self._build_worker.progress_updated.connect(self._on_build_progress)
        self._build_worker.finished_building.connect(self._on_build_finished)
        self._build_worker.start()

    def _on_build_progress(self, pct: float, msg: str):
        self.build_progress.setValue(int(pct * 100))
        self.lbl_build_status.setText(msg)

    def _on_build_finished(self, ok: bool, path_or_msg: str, count: int):
        self.build_progress.setVisible(False)
        self.btn_build_manifest.setEnabled(True)
        self.btn_build_manifest.setText(" توليد المانيفست الآن")

        if ok:
            self.lbl_build_status.setText(f"اكتمل التوليد بنجاح: تم فحص {count} ملف وحفظ المانيفست.")
            QMessageBox.information(
                self,
                "تم بنجاح",
                f"تم إنشاء مانيفست البصمات الرقمية بنجاح!\n\nعدد الملفات المفحوصة: {count}\nالملف الناتج:\n{path_or_msg}"
            )
        else:
            self.lbl_build_status.setText(f"خطأ: {path_or_msg}")
            QMessageBox.critical(self, "فشل العملية", f"تعذر إنشاء المانيفست:\n{path_or_msg}")

    # -------------------------------------------------------------
    # Tab 2: Verify Manifest
    # -------------------------------------------------------------
    def _build_verify_manifest_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Selector Row
        top_box = QFrame()
        top_box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        tb_layout = QVBoxLayout(top_box)
        tb_layout.setSpacing(8)

        # Folder
        row1 = QHBoxLayout()
        l1 = QLabel("المجلد المراد تدقيقه:")
        l1.setStyleSheet("color: #8B949E; font-weight: bold; width: 140px;")
        row1.addWidget(l1)

        self.txt_verify_folder = QLineEdit()
        self.txt_verify_folder.setPlaceholderText("اختر المجلد المحتوي على الملفات...")
        self.txt_verify_folder.setStyleSheet("background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px;")
        row1.addWidget(self.txt_verify_folder, 1)

        btn_f = QPushButton("استعراض...")
        btn_f.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 12px;")
        btn_f.clicked.connect(self._on_browse_verify_folder)
        row1.addWidget(btn_f)
        tb_layout.addLayout(row1)

        # Manifest File
        row2 = QHBoxLayout()
        l2 = QLabel("ملف المانيفست (اختياري):")
        l2.setStyleSheet("color: #8B949E; font-weight: bold; width: 140px;")
        row2.addWidget(l2)

        self.txt_verify_manifest = QLineEdit()
        self.txt_verify_manifest.setPlaceholderText("تلقائي (يبحث عن SINAX_integrity_manifest.json داخل المجلد)...")
        self.txt_verify_manifest.setStyleSheet("background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px;")
        row2.addWidget(self.txt_verify_manifest, 1)

        btn_m = QPushButton("اختيار ملف...")
        btn_m.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 12px;")
        btn_m.clicked.connect(self._on_browse_verify_manifest)
        row2.addWidget(btn_m)

        self.btn_run_verify = QPushButton(" فحص ومطابقة المانيفست")
        self.btn_run_verify.setIcon(get_icon("check", color="#FFFFFF"))
        self.btn_run_verify.setStyleSheet("""
            QPushButton {
                background-color: #1F6FEB; color: #FFFFFF; border-radius: 6px;
                padding: 6px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #388BFD; }
        """)
        self.btn_run_verify.clicked.connect(self._start_verify_manifest)
        row2.addWidget(self.btn_run_verify)
        tb_layout.addLayout(row2)

        layout.addWidget(top_box)

        # Progress bar
        self.verify_progress = QProgressBar()
        self.verify_progress.setRange(0, 100)
        self.verify_progress.setValue(0)
        self.verify_progress.setFixedHeight(6)
        self.verify_progress.setVisible(False)
        self.verify_progress.setStyleSheet("""
            QProgressBar { background-color: #161B22; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #38BDF8; border-radius: 3px; }
        """)
        layout.addWidget(self.verify_progress)

        # Diff Stats Bar
        self.diff_bar = QFrame()
        self.diff_bar.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px;")
        db_layout = QHBoxLayout(self.diff_bar)
        db_layout.setSpacing(20)

        self.lbl_d_unchanged = QLabel("سليمة ومتطابقة: 0")
        self.lbl_d_unchanged.setStyleSheet("color: #34D399; font-weight: bold;")
        db_layout.addWidget(self.lbl_d_unchanged)

        self.lbl_d_modified = QLabel("معدلة (Modified): 0")
        self.lbl_d_modified.setStyleSheet("color: #F87171; font-weight: bold;")
        db_layout.addWidget(self.lbl_d_modified)

        self.lbl_d_missing = QLabel("مفقودة (Missing): 0")
        self.lbl_d_missing.setStyleSheet("color: #FBBF24; font-weight: bold;")
        db_layout.addWidget(self.lbl_d_missing)

        self.lbl_d_new = QLabel("جديدة (New): 0")
        self.lbl_d_new.setStyleSheet("color: #38BDF8; font-weight: bold;")
        db_layout.addWidget(self.lbl_d_new)
        db_layout.addStretch(1)

        layout.addWidget(self.diff_bar)

        # Table of diffs
        self.verify_table = QTableWidget()
        self.verify_table.setColumnCount(4)
        self.verify_table.setHorizontalHeaderLabels(["حالة الملف", "المسار النسبي", "الحجم", "التفاصيل والبصمة"])
        self.verify_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.verify_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.verify_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.verify_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.verify_table.setAlternatingRowColors(True)
        self.verify_table.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117; alternate-background-color: #161B22;
                border: 1px solid #30363D; border-radius: 6px; gridline-color: #21262D; color: #F0F6FC;
            }
            QHeaderView::section {
                background-color: #161B22; color: #8B949E; font-weight: bold; border: 1px solid #21262D; padding: 6px;
            }
        """)
        layout.addWidget(self.verify_table, 1)

        return widget

    def _on_browse_verify_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد التدقيق")
        if folder:
            self.txt_verify_folder.setText(folder)

    def _on_browse_verify_manifest(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "اختر ملف المانيفست", "", "JSON Files (*.json);;All Files (*.*)")
        if file_path:
            self.txt_verify_manifest.setText(file_path)

    def _start_verify_manifest(self):
        target = self.txt_verify_folder.text().strip()
        if not target or not os.path.isdir(target):
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار مجلد صالح أولاً.")
            return

        man = self.txt_verify_manifest.text().strip() or None
        self.btn_run_verify.setEnabled(False)
        self.verify_progress.setVisible(True)
        self.verify_progress.setValue(0)
        self.verify_table.setRowCount(0)

        self._verify_worker = ManifestVerifierWorker(target, man)
        self._verify_worker.progress_updated.connect(lambda p, m: self.verify_progress.setValue(int(p * 100)))
        self._verify_worker.finished_verifying.connect(self._on_verify_finished)
        self._verify_worker.start()

    def _on_verify_finished(self, ok: bool, msg: str, diff: IntegrityDiff):
        self.verify_progress.setVisible(False)
        self.btn_run_verify.setEnabled(True)

        if not ok:
            QMessageBox.critical(self, "خطأ في التدقيق", msg)
            return

        self.lbl_d_unchanged.setText(f"سليمة ومتطابقة: {len(diff.unchanged_files)}")
        self.lbl_d_modified.setText(f"معدلة (Modified): {len(diff.modified_files)}")
        self.lbl_d_missing.setText(f"مفقودة (Missing): {len(diff.missing_files)}")
        self.lbl_d_new.setText(f"جديدة (New): {len(diff.new_files)}")

        # Build table rows
        rows = []
        for m in diff.modified_files:
            rows.append(("تم التعديل (Modified)", m["relative_path"], format_bytes(m.get("current_size", 0)), "تغيرت بصمة التجزئة الرقمية", "#F87171"))
        for miss in diff.missing_files:
            rows.append(("مفقود (Missing)", miss["relative_path"], "—", "الملف كان موجوداً في المانيفست وتم حذفه", "#FBBF24"))
        for n in diff.new_files:
            rows.append(("جديد (New)", n["relative_path"], format_bytes(n.get("size_bytes", 0)), "ملف جديد لم يكن موجوداً في المانيفست", "#38BDF8"))
        for u in diff.unchanged_files:
            rows.append(("متطابق وسليم (Unchanged)", u["relative_path"], format_bytes(u.get("size_bytes", 0)), "البصمة مطابقة تماماً", "#34D399"))

        self.verify_table.setRowCount(len(rows))
        for idx, (st, rel, sz, det, color) in enumerate(rows):
            it_st = QTableWidgetItem(st)
            it_st.setForeground(QColor(color))
            self.verify_table.setItem(idx, 0, it_st)

            self.verify_table.setItem(idx, 1, QTableWidgetItem(rel))
            self.verify_table.setItem(idx, 2, QTableWidgetItem(sz))
            self.verify_table.setItem(idx, 3, QTableWidgetItem(det))

        if diff.has_changes:
            QMessageBox.warning(self, "نتيجة التدقيق", f"تم رصد تغييرات بالملفات:\n{msg}")
        else:
            QMessageBox.information(self, "نتيجة التدقيق", "تطابق تام! كافة الملفات مطابقة للمانيفست بنسبة 100% دون أي تعديل أو نقص.")

    # -------------------------------------------------------------
    # Tab 3: Single File Match
    # -------------------------------------------------------------
    def _build_single_hash_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        box = QFrame()
        box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        b_layout = QVBoxLayout(box)
        b_layout.setSpacing(12)

        # File picker
        r1 = QHBoxLayout()
        l_f = QLabel("الملف المراد فحصه:")
        l_f.setStyleSheet("color: #8B949E; font-weight: bold; width: 130px;")
        r1.addWidget(l_f)

        self.txt_single_f = QLineEdit()
        self.txt_single_f.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px;")
        r1.addWidget(self.txt_single_f, 1)

        btn_bf = QPushButton("استعراض...")
        btn_bf.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 12px;")
        btn_bf.clicked.connect(self._on_browse_single_file)
        r1.addWidget(btn_bf)
        b_layout.addLayout(r1)

        # Expected hash
        r2 = QHBoxLayout()
        l_e = QLabel("بصمة الهاش المتوقعة:")
        l_e.setStyleSheet("color: #8B949E; font-weight: bold; width: 130px;")
        r2.addWidget(l_e)

        self.txt_expected_hash = QLineEdit()
        self.txt_expected_hash.setPlaceholderText("الصق بصمة الهاش (SHA-256 أو SHA-512) التي نشرها المطور أو المصدر...")
        self.txt_expected_hash.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px; font-family: Consolas, monospace;")
        r2.addWidget(self.txt_expected_hash, 1)

        btn_verify_single = QPushButton("تحقق ومطابقة")
        btn_verify_single.setIcon(get_icon("check", color="#FFFFFF"))
        btn_verify_single.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: #FFFFFF; border-radius: 6px;
                padding: 6px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2EA043; }
        """)
        btn_verify_single.clicked.connect(self._verify_single_hash)
        r2.addWidget(btn_verify_single)
        b_layout.addLayout(r2)

        layout.addWidget(box)

        # Result card
        self.single_hash_result_card = QFrame()
        self.single_hash_result_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px;")
        res_vbox = QVBoxLayout(self.single_hash_result_card)
        self.lbl_single_hash_verdict = QLabel("أدخل الملف والهاش المتوقع للبدء في المقارنة...")
        self.lbl_single_hash_verdict.setStyleSheet("color: #8B949E; font-size: 14px; font-weight: bold;")
        res_vbox.addWidget(self.lbl_single_hash_verdict)

        self.lbl_single_hash_details = QLabel("")
        self.lbl_single_hash_details.setWordWrap(True)
        self.lbl_single_hash_details.setStyleSheet("color: #6E7681; font-size: 12px; font-family: Consolas, monospace;")
        res_vbox.addWidget(self.lbl_single_hash_details)

        layout.addWidget(self.single_hash_result_card)
        layout.addStretch(1)
        return widget

    def _on_browse_single_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً للمطابقة", "", "كافة الملفات (*.*)")
        if f:
            self.txt_single_f.setText(f)

    def _verify_single_hash(self):
        f = self.txt_single_f.text().strip()
        exp = self.txt_expected_hash.text().strip()

        if not f or not os.path.isfile(f):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف موجود صالح.")
            return
        if not exp:
            QMessageBox.warning(self, "تنبيه", "يرجى لصق الهاش المتوقع للمقارنة معه.")
            return

        algo = "SHA-512" if len(exp) == 128 else "SHA-256"
        match, computed, msg = IntegrityService.verify_hash(f, exp, algorithm=algo)

        if match:
            self.single_hash_result_card.setStyleSheet("background-color: #132E22; border: 1px solid #34D399; border-radius: 8px; padding: 14px;")
            self.lbl_single_hash_verdict.setText(" تطابق تام (MATCH): الملف سليم 100% ومطابق للهاش المعلن!")
            self.lbl_single_hash_verdict.setStyleSheet("color: #34D399; font-size: 15px; font-weight: bold;")
        else:
            self.single_hash_result_card.setStyleSheet("background-color: #2D1418; border: 1px solid #F87171; border-radius: 8px; padding: 14px;")
            self.lbl_single_hash_verdict.setText(" عدم تطابق (MISMATCH): الهاش المحسوب يختلف عن الهاش المتوقع!")
            self.lbl_single_hash_verdict.setStyleSheet("color: #F87171; font-size: 15px; font-weight: bold;")

        self.lbl_single_hash_details.setText(
            f"الهاش المحسوب ({algo}):\n{computed}\n\n"
            f"الهاش المتوقع:\n{exp}"
        )
