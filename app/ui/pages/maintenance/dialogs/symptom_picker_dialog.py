# -*- coding: utf-8 -*-
"""
'ما المشكلة التي تواجهها؟' (What Issue Are You Facing?) Symptom Picker Dialog for SINAX.
Guides users through targeted diagnostics based on their immediate symptom
rather than running blind, intrusive system commands.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from app.ui.icons import get_icon


class SymptomPickerDialog(QDialog):
    """Interactive modal with cards representing common system symptoms."""

    symptom_selected = Signal(str) # symptom_key

    SYMPTOMS = [
        ("slow_pc", "جهازي بطيء", "بطء عام وتأخر في فتح البرامج واستجابة النظام", "doctor"),
        ("freezing", "Windows يتجمد", "تعليق مفاجئ وتوقف مؤشر الفأرة أو النوافذ عن الاستجابة", "process"),
        ("internet_down", "الإنترنت لا يعمل", "انقطاع الاتصال أو فشل فتح المواقع وعناوين DNS", "network"),
        ("disk_full", "القرص ممتلئ", "امتلاء القرص C وظهور تحذيرات انخفاض المساحة", "storage"),
        ("app_crash", "برنامج يتعطل أو لا يفتح", "تكرار إغلاق البرامج فجأة أو فشل إطلاقها", "apps"),
        ("update_fails", "Windows Update يفشل", "توقف تثبيت التحديثات أو ظهور رموز أخطاء", "update"),
        ("explorer_glitch", "شريط المهام أو Explorer معلق", "اختفاء سطح المكتب أو الأيقونات أو تجمّد شريط المهام", "tools"),
        ("sound_issues", "الصوت لا يعمل", "انقطاع الصوت أو عدم التعرف على السماعات ومخارج الصوت", "audio"),
        ("printer_issues", "الطابعة لا تستجيب", "تعليق ملفات الطباعة في قائمة الانتظار Spooler", "devices"),
        ("bluetooth_issues", "البلوتوث لا يعمل", "فشل اقتران الأجهزة اللاسلكية أو انقطاع الراديو", "wifi"),
        ("slow_startup", "بدء التشغيل بطيء جداً", "استغراق دقائق طويلة للوصول إلى سطح المكتب بعد التشغيل", "startup"),
        ("bsod_crash", "ظهرت شاشة زرقاء (BSOD)", "إعادة تشغيل مفاجئة أو ظهور شاشة الموت الزرقاء", "doctor"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ما المشكلة التي تواجهها؟ - طبيب SINAX")
        self.setMinimumSize(780, 560)
        self.setLayoutDirection(Qt.RightToLeft)
        self.selected_key: str = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        t_lbl = QLabel("ما المشكلة التي تواجهها في جهازك حالياً؟")
        t_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #F0F6FC;")
        layout.addWidget(t_lbl)

        sub_lbl = QLabel("اختر العَرَض الأكثر دقة لبدء تشخيص موجه ومباشر دون تشغيل أوامر عشوائية:")
        sub_lbl.setStyleSheet("font-size: 13px; color: #8B949E;")
        layout.addWidget(sub_lbl)

        # Scrollable Grid of Symptoms
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        c_layout = QGridLayout(container)
        c_layout.setSpacing(12)

        for idx, (key, title, desc, icon_name) in enumerate(self.SYMPTOMS):
            card = QPushButton()
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet("""
                QPushButton {
                    background-color: #161B22;
                    border: 1px solid #30363D;
                    border-radius: 10px;
                    padding: 14px;
                    text-align: right;
                }
                QPushButton:hover {
                    background-color: #21262D;
                    border-color: #38BDF8;
                }
            """)

            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(12)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_icon(icon_name, color_hex="#38BDF8", size=32).pixmap(32, 32))
            card_layout.addWidget(icon_lbl)

            text_col = QVBoxLayout()
            text_col.setSpacing(4)
            name_lbl = QLabel(title)
            name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #F0F6FC;")
            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("font-size: 11px; color: #8B949E; line-height: 1.3;")
            text_col.addWidget(name_lbl)
            text_col.addWidget(desc_lbl)
            card_layout.addLayout(text_col, 1)

            card.clicked.connect(lambda _, k=key: self._on_select(k))

            row = idx // 2
            col = idx % 2
            c_layout.addWidget(card, row, col)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        # Bottom Close Button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        close_btn = QPushButton("إلغاء")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #C9D1D9;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363D;
            }
        """)
        close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)

    def _on_select(self, key: str):
        self.selected_key = key
        self.symptom_selected.emit(key)
        self.accept()
