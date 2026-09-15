# -*- coding: utf-8 -*-
"""
File Safety Inspector Subpage (فحص سلامة الملفات) for SINAX Privacy & Security Center.
Performs non-executable static analysis:
- Magic bytes vs extension mismatch detector
- Double extension deception detector (.pdf.exe, .jpg.scr)
- Mark of the Web (Zone.Identifier) inspection
- SHA-256 and SHA-512 cryptographic digests
- Authenticode signature summary
- On-demand Microsoft Defender scan execution
"""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import format_bytes
from app.services.privacy_security.defender_service import DefenderService
from app.services.privacy_security.file_safety_service import FileSafetyService
from app.services.privacy_security.models import FileSafetyReport, SafetyLevel
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class DefenderScanWorker(QThread):
    """Background worker for on-demand Defender file scan."""
    finished_scan = Signal(bool, str)

    def __init__(self, target_path: str):
        super().__init__()
        self.target_path = target_path

    def run(self):
        service = DefenderService()
        clean, msg = service.scan_path(self.target_path)
        self.finished_scan.emit(clean, msg)


class DropZoneFrame(QFrame):
    """Drag & Drop zone with visual feedback."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._set_idle_style()

    def _set_idle_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 2px dashed #30363D;
                border-radius: 12px;
                padding: 24px;
            }
            QFrame:hover {
                border-color: #38BDF8;
                background-color: #1A2230;
            }
        """)

    def _set_drag_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #1A2E3D;
                border: 2px dashed #38BDF8;
                border-radius: 12px;
                padding: 24px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_style()

    def dragLeaveEvent(self, event):
        self._set_idle_style()

    def dropEvent(self, event: QDropEvent):
        self._set_idle_style()
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isfile(path):
                self.file_dropped.emit(path)


