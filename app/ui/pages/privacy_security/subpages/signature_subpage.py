# -*- coding: utf-8 -*-
"""
Digital Signature Subpage (التوقيع الرقمي وشهادات X.509) for SINAX Privacy & Security Center.
Features:
1. Single executable/binary Authenticode verification and deep X.509 certificate viewer.
2. High-performance batch directory signature auditor with filtering and CSV export.
"""

import csv
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
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

from app.services.privacy_security.models import CertificateDetails, SignatureStatus
from app.services.privacy_security.signature_service import BatchSignatureResult, SignatureService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class BatchSignatureScanWorker(QThread):
    """Background worker for batch directory signature auditing."""
    progress_updated = Signal(float, str)
    scan_finished = Signal(object)

    def __init__(self, folder_path: str, recursive: bool):
        super().__init__()
        self.folder_path = folder_path
        self.recursive = recursive
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        result = SignatureService.scan_directory(
            self.folder_path,
            recursive=self.recursive,
            progress_cb=lambda p, msg: self.progress_updated.emit(p, msg),
            cancel_check=lambda: self._is_cancelled,
        )
        self.scan_finished.emit(result)


class SignatureSubpage(QWidget):
    """Digital Signature & Authenticode Verification Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._batch_worker: Optional[BatchSignatureScanWorker] = None
        self._batch_results: List[Dict[str, Any]] = []
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
        t_lbl = QLabel("التوقيع الرقمي والشهادات (Authenticode & X.509)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("التحقق من سلامة وصلاحية التواقيع الرقمية للبرامج والمكتبات واستعراض شهادات X.509 وسلسلة الثقة.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        main_layout.addLayout(header_row)

        # 2. Tab Widget (Single File vs Batch Folder)
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363D;
                background-color: #0D1117;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #161B22;
                color: #8B949E;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                margin-left: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0D1117;
                color: #38BDF8;
                border: 1px solid #30363D;
                border-bottom: 1px solid #0D1117;
            }
            QTabBar::tab:hover:!selected {
                background-color: #21262D;
                color: #F0F6FC;
            }
        """)

        tab_single = self._build_single_file_tab()
        tab_batch = self._build_batch_folder_tab()

        self.tabs.addTab(tab_single, "فحص ملف فردي وتفاصيل الشهادة")
        self.tabs.addTab(tab_batch, "فحص مجلد كامل (تدقيق جماعي)")

        main_layout.addWidget(self.tabs, 1)

    # -------------------------------------------------------------
    # Tab 1: Single File Inspector
    # -------------------------------------------------------------
    def _build_single_file_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea(widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: #0D1117;")

        container = QWidget()
        container.setStyleSheet("background-color: #0D1117;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Selector Row
        sel_frame = QFrame()
        sel_frame.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        sel_layout = QHBoxLayout(sel_frame)
        sel_layout.setSpacing(10)

        sel_lbl = QLabel("الملف التنفيذي:")
        sel_lbl.setStyleSheet("color: #8B949E; font-weight: bold;")
        sel_layout.addWidget(sel_lbl)

        self.txt_single_path = QLineEdit()
        self.txt_single_path.setPlaceholderText("اختر ملف .exe, .dll, .sys, .msi...")
        self.txt_single_path.setStyleSheet("""
            QLineEdit {
                background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px; font-size: 12px;
            }
        """)
        sel_layout.addWidget(self.txt_single_path, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: #FFFFFF; border-radius: 6px;
                padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2EA043; }
        """)
        btn_browse.clicked.connect(self._on_browse_single)
        sel_layout.addWidget(btn_browse)

        btn_verify = QPushButton("تحقق الآن")
        btn_verify.setIcon(get_icon("check", color="#FFFFFF"))
        btn_verify.setStyleSheet("""
            QPushButton {
                background-color: #1F6FEB; color: #FFFFFF; border-radius: 6px;
                padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #388BFD; }
        """)
        btn_verify.clicked.connect(self._on_verify_single)
        sel_layout.addWidget(btn_verify)

        layout.addWidget(sel_frame)

        # Status Summary Card
        self.single_status_card = QFrame()
        self.single_status_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        sum_layout = QHBoxLayout(self.single_status_card)
        sum_layout.setSpacing(14)

        self.lbl_single_icon = QLabel()
        self.lbl_single_icon.setPixmap(get_icon("signature", color="#8B949E", size=36).pixmap(36, 36))
        sum_layout.addWidget(self.lbl_single_icon)

        sum_vbox = QVBoxLayout()
        self.lbl_single_status_title = QLabel("في انتظار اختيار ملف تنفيذي...", self)
        self.lbl_single_status_title.setStyleSheet("color: #8B949E; font-size: 16px; font-weight: bold;")
        sum_vbox.addWidget(self.lbl_single_status_title)

        self.lbl_single_status_sub = QLabel("يدعم فحص تواقيع Microsoft Authenticode الرسمية وشهادات X.509 والختم الزمني.", self)
        self.lbl_single_status_sub.setStyleSheet("color: #6E7681; font-size: 12px;")
        sum_vbox.addWidget(self.lbl_single_status_sub)
        sum_layout.addLayout(sum_vbox, 1)

        layout.addWidget(self.single_status_card)

        # X.509 Certificate Card
        self.cert_card = QFrame()
        self.cert_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        cert_vbox = QVBoxLayout(self.cert_card)
        cert_vbox.setSpacing(10)

        c_head = QHBoxLayout()
        c_icon = QLabel()
        c_icon.setPixmap(get_icon("certificate", color="#38BDF8", size=20).pixmap(20, 20))
        c_head.addWidget(c_icon)
        c_title = QLabel("تفاصيل شهادة X.509 والناشر المعتمد")
        c_title.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        c_head.addWidget(c_title)
        c_head.addStretch(1)
        cert_vbox.addLayout(c_head)

        self.lbl_cert_content = QLabel("لا توجد بيانات شهادة معروضة حالياً.")
        self.lbl_cert_content.setWordWrap(True)
        self.lbl_cert_content.setStyleSheet("color: #8B949E; font-size: 12px; line-height: 1.6;")
        cert_vbox.addWidget(self.lbl_cert_content)

        layout.addWidget(self.cert_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        w_layout = QVBoxLayout(widget)
        w_layout.setContentsMargins(0, 0, 0, 0)
        w_layout.addWidget(scroll)
        return widget

    def _on_browse_single(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملفاً تنفيذياً للتحقق من توقيعه",
            "",
            "ملفات تنفيذية ومكتبات (*.exe *.dll *.sys *.msi *.ps1);;كافة الملفات (*.*)"
        )
        if path:
            self.txt_single_path.setText(path)
            self._on_verify_single()

    def _on_verify_single(self):
        target = self.txt_single_path.text().strip()
        if not target or not os.path.isfile(target):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف موجود صالح للفحص.")
            return

        status, signer, cert = SignatureService.inspect_file(target)

        # Update card UI
        if status == SignatureStatus.VALID:
            self.lbl_single_status_title.setText("التوقيع الرقمي صالح وموثوق (Valid Authenticode)")
            self.lbl_single_status_title.setStyleSheet("color: #34D399; font-size: 16px; font-weight: bold;")
            self.lbl_single_icon.setPixmap(get_icon("shield", color="#34D399", size=36).pixmap(36, 36))
            self.single_status_card.setStyleSheet("background-color: #132E22; border: 1px solid #34D399; border-radius: 10px; padding: 14px;")
            self.lbl_single_status_sub.setText(f"الناشر: {signer or 'غير محدد'}")
        elif status == SignatureStatus.UNSIGNED:
            self.lbl_single_status_title.setText("الملف غير موقّع رقمياً (Unsigned Executable)")
            self.lbl_single_status_title.setStyleSheet("color: #FBBF24; font-size: 16px; font-weight: bold;")
            self.lbl_single_icon.setPixmap(get_icon("warning", color="#FBBF24", size=36).pixmap(36, 36))
            self.single_status_card.setStyleSheet("background-color: #2B2111; border: 1px solid #FBBF24; border-radius: 10px; padding: 14px;")
            self.lbl_single_status_sub.setText("هذا البرنامج لا يحتوي على توقيع رقمي معتمد من ناشر برمجيات موثوق.")
        else:
            self.lbl_single_status_title.setText(f"تنبيه: توقيع غير صالح أو غير موثوق ({status.value})")
            self.lbl_single_status_title.setStyleSheet("color: #F87171; font-size: 16px; font-weight: bold;")
            self.lbl_single_icon.setPixmap(get_icon("warning", color="#F87171", size=36).pixmap(36, 36))
            self.single_status_card.setStyleSheet("background-color: #2D1418; border: 1px solid #F87171; border-radius: 10px; padding: 14px;")
            self.lbl_single_status_sub.setText(f"تفاصيل الخطأ: {signer}")

        # Update Cert details
        if cert:
            ts_str = "نعم (معتمد)" if cert.has_timestamp else "لا يوجد ختم زمني"
            valid_from = cert.valid_from or "غير محدد"
            valid_to = cert.valid_to or "غير محدد"
            cert_text = (
                f"<b>صاحب الشهادة (Subject):</b> {cert.subject}<br>"
                f"<b>الجهة المصدرة (Issuer):</b> {cert.issuer}<br>"
                f"<b>الرقم التسلسلي:</b> <code>{cert.serial_number or 'غير متوفر'}</code><br>"
                f"<b>بصمة الشهادة (Thumbprint):</b> <code>{cert.thumbprint or 'غير متوفر'}</code><br>"
                f"<b>فترة الصلاحية:</b> من {valid_from} إلى {valid_to}<br>"
                f"<b>الختم الزمني (Timestamp):</b> {ts_str}"
            )
            self.lbl_cert_content.setText(cert_text)
        else:
            self.lbl_cert_content.setText("لا تتوفر تفاصيل شهادة رقمية لهذا الملف (الملف غير موقّع أو تالف التوقيع).")

    # -------------------------------------------------------------
    # Tab 2: Batch Folder Auditor
    # -------------------------------------------------------------
    def _build_batch_folder_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Folder selector row
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        lbl_f = QLabel("مجلد البرامج:")
        lbl_f.setStyleSheet("color: #8B949E; font-weight: bold;")
        top_row.addWidget(lbl_f)

        self.txt_batch_folder = QLineEdit()
        self.txt_batch_folder.setPlaceholderText("حدد مسار مجلد لفحص كافة ملفات .exe و .dll داخله...")
        self.txt_batch_folder.setStyleSheet("""
            QLineEdit {
                background-color: #161B22; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px; font-size: 12px;
            }
        """)
        top_row.addWidget(self.txt_batch_folder, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #30363D; }
        """)
        btn_browse.clicked.connect(self._on_browse_batch_folder)
        top_row.addWidget(btn_browse)

        self.chk_recursive = QCheckBox("تضمين المجلدات الفرعية (Recursive)")
        self.chk_recursive.setChecked(True)
        self.chk_recursive.setStyleSheet("color: #8B949E; font-weight: bold;")
        top_row.addWidget(self.chk_recursive)

        self.btn_start_batch = QPushButton("بدء الفحص الجماعي")
        self.btn_start_batch.setIcon(get_icon("play", color="#FFFFFF"))
        self.btn_start_batch.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: #FFFFFF; border-radius: 6px;
                padding: 8px 18px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2EA043; }
        """)
        self.btn_start_batch.clicked.connect(self._start_batch_scan)
        top_row.addWidget(self.btn_start_batch)

        layout.addLayout(top_row)

        # Progress bar
        self.batch_progress = QProgressBar()
        self.batch_progress.setRange(0, 100)
        self.batch_progress.setValue(0)
        self.batch_progress.setFixedHeight(6)
        self.batch_progress.setVisible(False)
        self.batch_progress.setStyleSheet("""
            QProgressBar { background-color: #161B22; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #38BDF8; border-radius: 3px; }
        """)
        layout.addWidget(self.batch_progress)

        # Summary Metrics Bar
        self.metrics_bar = QFrame()
        self.metrics_bar.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 10px;")
        m_layout = QHBoxLayout(self.metrics_bar)
        m_layout.setSpacing(20)

        self.lbl_m_total = QLabel("إجمالي الملفات: 0")
        self.lbl_m_total.setStyleSheet("color: #F0F6FC; font-weight: bold;")
        m_layout.addWidget(self.lbl_m_total)

        self.lbl_m_valid = QLabel("موقعة وصالحة: 0")
        self.lbl_m_valid.setStyleSheet("color: #34D399; font-weight: bold;")
        m_layout.addWidget(self.lbl_m_valid)

        self.lbl_m_unsigned = QLabel("غير موقعة: 0")
        self.lbl_m_unsigned.setStyleSheet("color: #FBBF24; font-weight: bold;")
        m_layout.addWidget(self.lbl_m_unsigned)

        self.lbl_m_invalid = QLabel("تالفة/غير موثوقة: 0")
        self.lbl_m_invalid.setStyleSheet("color: #F87171; font-weight: bold;")
        m_layout.addWidget(self.lbl_m_invalid)

        m_layout.addStretch(1)

        # Filter combo
        lbl_filter = QLabel("تصفية:")
        lbl_filter.setStyleSheet("color: #8B949E; font-size: 12px;")
        m_layout.addWidget(lbl_filter)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["عرض الكل", "الموقعة والصالحة فقط", "غير الموقعة فقط", "التالفة وغير الموثوقة"])
        self.cmb_filter.setStyleSheet("""
            QComboBox {
                background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 4px; padding: 4px 8px; font-size: 11px;
            }
        """)
        self.cmb_filter.currentIndexChanged.connect(self._apply_batch_filter)
        m_layout.addWidget(self.cmb_filter)

        # Export CSV Button
        btn_export = QPushButton("تصدير CSV")
        btn_export.setIcon(get_icon("download", color="#38BDF8"))
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: #0D1117; color: #38BDF8; border: 1px solid #38BDF8;
                border-radius: 4px; padding: 4px 12px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background-color: #38BDF8; color: #0D1117; }
        """)
        btn_export.clicked.connect(self._export_batch_csv)
        m_layout.addWidget(btn_export)

        layout.addWidget(self.metrics_bar)

        # High-performance Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["اسم الملف", "الامتداد", "حالة التوقيع", "الناشر / صاحب التوقيع", "الختم الزمني", "المسار الكامل"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117;
                alternate-background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                gridline-color: #21262D;
                color: #F0F6FC;
            }
            QHeaderView::section {
                background-color: #161B22;
                color: #8B949E;
                font-weight: bold;
                border: 1px solid #21262D;
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #1F6FEB;
                color: #FFFFFF;
            }
        """)
        layout.addWidget(self.table, 1)

        return widget

    def _on_browse_batch_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد البرامج للفحص الجماعي")
        if folder:
            self.txt_batch_folder.setText(folder)

    def _start_batch_scan(self):
        target = self.txt_batch_folder.text().strip()
        if not target or not os.path.isdir(target):
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار مجلد صالح أولاً.")
            return

        self.btn_start_batch.setEnabled(False)
        self.btn_start_batch.setText("جاري الفحص...")
        self.batch_progress.setVisible(True)
        self.batch_progress.setValue(0)
        self.table.setRowCount(0)

        self._batch_worker = BatchSignatureScanWorker(target, self.chk_recursive.isChecked())
        self._batch_worker.progress_updated.connect(self._on_batch_progress)
        self._batch_worker.scan_finished.connect(self._on_batch_finished)
        self._batch_worker.start()

    def _on_batch_progress(self, pct: float, msg: str):
        self.batch_progress.setValue(int(pct * 100))

    def _on_batch_finished(self, result: BatchSignatureResult):
        self.batch_progress.setVisible(False)
        self.btn_start_batch.setEnabled(True)
        self.btn_start_batch.setText("بدء الفحص الجماعي")

        self.lbl_m_total.setText(f"إجمالي الملفات: {result.total_scanned}")
        self.lbl_m_valid.setText(f"موقعة وصالحة: {result.valid_count}")
        self.lbl_m_unsigned.setText(f"غير موقعة: {result.unsigned_count}")
        self.lbl_m_invalid.setText(f"تالفة/غير موثوقة: {result.invalid_count}")

        self._batch_results = result.files_details or []
        self._populate_batch_table(self._batch_results)

    def _populate_batch_table(self, items: List[Dict[str, Any]]):
        self.table.setRowCount(len(items))
        for row_idx, item in enumerate(items):
            # File name
            it_name = QTableWidgetItem(item.get("filename", ""))
            self.table.setItem(row_idx, 0, it_name)

            # Ext
            it_ext = QTableWidgetItem(item.get("extension", ""))
            self.table.setItem(row_idx, 1, it_ext)

            # Status
            st = item.get("status", "")
            it_st = QTableWidgetItem(st)
            if st == "VALID":
                it_st.setForeground(QColor("#34D399"))
            elif st == "UNSIGNED":
                it_st.setForeground(QColor("#FBBF24"))
            else:
                it_st.setForeground(QColor("#F87171"))
            self.table.setItem(row_idx, 2, it_st)

            # Signer
            it_signer = QTableWidgetItem(item.get("signer", "—"))
            self.table.setItem(row_idx, 3, it_signer)

            # Timestamp
            ts = "نعم" if item.get("has_timestamp") else "لا"
            it_ts = QTableWidgetItem(ts)
            self.table.setItem(row_idx, 4, it_ts)

            # Path
            it_path = QTableWidgetItem(item.get("path", ""))
            it_path.setToolTip(item.get("path", ""))
            self.table.setItem(row_idx, 5, it_path)

    def _apply_batch_filter(self, index: int):
        if not self._batch_results:
            return

        if index == 0:  # All
            filtered = self._batch_results
        elif index == 1:  # Valid
            filtered = [x for x in self._batch_results if x.get("status") == "VALID"]
        elif index == 2:  # Unsigned
            filtered = [x for x in self._batch_results if x.get("status") == "UNSIGNED"]
        else:  # Invalid
            filtered = [x for x in self._batch_results if x.get("status") not in ("VALID", "UNSIGNED")]

        self._populate_batch_table(filtered)

    def _export_batch_csv(self):
        if not self._batch_results:
            QMessageBox.information(self, "تنبيه", "لا توجد نتائج لتصديرها.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ تقرير التواقيع بصيغة CSV",
            "SINAX_Signatures_Audit.csv",
            "ملفات CSV (*.csv)"
        )
        if not save_path:
            return

        try:
            with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Filename", "Extension", "Status", "Signer", "Has_Timestamp", "Full_Path"])
                for it in self._batch_results:
                    writer.writerow([
                        it.get("filename", ""),
                        it.get("extension", ""),
                        it.get("status", ""),
                        it.get("signer", ""),
                        it.get("has_timestamp", False),
                        it.get("path", "")
                    ])
            QMessageBox.information(self, "نجاح", f"تم تصدير التقرير بنجاح إلى:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل تصدير ملف CSV:\n{str(e)}")
