# -*- coding: utf-8 -*-
"""
Encryption & Portable Vault Subpage (التشفير والخزنة الآمنة) for SINAX Privacy & Security Center.
Features:
1. Create portable .sinaxvault containers (AES-256-GCM + scrypt key derivation) with streaming chunks.
2. Windows Account restricted mode (DPAPI).
3. Directory structure preservation.
4. Vault inspection and extraction.
5. BitLocker drive encryption status display.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import format_bytes
from app.services.privacy_security.vault_service import VaultService
from app.services.privacy_security.windows_security_service import WindowsSecurityService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class CreateVaultWorker(QThread):
    """Background worker for vault creation with progress streaming."""
    progress_updated = Signal(float, str)
    vault_created = Signal(bool, str)

    def __init__(self, source_path: str, dest_vault_path: str, password: str, mode: str):
        super().__init__()
        self.source_path = source_path
        self.dest_vault_path = dest_vault_path
        self.password = password
        self.mode = mode
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        service = VaultService()
        ok, msg = service.create_vault(
            self.source_path,
            self.dest_vault_path,
            self.password,
            mode=self.mode,
            progress_cb=lambda p, m: self.progress_updated.emit(p, m),
            cancel_check=lambda: self._cancelled,
        )
        self.vault_created.emit(ok, msg)


class ExtractVaultWorker(QThread):
    """Background worker for vault decryption and extraction."""
    progress_updated = Signal(float, str)
    vault_extracted = Signal(bool, str)

    def __init__(self, vault_path: str, dest_dir: str, password: str):
        super().__init__()
        self.vault_path = vault_path
        self.dest_dir = dest_dir
        self.password = password
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        service = VaultService()
        ok, msg = service.open_vault(
            self.vault_path,
            self.dest_dir,
            password=self.password,
            progress_cb=lambda p, m: self.progress_updated.emit(p, m),
            cancel_check=lambda: self._cancelled,
        )
        self.vault_extracted.emit(ok, msg)


class VaultSubpage(QWidget):
    """SINAX Portable Vault & Encryption Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._vault_service = VaultService()
        self._win_sec = WindowsSecurityService()
        self._create_worker: Optional[CreateVaultWorker] = None
        self._extract_worker: Optional[ExtractVaultWorker] = None
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
        t_lbl = QLabel("التشفير والخزنة الآمنة (Encryption & SINAX Vault)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("إنشاء واستخراج حاويات .sinaxvault المشفرة بمعيار AES-256-GCM واشتقاق scrypt ودعم التشفير المقيد بحساب Windows.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        header_row.addWidget(ToolBadgeWidget.modifies_files(self))
        main_layout.addLayout(header_row)

        # Tabs
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #30363D; background-color: #0D1117; border-radius: 8px; }
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

        tab_create = self._build_create_tab()
        tab_extract = self._build_extract_tab()
        tab_bitlocker = self._build_bitlocker_tab()

        self.tabs.addTab(tab_create, "إنشاء خزنة مشفرة جديدة (.sinaxvault)")
        self.tabs.addTab(tab_extract, "فتح واستخراج محتويات الخزنة")
        self.tabs.addTab(tab_bitlocker, "سجل الخزائن وتشفير BitLocker")

        main_layout.addWidget(self.tabs, 1)

    # -------------------------------------------------------------
    # Tab 1: Create Vault
    # -------------------------------------------------------------
    def _build_create_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea(widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: #0D1117;")

        container = QWidget()
        container.setStyleSheet("background: #0D1117;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        box = QFrame()
        box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        b_vbox = QVBoxLayout(box)
        b_vbox.setSpacing(12)

        # 1. Source Path
        r1 = QHBoxLayout()
        l1 = QLabel("الملف أو المجلد المراد تشفيره:")
        l1.setStyleSheet("color: #F0F6FC; font-weight: bold; width: 180px;")
        r1.addWidget(l1)

        self.txt_source_path = QLineEdit()
        self.txt_source_path.setPlaceholderText("اختر ملفاً أو مجلداً كاملاً...")
        self.txt_source_path.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        r1.addWidget(self.txt_source_path, 1)

        btn_file = QPushButton("اختيار ملف...")
        btn_file.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 12px;")
        btn_file.clicked.connect(self._browse_create_file)
        r1.addWidget(btn_file)

        btn_folder = QPushButton("اختيار مجلد...")
        btn_folder.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 12px;")
        btn_folder.clicked.connect(self._browse_create_folder)
        r1.addWidget(btn_folder)
        b_vbox.addLayout(r1)

        # 2. Mode selection
        m_box = QFrame()
        m_box.setStyleSheet("background: #0D1117; border: 1px solid #21262D; border-radius: 6px; padding: 10px;")
        mb_vbox = QVBoxLayout(m_box)
        mb_vbox.setSpacing(6)

        m_title = QLabel("نمط التشفير:")
        m_title.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 12px;")
        mb_vbox.addWidget(m_title)

        self.radio_portable = QRadioButton("خزنة محمولة بكلمة مرور (AES-256-GCM + scrypt) - تفتح على أي جهاز باستخدام كلمة المرور")
        self.radio_portable.setChecked(True)
        self.radio_portable.setStyleSheet("color: #F0F6FC; font-size: 12px;")
        self.radio_portable.toggled.connect(self._on_mode_toggled)
        mb_vbox.addWidget(self.radio_portable)

        self.radio_dpapi = QRadioButton("مقيدة بحساب Windows الحالي (DPAPI) - لا تتطلب كلمة مرور وتفتح فقط على هذا المستخدم")
        self.radio_dpapi.setStyleSheet("color: #F0F6FC; font-size: 12px;")
        mb_vbox.addWidget(self.radio_dpapi)
        b_vbox.addWidget(m_box)

        # 3. Password Container
        self.pwd_container = QWidget()
        pc_vbox = QVBoxLayout(self.pwd_container)
        pc_vbox.setContentsMargins(0, 0, 0, 0)
        pc_vbox.setSpacing(10)

        r_pwd1 = QHBoxLayout()
        l_p1 = QLabel("كلمة مرور الخزنة:")
        l_p1.setStyleSheet("color: #F0F6FC; font-weight: bold; width: 180px;")
        r_pwd1.addWidget(l_p1)

        self.txt_create_pwd = QLineEdit()
        self.txt_create_pwd.setEchoMode(QLineEdit.Password)
        self.txt_create_pwd.setPlaceholderText("أدخل كلمة مرور قوية لتشفير الخزنة...")
        self.txt_create_pwd.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        r_pwd1.addWidget(self.txt_create_pwd, 1)
        pc_vbox.addLayout(r_pwd1)

        r_pwd2 = QHBoxLayout()
        l_p2 = QLabel("تأكيد كلمة المرور:")
        l_p2.setStyleSheet("color: #F0F6FC; font-weight: bold; width: 180px;")
        r_pwd2.addWidget(l_p2)

        self.txt_create_pwd_confirm = QLineEdit()
        self.txt_create_pwd_confirm.setEchoMode(QLineEdit.Password)
        self.txt_create_pwd_confirm.setPlaceholderText("أعد كتابة كلمة المرور للتأكيد...")
        self.txt_create_pwd_confirm.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        r_pwd2.addWidget(self.txt_create_pwd_confirm, 1)
        pc_vbox.addLayout(r_pwd2)

        self.chk_show_create_pwd = QCheckBox("إظهار كلمة المرور")
        self.chk_show_create_pwd.setStyleSheet("color: #8B949E; font-size: 11px;")
        self.chk_show_create_pwd.toggled.connect(self._toggle_create_pwd_visibility)
        pc_vbox.addWidget(self.chk_show_create_pwd)

        b_vbox.addWidget(self.pwd_container)

        # 4. Action Button & Progress
        self.btn_create_vault = QPushButton(" إنشاء الخزنة المشفرة (.sinaxvault)")
        self.btn_create_vault.setIcon(get_icon("vault", color="#0D1117"))
        self.btn_create_vault.setStyleSheet("""
            QPushButton {
                background-color: #38BDF8; color: #0D1117; border: none; border-radius: 8px;
                padding: 10px 24px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #7DD3FC; }
        """)
        self.btn_create_vault.clicked.connect(self._start_create_vault)
        b_vbox.addWidget(self.btn_create_vault)

        self.create_progress = QProgressBar()
        self.create_progress.setRange(0, 100)
        self.create_progress.setValue(0)
        self.create_progress.setFixedHeight(6)
        self.create_progress.setVisible(False)
        self.create_progress.setStyleSheet("""
            QProgressBar { background-color: #0D1117; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #38BDF8; border-radius: 3px; }
        """)
        b_vbox.addWidget(self.create_progress)

        self.lbl_create_status = QLabel("")
        self.lbl_create_status.setStyleSheet("color: #8B949E; font-size: 12px;")
        b_vbox.addWidget(self.lbl_create_status)

        layout.addWidget(box)
        layout.addStretch(1)

        scroll.setWidget(container)
        w_vbox = QVBoxLayout(widget)
        w_vbox.setContentsMargins(0, 0, 0, 0)
        w_vbox.addWidget(scroll)
        return widget

    def _on_mode_toggled(self, checked: bool):
        self.pwd_container.setVisible(self.radio_portable.isChecked())

    def _toggle_create_pwd_visibility(self, checked: bool):
        mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.txt_create_pwd.setEchoMode(mode)
        self.txt_create_pwd_confirm.setEchoMode(mode)

    def _browse_create_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً لتشفيره داخل الخزنة", "", "كافة الملفات (*.*)")
        if f:
            self.txt_source_path.setText(f)

    def _browse_create_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلداً لتشفيره بالكامل داخل الخزنة")
        if folder:
            self.txt_source_path.setText(folder)

    def _start_create_vault(self):
        src = self.txt_source_path.text().strip()
        if not src or not os.path.exists(src):
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار ملف أو مجلد صالح للتشفير أولاً.")
            return

        is_portable = self.radio_portable.isChecked()
        mode_str = "portable" if is_portable else "windows_dpapi"
        pwd = ""

        if is_portable:
            pwd = self.txt_create_pwd.text()
            confirm = self.txt_create_pwd_confirm.text()
            if not pwd:
                QMessageBox.warning(self, "تنبيه", "يرجى إدخال كلمة مرور لتشفير الخزنة المحمولة.")
                return
            if pwd != confirm:
                QMessageBox.warning(self, "تنبيه", "كلمتا المرور غير متطابقتين.")
                return

        # Choose destination vault path
        src_p = Path(src)
        default_out = str(src_p.parent / f"{src_p.stem}.sinaxvault")
        dest_vault, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ الخزنة المشفرة",
            default_out,
            "خزنة مشفرة (*.sinaxvault)"
        )
        if not dest_vault:
            return

        self.btn_create_vault.setEnabled(False)
        self.create_progress.setVisible(True)
        self.create_progress.setValue(0)
        self.lbl_create_status.setText("بدء التشفير التدفق...")

        self._create_worker = CreateVaultWorker(src, dest_vault, pwd, mode=mode_str)
        self._create_worker.progress_updated.connect(lambda p, m: (self.create_progress.setValue(int(p * 100)), self.lbl_create_status.setText(m)))
        self._create_worker.vault_created.connect(self._on_create_finished)
        self._create_worker.start()

    def _on_create_finished(self, ok: bool, msg: str):
        self.create_progress.setVisible(False)
        self.btn_create_vault.setEnabled(True)

        if ok:
            self.lbl_create_status.setText(msg)
            QMessageBox.information(self, "تم بنجاح", f"تم إنشاء الخزنة المشفرة بنجاح!\n\n{msg}")
            self.txt_create_pwd.clear()
            self.txt_create_pwd_confirm.clear()
        else:
            self.lbl_create_status.setText(f"خطأ: {msg}")
            QMessageBox.critical(self, "فشل التشفير", f"تعذر إنشاء الخزنة:\n{msg}")

    # -------------------------------------------------------------
    # Tab 2: Extract Vault
    # -------------------------------------------------------------
    def _build_extract_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        box = QFrame()
        box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        b_vbox = QVBoxLayout(box)
        b_vbox.setSpacing(12)

        # 1. Vault File Path
        r1 = QHBoxLayout()
        l1 = QLabel("ملف الخزنة (.sinaxvault):")
        l1.setStyleSheet("color: #F0F6FC; font-weight: bold; width: 170px;")
        r1.addWidget(l1)

        self.txt_extract_vault_path = QLineEdit()
        self.txt_extract_vault_path.setPlaceholderText("اختر ملف .sinaxvault المراد فتحه...")
        self.txt_extract_vault_path.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        r1.addWidget(self.txt_extract_vault_path, 1)

        btn_browse_v = QPushButton("استعراض...")
        btn_browse_v.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 14px;")
        btn_browse_v.clicked.connect(self._browse_extract_vault)
        r1.addWidget(btn_browse_v)
        b_vbox.addLayout(r1)

        # 2. Destination Folder
        r2 = QHBoxLayout()
        l2 = QLabel("مجلد الاستخراج:")
        l2.setStyleSheet("color: #F0F6FC; font-weight: bold; width: 170px;")
        r2.addWidget(l2)

        self.txt_extract_dest = QLineEdit()
        self.txt_extract_dest.setPlaceholderText("اختر المجلد الذي ستستخرج إليه المحتويات...")
        self.txt_extract_dest.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        r2.addWidget(self.txt_extract_dest, 1)

        btn_browse_d = QPushButton("استعراض...")
        btn_browse_d.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 14px;")
        btn_browse_d.clicked.connect(self._browse_extract_dest)
        r2.addWidget(btn_browse_d)
        b_vbox.addLayout(r2)

        # 3. Password
        r3 = QHBoxLayout()
        l3 = QLabel("كلمة المرور:")
        l3.setStyleSheet("color: #F0F6FC; font-weight: bold; width: 170px;")
        r3.addWidget(l3)

        self.txt_extract_pwd = QLineEdit()
        self.txt_extract_pwd.setEchoMode(QLineEdit.Password)
        self.txt_extract_pwd.setPlaceholderText("أدخل كلمة المرور (اتركه فارغاً إذا كان نمط DPAPI)...")
        self.txt_extract_pwd.setStyleSheet("background: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        r3.addWidget(self.txt_extract_pwd, 1)
        b_vbox.addLayout(r3)

        # Action & Progress
        self.btn_extract_vault = QPushButton(" فك التشفير واستخراج محتويات الخزنة")
        self.btn_extract_vault.setIcon(get_icon("unlock", color="#0D1117"))
        self.btn_extract_vault.setStyleSheet("""
            QPushButton {
                background-color: #34D399; color: #0D1117; border: none; border-radius: 8px;
                padding: 10px 24px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #6EE7B7; }
        """)
        self.btn_extract_vault.clicked.connect(self._start_extract_vault)
        b_vbox.addWidget(self.btn_extract_vault)

        self.extract_progress = QProgressBar()
        self.extract_progress.setRange(0, 100)
        self.extract_progress.setValue(0)
        self.extract_progress.setFixedHeight(6)
        self.extract_progress.setVisible(False)
        self.extract_progress.setStyleSheet("""
            QProgressBar { background-color: #0D1117; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #34D399; border-radius: 3px; }
        """)
        b_vbox.addWidget(self.extract_progress)

        self.lbl_extract_status = QLabel("")
        self.lbl_extract_status.setStyleSheet("color: #8B949E; font-size: 12px;")
        b_vbox.addWidget(self.lbl_extract_status)

        layout.addWidget(box)
        layout.addStretch(1)
        return widget

    def _browse_extract_vault(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملف الخزنة", "", "خزائن SINAX (*.sinaxvault);;كافة الملفات (*.*)")
        if f:
            self.txt_extract_vault_path.setText(f)
            p = Path(f)
            self.txt_extract_dest.setText(str(p.parent / f"{p.stem}_extracted"))

    def _browse_extract_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلد الاستخراج")
        if folder:
            self.txt_extract_dest.setText(folder)

    def _start_extract_vault(self):
        v = self.txt_extract_vault_path.text().strip()
        d = self.txt_extract_dest.text().strip()
        pwd = self.txt_extract_pwd.text()

        if not v or not os.path.isfile(v):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف خزنة صالح أولاً.")
            return
        if not d:
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مجلد لاستخراج المحتويات.")
            return

        self.btn_extract_vault.setEnabled(False)
        self.extract_progress.setVisible(True)
        self.extract_progress.setValue(0)
        self.lbl_extract_status.setText("جاري فك التشفير...")

        self._extract_worker = ExtractVaultWorker(v, d, pwd)
        self._extract_worker.progress_updated.connect(lambda p, m: (self.extract_progress.setValue(int(p * 100)), self.lbl_extract_status.setText(m)))
        self._extract_worker.vault_extracted.connect(self._on_extract_finished)
        self._extract_worker.start()

    def _on_extract_finished(self, ok: bool, msg: str):
        self.extract_progress.setVisible(False)
        self.btn_extract_vault.setEnabled(True)

        if ok:
            self.lbl_extract_status.setText(msg)
            QMessageBox.information(self, "نجاح الاستخراج", msg)
            self.txt_extract_pwd.clear()
        else:
            self.lbl_extract_status.setText(f"خطأ: {msg}")
            QMessageBox.critical(self, "فشل فك التشفير", f"تعذر استخراج الخزنة (تأكد من صحة كلمة المرور):\n{msg}")

    # -------------------------------------------------------------
    # Tab 3: History & BitLocker
    # -------------------------------------------------------------
    def _build_bitlocker_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # BitLocker status card
        bl_card = QFrame()
        bl_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        bl_vbox = QVBoxLayout(bl_card)
        bl_vbox.setSpacing(10)

        bl_head = QHBoxLayout()
        bl_icon = QLabel()
        bl_icon.setPixmap(get_icon("lock", color="#38BDF8", size=24).pixmap(24, 24))
        bl_head.addWidget(bl_icon)

        bl_t = QLabel("حالة تشفير الأقراص الكامل (BitLocker Drive Encryption)")
        bl_t.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 14px;")
        bl_head.addWidget(bl_t)
        bl_head.addStretch(1)

        btn_open_bl = QPushButton(" فتح إعدادات BitLocker في Windows")
        btn_open_bl.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #38BDF8; border: 1px solid #38BDF8;
                border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background: #38BDF8; color: #0D1117; }
        """)
        btn_open_bl.clicked.connect(self._win_sec.open_bitlocker_settings)
        bl_head.addWidget(btn_open_bl)
        bl_vbox.addLayout(bl_head)

        self.lbl_bl_status = QLabel("الحالة الحالية: <b>جاري التحقق...</b>")
        self.lbl_bl_status.setStyleSheet("color: #38BDF8; font-size: 13px;")
        bl_vbox.addWidget(self.lbl_bl_status)
        QTimer.singleShot(100, self._check_bitlocker_async)

        bl_desc = QLabel("تشفير BitLocker يحمي القرص بأكمله عند إيقاف تشغيل الجهاز أو سرقة وحدة التخزين الفيزيائية.")
        bl_desc.setStyleSheet("color: #8B949E; font-size: 12px;")
        bl_vbox.addWidget(bl_desc)

        layout.addWidget(bl_card)

        # Vaults History Table
        lbl_hist = QLabel("سجل الخزائن المسجلة في SINAX:")
        lbl_hist.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px;")
        layout.addWidget(lbl_hist)

        self.table_vaults = QTableWidget()
        self.table_vaults.setColumnCount(4)
        self.table_vaults.setHorizontalHeaderLabels(["اسم الخزنة", "المسار", "الحجم", "التاريخ"])
        self.table_vaults.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_vaults.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_vaults.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_vaults.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_vaults.setAlternatingRowColors(True)
        self.table_vaults.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117; alternate-background-color: #161B22;
                border: 1px solid #30363D; border-radius: 6px; gridline-color: #21262D; color: #F0F6FC;
            }
            QHeaderView::section {
                background-color: #161B22; color: #8B949E; font-weight: bold; border: 1px solid #21262D; padding: 6px;
            }
        """)
        layout.addWidget(self.table_vaults, 1)

        self._load_vaults_history()
        return widget

    def _load_vaults_history(self):
        vaults = self._vault_service.get_known_vaults()
        self.table_vaults.setRowCount(len(vaults))
        for idx, v in enumerate(vaults):
            p = Path(v.get("vault_path", ""))
            self.table_vaults.setItem(idx, 0, QTableWidgetItem(p.name))
            self.table_vaults.setItem(idx, 1, QTableWidgetItem(str(p)))
            sz = format_bytes(v.get("size_bytes", 0))
            self.table_vaults.setItem(idx, 2, QTableWidgetItem(sz))
            self.table_vaults.setItem(idx, 3, QTableWidgetItem(v.get("created_at", "—")))

    def _check_bitlocker_async(self):
        import threading
        def worker():
            try:
                data = self._win_sec.get_security_overview()
                bl_status = data.get("BitLocker", "غير متوفر")
                QTimer.singleShot(0, lambda: self.lbl_bl_status.setText(f"الحالة الحالية: <b>{bl_status}</b>"))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True, name="BitLockerCheckThread").start()
