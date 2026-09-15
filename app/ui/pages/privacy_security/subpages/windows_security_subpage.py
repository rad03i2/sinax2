# -*- coding: utf-8 -*-
"""
Windows Security Subpage (حماية Windows والسمعة الرقمية) for SINAX Privacy & Security Center.
Features:
1. Live Windows Security Posture:
   - Microsoft Defender status
   - Real-time protection status
   - Windows Firewall profile status
   - SmartScreen download protection
   - Controlled Folder Access (Ransomware protection)
   - BitLocker drive encryption
2. Actions:
   - Security definitions update (update_signatures) in background
   - Direct shortcuts to native Windows Security panels
3. Online Reputation by Hash:
   - SHA-256 only transmission (never uploads files)
   - Encrypted API key storage via Windows DPAPI
   - Explicit confirmation before network query
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
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

from app.services.privacy_security.defender_service import DefenderService
from app.services.privacy_security.reputation_service import ReputationService
from app.services.privacy_security.windows_security_service import WindowsSecurityService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class UpdateSignaturesWorker(QThread):
    """Background worker for updating Windows Defender signatures."""
    finished = Signal(bool, str)

    def run(self):
        service = DefenderService()
        ok, msg = service.update_signatures()
        self.finished.emit(ok, msg)


class ReputationCheckWorker(QThread):
    """Background worker for checking online reputation via hash."""
    finished = Signal(bool, str, dict)

    def __init__(self, sha256_hash: str):
        super().__init__()
        self.sha256_hash = sha256_hash

    def run(self):
        service = ReputationService()
        ok, msg, data = service.check_hash_reputation(self.sha256_hash)
        self.finished.emit(ok, msg, data)


class TelemetryFetchWorker(QThread):
    """Background worker for querying live Windows security posture without UI freeze."""
    finished = Signal(dict)

    def run(self):
        service = WindowsSecurityService()
        data = service.get_security_overview(force_refresh=True)
        self.finished.emit(data)


class WindowsSecuritySubpage(QWidget):
    """Windows Security Center & Digital Reputation Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._win_service = WindowsSecurityService()
        self._defender_service = DefenderService()
        self._rep_service = ReputationService()
        self._update_worker: Optional[UpdateSignaturesWorker] = None
        self._rep_worker: Optional[ReputationCheckWorker] = None
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
        t_lbl = QLabel("حماية وأمان Windows المتقدم (Windows Security Center)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("استعراض الحالة الحية لعناصر الأمان الأصلية وتحديث التواقيع وفحص السمعة الرقمية للهاش بأمان.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        header_row.addWidget(ToolBadgeWidget.requires_admin(self))
        layout.addLayout(header_row)

        # 2. Windows Security Posture Grid
        grid_card = QFrame()
        grid_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        gc_vbox = QVBoxLayout(grid_card)
        gc_vbox.setSpacing(12)

        gc_head = QHBoxLayout()
        gc_icon = QLabel()
        gc_icon.setPixmap(get_icon("security", color="#38BDF8", size=22).pixmap(22, 22))
        gc_head.addWidget(gc_icon)

        gc_t = QLabel("حالة حماية النظام (Windows Native Security Posture)")
        gc_t.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        gc_head.addWidget(gc_t)
        gc_head.addStretch(1)

        btn_refresh = QPushButton("تحديث البيانات الحية")
        btn_refresh.setIcon(get_icon("refresh", color="#8B949E"))
        btn_refresh.setStyleSheet("background: #21262D; color: #8B949E; border: 1px solid #30363D; border-radius: 4px; padding: 4px 10px; font-size: 11px;")
        btn_refresh.clicked.connect(self._refresh_security_posture)
        gc_head.addWidget(btn_refresh)
        gc_vbox.addLayout(gc_head)

        grid = QGridLayout()
        grid.setSpacing(12)

        self.card_def = self._make_telemetry_item("مضاد الفيروسات Defender", "shield")
        self.card_rtp = self._make_telemetry_item("الحماية في الوقت الفعلي", "security")
        self.card_fw = self._make_telemetry_item("جدار الحماية (Firewall)", "firewall")
        self.card_cfa = self._make_telemetry_item("الحماية من برامج الفدية (CFA)", "lock")
        self.card_ss = self._make_telemetry_item("حماية التنزيل (SmartScreen)", "globe")
        self.card_bde = self._make_telemetry_item("تشفير الأقراص (BitLocker)", "vault")

        grid.addWidget(self.card_def, 0, 0)
        grid.addWidget(self.card_rtp, 0, 1)
        grid.addWidget(self.card_fw, 0, 2)
        grid.addWidget(self.card_cfa, 1, 0)
        grid.addWidget(self.card_ss, 1, 1)
        grid.addWidget(self.card_bde, 1, 2)

        gc_vbox.addLayout(grid)

        # Action Buttons Row
        acts_row = QHBoxLayout()
        self.btn_update_sig = QPushButton(" تحديث تواقيع أمان Defender")
        self.btn_update_sig.setIcon(get_icon("download", color="#FFFFFF"))
        self.btn_update_sig.setStyleSheet("""
            QPushButton {
                background-color: #238636; color: #FFFFFF; border-radius: 6px;
                padding: 8px 16px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background-color: #2EA043; }
        """)
        self.btn_update_sig.clicked.connect(self._trigger_update_signatures)
        acts_row.addWidget(self.btn_update_sig)

        btn_open_win_sec = QPushButton(" فتح تطبيق أمان Windows")
        btn_open_win_sec.setIcon(get_icon("external_link", color="#38BDF8"))
        btn_open_win_sec.setStyleSheet("""
            QPushButton {
                background: #1E293B; color: #38BDF8; border: 1px solid #38BDF8;
                border-radius: 6px; padding: 8px 16px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background: #38BDF8; color: #0D1117; }
        """)
        btn_open_win_sec.clicked.connect(self._defender_service.open_windows_security)
        acts_row.addWidget(btn_open_win_sec)

        btn_cfa = QPushButton(" إعدادات الحماية من برامج الفدية")
        btn_cfa.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px 14px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background: #30363D; }
        """)
        btn_cfa.clicked.connect(self._defender_service.open_ransomware_settings)
        acts_row.addWidget(btn_cfa)
        acts_row.addStretch(1)

        gc_vbox.addLayout(acts_row)

        self.update_progress = QProgressBar()
        self.update_progress.setRange(0, 0)
        self.update_progress.setFixedHeight(4)
        self.update_progress.setVisible(False)
        self.update_progress.setStyleSheet("QProgressBar { background-color: #0D1117; border: none; } QProgressBar::chunk { background-color: #38BDF8; }")
        gc_vbox.addWidget(self.update_progress)

        layout.addWidget(grid_card)

        # 3. Online File Reputation by Hash Card
        rep_card = QFrame()
        rep_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        rc_vbox = QVBoxLayout(rep_card)
        rc_vbox.setSpacing(12)

        rc_head = QHBoxLayout()
        rc_icon = QLabel()
        rc_icon.setPixmap(get_icon("globe", color="#38BDF8", size=22).pixmap(22, 22))
        rc_head.addWidget(rc_icon)

        rc_t = QLabel("فحص السمعة الرقمية عبر الهاش (Hash-Only Reputation)")
        rc_t.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        rc_head.addWidget(rc_t)

        rc_head.addWidget(ToolBadgeWidget.online(self))
        rc_head.addStretch(1)

        btn_api_key = QPushButton(" إعداد مفتاح API")
        btn_api_key.setStyleSheet("background: #21262D; color: #8B949E; border: 1px solid #30363D; border-radius: 4px; padding: 4px 10px; font-size: 11px;")
        btn_api_key.clicked.connect(self._configure_api_key)
        rc_head.addWidget(btn_api_key)
        rc_vbox.addLayout(rc_head)

        rc_desc = QLabel(
            "تلتزم SINAX بأعلى معايير الخصوصية: <b>لا يتم رفع أي ملف إلى الإنترنت إطلاقاً</b>.<br>"
            "يتم إرسال بصمة الهاش الرقمية (SHA-256) فقط للاستعلام عن التهديدات المعروفة عالمياً."
        )
        rc_desc.setWordWrap(True)
        rc_desc.setStyleSheet("color: #8B949E; font-size: 12px; line-height: 1.5;")
        rc_vbox.addWidget(rc_desc)

        # Hash Input row
        h_row = QHBoxLayout()
        self.txt_rep_hash = QLineEdit()
        self.txt_rep_hash.setPlaceholderText("أدخل بصمة SHA-256 (64 محرف) أو اختر ملفاً لحساب بصمته محلياً...")
        self.txt_rep_hash.setStyleSheet("background: #0D1117; color: #58A6FF; border: 1px solid #30363D; border-radius: 6px; padding: 8px; font-family: Consolas, monospace; font-size: 12px;")
        h_row.addWidget(self.txt_rep_hash, 1)

        btn_pick_file = QPushButton("اختيار ملف...")
        btn_pick_file.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 8px 14px; font-weight: bold;")
        btn_pick_file.clicked.connect(self._browse_hash_file)
        h_row.addWidget(btn_pick_file)

        self.btn_check_rep = QPushButton(" فحص السمعة بالهاش")
        self.btn_check_rep.setIcon(get_icon("search", color="#0D1117"))
        self.btn_check_rep.setStyleSheet("""
            QPushButton {
                background-color: #38BDF8; color: #0D1117; border-radius: 6px;
                padding: 8px 20px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background-color: #7DD3FC; }
        """)
        self.btn_check_rep.clicked.connect(self._start_reputation_check)
        h_row.addWidget(self.btn_check_rep)
        rc_vbox.addLayout(h_row)

        # Reputation Verdict Frame (Initially Hidden)
        self.rep_result_frame = QFrame()
        self.rep_result_frame.setVisible(False)
        self.rep_result_frame.setStyleSheet("background-color: #0D1117; border: 1px solid #21262D; border-radius: 8px; padding: 12px;")
        rf_vbox = QVBoxLayout(self.rep_result_frame)
        self.lbl_rep_verdict = QLabel("")
        self.lbl_rep_verdict.setStyleSheet("color: #F0F6FC; font-size: 13px; font-weight: bold;")
        rf_vbox.addWidget(self.lbl_rep_verdict)
        rc_vbox.addWidget(self.rep_result_frame)

        layout.addWidget(rep_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._refresh_security_posture()

    def _make_telemetry_item(self, title: str, icon_name: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet("background-color: #0D1117; border: 1px solid #21262D; border-radius: 8px; padding: 10px;")
        v = QVBoxLayout(f)
        v.setSpacing(4)

        top = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(get_icon(icon_name, color="#58A6FF", size=16).pixmap(16, 16))
        top.addWidget(icon)
        tl = QLabel(title)
        tl.setStyleSheet("color: #8B949E; font-size: 11px; font-weight: bold;")
        top.addWidget(tl)
        top.addStretch(1)
        v.addLayout(top)

        val = QLabel("جاري التحميل...")
        val.setObjectName("val_label")
        val.setStyleSheet("color: #F0F6FC; font-size: 13px; font-weight: bold;")
        v.addWidget(val)
        return f

    def _refresh_security_posture(self):
        self._telemetry_worker = TelemetryFetchWorker(self)
        self._telemetry_worker.finished.connect(self._on_telemetry_ready)
        self._telemetry_worker.start()

    def _on_telemetry_ready(self, data: dict):
        def_st = data.get("Defender", "غير متوفر")
        rtp_st = data.get("RealTimeProtection", "غير متوفر")
        fw_st = data.get("Firewall", "غير متوفر")
        cfa_st = data.get("ControlledFolderAccess", "غير متوفر")
        ss_st = data.get("SmartScreen", "غير متوفر")
        bl_st = data.get("BitLocker", "غير متوفر")

        self._set_item_value(self.card_def, def_st)
        self._set_item_value(self.card_rtp, rtp_st)
        self._set_item_value(self.card_fw, fw_st)
        self._set_item_value(self.card_cfa, cfa_st)
        self._set_item_value(self.card_ss, ss_st)
        self._set_item_value(self.card_bde, bl_st)

    def _set_item_value(self, card: QFrame, val_str: str):
        lbl = card.findChild(QLabel, "val_label")
        if lbl:
            lbl.setText(val_str)
            if "مفعل" in val_str or "Active" in val_str:
                lbl.setStyleSheet("color: #34D399; font-size: 13px; font-weight: bold;")
            elif "معطل" in val_str or "Disabled" in val_str:
                lbl.setStyleSheet("color: #F87171; font-size: 13px; font-weight: bold;")
            else:
                lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: bold;")

    def _trigger_update_signatures(self):
        self.btn_update_sig.setEnabled(False)
        self.update_progress.setVisible(True)

        self._update_worker = UpdateSignaturesWorker()
        self._update_worker.finished.connect(self._on_update_signatures_finished)
        self._update_worker.start()

    def _on_update_signatures_finished(self, ok: bool, msg: str):
        self.update_progress.setVisible(False)
        self.btn_update_sig.setEnabled(True)

        if ok:
            QMessageBox.information(self, "تحديث التواقيع", msg)
            self._refresh_security_posture()
        else:
            QMessageBox.warning(self, "تنبيه", msg)

    def _browse_hash_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً لحساب بصمته محلياً", "", "كافة الملفات (*.*)")
        if f:
            from app.services.quick_tools.tools.hash_tools import HashTools
            sha = HashTools.compute_file_hash(f, algorithm="SHA-256")
            self.txt_rep_hash.setText(sha)

    def _configure_api_key(self):
        # Dialog to input VirusTotal API key (stored encrypted in DPAPI)
        dlg = QDialog(self)
        dlg.setWindowTitle("إعداد مفتاح API للسمعة الرقمية")
        dlg.setLayoutDirection(Qt.RightToLeft)
        dlg.setStyleSheet("background-color: #161B22; color: #F0F6FC;")
        dlg.setFixedSize(420, 180)

        v = QVBoxLayout(dlg)
        v.setSpacing(10)
        v.addWidget(QLabel("أدخل مفتاح VirusTotal API الخاص بك:"))
        lbl_info = QLabel("يتم تشفير المفتاح وحفظه بأمان عبر Windows DPAPI ولا يغادر جهازك إطلاقاً.")
        lbl_info.setStyleSheet("color: #8B949E; font-size: 11px;")
        v.addWidget(lbl_info)

        txt_k = QLineEdit(dlg)
        txt_k.setEchoMode(QLineEdit.Password)
        txt_k.setPlaceholderText("Paste API key here...")
        txt_k.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 4px; padding: 6px;")
        v.addWidget(txt_k)

        row = QHBoxLayout()
        btn_save = QPushButton("حفظ المفتاح المشفر", dlg)
        btn_save.setStyleSheet("background: #238636; color: #FFFFFF; border-radius: 4px; padding: 6px 14px; font-weight: bold;")
        btn_save.clicked.connect(lambda: (self._rep_service.save_api_key("virustotal", txt_k.text().strip()), dlg.accept()))
        row.addWidget(btn_save)

        btn_cancel = QPushButton("إلغاء", dlg)
        btn_cancel.setStyleSheet("background: #21262D; color: #8B949E; border-radius: 4px; padding: 6px 14px;")
        btn_cancel.clicked.connect(dlg.reject)
        row.addWidget(btn_cancel)
        v.addLayout(row)

        dlg.exec()

    def _start_reputation_check(self):
        sha = self.txt_rep_hash.text().strip()
        if not sha or len(sha) < 32:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال بصمة SHA-256 صالحة.")
            return

        if not self._rep_service.has_api_key("virustotal"):
            QMessageBox.information(
                self,
                "مفتاح API مطلوب",
                "لإجراء فحص السمعة الرقمية عبر الإنترنت، يلزم توفير مفتاح API مجاني لخدمة VirusTotal.\n"
                "يرجى الضغط على زر 'إعداد مفتاح API' لإدخاله."
            )
            self._configure_api_key()
            if not self._rep_service.has_api_key("virustotal"):
                return

        # Explicit user privacy consent
        reply = QMessageBox.question(
            self,
            "تأكيد إرسال بصمة الهاش",
            "سيتم إرسال بصمة الهاش فقط (SHA-256) إلى الخدمة السحابية للتحقق من السمعة، دون إرسال محتوى الملف إطلاقاً.\n\n"
            f"البصمة: {sha[:16]}...{sha[-8:]}\n\nهل ترغب في المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        self.btn_check_rep.setEnabled(False)
        self.btn_check_rep.setText("جاري الاستعلام...")
        self.rep_result_frame.setVisible(False)

        self._rep_worker = ReputationCheckWorker(sha)
        self._rep_worker.finished.connect(self._on_reputation_finished)
        self._rep_worker.start()

    def _on_reputation_finished(self, ok: bool, msg: str, data: dict):
        self.btn_check_rep.setEnabled(True)
        self.btn_check_rep.setText(" فحص السمعة بالهاش")
        self.rep_result_frame.setVisible(True)

        if ok:
            pos = data.get("positives", 0)
            tot = data.get("total", 0)
            if pos > 0:
                self.lbl_rep_verdict.setText(f"⚠️ تنبيه سمعة: تم تصنيف الهاش كمشبوه أو ضار بواسطة {pos} من أصل {tot} محرك فحص عالمي!")
                self.lbl_rep_verdict.setStyleSheet("color: #F87171; font-size: 13px; font-weight: bold;")
                self.rep_result_frame.setStyleSheet("background-color: #2D1418; border: 1px solid #F87171; border-radius: 8px; padding: 12px;")
            else:
                self.lbl_rep_verdict.setText(f"✅ سليم ونظيف: لم يسجل أي محرك فحص (0 من {tot}) أي مؤشرات خطر على هذا الهاش.")
                self.lbl_rep_verdict.setStyleSheet("color: #34D399; font-size: 13px; font-weight: bold;")
                self.rep_result_frame.setStyleSheet("background-color: #132E22; border: 1px solid #34D399; border-radius: 8px; padding: 12px;")
        else:
            self.lbl_rep_verdict.setText(f"نتيجة الاستعلام: {msg}")
            self.lbl_rep_verdict.setStyleSheet("color: #FBBF24; font-size: 13px;")
            self.rep_result_frame.setStyleSheet("background-color: #2B2111; border: 1px solid #FBBF24; border-radius: 8px; padding: 12px;")
