# -*- coding: utf-8 -*-
"""
Clipboard & Password Privacy Subpage (خصوصية الحافظة وكلمات المرور) for SINAX Privacy & Security Center.
Features:
1. Clipboard Privacy Guard:
   - Live clipboard data type summary (Text, Image, URLs) without exposing secret contents.
   - Immediate wipe ("مسح الحافظة الآن").
   - Configurable auto-clear countdown timer (30s, 60s, 3m, 5m).
2. Direct integration with SINAX PasswordTools:
   - Cryptographically secure password generation.
   - Customizable character sets (Upper, Lower, Digits, Symbols).
   - "نسخ آمن مع تفريغ تلقائي" which copies the generated password and arms the 60s timer.
   - Offline password entropy and strength meter.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.services.privacy_security.clipboard_privacy_service import ClipboardPrivacyService
from app.services.quick_tools.tools.password_tools import PasswordTools
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class PasswordsSubpage(QWidget):
    """Clipboard Privacy & Secure Password Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._clip_service = ClipboardPrivacyService(self)
        self._clip_service.timer_ticked.connect(self._on_clipboard_timer_tick)
        self._clip_service.clipboard_cleared.connect(self._on_clipboard_cleared)
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
        t_lbl = QLabel("خصوصية الحافظة وكلمات المرور (Clipboard & Password Privacy)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("حماية محتويات الحافظة ومسحها التلقائي عند نسخ البيانات الحساسة، وتوليد كلمات مرور مشفرة محلياً 100%.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        layout.addLayout(header_row)

        # 2. Clipboard Privacy Guard Card
        clip_card = QFrame()
        clip_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        cc_vbox = QVBoxLayout(clip_card)
        cc_vbox.setSpacing(12)

        cc_head = QHBoxLayout()
        cc_icon = QLabel()
        cc_icon.setPixmap(get_icon("key", color="#38BDF8", size=22).pixmap(22, 22))
        cc_head.addWidget(cc_icon)

        cc_t = QLabel("حارس خصوصية الحافظة (Clipboard Privacy Guard)")
        cc_t.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        cc_head.addWidget(cc_t)
        cc_head.addStretch(1)

        btn_refresh_clip = QPushButton("تحديث الحالة")
        btn_refresh_clip.setStyleSheet("background: #21262D; color: #8B949E; border: 1px solid #30363D; border-radius: 4px; padding: 4px 10px; font-size: 11px;")
        btn_refresh_clip.clicked.connect(self._update_clipboard_status)
        cc_head.addWidget(btn_refresh_clip)
        cc_vbox.addLayout(cc_head)

        # Status text
        self.lbl_clip_summary = QLabel("محتوى الحافظة الحالي: فحص...")
        self.lbl_clip_summary.setStyleSheet("color: #8B949E; font-size: 12px;")
        cc_vbox.addWidget(self.lbl_clip_summary)

        # Action Buttons Row
        act_row = QHBoxLayout()
        btn_clear_now = QPushButton(" مسح الحافظة فوراً")
        btn_clear_now.setIcon(get_icon("trash", color="#FFFFFF"))
        btn_clear_now.setStyleSheet("""
            QPushButton {
                background-color: #DC2626; color: #FFFFFF; border-radius: 6px;
                padding: 8px 18px; font-weight: bold;
            }
            QPushButton:hover { background-color: #EF4444; }
        """)
        btn_clear_now.clicked.connect(self._clear_clipboard_now)
        act_row.addWidget(btn_clear_now)

        # Timer scheduler
        lbl_timer = QLabel("جدولة تفريغ تلقائي:")
        lbl_timer.setStyleSheet("color: #8B949E; font-size: 12px; margin-right: 12px;")
        act_row.addWidget(lbl_timer)

        self.cmb_timer_secs = QComboBox()
        self.cmb_timer_secs.addItem("بعد 30 ثانية", 30)
        self.cmb_timer_secs.addItem("بعد 60 ثانية (دقيقة واحدة)", 60)
        self.cmb_timer_secs.addItem("بعد 3 دقائق", 180)
        self.cmb_timer_secs.addItem("بعد 5 دقائق", 300)
        self.cmb_timer_secs.setCurrentIndex(1)
        self.cmb_timer_secs.setStyleSheet("""
            QComboBox {
                background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 4px; padding: 4px 10px; font-size: 11px;
            }
        """)
        act_row.addWidget(self.cmb_timer_secs)

        btn_start_timer = QPushButton("بدء المؤقت")
        btn_start_timer.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #38BDF8; border: 1px solid #38BDF8;
                border-radius: 4px; padding: 6px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #38BDF8; color: #0D1117; }
        """)
        btn_start_timer.clicked.connect(self._start_custom_timer)
        act_row.addWidget(btn_start_timer)

        self.btn_cancel_timer = QPushButton("إلغاء المؤقت")
        self.btn_cancel_timer.setVisible(False)
        self.btn_cancel_timer.setStyleSheet("background: #21262D; color: #F87171; border: 1px solid #F87171; border-radius: 4px; padding: 6px 12px;")
        self.btn_cancel_timer.clicked.connect(self._cancel_timer)
        act_row.addWidget(self.btn_cancel_timer)

        act_row.addStretch(1)
        cc_vbox.addLayout(act_row)

        # Countdown Banner
        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setVisible(False)
        self.lbl_countdown.setStyleSheet("color: #FBBF24; font-size: 12px; font-weight: bold; background: #2B2111; padding: 6px 12px; border-radius: 6px;")
        cc_vbox.addWidget(self.lbl_countdown)

        layout.addWidget(clip_card)

        # 3. Integrated Strong Password Generator
        pwd_card = QFrame()
        pwd_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 16px;")
        pc_vbox = QVBoxLayout(pwd_card)
        pc_vbox.setSpacing(14)

        pc_head = QHBoxLayout()
        pc_icon = QLabel()
        pc_icon.setPixmap(get_icon("password", color="#34D399", size=22).pixmap(22, 22))
        pc_head.addWidget(pc_icon)

        pc_t = QLabel("توليد كلمات مرور مشفرة فائقة القوة (عبر وحدة Quick Tools المعتمدة)")
        pc_t.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        pc_head.addWidget(pc_t)
        pc_head.addStretch(1)
        pc_vbox.addLayout(pc_head)

        # Controls row: Length slider
        sl_row = QHBoxLayout()
        self.lbl_len_display = QLabel("طول كلمة المرور: 20 حرفاً")
        self.lbl_len_display.setStyleSheet("color: #F0F6FC; font-weight: bold; width: 160px;")
        sl_row.addWidget(self.lbl_len_display)

        self.slider_len = QSlider(Qt.Horizontal)
        self.slider_len.setRange(8, 64)
        self.slider_len.setValue(20)
        self.slider_len.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #0D1117; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #38BDF8; border-radius: 3px; }
            QSlider::handle:horizontal { background: #FFFFFF; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }
        """)
        self.slider_len.valueChanged.connect(self._on_len_changed)
        sl_row.addWidget(self.slider_len, 1)
        pc_vbox.addLayout(sl_row)

        # Checkboxes row
        chk_row = QHBoxLayout()
        self.chk_upper = QCheckBox("أحرف كبيرة (A-Z)")
        self.chk_upper.setChecked(True)
        self.chk_upper.setStyleSheet("color: #F0F6FC;")
        chk_row.addWidget(self.chk_upper)

        self.chk_lower = QCheckBox("أحرف صغيرة (a-z)")
        self.chk_lower.setChecked(True)
        self.chk_lower.setStyleSheet("color: #F0F6FC;")
        chk_row.addWidget(self.chk_lower)

        self.chk_digits = QCheckBox("أرقام (0-9)")
        self.chk_digits.setChecked(True)
        self.chk_digits.setStyleSheet("color: #F0F6FC;")
        chk_row.addWidget(self.chk_digits)

        self.chk_symbols = QCheckBox("رموز خاصة (!@#$%)")
        self.chk_symbols.setChecked(True)
        self.chk_symbols.setStyleSheet("color: #F0F6FC;")
        chk_row.addWidget(self.chk_symbols)

        chk_row.addStretch(1)

        btn_gen = QPushButton(" توليد جديد")
        btn_gen.setIcon(get_icon("refresh", color="#FFFFFF"))
        btn_gen.setStyleSheet("""
            QPushButton {
                background: #1F6FEB; color: #FFFFFF; border-radius: 6px; padding: 6px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #388BFD; }
        """)
        btn_gen.clicked.connect(self._generate_new_password)
        chk_row.addWidget(btn_gen)
        pc_vbox.addLayout(chk_row)

        # Output Password Row
        out_row = QHBoxLayout()
        self.txt_output_pwd = QLineEdit()
        self.txt_output_pwd.setReadOnly(True)
        self.txt_output_pwd.setStyleSheet("""
            QLineEdit {
                background: #0D1117; color: #34D399; border: 1px solid #30363D;
                border-radius: 6px; padding: 8px 12px; font-family: Consolas, monospace; font-size: 14px; font-weight: bold;
            }
        """)
        out_row.addWidget(self.txt_output_pwd, 1)

        # Regular copy
        btn_copy = QPushButton("نسخ عادي")
        btn_copy.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 8px 14px; font-weight: bold;")
        btn_copy.clicked.connect(self._copy_normal)
        out_row.addWidget(btn_copy)

        # Secure Copy with 60s TTL
        btn_secure_copy = QPushButton(" 🛡️ نسخ مع حماية وتفريغ بعد 60 ثانية")
        btn_secure_copy.setStyleSheet("""
            QPushButton {
                background: #238636; color: #FFFFFF; border-radius: 4px; padding: 8px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #2EA043; }
        """)
        btn_secure_copy.clicked.connect(self._copy_secure_60s)
        out_row.addWidget(btn_secure_copy)
        pc_vbox.addLayout(out_row)

        # Strength & Entropy meter
        self.lbl_entropy = QLabel("الإنتروبيا والقوة: اضغط توليد...")
        self.lbl_entropy.setStyleSheet("color: #8B949E; font-size: 12px;")
        pc_vbox.addWidget(self.lbl_entropy)

        layout.addWidget(pwd_card)
        layout.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._update_clipboard_status()
        self._generate_new_password()

    def _update_clipboard_status(self):
        types = self._clip_service.get_clipboard_summary()
        parts = []
        if types.get("has_text"):
            parts.append("نص (Text)")
        if types.get("has_image"):
            parts.append("صورة (Image)")
        if types.get("has_urls"):
            parts.append("روابط (URLs)")

        if parts:
            desc = "، ".join(parts)
            self.lbl_clip_summary.setText(f"محتوى الحافظة الحالي: يحتوي على [{desc}] (المحتوى محمي ولا يتم تسجيله)")
        else:
            self.lbl_clip_summary.setText("محتوى الحافظة الحالي: فارغة تماماً")

    def _clear_clipboard_now(self):
        self._clip_service.clear_now()
        self._update_clipboard_status()
        self.lbl_countdown.setVisible(False)
        self.btn_cancel_timer.setVisible(False)
        QMessageBox.information(self, "نجاح", "تم مسح وتفريغ الحافظة فوراً.")

    def _start_custom_timer(self):
        secs = self.cmb_timer_secs.currentData()
        self._clip_service.schedule_clear(secs)
        self.lbl_countdown.setVisible(True)
        self.btn_cancel_timer.setVisible(True)

    def _cancel_timer(self):
        self._clip_service.stop_timer()
        self.lbl_countdown.setVisible(False)
        self.btn_cancel_timer.setVisible(False)

    def _on_clipboard_timer_tick(self, rem_seconds: int):
        self.lbl_countdown.setText(f"⏱️ سيتم مسح محتويات الحافظة تلقائياً بعد {rem_seconds} ثانية...")

    def _on_clipboard_cleared(self):
        self.lbl_countdown.setVisible(False)
        self.btn_cancel_timer.setVisible(False)
        self._update_clipboard_status()

    def _on_len_changed(self, val: int):
        self.lbl_len_display.setText(f"طول كلمة المرور: {val} حرفاً")
        self._generate_new_password()

    def _generate_new_password(self):
        length = self.slider_len.value()
        pwd = PasswordTools.generate_password(
            length=length,
            use_upper=self.chk_upper.isChecked(),
            use_lower=self.chk_lower.isChecked(),
            use_digits=self.chk_digits.isChecked(),
            use_symbols=self.chk_symbols.isChecked(),
        )
        self.txt_output_pwd.setText(pwd)

        entropy_info = PasswordTools.estimate_password_strength(pwd)
        bits = entropy_info.get("entropy_bits", 0.0)
        strength = entropy_info.get("label_ar", "قوية")
        self.lbl_entropy.setText(f"مستوى الأمان: <b><font color='#34D399'>{strength}</font></b> | الإنتروبيا الرياضية: <b>{bits:.1f} بت</b> (غير قابلة للاختراق بالقوة الغاشمة محلياً)")

    def _copy_normal(self):
        pwd = self.txt_output_pwd.text()
        if pwd:
            clipboard = QApplication.clipboard()
            clipboard.setText(pwd)
            self._update_clipboard_status()
            QMessageBox.information(self, "تم النسخ", "تم نسخ كلمة المرور إلى الحافظة.")

    def _copy_secure_60s(self):
        pwd = self.txt_output_pwd.text()
        if pwd:
            self._clip_service.set_sensitive_text(pwd, ttl_seconds=60)
            self._update_clipboard_status()
            self.lbl_countdown.setVisible(True)
            self.btn_cancel_timer.setVisible(True)
            QMessageBox.information(
                self,
                "نسخ آمن ومؤقت",
                "تم نسخ كلمة المرور إلى الحافظة وتفعيل الحماية.\nسيتم مسح الحافظة تلقائياً بعد 60 ثانية لحماية خصوصيتك."
            )
