# -*- coding: utf-8 -*-
"""
SINAX System & Storage - Device Specs & Reports Subpage (مواصفات الجهاز)
Comprehensive hardware, firmware, and OS diagnostics with multi-format export:
- OS & Architecture & Uptime
- CPU, Memory, GPU, Motherboard & BIOS
- Battery and Power health
- Export report to TXT, JSON, CSV, and HTML
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.system_storage.device_info_service import DeviceInfoService, SystemSpecs
from app.ui.icons import get_icon


class DeviceSubpage(QWidget):
    """System specifications and diagnostic export subpage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.specs: Optional[SystemSpecs] = None
        self._init_ui()
        self.refresh_specs()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Top Bar: Export Options
        top_bar = QFrame()
        top_bar.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 10px;")
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(16, 8, 16, 8)
        tb_lay.setSpacing(12)

        lbl_title = QLabel("تقرير مواصفات العتاد والنظام")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_title.setStyleSheet("color: #F0F6FC;")
        tb_lay.addWidget(lbl_title)

        tb_lay.addStretch(1)

        # Export buttons
        formats = [("TXT", "txt"), ("JSON", "json"), ("CSV", "csv"), ("HTML", "html")]
        for label, fmt in formats:
            btn = QPushButton(f"تصدير {label}")
            btn.setStyleSheet("""
                QPushButton {
                    background: #21262D; color: #58A6FF; border: 1px solid #30363D;
                    border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 11px;
                }
                QPushButton:hover { background: #30363D; border-color: #58A6FF; }
            """)
            btn.clicked.connect(lambda _, f=fmt: self._export_as(f))
            tb_lay.addWidget(btn)

        main_layout.addWidget(top_bar)

        # Scroll area for specification sections
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(14)

        scroll.setWidget(self.content)
        main_layout.addWidget(scroll, 1)

    def refresh_specs(self):
        self.specs = DeviceInfoService.get_system_specs()
        self._populate_grid()

    def _populate_grid(self):
        # Clear
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.specs:
            return

        s = self.specs

        # 1. OS Card
        c_os = self._create_card(
            title="نظام التشغيل والبيئة",
            icon="storage",
            rows=[
                ("الإصدار", f"{s.os_name} {s.os_release} ({s.os_arch})"),
                ("رقم البناء (Build)", s.os_version),
                ("اسم الكمبيوتر", s.computer_name),
                ("المستخدم الحالي", s.username),
                ("مدة التشغيل (Uptime)", s.uptime_formatted),
                ("تاريخ آخر إقلاع", s.boot_time),
            ]
        )
        self.grid.addWidget(c_os, 0, 0)

        # 2. Processor (CPU) Card
        c_cpu = self._create_card(
            title="المعالج المركزي (CPU)",
            icon="cpu",
            rows=[
                ("الموديل", s.cpu_name),
                ("الأنوية الفيزيائية", f"{s.cpu_cores_physical} أنوية حقيقية"),
                ("الأنوية المنطقية", f"{s.cpu_cores_logical} خيط معالجة (Threads)"),
                ("التردد الأقصى", f"{s.cpu_freq_max_mhz:.0f} MHz" if s.cpu_freq_max_mhz > 0 else "غير متوفر"),
                ("المعمارية", s.cpu_arch),
            ]
        )
        self.grid.addWidget(c_cpu, 0, 1)

        # 3. Memory (RAM) Card
        c_ram = self._create_card(
            title="الذاكرة العشوائية (RAM)",
            icon="ram",
            rows=[
                ("الذاكرة الكلية المثبتة", s.ram_total_formatted),
                ("الذاكرة المتاحة حالياً", s.ram_available_formatted),
                ("ملف التبديل (Pagefile)", s.swap_total_formatted),
            ]
        )
        self.grid.addWidget(c_ram, 1, 0)

        # 4. Motherboard & BIOS Card
        c_mb = self._create_card(
            title="اللوحة الأم والـ BIOS",
            icon="storage",
            rows=[
                ("الشركة المصنعة", s.motherboard_manufacturer),
                ("موديل اللوحة الأم", s.motherboard_product),
                ("إصدار BIOS", s.bios_version),
            ]
        )
        self.grid.addWidget(c_mb, 1, 1)

        # 5. GPUs Card
        gpu_rows = []
        for idx, g in enumerate(s.gpus):
            gpu_rows.append((f"بطاقة الرسوميات #{idx+1}", f"{g.name}"))
            gpu_rows.append((f"إصدار التعريف", g.driver_version))
            gpu_rows.append((f"ذاكرة الفيديو (VRAM)", g.vram_formatted))

        if not gpu_rows:
            gpu_rows.append(("بطاقة الرسوميات", "محول شاشة قياسي"))

        c_gpu = self._create_card(
            title="بطاقات العرض والرسوميات (GPU)",
            icon="chart",
            rows=gpu_rows
        )
        self.grid.addWidget(c_gpu, 2, 0)

        # 6. Battery / Power Card
        bat_rows = []
        if s.battery and s.battery.has_battery:
            plug_str = "متصل بالشاحن (AC)" if s.battery.is_plugged else "يعمل على البطارية"
            bat_rows.append(("حالة الشحن", plug_str))
            bat_rows.append(("نسبة البطارية", f"{s.battery.percent}%"))
            if s.battery.time_left_formatted:
                bat_rows.append(("الوقت المتبقي المقدر", s.battery.time_left_formatted))
        else:
            bat_rows.append(("نوع الطاقة", "حاسوب مكتبي أو غير مزود ببطارية"))

        c_bat = self._create_card(
            title="الطاقة والبطارية",
            icon="performance",
            rows=bat_rows
        )
        self.grid.addWidget(c_bat, 2, 1)

    def _create_card(self, title: str, icon: str, rows: list) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #161B22; border: 1px solid #30363D;
                border-radius: 10px; padding: 14px;
            }
        """)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        # Title
        t_row = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(get_icon(icon, color="#58A6FF").pixmap(20, 20))
        t_row.addWidget(ico)

        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl.setStyleSheet("color: #F0F6FC;")
        t_row.addWidget(lbl)
        t_row.addStretch(1)
        lay.addLayout(t_row)

        # Rows
        for r_name, r_val in rows:
            row_box = QHBoxLayout()
            lbl_k = QLabel(r_name)
            lbl_k.setStyleSheet("color: #8B949E; font-size: 11px;")
            lbl_v = QLabel(str(r_val))
            lbl_v.setStyleSheet("color: #F0F6FC; font-weight: 500; font-size: 11px;")
            lbl_v.setWordWrap(True)
            lbl_v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            row_box.addWidget(lbl_k)
            row_box.addStretch(1)
            row_box.addWidget(lbl_v)
            lay.addLayout(row_box)

        return frame

    def _export_as(self, fmt: str):
        if not self.specs:
            return
        ext_map = {"txt": "نص (*.txt)", "json": "JSON (*.json)", "csv": "CSV (*.csv)", "html": "صفحة ويب (*.html)"}
        path, _ = QFileDialog.getSaveFileName(self, f"تصدير تقرير النظام بصيغة {fmt.upper()}", f"SINAX_System_Report.{fmt}", ext_map.get(fmt, "*.*"))
        if path:
            ok = DeviceInfoService.export_report(self.specs, path, format_type=fmt)
            if ok:
                QMessageBox.information(self, "نجاح التصدير", f"تم حفظ التقرير بنجاح في:\n{path}")
            else:
                QMessageBox.critical(self, "خطأ", "فشل تصدير التقرير.")
