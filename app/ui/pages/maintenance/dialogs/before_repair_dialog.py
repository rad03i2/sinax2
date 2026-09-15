# -*- coding: utf-8 -*-
"""
'قبل أن أصلح' (Before I Repair) Dialog for SINAX.
A transparent pre-repair confirmation modal explaining:
- What the tool will do
- Why it is recommended
- What will change
- Prerequisites (Admin, Internet, Restart)
- Reversibility and Risk Level
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from app.services.maintenance.models import MaintenanceAction, RiskLevel
from app.ui.icons import get_icon


class BeforeRepairDialog(QDialog):
    """Explains an operation's impact and risk before execution."""

    def __init__(self, action: MaintenanceAction, parent=None):
        super().__init__(parent)
        self.action = action
        self.setWindowTitle(f"قبل التنفيذ: {action.title_ar}")
        self.setMinimumWidth(560)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header card
        header = QFrame(self)
        header.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon("doctor", color_hex="#38BDF8", size=40).pixmap(40, 40))
        h_layout.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        t_lbl = QLabel(self.action.title_ar)
        t_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #F0F6FC;")
        title_col.addWidget(t_lbl)

        risk_color = "#34D399" if self.action.risk_level == RiskLevel.LEVEL_1_LOW_RISK else (
            "#FBBF24" if self.action.risk_level == RiskLevel.LEVEL_2_SYSTEM_CHANGE else "#F87171"
        )
        risk_lbl = QLabel(f"مستوى المخاطرة: {self.action.risk_level.name}")
        risk_lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {risk_color};")
        title_col.addWidget(risk_lbl)
        h_layout.addLayout(title_col, 1)
        layout.addWidget(header)

        # Explanatory Content Card
        info_card = QFrame(self)
        info_card.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(12)

        def add_row(q_text: str, a_text: str):
            row = QVBoxLayout()
            row.setSpacing(3)
            q = QLabel(q_text)
            q.setStyleSheet("font-size: 13px; font-weight: bold; color: #58A6FF;")
            a = QLabel(a_text)
            a.setWordWrap(True)
            a.setStyleSheet("font-size: 13px; color: #C9D1D9; line-height: 1.4;")
            row.addWidget(q)
            row.addWidget(a)
            info_layout.addLayout(row)

        add_row("ما الذي سيفعله هذا الإجراء؟", self.action.what_will_it_do_ar or self.action.description_ar)
        add_row("ما النتيجة المتوقعة؟", self.action.expected_outcome_ar or "تحسين استقرار وأداء النظام.")
        add_row("هل يحذف ملفاتك الشخصية أو صورك؟", "لا، هذا الإجراء لا يمس ملفات المستخدم الشخصية إطلاقاً." if not self.action.does_delete_user_files else "تنبيه: قد يتضمن هذا الإجراء حذف عناصر محددة.")

        # Requirements Row
        reqs = []
        if self.action.requires_admin:
            reqs.append("يتطلب صلاحيات مسؤول (Admin)")
        if self.action.requires_restart:
            reqs.append("يتطلب إعادة تشغيل الجهاز")
        if self.action.requires_internet:
            reqs.append("يتطلب اتصالاً بالإنترنت")
        if not reqs:
            reqs.append("لا توجد متطلبات خاصة (يعمل محلياً وبشكل فوري)")

        add_row("المتطلبات:", " • ".join(reqs))
        add_row("المدة التقديرية:", self.action.estimated_duration_str)

        layout.addWidget(info_card)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363D;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch(1)

        exec_btn = QPushButton("تأكيد وتنفيذ الإجراء")
        exec_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        exec_btn.clicked.connect(self.accept)
        btn_layout.addWidget(exec_btn)

        layout.addLayout(btn_layout)
