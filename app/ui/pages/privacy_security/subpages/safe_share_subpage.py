# -*- coding: utf-8 -*-
"""
Safe Share Studio Subpage (المشاركة الآمنة) for SINAX Privacy & Security Center.
Orchestrates the flagship 7-stage automated privacy pipeline:
"جهّز هذا الملف للمشاركة بأمان"
1. Creates isolated working copy (Original is NEVER modified)
2. Inspects privacy metadata
3. Scans for sensitive credentials (API tokens, emails, keys)
4. Applies chosen privacy preset sanitization
5. Executes Microsoft Defender scan
6. Generates SHA-256 integrity digest
7. Verifies final output file before distribution
"""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import format_bytes
from app.services.privacy_security.models import PrivacyPreset
from app.services.privacy_security.safe_share_service import SafeShareResult, SafeShareService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class SafeSharePipelineWorker(QThread):
    """Background worker executing the 7-stage Safe Share pipeline."""
    stage_progress = Signal(float, str)
    pipeline_finished = Signal(bool, object)

    def __init__(self, file_path: str, preset: PrivacyPreset):
        super().__init__()
        self.file_path = file_path
        self.preset = preset
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        service = SafeShareService()
        ok, result = service.process_safe_share(
            self.file_path,
            preset=self.preset,
            progress_cb=lambda p, msg: self.stage_progress.emit(p, msg),
            cancel_check=lambda: self._cancelled,
        )
        self.pipeline_finished.emit(ok, result)


