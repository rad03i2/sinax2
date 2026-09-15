# -*- coding: utf-8 -*-
"""
SINAX 7-Step Backup Wizard Subpage (معالج إنشاء خطة النسخ الاحتياطي).
Guided step-by-step workflow:
1. What to protect (Known Folders presets + Custom paths)
2. Where to save (Destination selection + Physical Disk check + FAT32 check)
3. Backup Mode (Full vs Incremental)
4. Schedule (Manual, Daily, On Connect)
5. Retention (Keep N, Keep Days, Never destroy last good)
6. Plan Review & Preflight
7. Execution
"""

import os
from pathlib import Path
import time
from typing import List
import uuid

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from app.services.backup_sync.backup_coordinator import BackupCoordinator
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.device_identity_service import DeviceIdentityService
from app.services.backup_sync.known_folders_service import KnownFoldersService
from app.services.backup_sync.models import (
    BackupProfile,
    BackupType,
    IncrementalMode,
    RetentionPolicy,
    VerificationLevel,
)
from app.services.backup_sync.physical_disk_service import PhysicalDiskService
from app.ui.icons import get_icon
from app.ui.pages.backup_sync.dialogs.backup_progress_dialog import BackupProgressDialog


class WizardSubpage(QWidget):
    """Step-by-step backup plan configuration wizard."""

    backup_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.db = BackupDatabase()
        self.current_step = 0
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Step Indicator Header
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        h_lay = QHBoxLayout(self.header_frame)
        self.lbl_step_title = QLabel("الخطوة 1 من 6: ماذا تريد حمايته؟")
        self.lbl_step_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #F0F6FC;")
        h_lay.addWidget(self.lbl_step_title)
        h_lay.addStretch(1)
        main_layout.addWidget(self.header_frame)

        # Wizard Steps Stack
        self.stack = QStackedWidget()

        # Step 1: What to protect
        self.step1_widget = self._create_step1()
        self.stack.addWidget(self.step1_widget)

        # Step 2: Destination
        self.step2_widget = self._create_step2()
        self.stack.addWidget(self.step2_widget)

        # Step 3: Mode & Verification
        self.step3_widget = self._create_step3()
        self.stack.addWidget(self.step3_widget)

        # Step 4: Schedule
        self.step4_widget = self._create_step4()
        self.stack.addWidget(self.step4_widget)

        # Step 5: Retention
        self.step5_widget = self._create_step5()
        self.stack.addWidget(self.step5_widget)

        # Step 6: Review & Launch
        self.step6_widget = self._create_step6()
        self.stack.addWidget(self.step6_widget)

        main_layout.addWidget(self.stack, 1)

        # Bottom Navigation Buttons
        nav_row = QHBoxLayout()
        self.btn_prev = QPushButton("السابق")
        self.btn_prev.setEnabled(False)
        self.btn_prev.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 20px; border-radius: 6px;")
        self.btn_prev.clicked.connect(self._prev_step)
        nav_row.addWidget(self.btn_prev)

        nav_row.addStretch(1)

        self.btn_next = QPushButton("التالي")
        self.btn_next.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 24px; border-radius: 6px;")
        self.btn_next.clicked.connect(self._next_step)
        nav_row.addWidget(self.btn_next)

        main_layout.addLayout(nav_row)

    def _create_step1(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        info = QLabel("حدد المجلدات التي ترغب في تضمينها في خطة النسخ الاحتياطي:")
        info.setStyleSheet("font-size: 13px; color: #C9D1D9;")
        lay.addWidget(info)

        self.cb_desktop = QCheckBox("سطح المكتب (Desktop)")
        self.cb_desktop.setChecked(True)
        self.cb_docs = QCheckBox("المستندات (Documents)")
        self.cb_docs.setChecked(True)
        self.cb_pics = QCheckBox("الصور (Pictures)")
        self.cb_pics.setChecked(True)
        self.cb_videos = QCheckBox("الفيديوهات (Videos)")
        self.cb_music = QCheckBox("الموسيقى (Music)")
        self.cb_downloads = QCheckBox("التنزيلات (Downloads)")

        for cb in (self.cb_desktop, self.cb_docs, self.cb_pics, self.cb_videos, self.cb_music, self.cb_downloads):
            cb.setStyleSheet("font-size: 13px; color: #F0F6FC; padding: 4px 0;")
            lay.addWidget(cb)

        # Custom Folder Row
        custom_row = QHBoxLayout()
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("أو اختر مجلداً مخصصاً (مثل D:\\University)...")
        self.txt_custom.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; color: #F0F6FC; padding: 8px; border-radius: 6px;")
        custom_row.addWidget(self.txt_custom, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 14px; border-radius: 6px;")
        btn_browse.clicked.connect(self._browse_custom_source)
        custom_row.addWidget(btn_browse)
        lay.addLayout(custom_row)

        lay.addStretch(1)
        return w

    def _create_step2(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        info = QLabel("حدد مكان حفظ النسخة الاحتياطية (قرص خارجي، USB، أو مجلد آخر):")
        info.setStyleSheet("font-size: 13px; color: #C9D1D9;")
        lay.addWidget(info)

        row = QHBoxLayout()
        self.txt_dest = QLineEdit()
        self.txt_dest.setPlaceholderText("مسار مجلد النسخة الاحتياطية (مثال: D:\\SINAX_Backup)...")
        self.txt_dest.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; color: #F0F6FC; padding: 8px; border-radius: 6px;")
        row.addWidget(self.txt_dest, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setStyleSheet("background-color: #21262D; color: #F0F6FC; border: 1px solid #30363D; padding: 8px 14px; border-radius: 6px;")
        btn_browse.clicked.connect(self._browse_dest)
        row.addWidget(btn_browse)
        lay.addLayout(row)

        self.lbl_dest_warn = QLabel("")
        self.lbl_dest_warn.setWordWrap(True)
        self.lbl_dest_warn.setStyleSheet("color: #FBBF24; font-weight: bold; font-size: 12px; padding: 4px 0;")
        lay.addWidget(self.lbl_dest_warn)

        # Eject option
        self.cb_eject = QCheckBox("إخراج القرص بأمان تلقائياً بعد نجاح النسخ والتحقق")
        self.cb_eject.setStyleSheet("color: #C9D1D9; font-size: 12px;")
        lay.addWidget(self.cb_eject)

        lay.addStretch(1)
        return w

    def _create_step3(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lay.addWidget(QLabel("نوع النسخ الاحتياطي:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["نسخ تراكمي ذكي (Incremental - موصى به)", "نسخ كامل (Full Backup)"])
        self.combo_type.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; color: #F0F6FC; padding: 8px; border-radius: 6px;")
        lay.addWidget(self.combo_type)

        lay.addWidget(QLabel("مستوى التحقق من سلامة البيانات (Verification):"))
        self.combo_verify = QComboBox()
        self.combo_verify.addItems(["متوازن (Balanced - فحص وجود + حجم + عينات هاش)", "شامل وفوري (Full SHA-256 لجميع الملفات)", "أساسي (Basic - الحجم والوجود)"])
        self.combo_verify.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; color: #F0F6FC; padding: 8px; border-radius: 6px;")
        lay.addWidget(self.combo_verify)

        lay.addStretch(1)
        return w

    def _create_step4(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lay.addWidget(QLabel("متى ترغب في تشغيل النسخ؟"))
        self.combo_schedule = QComboBox()
        self.combo_schedule.addItems(["يدوياً عند الطلب (Manual)", "يومياً في وقت محدد", "أسبوعياً (كل جمعة)", "تلقائياً عند توصيل القرص الموثوق (Backup on Connect)"])
        self.combo_schedule.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; color: #F0F6FC; padding: 8px; border-radius: 6px;")
        lay.addWidget(self.combo_schedule)

        row_t = QHBoxLayout()
        row_t.addWidget(QLabel("توقيت التشغيل اليومي:"))
        self.txt_time = QLineEdit("02:00")
        self.txt_time.setFixedWidth(80)
        self.txt_time.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; color: #F0F6FC; padding: 6px; border-radius: 6px;")
        row_t.addWidget(self.txt_time)
        row_t.addStretch(1)
        lay.addLayout(row_t)

        lay.addStretch(1)
        return w

    def _create_step5(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        lay.addWidget(QLabel("سياسة الاحتفاظ بالإصدارات السابقة (Retention Policy):"))
        self.cb_ret_all = QCheckBox("الاحتفاظ بجميع الإصدارات السابقة دائماً")
        self.cb_ret_all.setStyleSheet("color: #F0F6FC; font-size: 13px;")
        lay.addWidget(self.cb_ret_all)

        row_n = QHBoxLayout()
        row_n.addWidget(QLabel("أو الاحتفاظ بآخر:"))
        self.spin_keep_n = QSpinBox()
        self.spin_keep_n.setRange(1, 100)
        self.spin_keep_n.setValue(10)
        self.spin_keep_n.setStyleSheet("background-color: #161B22; color: white; padding: 4px;")
        row_n.addWidget(self.spin_keep_n)
        row_n.addWidget(QLabel("إصدارات للملف"))
        row_n.addStretch(1)
        lay.addLayout(row_n)

        note = QLabel("✓ قاعدة الأمان الذهبية: لن يقوم SINAX أبداً بحذف آخر نسخة صالحة مهما كانت السياسة.")
        note.setStyleSheet("color: #34D399; font-size: 12px; font-weight: bold; margin-top: 10px;")
        lay.addWidget(note)

        lay.addStretch(1)
        return w

    def _create_step6(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(14)

        lay.addWidget(QLabel("مراجعة وتأكيد خطة النسخ الاحتياطي:"))
        self.lbl_review = QLabel("")
        self.lbl_review.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 14px; font-size: 13px; line-height: 1.6;")
        lay.addWidget(self.lbl_review)

        lay.addStretch(1)
        return w

    def _browse_custom_source(self):
        d = QFileDialog.getExistingDirectory(self, "اختر مجلداً مخصصاً")
        if d:
            self.txt_custom.setText(d)

    def _browse_dest(self):
        d = QFileDialog.getExistingDirectory(self, "اختر وجهة النسخ الاحتياطي")
        if d:
            self.txt_dest.setText(d)
            self._check_dest_warnings(d)

    def _check_dest_warnings(self, dest_path: str):
        sources = self._get_selected_sources()
        if sources:
            is_same, disk_num = PhysicalDiskService.is_same_physical_disk(sources[0], dest_path)
            if is_same:
                disk_label = f"Disk #{disk_num}" if disk_num is not None else "نفس القرص"
                self.lbl_dest_warn.setText(
                    f"⚠ تحذير: المصدر والوجهة يقعان على نفس القرص الفيزيائي ({disk_label}). "
                    f"تعطل القرص قد يؤدي لفقدان الأصل والنسخة معاً."
                )
            else:
                self.lbl_dest_warn.setText("✓ الوجهة تقع على قرص فيزيائي مستقل سليم.")

    def _get_selected_sources(self) -> List[str]:
        known = KnownFoldersService.get_known_folders(calculate_sizes=False)
        k_map = {k.key: k.path for k in known}
        res = []
        if self.cb_desktop.isChecked() and "desktop" in k_map:
            res.append(k_map["desktop"])
        if self.cb_docs.isChecked() and "documents" in k_map:
            res.append(k_map["documents"])
        if self.cb_pics.isChecked() and "pictures" in k_map:
            res.append(k_map["pictures"])
        if self.cb_videos.isChecked() and "videos" in k_map:
            res.append(k_map["videos"])
        if self.cb_music.isChecked() and "music" in k_map:
            res.append(k_map["music"])
        if self.cb_downloads.isChecked() and "downloads" in k_map:
            res.append(k_map["downloads"])
        if self.txt_custom.text().strip() and os.path.exists(self.txt_custom.text().strip()):
            res.append(self.txt_custom.text().strip())
        return res

    def _next_step(self):
        if self.current_step == 0:
            sources = self._get_selected_sources()
            if not sources:
                QMessageBox.warning(self, "تنبيه", "يرجى تحديد مجلد واحد على الأقل للنسخ.")
                return
        elif self.current_step == 1:
            dest = self.txt_dest.text().strip()
            if not dest:
                QMessageBox.warning(self, "تنبيه", "يرجى تحديد مسار وجهة النسخ الاحتياطي.")
                return

        if self.current_step == 4:
            # Entering Review step
            self._update_review_text()

        if self.current_step == 5:
            # Final step -> Run Backup!
            self._launch_backup_job()
            return

        self.current_step += 1
        self.stack.setCurrentIndex(self.current_step)
        self._update_nav()

    def _prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stack.setCurrentIndex(self.current_step)
            self._update_nav()

    def _update_nav(self):
        step_titles = [
            "الخطوة 1 من 6: ماذا تريد حمايته؟",
            "الخطوة 2 من 6: أين تريد حفظ النسخة؟",
            "الخطوة 3 من 6: كيف تريد النسخ والتحقق؟",
            "الخطوة 4 من 6: متى ترغب في تشغيل النسخ؟",
            "الخطوة 5 من 6: الاحتفاظ بالإصدارات السابقة",
            "الخطوة 6 من 6: مراجعة الخطة والبدء",
        ]
        self.lbl_step_title.setText(step_titles[self.current_step])
        self.btn_prev.setEnabled(self.current_step > 0)
        if self.current_step == 5:
            self.btn_next.setText("بدء النسخ الاحتياطي الآن")
            self.btn_next.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 24px; border-radius: 6px;")
        else:
            self.btn_next.setText("التالي")
            self.btn_next.setStyleSheet("background-color: #238636; color: white; font-weight: bold; padding: 8px 24px; border-radius: 6px;")

    def _update_review_text(self):
        sources = self._get_selected_sources()
        dest = self.txt_dest.text().strip()
        b_type = "تراكمي (Incremental)" if "تراكمي" in self.combo_type.currentText() else "كامل (Full)"
        v_level = self.combo_verify.currentText()
        sched = self.combo_schedule.currentText()
        ret = "الاحتفاظ بكل الإصدارات" if self.cb_ret_all.isChecked() else f"الاحتفاظ بآخر {self.spin_keep_n.value()} إصدارات"

        text = (
            f"<b>المجلدات المصدرية ({len(sources)}):</b><br>• " + "<br>• ".join(sources) + "<br><br>"
            f"<b>الوجهة:</b> {dest}<br>"
            f"<b>نوع النسخ:</b> {b_type}<br>"
            f"<b>مستوى التحقق:</b> {v_level}<br>"
            f"<b>الجدولة:</b> {sched}<br>"
            f"<b>سياسة الإصدارات:</b> {ret}<br>"
            f"<b>إخراج القرص تلقائياً:</b> {'نعم' if self.cb_eject.isChecked() else 'لا'}"
        )
        self.lbl_review.setText(text)

    def _launch_backup_job(self):
        sources = self._get_selected_sources()
        dest = self.txt_dest.text().strip()

        profile = BackupProfile(
            id=f"prof_{str(uuid.uuid4())[:8]}",
            name="خطة النسخ الاحتياطي",
            sources=sources,
            destination=dest,
            backup_type=BackupType.INCREMENTAL if "تراكمي" in self.combo_type.currentText() else BackupType.FULL,
            incremental_mode=IncrementalMode.FAST,
            verification_level=VerificationLevel.BALANCED,
            retention=RetentionPolicy(
                keep_all=self.cb_ret_all.isChecked(),
                keep_last_n=self.spin_keep_n.value()
            ),
            eject_after_backup=self.cb_eject.isChecked()
        )
        self.db.save_profile(profile)

        # Launch progress dialog
        dlg = BackupProgressDialog(parent=self)
        coord = BackupCoordinator(self.db)

        import threading
        from PySide6.QtCore import QTimer

        is_cancelled = [False]
        dlg.cancel_requested.connect(lambda: is_cancelled.insert(0, True))

        def _worker():
            def _prog(stage, done, total, detail):
                QTimer.singleShot(0, lambda: dlg.update_progress(stage, done, total, detail))

            job = coord.run_backup(profile, progress_cb=_prog, cancel_check=lambda: is_cancelled[0])
            def _done():
                dlg.btn_cancel.setText("إغلاق")
                self.backup_finished.emit()
            QTimer.singleShot(0, _done)

        threading.Thread(target=_worker, daemon=True).start()
        dlg.exec()
