# -*- coding: utf-8 -*-
"""
SINAX System & Storage - Overview Subpage (لوحة القيادة العامة)
Answers the master question: "أين ذهبت مساحة جهازي؟" with:
- Hero quick-scan banner
- Drive capacity cards (C:, D:) with donut gauges
- Quick diagnostic metric badges
- Smart recommendation cards with actionable triggers
"""

from typing import Callable, List, Optional

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

from app.services.system_storage.cleanup_service import CleanupService
from app.services.system_storage.disk_health_service import DiskHealthService, LogicalDriveInfo
from app.services.system_storage.performance_service import PerformanceService
from app.services.system_storage.recommendation_engine import RecommendationCard, RecommendationEngine
from app.services.system_storage.startup_service import StartupService
from app.services.system_storage.storage_scanner import format_bytes
from app.ui.icons import get_icon
from app.ui.pages.system_storage.chart_widgets import CapacityGaugeWidget


class DriveCard(QFrame):
    """Card displaying a single logical drive partition with Donut gauge and stats."""

    def __init__(self, drive: LogicalDriveInfo, on_analyze: Optional[Callable[[str], None]] = None, parent=None):
        super().__init__(parent)
        self.drive = drive
        self.on_analyze = on_analyze
        self.setObjectName("DriveCard")
        self.setStyleSheet("""
            #DriveCard {
                background: #161B22;
                border: 1px solid #30363D;
                border-radius: 12px;
                padding: 12px;
            }
            #DriveCard:hover {
                border-color: #58A6FF;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header: Drive Letter + Label
        header = QHBoxLayout()
        lbl_drive = QLabel(f"القرص {self.drive.drive_letter}")
        lbl_drive.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_drive.setStyleSheet("color: #58A6FF;")
        header.addWidget(lbl_drive)

        lbl_vol = QLabel(f"({self.drive.volume_label or 'قرص محلي'}) - {self.drive.filesystem}")
        lbl_vol.setStyleSheet("color: #8B949E; font-size: 11px;")
        header.addWidget(lbl_vol)
        header.addStretch(1)

        if self.drive.is_system_drive:
            lbl_sys = QLabel("قرص النظام")
            lbl_sys.setStyleSheet("""
                background: rgba(88, 166, 255, 0.15); color: #58A6FF;
                border: 1px solid rgba(88, 166, 255, 0.3); border-radius: 4px;
                padding: 2px 8px; font-size: 10px; font-weight: bold;
            """)
            header.addWidget(lbl_sys)

        layout.addLayout(header)

        # Gauge & Stats row
        row = QHBoxLayout()
        row.setSpacing(16)

        self.gauge = CapacityGaugeWidget(
            title=self.drive.drive_letter,
            total_bytes=self.drive.total_bytes,
            used_bytes=self.drive.used_bytes,
            parent=self
        )
        self.gauge.setFixedSize(140, 140)
        row.addWidget(self.gauge)

        # Stats Column
        stats_col = QVBoxLayout()
        stats_col.setSpacing(6)

        free_lbl = QLabel(f"المساحة الحرة: <b style='color:#3FB950;'>{format_bytes(self.drive.free_bytes)}</b>")
        free_lbl.setStyleSheet("font-size: 12px; color: #C9D1D9;")
        stats_col.addWidget(free_lbl)

        used_lbl = QLabel(f"المساحة المستخدمة: <b>{format_bytes(self.drive.used_bytes)}</b>")
        used_lbl.setStyleSheet("font-size: 12px; color: #C9D1D9;")
        stats_col.addWidget(used_lbl)

        tot_lbl = QLabel(f"السعة الإجمالية: <b>{format_bytes(self.drive.total_bytes)}</b>")
        tot_lbl.setStyleSheet("font-size: 12px; color: #8B949E;")
        stats_col.addWidget(tot_lbl)

        stats_col.addStretch(1)

        btn_scan = QPushButton("تحليل تفصيلي")
        btn_scan.setIcon(get_icon("treemap", color="#F0F6FC"))
        btn_scan.setStyleSheet("""
            QPushButton {
                background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 14px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background: #30363D; border-color: #58A6FF; color: #58A6FF; }
        """)
        if self.on_analyze:
            btn_scan.clicked.connect(lambda: self.on_analyze(self.drive.drive_letter))
        stats_col.addWidget(btn_scan)

        row.addLayout(stats_col, 1)
        layout.addLayout(row)


class OverviewSubpage(QWidget):
    """Main dashboard tab for System & Storage."""

    navigate_requested = Signal(str, object)  # (subpage_key, optional_param)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area for responsive dashboard
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(20)

        # 1. Hero Card: "أين ذهبت مساحة جهازي؟"
        hero_card = QFrame()
        hero_card.setObjectName("HeroCard")
        hero_card.setLayoutDirection(Qt.RightToLeft)
        hero_card.setStyleSheet("""
            #HeroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1F2937, stop:1 #111827);
                border: 1px solid rgba(88, 166, 255, 0.4);
                border-radius: 14px;
            }
        """)
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(20)

        hero_text_col = QVBoxLayout()
        hero_text_col.setSpacing(6)

        hero_title = QLabel("أين ذهبت مساحة جهازي؟")
        hero_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        hero_title.setStyleSheet("color: #58A6FF;")
        hero_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hero_text_col.addWidget(hero_title)

        hero_sub = QLabel("فحص فوري وتحليل شجري وتفاعلي لمجلدات وملفات ويندوز لمعرفة أكبر مستهلكي القرص بدقة.")
        hero_sub.setStyleSheet("color: #8B949E; font-size: 12px;")
        hero_sub.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hero_sub.setWordWrap(True)
        hero_text_col.addWidget(hero_sub)

        hero_layout.addLayout(hero_text_col, 1)

        btn_hero_scan = QPushButton("فحص شامل فوري للقرص C:")
        btn_hero_scan.setIcon(get_icon("storage", color="#FFFFFF"))
        btn_hero_scan.setFixedHeight(42)
        btn_hero_scan.setStyleSheet("""
            QPushButton {
                background: #1F6FEB; color: #FFFFFF; border: none;
                border-radius: 8px; padding: 8px 22px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #388BFD; }
        """)
        btn_hero_scan.clicked.connect(lambda: self.navigate_requested.emit("analyzer", "C:"))
        hero_layout.addWidget(btn_hero_scan)

        self.content_layout.addWidget(hero_card)

        # 2. Quick Stat Badges
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(12)
        self.content_layout.addLayout(self.stats_grid)

        # 3. Drive Cards Section
        lbl_drives_title = QLabel("وحدات التخزين المحلية")
        lbl_drives_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_drives_title.setStyleSheet("color: #F0F6FC;")
        self.content_layout.addWidget(lbl_drives_title)

        self.drives_container = QHBoxLayout()
        self.drives_container.setSpacing(16)
        self.content_layout.addLayout(self.drives_container)

        # 4. Smart Recommendations Section
        lbl_recs_title = QLabel("التوصيات الذكية والإجراءات السريعة")
        lbl_recs_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl_recs_title.setStyleSheet("color: #F0F6FC;")
        self.content_layout.addWidget(lbl_recs_title)

        self.recs_container = QVBoxLayout()
        self.recs_container.setSpacing(10)
        self.content_layout.addLayout(self.recs_container)

        self.content_layout.addStretch(1)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        """Reload drives, hardware stats, and recommendations."""
        # Clear drives
        while self.drives_container.count():
            item = self.drives_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load logical drives
        drives = DiskHealthService.get_logical_drives()
        for d in drives:
            card = DriveCard(
                drive=d,
                on_analyze=lambda dl: self.navigate_requested.emit("analyzer", dl),
                parent=self
            )
            self.drives_container.addWidget(card)

        # Quick stats badges
        self._populate_stat_badges()

        # Populate Recommendations
        self._populate_recommendations(drives)

    def _populate_stat_badges(self):
        # Clear old badges
        while self.stats_grid.count():
            item = self.stats_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 1. CPU
        import psutil
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
        except Exception:
            cpu_pct = 0.0

        # 2. RAM
        try:
            vm = psutil.virtual_memory()
            ram_pct = vm.percent
        except Exception:
            ram_pct = 0.0

        # 3. Startup apps
        try:
            startup_items = StartupService.list_startup_items()
            enabled_startup = sum(1 for s in startup_items if s.is_enabled)
        except Exception:
            enabled_startup = 0

        # 4. Recycle Bin
        rb_sz, _ = CleanupService.query_recycle_bin()

        badges = [
            ("المعالج (CPU)", f"{cpu_pct:.1f}%", "cpu", "#58A6FF", "performance"),
            ("الذاكرة (RAM)", f"{ram_pct:.1f}%", "ram", "#BC8CFF" if ram_pct > 80 else "#3FB950", "processes"),
            ("سلة المحذوفات", format_bytes(rb_sz), "clean", "#D29922", "cleanup"),
            ("تطبيقات الإقلاع", f"{enabled_startup} نشط", "startup", "#58A6FF", "startup"),
        ]

        for col, (title, val, icon_name, val_color, target_subpage) in enumerate(badges):
            b_card = QFrame()
            b_card.setLayoutDirection(Qt.RightToLeft)
            b_card.setStyleSheet("""
                QFrame {
                    background: #161B22; border: 1px solid #30363D;
                    border-radius: 10px;
                }
                QFrame:hover { border-color: #58A6FF; }
            """)
            b_lay = QHBoxLayout(b_card)
            b_lay.setContentsMargins(12, 10, 12, 10)
            b_lay.setSpacing(12)

            ico = QLabel()
            ico.setPixmap(get_icon(icon_name, color=val_color).pixmap(24, 24))
            b_lay.addWidget(ico)

            txt_col = QVBoxLayout()
            txt_col.setSpacing(2)
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("color: #8B949E; font-size: 11px;")
            lbl_t.setAlignment(Qt.AlignRight)
            lbl_v = QLabel(val)
            lbl_v.setStyleSheet(f"color: {val_color}; font-size: 14px; font-weight: bold;")
            lbl_v.setAlignment(Qt.AlignRight)
            txt_col.addWidget(lbl_t)
            txt_col.addWidget(lbl_v)
            b_lay.addLayout(txt_col, 1)

            btn_go = QPushButton("عرض")
            btn_go.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #58A6FF; border: none; font-size: 11px; font-weight: bold;
                }
                QPushButton:hover { text-decoration: underline; }
            """)
            btn_go.clicked.connect(lambda _, sp=target_subpage: self.navigate_requested.emit(sp, None))
            b_lay.addWidget(btn_go)

            self.stats_grid.addWidget(b_card, 0, col)

    def _populate_recommendations(self, drives: List[LogicalDriveInfo]):
        while self.recs_container.count():
            item = self.recs_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = RecommendationEngine.evaluate_system(drives=drives, physical_disks=[])
        if not cards:
            no_rec = QLabel("النظام في حالة ممتازة ولا توجد إجراءات عاجلة مطلوبة حالياً.")
            no_rec.setStyleSheet("color: #3FB950; font-size: 13px; padding: 12px;")
            self.recs_container.addWidget(no_rec)
            return

        for c in cards:
            r_frame = QFrame()
            r_frame.setLayoutDirection(Qt.RightToLeft)
            border_col = "#F85149" if c.severity == "critical" else ("#D29922" if c.severity == "warning" else "#30363D")
            r_frame.setStyleSheet(f"""
                QFrame {{
                    background: #161B22; border: 1px solid {border_col};
                    border-radius: 10px; padding: 12px;
                }}
            """)
            r_lay = QHBoxLayout(r_frame)
            r_lay.setContentsMargins(14, 10, 14, 10)
            r_lay.setSpacing(14)

            # Icon
            ico_col = "#F85149" if c.severity == "critical" else ("#D29922" if c.severity == "warning" else "#58A6FF")
            ico = QLabel()
            ico.setPixmap(get_icon(c.icon, color=ico_col).pixmap(24, 24))
            r_lay.addWidget(ico)

            # Texts
            t_col = QVBoxLayout()
            t_col.setSpacing(3)
            t_title = QLabel(c.title_ar)
            t_title.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px;")
            t_desc = QLabel(c.description_ar)
            t_desc.setStyleSheet("color: #8B949E; font-size: 11px;")
            t_desc.setWordWrap(True)
            t_col.addWidget(t_title)
            t_col.addWidget(t_desc)
            r_lay.addLayout(t_col, 1)

            # Action button
            btn_act = QPushButton(c.action_label_ar)
            btn_act.setStyleSheet("""
                QPushButton {
                    background: #21262D; color: #58A6FF; border: 1px solid #30363D;
                    border-radius: 6px; padding: 6px 16px; font-weight: bold; font-size: 11px;
                }
                QPushButton:hover { background: #30363D; border-color: #58A6FF; }
            """)
            # Map action_id to subpage
            subpage_map = {
                "go_analyzer": "analyzer",
                "go_cleanup": "cleanup",
                "go_startup": "startup",
                "go_processes": "processes",
                "go_health": "health",
            }
            target = subpage_map.get(c.action_id, "analyzer")
            btn_act.clicked.connect(lambda _, sp=target: self.navigate_requested.emit(sp, None))
            r_lay.addWidget(btn_act)

            self.recs_container.addWidget(r_frame)