class FileSafetySubpage(QWidget):
    """File Safety Inspector interactive subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._current_file: Optional[str] = None
        self._scan_worker: Optional[DefenderScanWorker] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll container
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #0D1117; }")

        container = QWidget()
        container.setStyleSheet("background-color: #0D1117;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # 1. Header with back button
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self.btn_back = QPushButton(" العودة للرئيسية")
        self.btn_back.setIcon(get_icon("arrow_back", color="#8B949E"))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #161B22;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #21262D;
                color: #F0F6FC;
            }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.btn_back)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel("فاحص سلامة الملفات (File Safety Inspector)", self)
        title_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(title_lbl)

        sub_lbl = QLabel("فحص استاتيكي دقيق فوري دون تنفيذ الملف، مع كشف الامتدادات المخادعة وتكامل Microsoft Defender.", self)
        sub_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(sub_lbl)
        header_row.addLayout(title_vbox, 1)

        # Local badge
        header_row.addWidget(ToolBadgeWidget.local_100(self))
        layout.addLayout(header_row)

        # 2. Drag & Drop selection zone
        self.drop_zone = DropZoneFrame(self)
        self.drop_zone.file_dropped.connect(self.inspect_target)
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setAlignment(Qt.AlignCenter)
        drop_layout.setSpacing(10)

        drop_icon = QLabel()
        drop_icon.setPixmap(get_icon("eye", color="#38BDF8", size=40).pixmap(40, 40))
        drop_icon.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_icon)

        drop_text = QLabel("اسحب وأفلت أي ملف هنا للفحص الاستاتيكي الفوري، أو اضغط للاختيار")
        drop_text.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        drop_text.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_text)

        drop_hint = QLabel("يدعم البرامج التنفيذية، المستندات، الصور، والملفات المضغوطة (لا يتم تشغيل أي كود أثناء الفحص)")
        drop_hint.setStyleSheet("color: #6E7681; font-size: 11px;")
        drop_hint.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_hint)

        btn_browse = QPushButton(" اختيار ملف من الجهاز...")
        btn_browse.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #FFFFFF;
                border: 1px solid rgba(240, 246, 252, 0.1);
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2EA043;
            }
        """)
        btn_browse.clicked.connect(self._on_browse_file)
        drop_layout.addWidget(btn_browse, 0, Qt.AlignCenter)

        layout.addWidget(self.drop_zone)

        # 3. Results Container (Initially Hidden until file inspected)
        self.results_container = QWidget(self)
        self.results_container.setVisible(False)
        res_layout = QVBoxLayout(self.results_container)
        res_layout.setContentsMargins(0, 8, 0, 0)
        res_layout.setSpacing(14)

        # Result Summary Banner Card
        self.summary_card = QFrame()
        self.summary_card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 14px;
            }
        """)
        sum_layout = QHBoxLayout(self.summary_card)
        sum_layout.setSpacing(14)

        self.status_icon_lbl = QLabel()
        self.status_icon_lbl.setPixmap(get_icon("shield", color="#34D399", size=36).pixmap(36, 36))
        sum_layout.addWidget(self.status_icon_lbl)

        sum_info = QVBoxLayout()
        sum_info.setSpacing(4)
        self.lbl_result_title = QLabel("الملف آمن استاتيكياً", self)
        self.lbl_result_title.setStyleSheet("color: #34D399; font-size: 16px; font-weight: bold;")
        sum_info.addWidget(self.lbl_result_title)

        self.lbl_result_file = QLabel("", self)
        self.lbl_result_file.setStyleSheet("color: #8B949E; font-size: 12px;")
        sum_info.addWidget(self.lbl_result_file)
        sum_layout.addLayout(sum_info, 1)

        # Defender Action in Banner
        self.btn_defender_scan = QPushButton(" فحص عبر Microsoft Defender")
        self.btn_defender_scan.setIcon(get_icon("security", color="#38BDF8"))
        self.btn_defender_scan.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #38BDF8;
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #38BDF8;
                color: #0D1117;
            }
        """)
        self.btn_defender_scan.clicked.connect(self._run_defender_scan)
        sum_layout.addWidget(self.btn_defender_scan)

        res_layout.addWidget(self.summary_card)

        # Progress bar for scan
        self.scan_progress = QProgressBar(self)
        self.scan_progress.setRange(0, 0)
        self.scan_progress.setFixedHeight(6)
        self.scan_progress.setVisible(False)
        self.scan_progress.setStyleSheet("""
            QProgressBar {
                background-color: #161B22;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 3px;
            }
        """)
        res_layout.addWidget(self.scan_progress)

        # Detailed Grid: Inspection findings
        grid = QGridLayout()
        grid.setSpacing(12)

        # Box 1: File Identity & Magic Bytes
        self.box_identity = self._create_card("الهوية والبصمة السحرية (Magic Bytes)", "document")
        self.lbl_magic_info = QLabel("—")
        self.lbl_magic_info.setWordWrap(True)
        self.lbl_magic_info.setStyleSheet("color: #F0F6FC; font-size: 12px; line-height: 1.4;")
        self.box_identity.layout().addWidget(self.lbl_magic_info)
        grid.addWidget(self.box_identity, 0, 0)

        # Box 2: Extension & Deception Check
        self.box_extension = self._create_card("الامتداد وكشف التمويه", "eye")
        self.lbl_ext_info = QLabel("—")
        self.lbl_ext_info.setWordWrap(True)
        self.lbl_ext_info.setStyleSheet("color: #F0F6FC; font-size: 12px; line-height: 1.4;")
        self.box_extension.layout().addWidget(self.lbl_ext_info)
        grid.addWidget(self.box_extension, 0, 1)

        # Box 3: Origin & Internet Mark (MOTW)
        self.box_origin = self._create_card("وسام الإنترنت ومصدر الملف (MOTW)", "globe")
        self.lbl_origin_info = QLabel("—")
        self.lbl_origin_info.setWordWrap(True)
        self.lbl_origin_info.setStyleSheet("color: #F0F6FC; font-size: 12px; line-height: 1.4;")
        self.box_origin.layout().addWidget(self.lbl_origin_info)
        grid.addWidget(self.box_origin, 1, 0)

        # Box 4: Digital Signature (Authenticode)
        self.box_signature = self._create_card("التوقيع الرقمي (Authenticode)", "signature")
        self.lbl_sig_info = QLabel("—")
        self.lbl_sig_info.setWordWrap(True)
        self.lbl_sig_info.setStyleSheet("color: #F0F6FC; font-size: 12px; line-height: 1.4;")
        self.box_signature.layout().addWidget(self.lbl_sig_info)
        grid.addWidget(self.box_signature, 1, 1)

        res_layout.addLayout(grid)

        # Hashes Card with Copy
        hash_card = self._create_card("بصمات التجزئة الرقمية (Cryptographic Hashes)", "hash")
        hash_layout = QVBoxLayout()
        hash_layout.setSpacing(8)

        # SHA-256 row
        sha256_row = QHBoxLayout()
        lbl_s256 = QLabel("SHA-256:")
        lbl_s256.setStyleSheet("color: #8B949E; font-weight: bold; width: 65px;")
        sha256_row.addWidget(lbl_s256)

        self.txt_sha256 = QLineEdit()
        self.txt_sha256.setReadOnly(True)
        self.txt_sha256.setStyleSheet("""
            QLineEdit {
                background-color: #0D1117;
                color: #58A6FF;
                border: 1px solid #30363D;
                border-radius: 4px;
                padding: 4px 8px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        sha256_row.addWidget(self.txt_sha256, 1)

        btn_copy_256 = QPushButton("نسخ")
        btn_copy_256.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 4px; padding: 4px 10px;
            }
            QPushButton:hover { background: #30363D; }
        """)
        btn_copy_256.clicked.connect(lambda: self._copy_to_clipboard(self.txt_sha256.text()))
        sha256_row.addWidget(btn_copy_256)
        hash_layout.addLayout(sha256_row)

        # SHA-512 row
        sha512_row = QHBoxLayout()
        lbl_s512 = QLabel("SHA-512:")
        lbl_s512.setStyleSheet("color: #8B949E; font-weight: bold; width: 65px;")
        sha512_row.addWidget(lbl_s512)

        self.txt_sha512 = QLineEdit()
        self.txt_sha512.setReadOnly(True)
        self.txt_sha512.setStyleSheet("""
            QLineEdit {
                background-color: #0D1117;
                color: #8B949E;
                border: 1px solid #30363D;
                border-radius: 4px;
                padding: 4px 8px;
                font-family: Consolas, monospace;
                font-size: 10px;
            }
        """)
        sha512_row.addWidget(self.txt_sha512, 1)

        btn_copy_512 = QPushButton("نسخ")
        btn_copy_512.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 4px; padding: 4px 10px;
            }
            QPushButton:hover { background: #30363D; }
        """)
        btn_copy_512.clicked.connect(lambda: self._copy_to_clipboard(self.txt_sha512.text()))
        sha512_row.addWidget(btn_copy_512)
        hash_layout.addLayout(sha512_row)

        hash_card.layout().addLayout(hash_layout)
        res_layout.addWidget(hash_card)

        # Recommendations Card
        rec_card = self._create_card("التوصيات والإرشادات الأمنية", "shield")
        self.lbl_recommendations = QLabel("—")
        self.lbl_recommendations.setWordWrap(True)
        self.lbl_recommendations.setStyleSheet("color: #8B949E; font-size: 12px; line-height: 1.5;")
        rec_card.layout().addWidget(self.lbl_recommendations)
        res_layout.addWidget(rec_card)

        layout.addWidget(self.results_container)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_card(self, title: str, icon_name: str) -> QFrame:
        """Creates a standardized Fluent dark card."""
        card = QFrame(self)
        card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 14px;
            }
        """)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(icon_name, color="#58A6FF", size=18).pixmap(18, 18))
        header.addWidget(icon_lbl)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: bold;")
        header.addWidget(lbl_t)
        header.addStretch(1)

        vbox.addLayout(header)
        return card

    def _on_browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملفاً لفحصه استاتيكياً",
            "",
            "كافة الملفات (*.*)"
        )
        if path:
            self.inspect_target(path)

    def inspect_target(self, file_path: str):
        """Performs static file inspection and populates results."""
        p = Path(file_path).resolve()
        if not p.exists() or not p.is_file():
            QMessageBox.warning(self, "تنبيه", "الملف المحدد غير موجود على القرص.")
            return

        self._current_file = str(p)
        report: FileSafetyReport = FileSafetyService.inspect_file(str(p))

        self.results_container.setVisible(True)
        self.lbl_result_file.setText(f"المسار: {p.name} ({format_bytes(report.size_bytes)})")

        # Set summary status colors
        if report.safety_level in (SafetyLevel.CRITICAL, SafetyLevel.DANGER):
            self.lbl_result_title.setText("تنبيه خطورة: تم اكتشاف محاولة تمويه أو خطر محتمل!")
            self.lbl_result_title.setStyleSheet("color: #F87171; font-size: 16px; font-weight: bold;")
            self.status_icon_lbl.setPixmap(get_icon("warning", color="#F87171", size=36).pixmap(36, 36))
            self.summary_card.setStyleSheet("QFrame { background-color: #2D1418; border: 1px solid #F87171; border-radius: 10px; padding: 14px; }")
        elif report.safety_level == SafetyLevel.WARNING:
            self.lbl_result_title.setText("تحذير: خصائص مشبوهة أو ملف تنفيذي غير موقّع")
            self.lbl_result_title.setStyleSheet("color: #FBBF24; font-size: 16px; font-weight: bold;")
            self.status_icon_lbl.setPixmap(get_icon("warning", color="#FBBF24", size=36).pixmap(36, 36))
            self.summary_card.setStyleSheet("QFrame { background-color: #2B2111; border: 1px solid #FBBF24; border-radius: 10px; padding: 14px; }")
        else:
            self.lbl_result_title.setText("الملف يبدو سليماً استاتيكياً (لم يتم رصد تمويه)")
            self.lbl_result_title.setStyleSheet("color: #34D399; font-size: 16px; font-weight: bold;")
            self.status_icon_lbl.setPixmap(get_icon("shield", color="#34D399", size=36).pixmap(36, 36))
            self.summary_card.setStyleSheet("QFrame { background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px; }")

        # Identity & Magic
        mismatch_txt = "<font color='#F87171'><b>(عدم تطابق مع الامتداد!)</b></font>" if report.is_magic_mismatch else "<font color='#34D399'><b>(متطابق)</b></font>"
        self.lbl_magic_info.setText(
            f"<b>النوع المكتشف:</b> {report.detected_type_name}<br>"
            f"<b>النوع البرمجي (MIME):</b> {report.detected_mime}<br>"
            f"<b>حالة التوافق:</b> {mismatch_txt}"
        )

        # Extension & Double Ext
        double_txt = "<font color='#F87171'><b>نعم (امتداد مزدوج مخادع!)</b></font>" if report.is_double_extension else "لا (امتداد طبيعي)"
        self.lbl_ext_info.setText(
            f"<b>الامتداد الظاهر:</b> {report.extension or 'بدون امتداد'}<br>"
            f"<b>كشف الامتداد المزدوج:</b> {double_txt}<br>"
            f"<b>اسم الملف الكامل:</b> {report.filename}"
        )

        # Origin / MOTW
        motw_txt = "<font color='#FBBF24'>تم تنزيله من الإنترنت (Zone 3 - Internet)</font>" if report.is_downloaded_from_internet else "ملف محلي (لا يوجد وسم إنترنت)"
        streams_count = len(report.alternate_data_streams)
        self.lbl_origin_info.setText(
            f"<b>وسام الويب (MOTW):</b> {motw_txt}<br>"
            f"<b>تدفقات NTFS البديلة (ADS):</b> {streams_count} تدفق(ات) مكتشفة"
        )

        # Signature
        sig_color = "#34D399" if report.signature_status.value == "VALID" else ("#8B949E" if report.signature_status.value == "UNSIGNED" else "#F87171")
        signer_info = f"<br><b>الجهة الموقعة:</b> {report.signature_publisher}" if report.signature_publisher else ""
        self.lbl_sig_info.setText(
            f"<b>حالة التوقيع الرقمي:</b> <font color='{sig_color}'><b>{report.signature_status.value}</b></font>"
            f"{signer_info}"
        )

        # Hashes
        self.txt_sha256.setText(report.sha256)
        self.txt_sha512.setText(report.sha512)

        # Recommendations
        if report.recommendations:
            rec_html = "<br>".join([f"• {r}" for r in report.recommendations])
            self.lbl_recommendations.setText(rec_html)
        else:
            self.lbl_recommendations.setText("• لم يتم رصد أي مؤشرات خطورة استاتيكية على هذا الملف.")

    def _run_defender_scan(self):
        if not self._current_file or not os.path.exists(self._current_file):
            return

        self.btn_defender_scan.setEnabled(False)
        self.scan_progress.setVisible(True)
        self.btn_defender_scan.setText("جاري فحص Defender...")

        self._scan_worker = DefenderScanWorker(self._current_file)
        self._scan_worker.finished_scan.connect(self._on_defender_finished)
        self._scan_worker.start()

    def _on_defender_finished(self, clean: bool, message: str):
        self.scan_progress.setVisible(False)
        self.btn_defender_scan.setEnabled(True)
        self.btn_defender_scan.setText(" فحص عبر Microsoft Defender")

        if clean:
            QMessageBox.information(self, "نتيجة فحص Microsoft Defender", f"نتيجة الفحص:\n{message}")
        else:
            QMessageBox.critical(self, "تنبيه من Microsoft Defender", f"تم اكتشاف مشكلة أو تهديد بواسطة Defender:\n{message}")

    def _copy_to_clipboard(self, text: str):
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
