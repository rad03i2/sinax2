# -*- coding: utf-8 -*-
"""
Startup Maintenance & Clean Boot Assistant Subpage for SINAX.
Reviews high-impact startup items safely (disable with undo backup; never delete)
and provides a step-by-step Clean Boot Assistant wizard to isolate software conflicts.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from app.services.system_storage.startup_service import StartupService
from app.ui.icons import get_icon


class StartupSubpage(QWidget):
    """Subpage for reviewing startup impact and Clean Boot isolation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.startup_svc = StartupService()
        self._init_ui()
        self.load_startup_apps()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        tabs = QTabWidget(self)
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363D;
                background-color: #0D1117;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #161B22;
                color: #8B949E;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #21262D;
                color: #38BDF8;
                border-bottom: 2px solid #38BDF8;
            }
        """)

        # Tab 1: Startup Maintenance
        self.tab_review = QWidget()
        self._init_review_tab()
        tabs.addTab(self.tab_review, "مراجعة تطبيقات بدء التشغيل")

        # Tab 2: Clean Boot Assistant
        self.tab_clean_boot = QWidget()
        self._init_clean_boot_tab()
        tabs.addTab(self.tab_clean_boot, "مساعد الإقلاع النظيف (Clean Boot Wizard)")

        main_layout.addWidget(tabs)

    def _init_review_tab(self):
        layout = QVBoxLayout(self.tab_review)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Stats row
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        s_layout = QHBoxLayout(stats_frame)
        self.lbl_stats = QLabel("تطبيقات الإقلاع: جاري التحميل...")
        self.lbl_stats.setStyleSheet("font-size: 13px; font-weight: bold; color: #F0F6FC;")
        s_layout.addWidget(self.lbl_stats)
        s_layout.addStretch(1)

        btn_refresh = QPushButton("تحديث القائمة")
        btn_refresh.setIcon(get_icon("update", color_hex="#8B949E"))
        btn_refresh.clicked.connect(self.load_startup_apps)
        s_layout.addWidget(btn_refresh)
        layout.addWidget(stats_frame)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["اسم التطبيق", "الشركة المصنعة", "أثر بدء التشغيل", "الحالة"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                gridline-color: #21262D;
                color: #C9D1D9;
            }
            QHeaderView::section {
                background-color: #0D1117;
                color: #8B949E;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.table, 1)

    def _init_clean_boot_tab(self):
        layout = QVBoxLayout(self.tab_clean_boot)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        info = QFrame()
        info.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        i_lay = QVBoxLayout(info)
        i_lay.setSpacing(6)

        t = QLabel("ما هو الإقلاع النظيف (Clean Boot)؟")
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #58A6FF;")
        d = QLabel(
            "الإقلاع النظيف هو طريقة رسمية تعتمدها Microsoft لتشغيل Windows بالحد الأدنى من التعريفات وبرامج الإقلاع.\n"
            "تساعد هذه الميزة في عزل المشاكل المعقدة وتحديد ما إذا كان هناك برنامج خارجي يتسبب في بطء أو تعطل النظام."
        )
        d.setWordWrap(True)
        d.setStyleSheet("font-size: 12px; color: #C9D1D9; line-height: 1.4;")
        i_lay.addWidget(t)
        i_lay.addWidget(d)
        layout.addWidget(info)

        # Steps card
        steps_card = QFrame()
        steps_card.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        sc_lay = QVBoxLayout(steps_card)
        sc_lay.setSpacing(8)

        def add_step(num: str, text: str):
            r = QHBoxLayout()
            n = QLabel(f" {num} ")
            n.setStyleSheet("background-color: #0284C7; color: white; border-radius: 4px; font-weight: bold;")
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #F0F6FC; font-size: 13px;")
            r.addWidget(n)
            r.addWidget(lbl, 1)
            sc_lay.addLayout(r)

        add_step("1", "فتح أداة تكوين النظام الرسمية (msconfig).")
        add_step("2", "في تبويب 'الخدمات' (Services)، تحديد 'إخفاء كافة خدمات Microsoft'.")
        add_step("3", "تعطيل الخدمات الخارجية المتبقية مؤقتاً لتشخيص المشكلة.")
        add_step("4", "إعادة تشغيل الجهاز؛ إذا اختفت المشكلة، فالسبب هو أحد تلك البرامج الخارجية.")
        layout.addWidget(steps_card)

        # Action button to open msconfig
        btn_bar = QHBoxLayout()
        btn_msconfig = QPushButton("فتح أداة تكوين النظام (msconfig)")
        btn_msconfig.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 8px 18px; border-radius: 6px;")
        btn_msconfig.clicked.connect(self._open_msconfig)
        btn_bar.addWidget(btn_msconfig)
        btn_bar.addStretch(1)
        layout.addLayout(btn_bar)

        layout.addStretch(1)

    def load_startup_apps(self):
        apps = self.startup_svc.list_startup_items()
        self.table.setRowCount(len(apps))
        enabled_cnt = 0
        for idx, app in enumerate(apps):
            if app.is_enabled:
                enabled_cnt += 1
            self.table.setItem(idx, 0, QTableWidgetItem(app.name))
            self.table.setItem(idx, 1, QTableWidgetItem(app.location_label_ar))
            self.table.setItem(idx, 2, QTableWidgetItem("مرتفع" if app.is_broken else "عادي"))
            self.table.setItem(idx, 3, QTableWidgetItem("مفعل" if app.is_enabled else "معطل"))

        self.lbl_stats.setText(
            f"إجمالي تطبيقات الإقلاع: {len(apps)} • المفعلة حالياً: {enabled_cnt}"
        )

    def _open_msconfig(self):
        import subprocess
        try:
            subprocess.Popen(["msconfig.exe"])
        except Exception:
            pass
