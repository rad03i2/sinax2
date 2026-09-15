# -*- coding: utf-8 -*-
"""
SINAX Apps & Programs Manager Overview Subpage
Provides dashboard diagnostic statistics, quick action navigation cards,
and truthful smart recommendations for software management.
"""

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import InstalledApp, format_bytes
from app.services.apps_manager.inventory_service import InventoryService
from app.ui.icons import get_icon


class StatCard(QFrame):
    """Modern dark dashboard stat card."""

    def __init__(self, title: str, value: str, icon_name: str, color_hex: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;
            }}
            QFrame:hover {{ border-color: {color_hex}; }}
        """)
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(icon_name, color=color_hex, size=32).pixmap(32, 32))
        layout.addWidget(icon_lbl)

        vbox = QVBoxLayout()
        vbox.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #8B949E; font-size: 12px; font-weight: bold;")
        vbox.addWidget(self.lbl_title)

        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet(f"color: {color_hex}; font-size: 20px; font-weight: bold;")
        vbox.addWidget(self.lbl_val)

        layout.addLayout(vbox, 1)

    def set_value(self, val: str):
        self.lbl_val.setText(val)


class OverviewSubpage(QWidget):
    """Overview dashboard for Apps & Programs Manager."""

    switch_subpage_requested = Signal(str)  # subpage key
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 1. Hero Banner
        hero = QFrame()
        hero.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1F242C, stop:1 #161B22);
                border: 1px solid #30363D; border-radius: 12px; padding: 18px;
            }
        """)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(14, 14, 14, 14)

        h_vbox = QVBoxLayout()
        h_title = QLabel("إدارة البرامج والتطبيقات (SINAX Apps Center)")
        h_title.setStyleSheet("color: #58A6FF; font-size: 18px; font-weight: bold;")
        h_vbox.addWidget(h_title)

        h_sub = QLabel("المركز الشامل لجرد وإلغاء تثبيت وتحديث البرامج واستعادتها بعد الفورمات بدقة وأمان تام.")
        h_sub.setStyleSheet("color: #8B949E; font-size: 13px;")
        h_vbox.addWidget(h_sub)
        hero_layout.addLayout(h_vbox, 1)

        self.btn_refresh = QPushButton("تحديث الجرد الآن")
        self.btn_refresh.setIcon(get_icon("update", color="#F0F6FC"))
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background: #1F6FEB; color: white; border: none; border-radius: 8px;
                padding: 10px 18px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background: #388BFD; }
        """)
        self.btn_refresh.clicked.connect(self.refresh_requested.emit)
        hero_layout.addWidget(self.btn_refresh)
        layout.addWidget(hero)

        # 2. Six Diagnostic Stat Cards
        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)

        self.card_total = StatCard("البرامج المثبتة", "جاري الفحص...", "apps", "#58A6FF")
        self.card_updates = StatCard("تحديثات متاحة", "جاري الفحص...", "update", "#238636")
        self.card_size = StatCard("الحجم المعروف", "جاري الحساب...", "storage", "#A371F7")
        self.card_startup = StatCard("بدء التشغيل (Startup)", "جاري الفحص...", "startup", "#D29922")
        self.card_large = StatCard("برامج كبيرة (>1 GB)", "جاري الفحص...", "chart", "#F0883E")
        self.card_broken = StatCard("إدخالات معطوبة", "جاري الفحص...", "uninstall", "#F85149")

        stats_grid.addWidget(self.card_total, 0, 0)
        stats_grid.addWidget(self.card_updates, 0, 1)
        stats_grid.addWidget(self.card_size, 0, 2)
        stats_grid.addWidget(self.card_startup, 1, 0)
        stats_grid.addWidget(self.card_large, 1, 1)
        stats_grid.addWidget(self.card_broken, 1, 2)
        layout.addLayout(stats_grid)

        # 3. Quick Action Cards
        lbl_sec1 = QLabel("الأقسام الرئيسية السريعة")
        lbl_sec1.setStyleSheet("color: #F0F6FC; font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_sec1)

        actions_grid = QGridLayout()
        actions_grid.setSpacing(12)

        cards_def = [
            ("inventory", "كل البرامج المثبتة", "جرد شامل لجميع البرامج والتطبيقات مع الفلترة والبحث المتقدم وتفاصيل الحزم.", "apps", "#58A6FF"),
            ("updates", "تحديثات البرامج", "اكتشاف أحدث الإصدارات المتاحة وتحديث البرامج فردياً أو جماعياً عبر WinGet.", "update", "#238636"),
            ("before_format", "قبل الفورمات (حفظ برامجي)", "تصدير قائمة كاملة ببرامجك ومعرفات استعادتها التلقائية بضغطة زر واحدة.", "backup", "#A371F7"),
            ("leftovers", "كشف وتنظيف البقايا", "البحث الذكي والحذر عن المجلدات والاختصارات المتروكة بعد إلغاء البرامج.", "leftover", "#D29922"),
        ]

        for i, (key, title, desc, icon_name, col) in enumerate(cards_def):
            btn_card = QFrame()
            btn_card.setStyleSheet(f"""
                QFrame {{
                    background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;
                }}
                QFrame:hover {{ border-color: {col}; background: #1C2128; }}
            """)
            bc_layout = QVBoxLayout(btn_card)
            bc_layout.setSpacing(6)

            top_h = QHBoxLayout()
            icon_l = QLabel()
            icon_l.setPixmap(get_icon(icon_name, color=col, size=24).pixmap(24, 24))
            top_h.addWidget(icon_l)

            lbl_t = QLabel(title)
            lbl_t.setStyleSheet(f"color: {col}; font-size: 14px; font-weight: bold;")
            top_h.addWidget(lbl_t, 1)
            bc_layout.addLayout(top_h)

            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet("color: #8B949E; font-size: 12px;")
            lbl_d.setWordWrap(True)
            bc_layout.addWidget(lbl_d)

            btn_open = QPushButton("فتح القسم")
            btn_open.setStyleSheet("""
                QPushButton { background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 12px; font-weight: bold; }
                QPushButton:hover { background: #30363D; }
            """)
            btn_open.clicked.connect(lambda _, k=key: self.switch_subpage_requested.emit(k))
            bc_layout.addWidget(btn_open, 0, Qt.AlignLeft)

            actions_grid.addWidget(btn_card, i // 2, i % 2)

        layout.addLayout(actions_grid)

        # 4. Smart Truthful Recommendations
        lbl_sec2 = QLabel("التوصيات الذكية")
        lbl_sec2.setStyleSheet("color: #F0F6FC; font-size: 15px; font-weight: bold;")
        layout.addWidget(lbl_sec2)

        self.recom_box = QVBoxLayout()
        self.recom_box.setSpacing(8)
        layout.addLayout(self.recom_box)

        layout.addStretch(1)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def update_data(self, apps: List[InstalledApp]):
        """Refreshes counters and recommendation cards with live app data."""
        stats = InventoryService.get_summary_stats(apps)

        self.card_total.set_value(str(stats["total_apps"]))
        self.card_updates.set_value(str(stats["updates_count"]))
        self.card_size.set_value(format_bytes(stats["total_size_bytes"]))
        self.card_startup.set_value(str(stats["startup_count"]))
        self.card_large.set_value(str(stats["large_count"]))
        self.card_broken.set_value(str(stats["broken_count"]))

        # Build recommendations
        while self.recom_box.count() > 0:
            item = self.recom_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if stats["updates_count"] > 0:
            self._add_recommendation_card(
                title=f"يوجد {stats['updates_count']} برنامجاً يتوفر لها تحديثات رسمية",
                desc="يوصى بتحديث التطبيقات لتحسين الأداء وسد الثغرات الأمنية.",
                btn_text="عرض التحديثات",
                target_subpage="updates",
                color_hex="#238636",
            )

        if stats["large_count"] > 0:
            self._add_recommendation_card(
                title=f"تم رصد {stats['large_count']} برامج تستهلك أكثر من 1 جيجابايت",
                desc="يمكنك مراجعة البرامج الكبيرة للتأكد من استمرار حاجتك إليها واستعادة مساحة القرص.",
                btn_text="عرض البرامج الكبيرة",
                target_subpage="large",
                color_hex="#F0883E",
            )

        if stats["broken_count"] > 0:
            self._add_recommendation_card(
                title=f"تم اكتشاف {stats['broken_count']} إدخالات برامج معطوبة في سجل ويندوز",
                desc="ملفات برنامج الإزالة محذوفة مسبقاً. يمكنك تنظيف السجل منها بأمان مع حفظ نسخة احتياطية.",
                btn_text="تنظيف الإدخالات المعطوبة",
                target_subpage="inventory",
                color_hex="#F85149",
            )

    def _add_recommendation_card(self, title: str, desc: str, btn_text: str, target_subpage: str, color_hex: str):
        card = QFrame()
        card.setStyleSheet(f"background: #161B22; border-right: 4px solid {color_hex}; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        h = QHBoxLayout(card)
        h.setContentsMargins(8, 8, 8, 8)

        v = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet(f"color: {color_hex}; font-weight: bold; font-size: 13px;")
        v.addWidget(t)
        d = QLabel(desc)
        d.setStyleSheet("color: #8B949E; font-size: 12px;")
        v.addWidget(d)
        h.addLayout(v, 1)

        btn = QPushButton(btn_text)
        btn.setStyleSheet("background: #21262D; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 6px 14px; font-weight: bold;")
        btn.clicked.connect(lambda: self.switch_subpage_requested.emit(target_subpage))
        h.addWidget(btn)

        self.recom_box.addWidget(card)
