# -*- coding: utf-8 -*-
"""
Hardware-Aware Secure Delete Subpage (الحذف الآمن الواعي بالعتاد) for SINAX Privacy & Security Center.
Features:
1. Physical drive detection (Magnetic HDD vs Flash SSD / NVMe).
2. Scientific NIST 800-88 transparency warning regarding Wear-Leveling and FTL on SSDs.
3. System protected paths safety lock (Windows, System32, Program Files).
4. Multi-pass overwrite execution (1, 3, or 7 passes).
5. Explicit safety confirmation dialog.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import format_bytes
from app.services.privacy_security.secure_delete_service import SecureDeleteService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class ShredWorker(QThread):
    """Background worker for multi-pass file/folder shredding."""
    progress_updated = Signal(float, str)
    finished = Signal(bool, str)

    def __init__(self, target_path: str, passes: int):
        super().__init__()
        self.target_path = target_path
        self.passes = passes
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        service = SecureDeleteService()
        ok, msg = service.execute_secure_delete(
            self.target_path,
            passes=self.passes,
            progress_cb=lambda p, m: self.progress_updated.emit(p, m),
            cancel_check=lambda: self._cancelled,
        )
        self.finished.emit(ok, msg)


class SecureDeleteSubpage(QWidget):
    """Secure Delete & Hardware-Aware Shredder Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._service = SecureDeleteService()
        self._target_info: Optional[Dict[str, Any]] = None
        self._worker: Optional[ShredWorker] = None
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
        t_lbl = QLabel("الحذف الآمن والواعي بالعتاد (Hardware-Aware Secure Delete)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("إتلاف البيانات الحساسة مع الكشف التلقائي لنوع القرص (HDD مقابل SSD/NVMe) وتنبيهات NIST 800-88 العلمية.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        header_row.addWidget(ToolBadgeWidget.modifies_files(self))
        layout.addLayout(header_row)

        # 2. Target Selector Box
        box = QFrame()
        box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        b_vbox = QVBoxLayout(box)
        b_vbox.setSpacing(10)

        b_lbl = QLabel("العنصر المراد حذفه نهائياً وإتلافه:")
        b_lbl.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px;")
        b_vbox.addWidget(b_lbl)

        r_pick = QHBoxLayout()
        self.txt_target = QLineEdit()
        self.txt_target.setPlaceholderText("اختر ملفاً أو مجلداً للحذف النهائي...")
        self.txt_target.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        r_pick.addWidget(self.txt_target, 1)

        btn_f = QPushButton("اختيار ملف...")
        btn_f.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 14px;")
        btn_f.clicked.connect(self._browse_file)
        r_pick.addWidget(btn_f)

        btn_d = QPushButton("اختيار مجلد...")
        btn_d.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 14px;")
        btn_d.clicked.connect(self._browse_folder)
        r_pick.addWidget(btn_d)
        b_vbox.addLayout(r_pick)

        layout.addWidget(box)

        # 3. Hardware Inspection Card
        self.inspect_card = QFrame()
        self.inspect_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        ic_vbox = QVBoxLayout(self.inspect_card)
        ic_vbox.setSpacing(10)

        ic_head = QHBoxLayout()
        ic_icon = QLabel()
        ic_icon.setPixmap(get_icon("shred", color="#38BDF8", size=22).pixmap(22, 22))
        ic_head.addWidget(ic_icon)

        ic_title = QLabel("تشخيص وسيط التخزين وتفاصيل الهدف:")
        ic_title.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        ic_head.addWidget(ic_title)
        ic_head.addStretch(1)
        ic_vbox.addLayout(ic_head)

        self.lbl_inspect_details = QLabel("حدد ملفاً أو مجلداً لمعاينة نوع القرص وسلامة المسار...")
        self.lbl_inspect_details.setWordWrap(True)
        self.lbl_inspect_details.setStyleSheet("color: #8B949E; font-size: 12px; line-height: 1.5;")
        ic_vbox.addWidget(self.lbl_inspect_details)

        # Scientific Note Banner
        self.scientific_banner = QFrame()
        self.scientific_banner.setVisible(False)
        self.scientific_banner.setStyleSheet("background-color: #2B2111; border: 1px solid #FBBF24; border-radius: 8px; padding: 12px;")
        sb_vbox = QVBoxLayout(self.scientific_banner)
        self.lbl_scientific_note = QLabel("")
        self.lbl_scientific_note.setWordWrap(True)
        self.lbl_scientific_note.setStyleSheet("color: #FBBF24; font-size: 12px; line-height: 1.5;")
        sb_vbox.addWidget(self.lbl_scientific_note)
        ic_vbox.addWidget(self.scientific_banner)

        layout.addWidget(self.inspect_card)

        # 4. Shredding Options & Action Card
        act_card = QFrame()
        act_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        ac_vbox = QVBoxLayout(act_card)
        ac_vbox.setSpacing(12)

        # Passes
        r_passes = QHBoxLayout()
        l_p = QLabel("خوارزمية وعدد دورات الكتابة (Overwrite Passes):")
        l_p.setStyleSheet("color: #F0F6FC; font-weight: bold;")
        r_passes.addWidget(l_p)

        self.cmb_passes = QComboBox()
        self.cmb_passes.addItem("دورة واحدة - كتابة أصفار سريعة (Zero Fill - 1 Pass)", 1)
        self.cmb_passes.addItem("3 دورات - معيار وزارة الدفاع الأمريكية (DoD 5220.22-M - 3 Passes)", 3)
        self.cmb_passes.addItem("7 دورات - معيار مكثف فائق الأمان (Gutmann Partial - 7 Passes)", 7)
        self.cmb_passes.setStyleSheet("""
            QComboBox {
                background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-size: 12px;
            }
        """)
        r_passes.addWidget(self.cmb_passes, 1)
        ac_vbox.addLayout(r_passes)

        # Action Button
        self.btn_shred = QPushButton(" بدء الحذف الآمن النهائي (SHRED)")
        self.btn_shred.setIcon(get_icon("trash", color="#FFFFFF"))
        self.btn_shred.setStyleSheet("""
            QPushButton {
                background-color: #DC2626; color: #FFFFFF; border: none; border-radius: 8px;
                padding: 12px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #EF4444; }
            QPushButton:disabled { background-color: #451A1A; color: #888888; }
        """)
        self.btn_shred.clicked.connect(self._confirm_and_shred)
        ac_vbox.addWidget(self.btn_shred)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #0D1117; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #EF4444; border-radius: 3px; }
        """)
        ac_vbox.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #8B949E; font-size: 12px;")
        ac_vbox.addWidget(self.lbl_status)

        layout.addWidget(act_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _browse_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً للحذف الآمن", "", "كافة الملفات (*.*)")
        if f:
            self.txt_target.setText(f)
            self._inspect_path(f)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلداً للحذف الآمن")
        if folder:
            self.txt_target.setText(folder)
            self._inspect_path(folder)

    def _inspect_path(self, target_path: str):
        p = Path(target_path).resolve()
        if not p.exists():
            return

        self._target_info = self._service.inspect_target_for_deletion(str(p))
        info = self._target_info

        is_prot = info.get("is_protected", False)
        type_str = "مجلد" if info.get("is_directory") else "ملف منفرد"
        total_items = info.get("total_items", 1)
        total_bytes = format_bytes(info.get("total_bytes", 0))

        details = (
            f"<b>النوع:</b> {type_str}<br>"
            f"<b>العناصر:</b> {total_items} ملف(ات)  |  <b>الحجم الإجمالي:</b> {total_bytes}<br>"
            f"<b>نوع وسيط التخزين:</b> <code>{info.get('storage_type')}</code> ({info.get('media_desc')})<br>"
        )

        if is_prot:
            details += "<font color='#F87171'><b>🔒 مسار نظام محمي: لا يمكن حذف هذا المسار لحماية استقرار Windows!</b></font>"
            self.btn_shred.setEnabled(False)
        else:
            self.btn_shred.setEnabled(True)

        self.lbl_inspect_details.setText(details)

        # Scientific note
        note = info.get("scientific_note", "")
        if note:
            self.scientific_banner.setVisible(True)
            self.lbl_scientific_note.setText(note)
        else:
            self.scientific_banner.setVisible(False)

    def _confirm_and_shred(self):
        target = self.txt_target.text().strip()
        if not target or not os.path.exists(target):
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار مسار موجود صالح أولاً.")
            return

        if self._target_info and self._target_info.get("is_protected"):
            QMessageBox.critical(self, "محاولة مرفوضة", "لا يمكن حذف ملفات أو مجلدات نظام التشغيل الأساسية.")
            return

        # High-security confirmation dialog
        reply = QMessageBox.question(
            self,
            "تأكيد الحذف الآمن النهائي",
            f"تحذير صارم:\nهل أنت متأكد تماماً من رغبتك في حذف وإتلاف:\n\n{target}\n\n"
            "هذه العملية غير قابلة للتراجع نهائياً ولن تتمكن أي برامج استرجاع ملفات من استعادة محتوياته.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        passes = self.cmb_passes.currentData()
        self.btn_shred.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("جاري إتلاف وتطهير البيانات...")

        self._worker = ShredWorker(target, passes)
        self._worker.progress_updated.connect(lambda p, m: (self.progress_bar.setValue(int(p * 100)), self.lbl_status.setText(m)))
        self._worker.finished.connect(self._on_shred_finished)
        self._worker.start()

    def _on_shred_finished(self, ok: bool, msg: str):
        self.progress_bar.setVisible(False)
        self.btn_shred.setEnabled(True)

        if ok:
            self.lbl_status.setText("اكتمل الحذف الآمن بنجاح.")
            self.txt_target.clear()
            self.lbl_inspect_details.setText("تم إتلاف الملف بنجاح.")
            self.scientific_banner.setVisible(False)
            QMessageBox.information(self, "نجاح العملية", msg)
        else:
            self.lbl_status.setText(f"خطأ: {msg}")
            QMessageBox.critical(self, "فشل الحذف الآمن", msg)
