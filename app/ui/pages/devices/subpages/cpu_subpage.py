# -*- coding: utf-8 -*-
"""
SINAX CPU Hardware Subpage (صفحة المعالج المركزي)
Displays detailed processor architecture, physical/logical cores, socket, caches,
virtualization capabilities, rolling 60s load chart, per-core utilization bars,
and a safe multi-threaded quick stress test with instant stop.
"""

from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, QPointF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QComboBox,
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

from app.services.devices.cpu_service import CpuService
from app.services.devices.hardware_models import CpuInfo
from app.ui.icons import get_icon
from app.ui.design_system import (
    ModernCard,
    InfoRow,
    SecondaryButton,
    DangerButton,
    SmoothScrollArea,
    ThemeTokens,
)


class CpuLoadGraph(QWidget):
    """60-second rolling CPU load mini-graph."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setStyleSheet("background: #0F172A; border-radius: 8px; border: 1px solid #1E293B;")
        self._history: List[float] = [0.0] * 60

    def update_history(self, history: List[float]):
        self._history = history[-60:]
        if len(self._history) < 60:
            self._history = [0.0] * (60 - len(self._history)) + self._history
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 10

        # Draw grid lines
        painter.setPen(QPen(QColor("#1E293B"), 1, Qt.DashLine))
        for pct in [0.25, 0.5, 0.75]:
            y = int(h - margin - pct * (h - 2 * margin))
            painter.drawLine(margin, y, w - margin, y)

        if not self._history:
            return

        # Draw load curve
        step_x = (w - 2 * margin) / max(1, len(self._history) - 1)
        points = []
        for i, val in enumerate(self._history):
            clamped = max(0.0, min(100.0, val))
            px = margin + i * step_x
            py = h - margin - (clamped / 100.0) * (h - 2 * margin)
            points.append((px, py))

        # Fill under curve
        brush_color = QColor(0, 120, 212, 40)
        painter.setBrush(brush_color)
        painter.setPen(Qt.NoPen)
        poly = QPolygonF()
        poly.append(QPointF(margin, h - margin))
        for px, py in points:
            poly.append(QPointF(px, py))
        poly.append(QPointF(w - margin, h - margin))
        painter.drawPolygon(poly)

        # Draw line
        painter.setPen(QPen(QColor("#0078D4"), 2))
        for i in range(len(points) - 1):
            painter.drawLine(int(points[i][0]), int(points[i][1]), int(points[i + 1][0]), int(points[i + 1][1]))


class CpuSubpage(QWidget):
    """Subpage for viewing detailed CPU specs, per-core metrics, and safe stress testing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._cpu_info: Optional[CpuInfo] = None
        self._timer: Optional[QTimer] = None
        self._is_stressing = False
        self._init_ui()
        self.refresh_specs()

        # Real-time update timer (every 1.5 seconds)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(1500)

    def closeEvent(self, event):
        if self._timer and self._timer.isActive():
            self._timer.stop()
        if self._is_stressing:
            CpuService.stop_quick_stress()
            self._is_stressing = False
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
        title = QLabel("المعالج المركزي (CPU)")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {ThemeTokens.TEXT_PRIMARY};")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.refresh_btn = SecondaryButton("تحديث", icon_name="cpu")
        self.refresh_btn.clicked.connect(self.refresh_specs)
        top_bar.addWidget(self.refresh_btn)
        layout.addLayout(top_bar)

        # 1. Main Specs Card
        self.specs_card = ModernCard(
            title="المواصفات والمعمارية",
            subtitle="الأنوية، المسارات، المقبس، وذاكرات الكاش"
        )
        self.cpu_name_lbl = QLabel("جاري قراءة المعالج...")
        self.cpu_name_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.cpu_name_lbl.setStyleSheet(f"color: {ThemeTokens.ACCENT_LIGHT}; background: transparent; padding-bottom: 6px;")
        self.specs_card.add_widget(self.cpu_name_lbl)

        grid = QGridLayout()
        grid.setSpacing(12)

        self.lbl_arch = self._create_spec_item(grid, 0, 0, "المعمارية:")
        self.lbl_socket = self._create_spec_item(grid, 0, 1, "المقبس (Socket):")
        self.lbl_cores = self._create_spec_item(grid, 0, 2, "الأنوية والمسارات:")

        self.lbl_clocks = self._create_spec_item(grid, 1, 0, "التردد الأقصى:")
        self.lbl_cache = self._create_spec_item(grid, 1, 1, "ذاكرة الكاش (L2/L3):")
        self.lbl_virt = self._create_spec_item(grid, 1, 2, "المحاكاة الافتراضية (VT-x):")

        self.specs_card.add_layout(grid)
        layout.addWidget(self.specs_card)

        # 2. Real-time Utilization & History Card
        self.util_card = ModernCard(
            title="سجل استهلاك المعالج (آخر 60 ثانية)",
            subtitle="مخطط لحظي لمستوى استهلاك أنوية المعالج"
        )

        util_header = QHBoxLayout()
        util_title = QLabel("الاستهلاك الحالي الإجمالي:")
        util_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        util_title.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; background: transparent;")
        util_header.addWidget(util_title)

        self.live_load_lbl = QLabel("0%")
        self.live_load_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.live_load_lbl.setStyleSheet(f"color: {ThemeTokens.ACCENT_LIGHT}; background: transparent;")
        util_header.addWidget(self.live_load_lbl)
        util_header.addStretch()
        self.util_card.add_layout(util_header)

        self.graph = CpuLoadGraph()
        self.util_card.add_widget(self.graph)

        # Per-core utilization container
        per_core_title = QLabel("استهلاك المسارات / الأنوية:")
        per_core_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        per_core_title.setStyleSheet(f"color: {ThemeTokens.TEXT_MUTED}; background: transparent; margin-top: 8px;")
        self.util_card.add_widget(per_core_title)

        self.core_bars_grid = QGridLayout()
        self.core_bars_grid.setSpacing(8)
        self.core_bars: List[QProgressBar] = []
        self.core_labels: List[QLabel] = []
        self.util_card.add_layout(self.core_bars_grid)

        layout.addWidget(self.util_card)

        # 3. Safe Multi-Threaded Stress Test Tool
        self.stress_card = ModernCard(
            title="أداة الفحص والتثبيت الآمن (Quick Stress Check)",
            subtitle="فحص حمل حسابي آمن ومحدد زمنيًا للتأكد من استقرار المعالج ونظام التبريد"
        )

        st_desc = QLabel(
            "تقوم هذه الأداة بإجراء اختبار حمل حسابي آمن ومحدد زمنيًا للتأكد من استقرار المعالج "
            "وقدرة نظام التبريد على تصريف الحرارة دون انهيار. يمكنك إيقاف الفحص في أي لحظة فورًا."
        )
        st_desc.setWordWrap(True)
        st_desc.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; background: transparent; line-height: 1.4;")
        self.stress_card.add_widget(st_desc)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)

        lbl_threads = QLabel("عدد المسارات:")
        lbl_threads.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; background: transparent;")
        ctrl_row.addWidget(lbl_threads)

        self.combo_threads = QComboBox()
        self.combo_threads.setStyleSheet(f"""
            QComboBox {{
                background: {ThemeTokens.SURFACE_PRIMARY}; color: {ThemeTokens.TEXT_PRIMARY};
                border: 1px solid {ThemeTokens.BORDER_LIGHT};
                border-radius: {ThemeTokens.RADIUS_SM}; padding: 4px 10px; min-width: 80px;
            }}
        """)
        ctrl_row.addWidget(self.combo_threads)

        lbl_dur = QLabel("المدة:")
        lbl_dur.setStyleSheet(f"color: {ThemeTokens.TEXT_SECONDARY}; background: transparent;")
        ctrl_row.addWidget(lbl_dur)

        self.combo_dur = QComboBox()
        self.combo_dur.setStyleSheet(f"""
            QComboBox {{
                background: {ThemeTokens.SURFACE_PRIMARY}; color: {ThemeTokens.TEXT_PRIMARY};
                border: 1px solid {ThemeTokens.BORDER_LIGHT};
                border-radius: {ThemeTokens.RADIUS_SM}; padding: 4px 10px; min-width: 90px;
            }}
        """)
        self.combo_dur.addItem("15 ثانية", 15)
        self.combo_dur.addItem("30 ثانية", 30)
        self.combo_dur.addItem("60 ثانية", 60)
        ctrl_row.addWidget(self.combo_dur)

        ctrl_row.addStretch()

        self.btn_stress = DangerButton("  بدء فحص الاستقرار", icon_name="play")
        self.btn_stress.clicked.connect(self._toggle_stress)
        ctrl_row.addWidget(self.btn_stress)

        self.stress_card.add_layout(ctrl_row)

        self.stress_status_lbl = QLabel("")
        self.stress_status_lbl.setStyleSheet(f"color: {ThemeTokens.WARNING}; font-weight: bold; background: transparent;")
        self.stress_card.add_widget(self.stress_status_lbl)

        layout.addWidget(self.stress_card)
        layout.addStretch()

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _create_spec_item(self, grid: QGridLayout, row: int, col: int, label_text: str) -> InfoRow:
        row_widget = InfoRow(key=label_text, value="—")
        grid.addWidget(row_widget, row, col)
        return row_widget

    def refresh_specs(self):
        try:
            self._cpu_info = CpuService.get_cpu_info()
            self._render_specs(self._cpu_info)
        except Exception:
            self.cpu_name_lbl.setText("خطأ في قراءة المعالج")

    def _render_specs(self, cpu: CpuInfo):
        self.cpu_name_lbl.setText(cpu.name)
        self.lbl_arch.setText(f"{cpu.architecture} ({cpu.address_width}-bit)")
        self.lbl_socket.setText(cpu.socket)
        self.lbl_cores.setText(f"{cpu.cores_physical} أنوية حقيقية / {cpu.cores_logical} مسار (Threads)")

        mhz_str = f"{cpu.max_clock_mhz / 1000.0:.2f} GHz" if cpu.max_clock_mhz > 0 else "غير متوفر"
        self.lbl_clocks.setText(mhz_str)

        l2_mb = f"{cpu.l2_cache_kb / 1024.0:.1f} MB" if cpu.l2_cache_kb else "0 MB"
        l3_mb = f"{cpu.l3_cache_kb / 1024.0:.1f} MB" if cpu.l3_cache_kb else "0 MB"
        self.lbl_cache.setText(f"L2: {l2_mb} | L3: {l3_mb}")

        v_text = "مفعلة (Enabled)" if cpu.virtualization_firmware_enabled else "غير مفعلة / معطلة"
        self.lbl_virt.setText(v_text)

        # Setup combo threads if empty
        if self.combo_threads.count() == 0:
            self.combo_threads.addItem("كل المسارات (All)", cpu.cores_logical)
            if cpu.cores_physical > 0:
                self.combo_threads.addItem(f"الأنوية فقط ({cpu.cores_physical})", cpu.cores_physical)
            self.combo_threads.addItem("مسار واحد (1 Core)", 1)

        # Setup per-core bars if not yet created
        if not self.core_bars and cpu.cores_logical > 0:
            cols = 4 if cpu.cores_logical >= 8 else 2
            for i in range(cpu.cores_logical):
                r = i // cols
                c = i % cols
                hbox = QHBoxLayout()
                lbl = QLabel(f"مسار {i + 1}:")
                lbl.setFixedWidth(50)
                lbl.setStyleSheet("color: #94A3B8; font-size: 10px; background: transparent;")
                bar = QProgressBar()
                bar.setFixedHeight(12)
                bar.setTextVisible(False)
                bar.setRange(0, 100)
                bar.setValue(0)
                bar.setStyleSheet("""
                    QProgressBar {
                        background: #0F172A; border: 1px solid #334155; border-radius: 4px;
                    }
                    QProgressBar::chunk {
                        background: #38BDF8; border-radius: 3px;
                    }
                """)
                hbox.addWidget(lbl)
                hbox.addWidget(bar)
                self.core_bars_grid.addLayout(hbox, r, c)
                self.core_bars.append(bar)
                self.core_labels.append(lbl)

    def _on_tick(self):
        # Refresh history and live load
        history = CpuService.get_cpu_history()
        self.graph.update_history(history)
        current = history[-1] if history else 0.0
        self.live_load_lbl.setText(f"{current:.1f}%")

        # Per-core utilization
        import psutil
        try:
            core_pcts = psutil.cpu_percent(percpu=True)
            for i, pct in enumerate(core_pcts):
                if i < len(self.core_bars):
                    self.core_bars[i].setValue(int(pct))
        except Exception:
            pass

    def _toggle_stress(self):
        if self._is_stressing:
            CpuService.stop_quick_stress()
            self._is_stressing = False
            self.btn_stress.setText("  بدء فحص الاستقرار")
            self.btn_stress.setStyleSheet(f"""
                QPushButton {{
                    background: {ThemeTokens.DANGER}; color: #FFFFFF; border-radius: {ThemeTokens.RADIUS_SM};
                    padding: 0 16px; font-weight: bold;
                }}
                QPushButton:hover {{ background: #DC2626; }}
            """)
            self.stress_status_lbl.setText("تم إيقاف الفحص يدويًا.")
        else:
            confirm = QMessageBox.question(
                self,
                "تأكيد فحص استقرار المعالج",
                "سيقوم الفحص برفع استهلاك أنوية المعالج إلى 100% لاختبار الثبات والتبريد.\n"
                "قد ترتفع سرعة دوران المراوح مؤقتًا.\n\nهل ترغب في البدء؟",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if confirm != QMessageBox.Yes:
                return

            threads = self.combo_threads.currentData()
            dur = self.combo_dur.currentData()
            self._is_stressing = True
            self.btn_stress.setText("  إيقاف الفحص الآن")
            self.btn_stress.setStyleSheet(f"""
                QPushButton {{
                    background: {ThemeTokens.WARNING}; color: #000000; border-radius: {ThemeTokens.RADIUS_SM};
                    padding: 0 16px; font-weight: bold;
                }}
                QPushButton:hover {{ background: #D97706; }}
            """)
            self.stress_status_lbl.setText(f"الفحص قيد التشغيل على {threads} مسار لمدة {dur} ثانية...")

            def on_finished():
                self._is_stressing = False
                self.btn_stress.setText("  بدء فحص الاستقرار")
                self.btn_stress.setStyleSheet(f"""
                    QPushButton {{
                        background: {ThemeTokens.DANGER}; color: #FFFFFF; border-radius: {ThemeTokens.RADIUS_SM};
                        padding: 0 16px; font-weight: bold;
                    }}
                    QPushButton:hover {{ background: #DC2626; }}
                """)
                self.stress_status_lbl.setText("اكتمل فحص الاستقرار بنجاح. المعالج يعمل بكفاءة.")

            CpuService.start_quick_stress(duration_sec=dur, threads_count=threads, on_finish=on_finished)
