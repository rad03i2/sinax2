# -*- coding: utf-8 -*-
"""
Overview Subpage (Dashboard) for SINAX Privacy & Security Center.
Displays real Windows security telemetry (Defender, Real-time, Firewall, SmartScreen, CFA, BitLocker)
and local SINAX metrics (monitored files, last scan, encrypted vaults) with zero mock data.
Presents the unified Security Tool Registry catalog with badges and launch handlers.
"""

from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.privacy_security.security_overview_service import SecurityOverviewService
from app.services.privacy_security.security_registry import SecurityToolRegistry, ToolBadge
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class TelemetryCard(QFrame):
    """Reusable Fluent card for displaying live Windows security metrics."""

    def __init__(self, title: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 14px;
            }
            QFrame:hover {
                border-color: #58A6FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header: Icon + Title
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.icon_lbl = QLabel(self)
        self.icon_lbl.setPixmap(get_icon(icon_name, color_hex="#58A6FF", size=22).pixmap(22, 22))
        top_row.addWidget(self.icon_lbl)

        self.title_lbl = QLabel(title, self)
        self.title_lbl.setStyleSheet("color: #8B949E; font-size: 13px; font-weight: 600;")
        top_row.addWidget(self.title_lbl)
        top_row.addStretch(1)

        layout.addLayout(top_row)

        # Value label
        self.val_lbl = QLabel("جاري التحميل...", self)
        self.val_lbl.setWordWrap(True)
        self.val_lbl.setStyleSheet("color: #F0F6FC; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.val_lbl)

        # Sub-detail label
        self.sub_lbl = QLabel("", self)
        self.sub_lbl.setWordWrap(True)
        self.sub_lbl.setStyleSheet("color: #6E7681; font-size: 11px;")
        layout.addWidget(self.sub_lbl)

    def update_data(self, value: str, sub_text: str = "", status_type: str = "neutral"):
        self.val_lbl.setText(value)
        self.sub_lbl.setText(sub_text)

        if "مفعل" in value or "Active" in value:
            color = "#34D399"  # Green
        elif "معطل" in value or "Disabled" in value:
            color = "#F87171"  # Red
        elif "غير متوفر" in value:
            color = "#94A3B8"  # Slate grey
        else:
            color = "#60CDFF"  # Accent blue

        self.val_lbl.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")


class MetricCard(QFrame):
    """Card for SINAX local privacy database metrics."""

    def __init__(self, title: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setStyleSheet("""
            QFrame {
                background-color: #0D1117;
                border: 1px solid #21262D;
                border-radius: 10px;
                padding: 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        icon = QLabel(self)
        icon.setPixmap(get_icon(icon_name, color_hex="#38BDF8", size=20).pixmap(20, 20))
        top_row.addWidget(icon)

        t_lbl = QLabel(title, self)
        t_lbl.setStyleSheet("color: #8B949E; font-size: 12px; font-weight: bold;")
        top_row.addWidget(t_lbl)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        self.num_lbl = QLabel("0", self)
        self.num_lbl.setStyleSheet("color: #38BDF8; font-size: 20px; font-weight: bold;")
        layout.addWidget(self.num_lbl)

        self.sub_lbl = QLabel("", self)
        self.sub_lbl.setStyleSheet("color: #6E7681; font-size: 11px;")
        layout.addWidget(self.sub_lbl)

    def set_value(self, val: str, sub: str = ""):
        self.num_lbl.setText(val)
        self.sub_lbl.setText(sub)


class OverviewSubpage(QWidget):
    """
    Overview Dashboard for SINAX Privacy & Security Center.
    Emits tool_selected(tool_id) when clicking a tool card.
    """

    tool_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._overview_service = SecurityOverviewService()
        self._init_ui()

        # Initial telemetry load deferred slightly to keep UI fluid
        QTimer.singleShot(100, self.refresh_telemetry)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(20)

        # 1. Header Banner
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #111827, stop:1 #1E293B);
                border: 1px solid #374151;
                border-radius: 12px;
                padding: 18px;
            }
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setSpacing(16)

        shield_icon = QLabel()
        shield_icon.setPixmap(get_icon("shield", color_hex="#38BDF8", size=48).pixmap(48, 48))
        h_layout.addWidget(shield_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        t_main = QLabel("مركز الخصوصية والأمان - SINAX Privacy & Security")
        t_main.setStyleSheet("font-size: 20px; font-weight: bold; color: #F0F6FC;")
        title_box.addWidget(t_main)

        t_sub = QLabel("لوحة القيادة الأمنية الموحدة ومراقبة حماية نظام Windows ومؤشرات الخصوصية محلياً")
        t_sub.setStyleSheet("font-size: 13px; color: #9CA3AF;")
        title_box.addWidget(t_sub)
        h_layout.addLayout(title_box, 1)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.refresh_btn = QPushButton("تحديث البيانات الحية")
        self.refresh_btn.setIcon(get_icon("refresh", color_hex="#F0F6FC", size=16))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        self.refresh_btn.clicked.connect(lambda: self.refresh_telemetry(force=True))
        btn_box.addWidget(self.refresh_btn)

        win_sec_btn = QPushButton("أمان Windows")
        win_sec_btn.setIcon(get_icon("security", color_hex="#F0F6FC", size=16))
        win_sec_btn.setStyleSheet("""
            QPushButton {
                background-color: #1F2937;
                color: #F0F6FC;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #374151;
            }
        """)
        win_sec_btn.clicked.connect(self._overview_service.open_windows_security)
        btn_box.addWidget(win_sec_btn)

        h_layout.addLayout(btn_box)
        c_layout.addWidget(header_frame)

        # 2. Windows Native Security Telemetry Section
        sec_title = QLabel("حالة حماية وأمان Windows الحقيقية")
        sec_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58A6FF; margin-top: 4px;")
        c_layout.addWidget(sec_title)

        telemetry_grid = QGridLayout()
        telemetry_grid.setSpacing(12)

        self.card_defender = TelemetryCard("Microsoft Defender", "shield")
        telemetry_grid.addWidget(self.card_defender, 0, 0)

        self.card_realtime = TelemetryCard("الحماية في الوقت الحقيقي", "pulse")
        telemetry_grid.addWidget(self.card_realtime, 0, 1)

        self.card_firewall = TelemetryCard("جدار حماية Windows", "security")
        telemetry_grid.addWidget(self.card_firewall, 0, 2)

        self.card_smartscreen = TelemetryCard("الفحص الذكي (SmartScreen)", "eye")
        telemetry_grid.addWidget(self.card_smartscreen, 1, 0)

        self.card_cfa = TelemetryCard("حماية الفدية (Controlled Folder Access)", "lock")
        telemetry_grid.addWidget(self.card_cfa, 1, 1)

        self.card_bitlocker = TelemetryCard("تشفير الأقراص (BitLocker)", "vault")
        telemetry_grid.addWidget(self.card_bitlocker, 1, 2)

        c_layout.addLayout(telemetry_grid)

        # 3. SINAX Local Privacy Metrics Section
        local_title = QLabel("مؤشرات الخصوصية وقاعدة البيانات المحلية لـ SINAX")
        local_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #34D399; margin-top: 8px;")
        c_layout.addWidget(local_title)

        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)

        self.metric_files = MetricCard("عدد الملفات المراقبة", "doctor")
        metrics_layout.addWidget(self.metric_files)

        self.metric_scan = MetricCard("آخر فحص خصوصية", "history")
        metrics_layout.addWidget(self.metric_scan)

        self.metric_vaults = MetricCard("عدد الخزن المشفرة", "vault")
        metrics_layout.addWidget(self.metric_vaults)

        c_layout.addLayout(metrics_layout)

        # 4. Security Tool Registry Catalog Section
        tools_title_row = QHBoxLayout()
        cat_title = QLabel("دليل أدوات الأمان والخصوصية (Security Tool Registry)")
        cat_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F0F6FC; margin-top: 8px;")
        tools_title_row.addWidget(cat_title)

        all_tools = SecurityToolRegistry.get_all_tools()
        tools_count_badge = QLabel(f" {len(all_tools)} أداة مسجلة ")
        tools_count_badge.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            border: 1px solid #0284C7;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        tools_title_row.addWidget(tools_count_badge)
        tools_title_row.addStretch(1)
        c_layout.addLayout(tools_title_row)

        tools_grid = QGridLayout()
        tools_grid.setSpacing(12)

        for idx, tool in enumerate(all_tools):
            row = idx // 2
            col = idx % 2
            card = self._build_tool_card(tool)
            tools_grid.addWidget(card, row, col)

        c_layout.addLayout(tools_grid)

        c_layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _build_tool_card(self, tool) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 10px;
                padding: 14px;
            }
            QFrame:hover {
                border-color: #38BDF8;
                background-color: #1C2128;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header: Icon + Title
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(tool.icon, color_hex="#38BDF8", size=24).pixmap(24, 24))
        top_row.addWidget(icon_lbl)

        title_lbl = QLabel(tool.title)
        title_lbl.setStyleSheet("color: #F0F6FC; font-size: 14px; font-weight: bold;")
        top_row.addWidget(title_lbl, 1)

        layout.addLayout(top_row)

        # Badges Row
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(6)

        # 100% Local or Online
        if tool.requires_network or tool.sends_data_externally:
            badges_layout.addWidget(ToolBadgeWidget.online())
        else:
            badges_layout.addWidget(ToolBadgeWidget.local_100())

        # Requires Admin
        if tool.requires_admin:
            badges_layout.addWidget(ToolBadgeWidget.requires_admin())

        # Modifies Files
        if tool.modifies_files:
            badges_layout.addWidget(ToolBadgeWidget.modifies_files())

        badges_layout.addStretch(1)
        layout.addLayout(badges_layout)

        # Description
        desc_lbl = QLabel(tool.description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #8B949E; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc_lbl, 1)

        # Footer Action Button
        btn_row = QHBoxLayout()
        btn = QPushButton("عرض تفاصيل الأداة")
        btn.setIcon(get_icon("info", color_hex="#38BDF8", size=14))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #58A6FF;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363D;
                color: #79C0FF;
            }
        """)
        btn.clicked.connect(lambda checked=False, tid=tool.id: self.tool_selected.emit(tid))
        btn_row.addWidget(btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        return card

    def refresh_telemetry(self, force: bool = False):
        """Fetches live telemetry and updates all UI cards."""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("جاري التحديث...")

        try:
            data = self._overview_service.get_dashboard_summary(force_refresh=force)

            # 1. Defender
            def_act = data.get("defender_active", "غير متوفر")
            sig_ver = data.get("signature_version", "غير متوفر")
            self.card_defender.update_data(def_act, f"إصدار التوقيعات: {sig_ver}")

            # 2. Real-time Protection
            rt_act = data.get("realtime_protection", "غير متوفر")
            self.card_realtime.update_data(rt_act, "مراقبة حية للملفات والعمليات النشطة")

            # 3. Firewall
            fw = data.get("firewall_status", "غير متوفر")
            self.card_firewall.update_data(fw, "جدار الحماية لشبكة الاتصال الحالية")

            # 4. SmartScreen
            ss = data.get("smartscreen_status", "غير متوفر")
            self.card_smartscreen.update_data(ss, "فحص تنزيل الملفات والتطبيقات المشبوهة")

            # 5. Controlled Folder Access
            cfa = data.get("controlled_folder_access", "غير متوفر")
            self.card_cfa.update_data(cfa, "حماية المجلدات الحساسة من تشفير الفدية")

            # 6. BitLocker
            bl = data.get("bitlocker_status", "غير متوفر")
            self.card_bitlocker.update_data(bl, "تشفير وحدات التخزين الكامل")

            # 7. Local Metrics
            mon_cnt = data.get("monitored_files_count", 0)
            self.metric_files.set_value(f"{mon_cnt:,} ملف", f"في {data.get('monitored_folders_count', 0)} مجلد مراقب")

            last_scan = data.get("last_privacy_scan", "لم يتم الفحص بعد")
            self.metric_scan.set_value(last_scan, "تاريخ آخر فحص خصوصية مسجل")

            vaults_cnt = data.get("encrypted_vaults_count", 0)
            self.metric_vaults.set_value(f"{vaults_cnt} خزن", "حاويات .sinaxvault نشطة")

        except Exception as e:
            self.card_defender.update_data("غير متوفر", f"خطأ: {str(e)}")
        finally:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("تحديث البيانات الحية")