class SafeShareSubpage(QWidget):
    """Safe Share Studio subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._current_file: Optional[str] = None
        self._result: Optional[SafeShareResult] = None
        self._worker: Optional[SafeSharePipelineWorker] = None
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
        t_lbl = QLabel("استوديو المشاركة الآمنة (Safe Share Studio)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("خط أنابيب متكامل من 7 مراحل لتجهيز وتطهير وتأمين الملفات قبل إرسالها أو نشرها على الإنترنت.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        header_row.addWidget(ToolBadgeWidget.modifies_files(self))
        layout.addLayout(header_row)

        # 2. Main Action Card (Flagship Button & Inputs)
        action_card = QFrame()
        action_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #161B22, stop:1 #1A2230);
                border: 1px solid #38BDF8;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        ac_layout = QVBoxLayout(action_card)
        ac_layout.setSpacing(14)

        # File row
        f_row = QHBoxLayout()
        lbl_target = QLabel("الملف المراد تجهيزه:")
        lbl_target.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px; width: 140px;")
        f_row.addWidget(lbl_target)

        self.txt_file_path = QLineEdit()
        self.txt_file_path.setPlaceholderText("اختر أي ملف أو مستند أو صورة لتجهيزها...")
        self.txt_file_path.setStyleSheet("""
            QLineEdit {
                background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px; font-size: 12px;
            }
        """)
        f_row.addWidget(self.txt_file_path, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background-color: #30363D; }
        """)
        btn_browse.clicked.connect(self._on_browse_file)
        f_row.addWidget(btn_browse)
        ac_layout.addLayout(f_row)

        # Preset row
        p_row = QHBoxLayout()
        lbl_preset = QLabel("قالب المشاركة (Preset):")
        lbl_preset.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px; width: 140px;")
        p_row.addWidget(lbl_preset)

        self.cmb_preset = QComboBox()
        self.cmb_preset.addItem("شبكات التواصل والويب (Social Media) - إزالة GPS والموقع وموديل الكاميرا", PrivacyPreset.SOCIAL.value)
        self.cmb_preset.addItem("مستندات عامة وأعمال (Work Document) - إزالة المؤلف والتعليقات وتاريخ التعديل", PrivacyPreset.WORK_DOC.value)
        self.cmb_preset.addItem("ملفات PDF عامة (Public PDF) - إزالة المرفقات والبيانات الوصفية", PrivacyPreset.PUBLIC_PDF.value)
        self.cmb_preset.addItem("أكواد ومشاريع برمجية (Code Project) - فحص وتعتيم المفاتيح وحماية التوكنات", PrivacyPreset.CODE_PROJECT.value)
        self.cmb_preset.addItem("ملف دعم فني وتشخيص (Tech Support) - حجب المسارات وأسماء المستخدمين والـ IP", PrivacyPreset.TECH_SUPPORT.value)
        self.cmb_preset.setStyleSheet("""
            QComboBox {
                background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px; font-size: 12px;
            }
        """)
        p_row.addWidget(self.cmb_preset, 1)
        ac_layout.addLayout(p_row)

        # The Grand Process Button
        self.btn_run_pipeline = QPushButton(" جهّز هذا الملف للمشاركة بأمان")
        self.btn_run_pipeline.setIcon(get_icon("share", color="#0D1117"))
        self.btn_run_pipeline.setStyleSheet("""
            QPushButton {
                background-color: #38BDF8;
                color: #0D1117;
                border: none;
                border-radius: 8px;
                padding: 12px 28px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7DD3FC;
            }
        """)
        self.btn_run_pipeline.clicked.connect(self._start_pipeline)
        ac_layout.addWidget(self.btn_run_pipeline)

        layout.addWidget(action_card)

        # 3. Seven Stages Visual Pipeline Cards
        pipe_card = QFrame()
        pipe_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        pc_layout = QVBoxLayout(pipe_card)
        pc_layout.setSpacing(10)

        pc_title = QLabel("خطوات الأمان التلقائية الـ 7:")
        pc_title.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 13px;")
        pc_layout.addWidget(pc_title)

        # 7-stage indicators
        self.stage_labels = []
        stages = [
            "1. إنشاء نسخة عمل مؤقتة معزولة (عدم لمس الملف الأصلي)",
            "2. فحص عميق للميتاداتا وبيانات الموقع الجغرافي (GPS)",
            "3. كاشف البيانات الحساسة (PII, مفاتيح API, الرموز السرية)",
            "4. تطبيق التطهير الرقمي المعتمد وإزالة الميتاداتا",
            "5. فحص الملف الناتج عبر Microsoft Defender للتأكد من خلوه من التهديدات",
            "6. توليد بصمة التجزئة الرقمية SHA-256 للمصادقة",
            "7. التحقق الذاتي من سلامة الملف الناتج وجهوزيته للمشاركة",
        ]

        for s in stages:
            lbl = QLabel(f"⚪ {s}")
            lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
            self.stage_labels.append(lbl)
            pc_layout.addWidget(lbl)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #0D1117; border: none; border-radius: 4px; }
            QProgressBar::chunk { background-color: #38BDF8; border-radius: 4px; }
        """)
        pc_layout.addWidget(self.progress_bar)

        layout.addWidget(pipe_card)

        # 4. Result Card (Initially Hidden)
        self.result_card = QFrame()
        self.result_card.setVisible(False)
        self.result_card.setStyleSheet("background-color: #132E22; border: 1px solid #34D399; border-radius: 10px; padding: 16px;")
        rc_vbox = QVBoxLayout(self.result_card)
        rc_vbox.setSpacing(10)

        rc_head = QHBoxLayout()
        rc_icon = QLabel()
        rc_icon.setPixmap(get_icon("shield", color="#34D399", size=28).pixmap(28, 28))
        rc_head.addWidget(rc_icon)

        self.lbl_rc_title = QLabel("الملف جاهز ومحمي للمشاركة بأمان!")
        self.lbl_rc_title.setStyleSheet("color: #34D399; font-size: 16px; font-weight: bold;")
        rc_head.addWidget(self.lbl_rc_title)
        rc_head.addStretch(1)

        btn_open_folder = QPushButton(" فتح المجلد الحاوي")
        btn_open_folder.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_open_folder.setStyleSheet("""
            QPushButton {
                background: #238636; color: #FFFFFF; border-radius: 4px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #2EA043; }
        """)
        btn_open_folder.clicked.connect(self._open_result_folder)
        rc_head.addWidget(btn_open_folder)
        rc_vbox.addLayout(rc_head)

        self.lbl_rc_details = QLabel("")
        self.lbl_rc_details.setWordWrap(True)
        self.lbl_rc_details.setStyleSheet("color: #F0F6FC; font-size: 12px; line-height: 1.6;")
        rc_vbox.addWidget(self.lbl_rc_details)

        # SHA-256 copy box
        sha_box = QHBoxLayout()
        lbl_sha_t = QLabel("بصمة SHA-256 للمشاركة:")
        lbl_sha_t.setStyleSheet("color: #8B949E; font-weight: bold;")
        sha_box.addWidget(lbl_sha_t)

        self.txt_sha = QLineEdit()
        self.txt_sha.setReadOnly(True)
        self.txt_sha.setStyleSheet("background: #0D1117; color: #58A6FF; border: 1px solid #30363D; border-radius: 4px; padding: 4px 8px; font-family: Consolas, monospace;")
        sha_box.addWidget(self.txt_sha, 1)

        btn_copy_sha = QPushButton("نسخ الهاش")
        btn_copy_sha.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 4px 10px;")
        btn_copy_sha.clicked.connect(lambda: self._copy_to_clipboard(self.txt_sha.text()))
        sha_box.addWidget(btn_copy_sha)
        rc_vbox.addLayout(sha_box)

        layout.addWidget(self.result_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _on_browse_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً لتجهيزه للمشاركة", "", "كافة الملفات (*.*)")
        if f:
            self.txt_file_path.setText(f)
            self._current_file = f
            self.result_card.setVisible(False)
            self._reset_stage_labels()

    def _reset_stage_labels(self):
        for idx, lbl in enumerate(self.stage_labels):
            t = lbl.text().replace("🟢 ", "").replace("🔵 ", "").replace("⚪ ", "")
            lbl.setText(f"⚪ {t}")
            lbl.setStyleSheet("color: #8B949E; font-size: 12px;")

    def _start_pipeline(self):
        target = self.txt_file_path.text().strip()
        if not target or not os.path.isfile(target):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف موجود صالح أولاً.")
            return

        preset_str = self.cmb_preset.currentData()
        preset_enum = PrivacyPreset(preset_str)

        self.btn_run_pipeline.setEnabled(False)
        self.btn_run_pipeline.setText("جاري تجهيز وتطهير الملف...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_card.setVisible(False)
        self._reset_stage_labels()

        self._worker = SafeSharePipelineWorker(target, preset_enum)
        self._worker.stage_progress.connect(self._on_stage_progress)
        self._worker.pipeline_finished.connect(self._on_pipeline_finished)
        self._worker.start()

    def _on_stage_progress(self, pct: float, msg: str):
        self.progress_bar.setValue(int(pct * 100))

        # Highlight current stage
        stage_idx = min(int(pct * 7), 6)
        for i in range(len(self.stage_labels)):
            t = self.stage_labels[i].text().replace("🟢 ", "").replace("🔵 ", "").replace("⚪ ", "")
            if i < stage_idx:
                self.stage_labels[i].setText(f"🟢 {t}")
                self.stage_labels[i].setStyleSheet("color: #34D399; font-size: 12px; font-weight: bold;")
            elif i == stage_idx:
                self.stage_labels[i].setText(f"🔵 {t}")
                self.stage_labels[i].setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: bold;")
            else:
                self.stage_labels[i].setText(f"⚪ {t}")
                self.stage_labels[i].setStyleSheet("color: #8B949E; font-size: 12px;")

    def _on_pipeline_finished(self, ok: bool, result: SafeShareResult):
        self.progress_bar.setVisible(False)
        self.btn_run_pipeline.setEnabled(True)
        self.btn_run_pipeline.setText(" جهّز هذا الملف للمشاركة بأمان")

        if not ok or not result.is_verified:
            QMessageBox.critical(self, "فشل التجهيز", f"حدث خطأ أثناء تجهيز الملف:\n{result.summary_message}")
            return

        self._result = result

        # Mark all stages green
        for i in range(len(self.stage_labels)):
            t = self.stage_labels[i].text().replace("🟢 ", "").replace("🔵 ", "").replace("⚪ ", "")
            self.stage_labels[i].setText(f"🟢 {t}")
            self.stage_labels[i].setStyleSheet("color: #34D399; font-size: 12px; font-weight: bold;")

        self.result_card.setVisible(True)
        out_p = Path(result.output_path)
        meta_count = len(result.metadata_removed)
        sens_count = result.sensitive_items_found

        sens_text = f"تم كشف {sens_count} عنصر حساس وتعتيمه" if sens_count > 0 else "خالٍ من الأسرار والبيانات الحساسة"
        details_html = (
            f"<b>الملف الآمن الجاهز:</b> <code>{out_p.name}</code> ({format_bytes(out_p.stat().st_size)})<br>"
            f"<b>البيانات الوصفية المطهرة:</b> {meta_count} عنصر ميتاداتا محذوف<br>"
            f"<b>كاشف البيانات الحساسة:</b> {sens_text}<br>"
            f"<b>فحص Microsoft Defender:</b> <font color='#34D399'><b>{result.defender_status}</b></font><br>"
            f"<b>استغرق التجهيز:</b> {result.duration_seconds:.2f} ثانية"
        )
        self.lbl_rc_details.setText(details_html)
        self.txt_sha.setText(result.sha256_hash)

        QMessageBox.information(
            self,
            "اكتملت المشاركة الآمنة",
            f"تم تجهيز الملف للمشاركة بأمان تام!\n\nالملف الناتج:\n{result.output_path}"
        )

    def _open_result_folder(self):
        if self._result and os.path.exists(self._result.output_path):
            folder = os.path.dirname(self._result.output_path)
            os.startfile(folder)

    def _copy_to_clipboard(self, text: str):
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
