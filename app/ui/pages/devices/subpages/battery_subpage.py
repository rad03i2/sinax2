# -*- coding: utf-8 -*-
"""
SINAX Battery & Power Subpage (صفحة البطارية وخطة الطاقة)
Displays laptop battery charge level, design capacity vs full charge capacity ratio,
cycle count, charging state, official Windows Battery Report generation,
and a clean graceful desktop empty state.
"""

import os
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.battery_service import BatteryService
from app.services.devices.hardware_models import BatteryDetails
from app.ui.icons import get_icon


class BatterySubpage(QWidget):
    """Subpage for battery telemetry, health ratio, and power management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._battery: Optional[BatteryDetails] = None
        self._timer: Optional[QTimer] = None
        self._init_ui()
        self.refresh_battery()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_battery)
        self._timer.start(5000)

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
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(24, 20, 24, 24)
        self.layout.setSpacing(18)

        # Header
        top_bar = QHBoxLayout()
        title = QLabel("البطارية وخطة الطاقة (Battery & Power)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.refresh_btn = QPushButton("  تحديث")
        self.refresh_btn.setIcon(get_icon("devices", "#FFFFFF", 16))
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #334155; color: #F8FAFC; border-radius: 6px;
                padding: 0 14px; font-weight: bold; border: 1px solid #475569;
            }
            QPushButton:hover { background: #475569; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_battery)
        top_bar.addWidget(self.refresh_btn)
        self.layout.addLayout(top_bar)

        # Desktop Empty State Container
        self.desktop_box = QFrame()
        self.desktop_box.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 30px;")
        d_layout = QVBoxLayout(self.desktop_box)
        d_layout.setAlignment(Qt.AlignCenter)
        d_layout.setSpacing(12)

        icon_pc = QLabel()
        icon_pc.setPixmap(get_icon("devices", "#38BDF8", 48).pixmap(48, 48))
        icon_pc.setAlignment(Qt.AlignCenter)
        d_layout.addWidget(icon_pc)

        lbl_pc_title = QLabel("كمبيوتر مكتبي (Desktop PC)")
        lbl_pc_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_pc_title.setStyleSheet("color: #F8FAFC; background: transparent;")
        lbl_pc_title.setAlignment(Qt.AlignCenter)
        d_layout.addWidget(lbl_pc_title)

        lbl_pc_desc = QLabel("لا توجد بطارية مثبتة في هذا الجهاز. الجهاز متصل ومزود بالتيار الكهربائي المباشر (AC Power).")
        lbl_pc_desc.setStyleSheet("color: #94A3B8; font-size: 13px; background: transparent;")
        lbl_pc_desc.setAlignment(Qt.AlignCenter)
        d_layout.addWidget(lbl_pc_desc)

        self.desktop_box.setVisible(False)
        self.layout.addWidget(self.desktop_box)

        # Laptop Battery Container
        self.laptop_container = QWidget()
        self.laptop_container.setStyleSheet("background: transparent;")
        l_layout = QVBoxLayout(self.laptop_container)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_layout.setSpacing(18)

        # 1. Gauge Card (Charge Level & Status)
        gauge_card = QFrame()
        gauge_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        g_layout = QVBoxLayout(gauge_card)
        g_layout.setSpacing(12)

        g_head = QHBoxLayout()
        self.charge_pct_lbl = QLabel("0%")
        self.charge_pct_lbl.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.charge_pct_lbl.setStyleSheet("color: #10B981; background: transparent;")
        g_head.addWidget(self.charge_pct_lbl)

        vbox_state = QVBoxLayout()
        vbox_state.setSpacing(4)
        self.state_lbl = QLabel("متصل بالشاحن")
        self.state_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.state_lbl.setStyleSheet("color: #F8FAFC; background: transparent;")
        self.source_lbl = QLabel("تيار كهربائي مباشر")
        self.source_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        vbox_state.addWidget(self.state_lbl)
        vbox_state.addWidget(self.source_lbl)
        g_head.addLayout(vbox_state)
        g_head.addStretch()

        self.time_rem_lbl = QLabel("الوقت المتبقي: —")
        self.time_rem_lbl.setStyleSheet("color: #CBD5E1; font-weight: bold; background: transparent;")
        g_head.addWidget(self.time_rem_lbl)
        g_layout.addLayout(g_head)

        self.charge_bar = QProgressBar()
        self.charge_bar.setFixedHeight(14)
        self.charge_bar.setTextVisible(False)
        self.charge_bar.setRange(0, 100)
        self.charge_bar.setValue(0)
        self.charge_bar.setStyleSheet("""
            QProgressBar { background: #0F172A; border: 1px solid #334155; border-radius: 4px; }
            QProgressBar::chunk { background: #10B981; border-radius: 3px; }
        """)
        g_layout.addWidget(self.charge_bar)
        l_layout.addWidget(gauge_card)

        # 2. Design Capacity vs Full Charge Ratio
        cap_card = QFrame()
        cap_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        c_layout = QVBoxLayout(cap_card)
        c_layout.setSpacing(14)

        c_title = QLabel("صحة البطارية وقدرة الشحن الفعلية (Health & Capacity Ratio)")
        c_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        c_title.setStyleSheet("color: #38BDF8; background: transparent;")
        c_layout.addWidget(c_title)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.lbl_design_cap = self._create_spec_item(grid, 0, 0, "سعة المصنع التصميمية:")
        self.lbl_full_cap = self._create_spec_item(grid, 0, 1, "السعة القصوى الحالية:")
        self.lbl_ratio = self._create_spec_item(grid, 0, 2, "نسبة كفاءة السعة:")
        self.lbl_cycles = self._create_spec_item(grid, 1, 0, "دورات الشحن (Cycle Count):")
        self.lbl_plan = self._create_spec_item(grid, 1, 1, "خطة الطاقة النشطة:")
        self.lbl_chem = self._create_spec_item(grid, 1, 2, "التركيب الكيميائي:")
        c_layout.addLayout(grid)
        l_layout.addWidget(cap_card)

        # 3. Official Battery Report Generator
        rep_card = QFrame()
        rep_card.setStyleSheet("background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 18px;")
        r_layout = QVBoxLayout(rep_card)
        r_layout.setSpacing(12)

        r_title = QLabel("تقرير البطارية الرسمي المفصل (Official Windows Battery Report)")
        r_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        r_title.setStyleSheet("color: #F8FAFC; background: transparent;")
        r_layout.addWidget(r_title)

        r_desc = QLabel(
            "تقوم أداة Windows powercfg بإنشاء سجل تاريخي مفصل لشحن وتفريغ البطارية "
            "خلال الأيام والأسابيع السابقة وتقديرات دقيقة لاستهلاك الطاقة."
        )
        r_desc.setStyleSheet("color: #94A3B8; background: transparent;")
        r_desc.setWordWrap(True)
        r_layout.addWidget(r_desc)

        btn_row = QHBoxLayout()
        self.btn_gen_rep = QPushButton("  إنشاء وفتح تقرير البطارية التفاعلي (HTML)")
        self.btn_gen_rep.setIcon(get_icon("devices", "#FFFFFF", 16))
        self.btn_gen_rep.setFixedHeight(36)
        self.btn_gen_rep.setStyleSheet("""
            QPushButton {
                background: #0078D4; color: #FFFFFF; border-radius: 6px;
                padding: 0 16px; font-weight: bold;
            }
            QPushButton:hover { background: #106EBE; }
        """)
        self.btn_gen_rep.clicked.connect(self._generate_report)
        btn_row.addWidget(self.btn_gen_rep)
        btn_row.addStretch()
        r_layout.addLayout(btn_row)

        self.rep_status_lbl = QLabel("")
        self.rep_status_lbl.setStyleSheet("color: #10B981; font-weight: bold; background: transparent;")
        r_layout.addWidget(self.rep_status_lbl)

        l_layout.addWidget(rep_card)
        self.layout.addWidget(self.laptop_container)

        self.layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_spec_item(self, grid: QGridLayout, row: int, col: int, label_text: str) -> QLabel:
        box = QVBoxLayout()
        box.setSpacing(4)
        t_lbl = QLabel(label_text)
        t_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        val_lbl = QLabel("—")
        val_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        val_lbl.setStyleSheet("color: #F8FAFC; background: transparent;")
        box.addWidget(t_lbl)
        box.addWidget(val_lbl)
        grid.addLayout(box, row, col)
        return val_lbl

    def refresh_battery(self):
        try:
            self._battery = BatteryService.get_battery_details()
            self._render()
        except Exception:
            pass

    def _render(self):
        if not self._battery or not self._battery.present:
            self.desktop_box.setVisible(True)
            self.laptop_container.setVisible(False)
            return

        self.desktop_box.setVisible(False)
        self.laptop_container.setVisible(True)

        self.charge_pct_lbl.setText(f"{self._battery.charge_percent}%")
        self.charge_bar.setValue(self._battery.charge_percent)
        self.state_lbl.setText(self._battery.charging_state)
        self.source_lbl.setText(self._battery.power_source)
        self.time_rem_lbl.setText(f"الوقت المتبقي: {self._battery.time_remaining_formatted}")

        des_str = f"{self._battery.design_capacity_mwh:,} mWh" if self._battery.design_capacity_mwh else "غير متوفر"
        full_str = f"{self._battery.full_charge_capacity_mwh:,} mWh" if self._battery.full_charge_capacity_mwh else "غير متوفر"
        self.lbl_design_cap.setText(des_str)
        self.lbl_full_cap.setText(full_str)

        if self._battery.capacity_ratio_percent is not None:
            self.lbl_ratio.setText(f"{self._battery.capacity_ratio_percent:.1f}%")
        else:
            self.lbl_ratio.setText("غير متوفرة")

        cyc_str = str(self._battery.cycle_count) if self._battery.cycle_count is not None else "غير متوفر"
        self.lbl_cycles.setText(cyc_str)
        self.lbl_plan.setText(self._battery.power_plan_name)
        self.lbl_chem.setText(self._battery.chemistry)

    def _generate_report(self):
        self.btn_gen_rep.setEnabled(False)
        self.rep_status_lbl.setText("جاري إنشاء تقرير البطارية عبر Windows powercfg...")

        import threading

        def worker():
            path = BatteryService.generate_official_battery_report()

            def done():
                self.btn_gen_rep.setEnabled(True)
                if path and os.path.exists(path):
                    self.rep_status_lbl.setText("✓ تم إنشاء التقرير بنجاح وفتحه في المتصفح.")
                    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
                else:
                    self.rep_status_lbl.setText("تعذر إنشاء تقرير البطارية.")

            QTimer.singleShot(0, done)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
