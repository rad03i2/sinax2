# -*- coding: utf-8 -*-
"""
SINAX GPU Hardware Subpage (صفحة كرت الشاشة والرسوميات)
Displays multi-GPU cards, dedicated vs shared VRAM memory bars,
clock speeds, temperatures, driver details, and real-time utilization.
"""

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.devices.gpu_service import GpuService
from app.services.devices.hardware_models import GpuInfo
from app.ui.icons import get_icon


class GpuSubpage(QWidget):
    """Subpage for inspecting graphics adapters (Integrated and Dedicated GPUs)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._gpus: List[GpuInfo] = []
        self._current_index = 0
        self._timer: Optional[QTimer] = None
        self._init_ui()
        self.refresh_gpus()

        # Real-time metrics timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(2000)

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
        layout.setSpacing(18)

        # Header
        top_bar = QHBoxLayout()
        title = QLabel("كرت الشاشة ومعالج الرسوميات (GPU)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.gpu_selector = QComboBox()
        self.gpu_selector.setStyleSheet("""
            QComboBox {
                background: #1E293B; color: #F8FAFC; border: 1px solid #334155;
                border-radius: 6px; padding: 6px 14px; font-weight: bold; min-width: 220px;
            }
        """)
        self.gpu_selector.currentIndexChanged.connect(self._on_gpu_selected)
        top_bar.addWidget(self.gpu_selector)

        self.refresh_btn = QPushButton("  تحديث")
        self.refresh_btn.setIcon(get_icon("gpu", "#FFFFFF", 16))
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #334155; color: #F8FAFC; border-radius: 6px;
                padding: 0 14px; font-weight: bold; border: 1px solid #475569;
            }
            QPushButton:hover { background: #475569; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_gpus)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Main GPU Card
        self.main_card = QFrame()
        self.main_card.setStyleSheet("""
            QFrame {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 18px;
            }
        """)
        card_layout = QVBoxLayout(self.main_card)
        card_layout.setSpacing(14)

        card_header = QHBoxLayout()
        self.gpu_name_lbl = QLabel("جاري فحص كرت الشاشة...")
        self.gpu_name_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.gpu_name_lbl.setStyleSheet("color: #38BDF8; background: transparent;")
        card_header.addWidget(self.gpu_name_lbl)
        card_header.addStretch()

        self.gpu_type_badge = QLabel("مدمج (Integrated)")
        self.gpu_type_badge.setStyleSheet("""
            background: #0284C7; color: #FFFFFF; border-radius: 6px;
            padding: 4px 10px; font-size: 11px; font-weight: bold;
        """)
        card_header.addWidget(self.gpu_type_badge)
        card_layout.addLayout(card_header)

        # Specs Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        self.lbl_vendor = self._create_spec_item(grid, 0, 0, "الشركة المصنعة:")
        self.lbl_driver_ver = self._create_spec_item(grid, 0, 1, "إصدار التعريف:")
        self.lbl_driver_date = self._create_spec_item(grid, 0, 2, "تاريخ التعريف:")

        self.lbl_res = self._create_spec_item(grid, 1, 0, "الدقة الحالية:")
        self.lbl_refresh = self._create_spec_item(grid, 1, 1, "معدل التحديث:")
        self.lbl_temp = self._create_spec_item(grid, 1, 2, "درجة الحرارة:")

        card_layout.addLayout(grid)
        layout.addWidget(self.main_card)

        # 2. Memory & Utilization Card
        mem_card = QFrame()
        mem_card.setStyleSheet("""
            QFrame {
                background: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 18px;
            }
        """)
        mem_layout = QVBoxLayout(mem_card)
        mem_layout.setSpacing(14)

        mem_title = QLabel("ذاكرة الفيديو واستهلاك المعالج الرسومي (VRAM & Load)")
        mem_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        mem_title.setStyleSheet("color: #F8FAFC; background: transparent;")
        mem_layout.addWidget(mem_title)

        # Dedicated VRAM
        vram_row = QHBoxLayout()
        lbl_vram_t = QLabel("ذاكرة الفيديو المخصصة (Dedicated VRAM):")
        lbl_vram_t.setStyleSheet("color: #CBD5E1; background: transparent;")
        self.lbl_vram_val = QLabel("0 GB")
        self.lbl_vram_val.setStyleSheet("color: #38BDF8; font-weight: bold; background: transparent;")
        vram_row.addWidget(lbl_vram_t)
        vram_row.addStretch()
        vram_row.addWidget(self.lbl_vram_val)
        mem_layout.addLayout(vram_row)

        self.bar_vram = QProgressBar()
        self.bar_vram.setFixedHeight(14)
        self.bar_vram.setTextVisible(False)
        self.bar_vram.setRange(0, 100)
        self.bar_vram.setValue(0)
        self.bar_vram.setStyleSheet("""
            QProgressBar {
                background: #0F172A; border: 1px solid #334155; border-radius: 4px;
            }
            QProgressBar::chunk {
                background: #0078D4; border-radius: 3px;
            }
        """)
        mem_layout.addWidget(self.bar_vram)

        # Shared Memory
        shared_row = QHBoxLayout()
        lbl_shared_t = QLabel("الذاكرة المشتركة مع النظام (Shared System Memory):")
        lbl_shared_t.setStyleSheet("color: #CBD5E1; background: transparent;")
        self.lbl_shared_val = QLabel("0 GB")
        self.lbl_shared_val.setStyleSheet("color: #94A3B8; font-weight: bold; background: transparent;")
        shared_row.addWidget(lbl_shared_t)
        shared_row.addStretch()
        shared_row.addWidget(self.lbl_shared_val)
        mem_layout.addLayout(shared_row)

        # Real-time Load (if available)
        load_row = QHBoxLayout()
        lbl_load_t = QLabel("نسبة الاستهلاك الحالية للكرت:")
        lbl_load_t.setStyleSheet("color: #CBD5E1; background: transparent;")
        self.lbl_load_val = QLabel("غير متوفرة")
        self.lbl_load_val.setStyleSheet("color: #F59E0B; font-weight: bold; background: transparent;")
        load_row.addWidget(lbl_load_t)
        load_row.addStretch()
        load_row.addWidget(self.lbl_load_val)
        mem_layout.addLayout(load_row)

        self.bar_load = QProgressBar()
        self.bar_load.setFixedHeight(14)
        self.bar_load.setTextVisible(False)
        self.bar_load.setRange(0, 100)
        self.bar_load.setValue(0)
        self.bar_load.setStyleSheet("""
            QProgressBar {
                background: #0F172A; border: 1px solid #334155; border-radius: 4px;
            }
            QProgressBar::chunk {
                background: #F59E0B; border-radius: 3px;
            }
        """)
        mem_layout.addWidget(self.bar_load)

        layout.addWidget(mem_card)

        # 3. Honest Advice Card
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 8px;
                padding: 12px 16px;
            }
        """)
        info_layout = QHBoxLayout(info_card)
        info_icon = QLabel()
        info_icon.setPixmap(get_icon("info", "#94A3B8", 20).pixmap(20, 20))
        info_layout.addWidget(info_icon)
        info_text = QLabel(
            "ملاحظة: كروت الرسوميات المدمجة (Intel UHD / Iris أو AMD Radeon Vega) تشارك ذاكرة النظام "
            "بشكل ديناميكي حسب حاجة التطبيقات. تتوفر قراءات حرارة واستهلاك دقيقة للكروت المنفصلة (NVIDIA / AMD) عبر واجهاتها الرسمية."
        )
        info_text.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text, 1)
        layout.addWidget(info_card)

        layout.addStretch()
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

    def refresh_gpus(self):
        try:
            self._gpus = GpuService.get_gpu_list()
            self.gpu_selector.blockSignals(True)
            self.gpu_selector.clear()
            for idx, gpu in enumerate(self._gpus):
                self.gpu_selector.addItem(f"{gpu.name} ({gpu.gpu_type})", idx)
            self.gpu_selector.blockSignals(False)

            if self._gpus:
                self._render_gpu(self._gpus[0])
            else:
                self.gpu_name_lbl.setText("لم يتم العثور على كروت شاشة")
        except Exception:
            self.gpu_name_lbl.setText("خطأ في قراءة كرت الشاشة")

    def _on_gpu_selected(self, index: int):
        if 0 <= index < len(self._gpus):
            self._current_index = index
            self._render_gpu(self._gpus[index])

    def _render_gpu(self, gpu: GpuInfo):
        self.gpu_name_lbl.setText(gpu.name)
        self.lbl_vendor.setText(gpu.vendor)
        self.lbl_driver_ver.setText(gpu.driver_version)
        self.lbl_driver_date.setText(gpu.driver_date)
        self.lbl_res.setText(gpu.current_resolution)
        self.lbl_refresh.setText(f"{gpu.refresh_rate_hz} Hz" if gpu.refresh_rate_hz > 0 else "غير متوفر")

        temp_str = f"{gpu.temperature_c:.0f}°C" if gpu.temperature_c is not None else "غير متوفرة"
        self.lbl_temp.setText(temp_str)

        self.gpu_type_badge.setText(gpu.gpu_type)
        if "منفصل" in gpu.gpu_type:
            self.gpu_type_badge.setStyleSheet("background: #10B981; color: #FFFFFF; border-radius: 6px; padding: 4px 10px; font-weight: bold;")
        else:
            self.gpu_type_badge.setStyleSheet("background: #0284C7; color: #FFFFFF; border-radius: 6px; padding: 4px 10px; font-weight: bold;")

        # VRAM
        self.lbl_vram_val.setText(gpu.dedicated_vram_formatted)
        if gpu.dedicated_vram_bytes > 0:
            self.bar_vram.setValue(100)
        else:
            self.bar_vram.setValue(0)

        shared_gb = gpu.shared_memory_bytes / (1024 ** 3)
        self.lbl_shared_val.setText(f"{shared_gb:.1f} GB" if shared_gb > 0 else "تلقائية")

        # Load
        if gpu.load_percent is not None:
            self.lbl_load_val.setText(f"{gpu.load_percent:.0f}%")
            self.bar_load.setValue(int(gpu.load_percent))
        else:
            self.lbl_load_val.setText("غير متوفرة")
            self.bar_load.setValue(0)

    def _on_tick(self):
        if not self._gpus or self._current_index >= len(self._gpus):
            return
        gpu = self._gpus[self._current_index]
        live = GpuService.get_gpu_live_metrics(gpu.id)
        if live.get("temperature_c") is not None:
            self.lbl_temp.setText(f"{live['temperature_c']:.0f}°C")
        if live.get("load_percent") is not None:
            self.lbl_load_val.setText(f"{live['load_percent']:.0f}%")
            self.bar_load.setValue(int(live["load_percent"]))
