# -*- coding: utf-8 -*-
"""
SINAX RAM Hardware Subpage (صفحة الذاكرة العشوائية ومنافذ اللوحة)
Displays physical memory slots, module types (DDR4/DDR5), speeds,
motherboard max capacity, upgrade advisor, and memory integrity test tools.
"""

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.hardware_models import MemoryArrayInfo
from app.services.devices.memory_service import MemoryService
from app.ui.icons import get_icon
from app.ui.design_system import (
    ModernCard,
    MetricCard,
    PrimaryButton,
    SecondaryButton,
    SmoothScrollArea,
    ThemeTokens,
)


class RamSubpage(QWidget):
    """Subpage for slot-by-slot RAM inspection, upgradeability helper, and memory tests."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._array_info: Optional[MemoryArrayInfo] = None
        self._timer: Optional[QTimer] = None
        self._init_ui()
        self.refresh_ram()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(2000)

    def closeEvent(self, event):
        if self._timer and self._timer.isActive():
            self._timer.stop()
        super().closeEvent(event)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = SmoothScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)

        # Header
        top_bar = QHBoxLayout()
        title = QLabel("الذاكرة العشوائية ومنافذ التوسعة (RAM)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY};")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.refresh_btn = SecondaryButton("تحديث", icon_name="ram")
        self.refresh_btn.clicked.connect(self.refresh_ram)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Metric Tiles (Total Installed, Usable, Available, Usage)
        tiles_layout = QHBoxLayout()
        tiles_layout.setSpacing(14)

        self.tile_installed = MetricCard("إجمالي الذاكرة المركبة", "0 GB", accent_color=ThemeTokens.ACCENT_LIGHT, icon_name="ram")
        self.tile_usable = MetricCard("الذاكرة المتاحة للنظام", "0 GB", accent_color=ThemeTokens.SUCCESS, icon_name="ram")
        self.tile_cached = MetricCard("الذاكرة المخبأة (Cache)", "0 GB", accent_color=ThemeTokens.WARNING, icon_name="ram")
        self.tile_slots = MetricCard("المنافذ المستعملة", "0 / 0", accent_color=ThemeTokens.PURPLE, icon_name="devices")

        tiles_layout.addWidget(self.tile_installed)
        tiles_layout.addWidget(self.tile_usable)
        tiles_layout.addWidget(self.tile_cached)
        tiles_layout.addWidget(self.tile_slots)
        layout.addLayout(tiles_layout)

        # Usage Progress Bar
        bar_box = ModernCard(title="الاستهلاك اللحظي للذاكرة", subtitle="نسبة استخدام ذاكرة الوصول العشوائي الحالية")
        bar_header = QHBoxLayout()
        bar_lbl = QLabel("الاستهلاك الفعلي:")
        bar_lbl.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; font-weight: bold; background: transparent;")
        self.usage_val_lbl = QLabel("0%")
        self.usage_val_lbl.setStyleSheet(f"color: {ThemeTokens.ACCENT_LIGHT}; font-weight: bold; font-size: 14px; background: transparent;")
        bar_header.addWidget(bar_lbl)
        bar_header.addStretch()
        bar_header.addWidget(self.usage_val_lbl)
        bar_box.add_layout(bar_header)

        self.usage_bar = QProgressBar()
        self.usage_bar.setFixedHeight(12)
        self.usage_bar.setTextVisible(False)
        self.usage_bar.setRange(0, 100)
        self.usage_bar.setValue(0)
        self.usage_bar.setStyleSheet(f"""
            QProgressBar {{ background: {ThemeTokens.SURFACE_PRIMARY}; border: 1px solid {ThemeTokens.BORDER_LIGHT}; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {ThemeTokens.ACCENT_LIGHT}; border-radius: 3px; }}
        """)
        bar_box.add_widget(self.usage_bar)
        layout.addWidget(bar_box)

        # 2. Upgrade Helper Banner
        self.upgrade_card = ModernCard()
        self.upgrade_card.setStyleSheet(f"""
            ModernCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ThemeTokens.BG_SURFACE}, stop:1 #1E1B4B);
                border: 1px solid #4338CA;
                border-radius: {ThemeTokens.RADIUS_LG};
            }}
        """)
        up_layout = QHBoxLayout()
        up_layout.setContentsMargins(14, 12, 14, 12)
        up_icon = QLabel()
        up_icon.setPixmap(get_icon("info", "#818CF8", 22).pixmap(22, 22))
        up_layout.addWidget(up_icon)

        self.upgrade_text_lbl = QLabel("جاري فحص إمكانيات ترقية الذاكرة...")
        self.upgrade_text_lbl.setStyleSheet("color: #E0E7FF; font-size: 12px; background: transparent;")
        self.upgrade_text_lbl.setWordWrap(True)
        up_layout.addWidget(self.upgrade_text_lbl, 1)
        self.upgrade_card.add_layout(up_layout)
        layout.addWidget(self.upgrade_card)

        # 3. Physical Modules Table
        tbl_card = ModernCard(
            title="شرائح الذاكرة الفيزيائية المركبة (Memory Modules)",
            subtitle="المواصفات والترددات لكل منفذ في اللوحة الأم"
        )

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "المنفذ (Slot)", "السعة", "النوع", "السرعة (MT/s)", "الشركة المصنعة", "الشكل (Form)", "رقم القطعة (Part #)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(140)
        tbl_card.add_widget(self.table)
        layout.addWidget(tbl_card)

        # 4. Diagnostic Tools Card
        diag_card = ModernCard(
            title="فحص سلامة واستقرار الذاكرة (Memory Diagnostics)",
            subtitle="فحص خلايا الذاكرة العشوائية للتأكد من خلوها من الأخطاء والانهيارات"
        )

        diag_desc = QLabel(
            "تسمح لك هذه الأدوات بفحص خلايا الذاكرة العشوائية للتأكد من خلوها من الأخطاء والانهيارات "
            "سواء بفحص سريع فوري أو بجدولة أداة تشخيص الذاكرة الرسمية لـ Windows عند إعادة التشغيل."
        )
        diag_desc.setWordWrap(True)
        diag_desc.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; background: transparent; line-height: 1.4;")
        diag_card.add_widget(diag_desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        self.btn_quick_test = PrimaryButton("  فحص سريع لخلايا الذاكرة (In-Process)", icon_name="play")
        self.btn_quick_test.clicked.connect(self._run_quick_test)
        btn_row.addWidget(self.btn_quick_test)

        self.btn_mdsched = SecondaryButton("  أداة تشخيص ذاكرة Windows الرسمية (mdsched.exe)", icon_name="devices")
        self.btn_mdsched.clicked.connect(self._launch_mdsched)
        btn_row.addWidget(self.btn_mdsched)

        btn_row.addStretch()
        diag_card.add_layout(btn_row)

        self.diag_res_lbl = QLabel("")
        self.diag_res_lbl.setStyleSheet(f"color: {ThemeTokens.SUCCESS}; font-weight: bold; background: transparent;")
        diag_card.add_widget(self.diag_res_lbl)

        layout.addWidget(diag_card)
        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_tile(self, title: str, val: str, color_hex: str):
        return MetricCard(title=title, value=val, accent_color=color_hex, icon_name="ram")

    def refresh_ram(self):
        try:
            self._array_info = MemoryService.get_memory_array_info()
            self._render_ram(self._array_info)
        except Exception:
            pass

    def _render_ram(self, ram: MemoryArrayInfo):
        self.tile_installed.val_label.setText(ram.total_installed_formatted)  # type: ignore
        self.tile_usable.val_label.setText(ram.usable_formatted)              # type: ignore
        cached_gb = ram.cached_bytes / (1024 ** 3)
        self.tile_cached.val_label.setText(f"{cached_gb:.1f} GB")             # type: ignore
        self.tile_slots.val_label.setText(f"{ram.used_slots} / {ram.total_slots}")  # type: ignore

        self.usage_val_lbl.setText(f"{ram.usage_percent:.1f}%")
        self.usage_bar.setValue(int(ram.usage_percent))

        # Upgrade note
        self.upgrade_text_lbl.setText(ram.upgrade_note_ar)

        # Populate table
        self.table.setRowCount(len(ram.modules))
        for r, mod in enumerate(ram.modules):
            self.table.setItem(r, 0, QTableWidgetItem(mod.slot))
            self.table.setItem(r, 1, QTableWidgetItem(mod.capacity_formatted))
            self.table.setItem(r, 2, QTableWidgetItem(mod.memory_type))
            self.table.setItem(r, 3, QTableWidgetItem(str(mod.speed_mts)))
            self.table.setItem(r, 4, QTableWidgetItem(mod.manufacturer))
            self.table.setItem(r, 5, QTableWidgetItem(mod.form_factor))
            self.table.setItem(r, 6, QTableWidgetItem(mod.part_number))

    def _on_tick(self):
        import psutil
        try:
            vm = psutil.virtual_memory()
            self.usage_val_lbl.setText(f"{vm.percent:.1f}%")
            self.usage_bar.setValue(int(vm.percent))
        except Exception:
            pass

    def _run_quick_test(self):
        self.btn_quick_test.setEnabled(False)
        self.diag_res_lbl.setText("جاري إجراء فحص سريع لكتل الذاكرة...")
        res = MemoryService.run_quick_memory_test(alloc_mb=256)
        self.btn_quick_test.setEnabled(True)
        if res.get("passed"):
            self.diag_res_lbl.setText(f"✓ {res.get('message_ar')} ({res.get('tested_bytes_formatted')})")
            self.diag_res_lbl.setStyleSheet("color: #10B981; font-weight: bold; background: transparent;")
        else:
            self.diag_res_lbl.setText(f"⚠ {res.get('message_ar')}")
            self.diag_res_lbl.setStyleSheet("color: #EF4444; font-weight: bold; background: transparent;")

    def _launch_mdsched(self):
        confirm = QMessageBox.question(
            self,
            "أداة فحص الذاكرة الرسمية",
            "سيتم الآن فتح نافذة تشخيص ذاكرة Windows (mdsched.exe).\n"
            "تتيح لك الأداة إعادة تشغيل الجهاز فورًا وفحص الذاكرة قبل إقلاع النظام.\n\nهل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if confirm == QMessageBox.Yes:
            success = MemoryService.launch_windows_mdsched()
            if not success:
                QMessageBox.warning(self, "تنبيه", "تعذر تشغيل أداة mdsched.exe")
