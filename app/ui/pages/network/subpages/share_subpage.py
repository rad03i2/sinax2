# -*- coding: utf-8 -*-
"""
SINAX Share Subpage (صفحة مشاركة الملفات السريعة بدون إنترنت)
Allows PC ↔ Phone sharing via dynamic QR code and local HTTP server,
and PC ↔ PC local network direct transfer with SHA-256 integrity verification.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.network.qr_generator import QrCodeGenerator
from app.services.network.share_service import ShareService
from app.ui.icons import get_icon


class ShareSubpage(QWidget):
    """Subpage for local network file transfer and phone QR sharing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        # 1. Header
        title = QLabel("منظومة مشاركة الملفات السريعة (SINAX Share)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        layout.addWidget(title)

        desc = QLabel("نقل مباشر فائق السرعة عبر شبكة Wi-Fi المحلية دون الحاجة لاتصال بالإنترنت وبدون استخدام السحابة.")
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        layout.addWidget(desc)

        # 2. Main Share Actions Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(14)

        self.send_file_btn = QPushButton("  إرسال ملف للهاتف (توليد QR)")
        self.send_file_btn.setIcon(get_icon("share", "#FFFFFF", 18))
        self.send_file_btn.setFixedHeight(44)
        self.send_file_btn.setStyleSheet("""
            QPushButton {
                background: #0078D4;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover { background: #106EBE; }
        """)
        self.send_file_btn.clicked.connect(self._start_send_to_phone)
        actions_row.addWidget(self.send_file_btn)

        self.receive_file_btn = QPushButton("  استقبال ملفات من الهاتف (توليد QR)")
        self.receive_file_btn.setIcon(get_icon("restore", "#FFFFFF", 18))
        self.receive_file_btn.setFixedHeight(44)
        self.receive_file_btn.setStyleSheet("""
            QPushButton {
                background: #10B981;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover { background: #059669; }
        """)
        self.receive_file_btn.clicked.connect(self._start_receive_from_phone)
        actions_row.addWidget(self.receive_file_btn)

        layout.addLayout(actions_row)

        # 3. QR Code & Session Display Frame
        self.qr_frame = QFrame()
        self.qr_frame.setStyleSheet("""
            QFrame {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 24px;
            }
        """)
        qr_layout = QVBoxLayout(self.qr_frame)
        qr_layout.setAlignment(Qt.AlignCenter)
        qr_layout.setSpacing(12)

        self.qr_title = QLabel("امسح رمز QR بكاميرا هاتفك لبدء النقل الفوري:")
        self.qr_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.qr_title.setStyleSheet("color: #FFFFFF;")
        self.qr_title.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(self.qr_title)

        self.qr_image_lbl = QLabel()
        self.qr_image_lbl.setAlignment(Qt.AlignCenter)
        self.qr_image_lbl.setFixedSize(220, 220)
        # Default placeholder QR
        default_qr = QrCodeGenerator.create_qr_pixmap("http://sinax.local", size=200)
        self.qr_image_lbl.setPixmap(default_qr)
        qr_layout.addWidget(self.qr_image_lbl, alignment=Qt.AlignCenter)

        self.url_display = QLabel("الرابط: —")
        self.url_display.setFont(QFont("Segoe UI", 12))
        self.url_display.setStyleSheet("color: #38BDF8; font-weight: 500;")
        self.url_display.setAlignment(Qt.AlignCenter)
        self.url_display.setTextInteractionFlags(Qt.TextSelectableByMouse)
        qr_layout.addWidget(self.url_display)

        self.session_info = QLabel("اختر أحد الأزرار أعلاه لإنشاء جلسة مشاركة محلية آمنة.")
        self.session_info.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.session_info.setAlignment(Qt.AlignCenter)
        qr_layout.addWidget(self.session_info)

        layout.addWidget(self.qr_frame)

        # 4. PC-to-PC Direct Transfer Card
        p2p_card = QFrame()
        p2p_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 16px;")
        p2p_l = QVBoxLayout(p2p_card)
        p2p_l.setSpacing(8)

        p2p_t = QLabel("نقل الملفات الضخمة بين كمبيوترين (PC ↔ PC Direct LAN):")
        p2p_t.setFont(QFont("Segoe UI", 13, QFont.Bold))
        p2p_t.setStyleSheet("color: #FFFFFF;")
        p2p_l.addWidget(p2p_t)

        p2p_d = QLabel("رمز الاقتران الأمني للاتصال المباشر بين أجهزة SINAX على نفس الشبكة: <b>" + ShareService.generate_pairing_code() + "</b> (مشفر ويدعم استئناف النقل تلقائياً مع فحص سلامة SHA-256).")
        p2p_d.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.5;")
        p2p_d.setWordWrap(True)
        p2p_l.addWidget(p2p_d)

        layout.addWidget(p2p_card)
        layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _start_send_to_phone(self):
        path, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً لإرساله إلى الهاتف")
        if not path:
            return

        file_p = Path(path)
        url, token = ShareService.create_send_session(str(file_p), expiry_minutes=30)
        qr_pix = QrCodeGenerator.create_qr_pixmap(url, size=200)

        self.qr_title.setText(f"جاهز للإرسال: {file_p.name}")
        self.qr_image_lbl.setPixmap(qr_pix)
        self.url_display.setText(f"الرابط المحلي: {url}")
        self.session_info.setText("افتح كاميرا الهاتف واضغط على الرابط ليبدأ تنزيل الملف مباشرة دون إنترنت.")

    def _start_receive_from_phone(self):
        dest_folder = str(Path.home() / "Downloads" / "SINAX_Received")
        url, token = ShareService.create_receive_session(target_folder=dest_folder, expiry_minutes=30)
        qr_pix = QrCodeGenerator.create_qr_pixmap(url, size=200)

        self.qr_title.setText("جاهز لاستقبال الصور والملفات من الهاتف")
        self.qr_image_lbl.setPixmap(qr_pix)
        self.url_display.setText(f"رابط الرفع: {url}")
        self.session_info.setText(f"امسح الرمز بالهاتف لاختيار الملفات وإرسالها مباشرة لمجلد:\n{dest_folder}")
