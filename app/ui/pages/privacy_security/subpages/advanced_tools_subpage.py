# -*- coding: utf-8 -*-
"""
Advanced File Privacy & Permissions Subpage (أدوات متقدمة وصلاحيات NTFS) for SINAX Privacy & Security Center.
Features:
1. Alternate Data Streams (ADS) & Mark of the Web (Zone.Identifier) Inspector & Unblocker.
2. NTFS Access Control List (ACL) Auditor (Owner, Permissions, Everyone exposure, Network share status).
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import format_bytes
from app.services.privacy_security.ads_service import AlternateDataStreamsService
from app.services.privacy_security.models import NTFSPermissionInfo
from app.services.privacy_security.permissions_service import PermissionsService
from app.ui.icons import get_icon
from app.ui.pages.privacy_security.widgets.badge_widget import ToolBadgeWidget


class AdvancedToolsSubpage(QWidget):
    """Advanced NTFS Tools & Access Control Subpage."""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._current_ads_file: Optional[str] = None
        self._current_acl_path: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        # 1. Header
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self.btn_back = QPushButton(" العودة للرئيسية")
        self.btn_back.setIcon(get_icon("arrow_back", color="#8B949E"))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #161B22; color: #8B949E; border: 1px solid #30363D;
                border-radius: 6px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #21262D; color: #F0F6FC; }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_row.addWidget(self.btn_back)

        title_vbox = QVBoxLayout()
        t_lbl = QLabel("أدوات متقدمة وصلاحيات NTFS (Advanced File Privacy)", self)
        t_lbl.setStyleSheet("color: #F0F6FC; font-size: 18px; font-weight: bold;")
        title_vbox.addWidget(t_lbl)

        s_lbl = QLabel("فحص تدفقات البيانات البديلة ADS، وسوم الإنترنت MOTW، وأذونات وصلاحيات NTFS ومشاركات الشبكة.", self)
        s_lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(s_lbl)
        header_row.addLayout(title_vbox, 1)

        header_row.addWidget(ToolBadgeWidget.local_100(self))
        header_row.addWidget(ToolBadgeWidget.modifies_files(self))
        main_layout.addLayout(header_row)

        # Tabs
        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #30363D; background-color: #0D1117; border-radius: 8px; }
            QTabBar::tab {
                background-color: #161B22; color: #8B949E; padding: 8px 16px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                font-weight: bold; font-size: 13px; margin-left: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0D1117; color: #38BDF8;
                border: 1px solid #30363D; border-bottom: 1px solid #0D1117;
            }
            QTabBar::tab:hover:!selected { background-color: #21262D; color: #F0F6FC; }
        """)

        tab_ads = self._build_ads_tab()
        tab_acl = self._build_acl_tab()

        self.tabs.addTab(tab_ads, "تدفقات NTFS البديلة ووسام الإنترنت (ADS & MOTW)")
        self.tabs.addTab(tab_acl, "فاحص صلاحيات NTFS ومشاركات الشبكة (ACL & Shares)")

        main_layout.addWidget(self.tabs, 1)

    # -------------------------------------------------------------
    # Tab 1: ADS & MOTW
    # -------------------------------------------------------------
    def _build_ads_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # File picker row
        box = QFrame()
        box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        b_layout = QHBoxLayout(box)
        b_layout.setSpacing(10)

        lbl = QLabel("الملف المستهدف:")
        lbl.setStyleSheet("color: #8B949E; font-weight: bold;")
        b_layout.addWidget(lbl)

        self.txt_ads_file = QLineEdit()
        self.txt_ads_file.setPlaceholderText("اختر ملفاً لفحص تدفقات ADS المخفية ووسام MOTW...")
        self.txt_ads_file.setStyleSheet("background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        b_layout.addWidget(self.txt_ads_file, 1)

        btn_browse = QPushButton("استعراض...")
        btn_browse.setIcon(get_icon("folder_open", color="#FFFFFF"))
        btn_browse.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 8px 14px; font-weight: bold;")
        btn_browse.clicked.connect(self._browse_ads_file)
        b_layout.addWidget(btn_browse)

        btn_scan = QPushButton(" فحص التدفقات")
        btn_scan.setIcon(get_icon("search", color="#FFFFFF"))
        btn_scan.setStyleSheet("background: #1F6FEB; color: #FFFFFF; border-radius: 4px; padding: 8px 18px; font-weight: bold;")
        btn_scan.clicked.connect(self._inspect_ads)
        b_layout.addWidget(btn_scan)

        layout.addWidget(box)

        # MOTW Info Card (Mark of the web)
        self.motw_card = QFrame()
        self.motw_card.setVisible(False)
        self.motw_card.setStyleSheet("background-color: #2B2111; border: 1px solid #FBBF24; border-radius: 8px; padding: 12px;")
        mc_layout = QHBoxLayout(self.motw_card)
        mc_icon = QLabel()
        mc_icon.setPixmap(get_icon("warning", color="#FBBF24", size=24).pixmap(24, 24))
        mc_layout.addWidget(mc_icon)

        self.lbl_motw_info = QLabel("")
        self.lbl_motw_info.setWordWrap(True)
        self.lbl_motw_info.setStyleSheet("color: #FBBF24; font-size: 12px; line-height: 1.5;")
        mc_layout.addWidget(self.lbl_motw_info, 1)

        self.btn_unblock = QPushButton(" إزالة الوسم وفك حظر الملف")
        self.btn_unblock.setStyleSheet("background: #FBBF24; color: #0D1117; border-radius: 4px; padding: 6px 14px; font-weight: bold;")
        self.btn_unblock.clicked.connect(self._unblock_motw)
        mc_layout.addWidget(self.btn_unblock)

        layout.addWidget(self.motw_card)

        # Streams Table
        self.table_ads = QTableWidget()
        self.table_ads.setColumnCount(3)
        self.table_ads.setHorizontalHeaderLabels(["اسم التدفق (Stream Name)", "الحجم", "نوع وتصنيف التدفق"])
        self.table_ads.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_ads.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_ads.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_ads.setAlternatingRowColors(True)
        self.table_ads.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117; alternate-background-color: #161B22;
                border: 1px solid #30363D; border-radius: 6px; gridline-color: #21262D; color: #F0F6FC;
            }
            QHeaderView::section {
                background-color: #161B22; color: #8B949E; font-weight: bold; border: 1px solid #21262D; padding: 6px;
            }
        """)
        layout.addWidget(self.table_ads, 1)

        return widget

    def _browse_ads_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً لفحص تدفقات ADS", "", "كافة الملفات (*.*)")
        if f:
            self.txt_ads_file.setText(f)
            self._inspect_ads()

    def _inspect_ads(self):
        target = self.txt_ads_file.text().strip()
        if not target or not os.path.isfile(target):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد ملف موجود صالح أولاً.")
            return

        self._current_ads_file = target
        streams = AlternateDataStreamsService.list_streams(target)
        zone_content = AlternateDataStreamsService.read_zone_identifier(target)

        if zone_content:
            self.motw_card.setVisible(True)
            self.lbl_motw_info.setText(
                "<b>تحذير: هذا الملف موسوم بعلامة التحميل من الإنترنت (Zone.Identifier / MOTW)!</b><br>"
                "يقوم Windows بحظر تشغيل الملفات المحملة تلقائياً كإجراء وقائي. يمكنك فك الحظر إن كنت تثق في المصدر."
            )
        else:
            self.motw_card.setVisible(False)

        self.table_ads.setRowCount(len(streams))
        for idx, s in enumerate(streams):
            s_name = s.get("name", "")
            s_size = format_bytes(s.get("size_bytes", 0))
            s_type = s.get("type", "")

            it_name = QTableWidgetItem(s_name)
            it_sz = QTableWidgetItem(s_size)
            it_type = QTableWidgetItem(s_type)

            if s.get("is_motw"):
                it_name.setForeground(QColor("#FBBF24"))
                it_type.setForeground(QColor("#FBBF24"))
            elif s_name == "::$DATA":
                it_type.setForeground(QColor("#34D399"))
            else:
                it_name.setForeground(QColor("#38BDF8"))
                it_type.setForeground(QColor("#38BDF8"))

            self.table_ads.setItem(idx, 0, it_name)
            self.table_ads.setItem(idx, 1, it_sz)
            self.table_ads.setItem(idx, 2, it_type)

    def _unblock_motw(self):
        if not self._current_ads_file or not os.path.exists(self._current_ads_file):
            return

        reply = QMessageBox.question(
            self,
            "تأكيد فك حظر الملف",
            "هل أنت متأكد من رغبتك في إزالة وسم الإنترنت (Zone.Identifier) من هذا الملف؟\n\n"
            "هذا سيجعل Windows يعامل الملف كملف محلي موثوق.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        ok, msg = AlternateDataStreamsService.remove_zone_identifier(self._current_ads_file)
        if ok:
            QMessageBox.information(self, "نجاح", msg)
            self._inspect_ads()
        else:
            QMessageBox.warning(self, "تنبيه", msg)

    # -------------------------------------------------------------
    # Tab 2: NTFS ACLs & Network Shares
    # -------------------------------------------------------------
    def _build_acl_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Selector Row
        box = QFrame()
        box.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        b_layout = QHBoxLayout(box)
        b_layout.setSpacing(10)

        lbl = QLabel("المسار المستهدف:")
        lbl.setStyleSheet("color: #8B949E; font-weight: bold;")
        b_layout.addWidget(lbl)

        self.txt_acl_path = QLineEdit()
        self.txt_acl_path.setPlaceholderText("اختر ملفاً أو مجلداً لفحص أذونات وصلاحيات NTFS...")
        self.txt_acl_path.setStyleSheet("background-color: #0D1117; color: #F0F6FC; border: 1px solid #30363D; border-radius: 6px; padding: 8px;")
        b_layout.addWidget(self.txt_acl_path, 1)

        btn_f = QPushButton("ملف...")
        btn_f.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 12px;")
        btn_f.clicked.connect(self._browse_acl_file)
        b_layout.addWidget(btn_f)

        btn_d = QPushButton("مجلد...")
        btn_d.setStyleSheet("background: #21262D; color: #F0F6FC; border-radius: 4px; padding: 6px 12px;")
        btn_d.clicked.connect(self._browse_acl_folder)
        b_layout.addWidget(btn_d)

        btn_inspect = QPushButton(" فحص الصلاحيات")
        btn_inspect.setIcon(get_icon("search", color="#FFFFFF"))
        btn_inspect.setStyleSheet("background: #1F6FEB; color: #FFFFFF; border-radius: 4px; padding: 8px 18px; font-weight: bold;")
        btn_inspect.clicked.connect(self._inspect_acl)
        b_layout.addWidget(btn_inspect)

        layout.addWidget(box)

        # Overview / Owner & Warnings bar
        self.acl_summary_card = QFrame()
        self.acl_summary_card.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 12px;")
        sc_vbox = QVBoxLayout(self.acl_summary_card)
        sc_vbox.setSpacing(6)

        self.lbl_acl_owner = QLabel("المالك (Owner): لم يتم الفحص بعد")
        self.lbl_acl_owner.setStyleSheet("color: #F0F6FC; font-weight: bold; font-size: 13px;")
        sc_vbox.addWidget(self.lbl_acl_owner)

        self.lbl_acl_share = QLabel("مشاركة الشبكة: —")
        self.lbl_acl_share.setStyleSheet("color: #8B949E; font-size: 12px;")
        sc_vbox.addWidget(self.lbl_acl_share)

        self.lbl_acl_warnings = QLabel("")
        self.lbl_acl_warnings.setWordWrap(True)
        self.lbl_acl_warnings.setStyleSheet("color: #F87171; font-size: 12px;")
        sc_vbox.addWidget(self.lbl_acl_warnings)

        layout.addWidget(self.acl_summary_card)

        # Table of ACL entries
        self.table_acl = QTableWidget()
        self.table_acl.setColumnCount(4)
        self.table_acl.setHorizontalHeaderLabels(["المستخدم أو المجموعة (Identity)", "مستوى الصلاحية (Rights)", "النوع (Type)", "موروثة (Inherited)"])
        self.table_acl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_acl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_acl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_acl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_acl.setAlternatingRowColors(True)
        self.table_acl.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117; alternate-background-color: #161B22;
                border: 1px solid #30363D; border-radius: 6px; gridline-color: #21262D; color: #F0F6FC;
            }
            QHeaderView::section {
                background-color: #161B22; color: #8B949E; font-weight: bold; border: 1px solid #21262D; padding: 6px;
            }
        """)
        layout.addWidget(self.table_acl, 1)

        return widget

    def _browse_acl_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "اختر ملفاً لفحص صلاحياته", "", "كافة الملفات (*.*)")
        if f:
            self.txt_acl_path.setText(f)
            self._inspect_acl()

    def _browse_acl_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "اختر مجلداً لفحص صلاحياته")
        if folder:
            self.txt_acl_path.setText(folder)
            self._inspect_acl()

    def _inspect_acl(self):
        target = self.txt_acl_path.text().strip()
        if not target or not os.path.exists(target):
            QMessageBox.warning(self, "تنبيه", "يرجى تحديد مسار صالح أولاً.")
            return

        self._current_acl_path = target
        info: NTFSPermissionInfo = PermissionsService.inspect_permissions(target)

        self.lbl_acl_owner.setText(f"المالك (Owner): <b><font color='#38BDF8'>{info.owner}</font></b>")

        # Network share check
        if os.path.isdir(target):
            is_shared, share_name = PermissionsService.check_network_share(target)
            if is_shared:
                self.lbl_acl_share.setText(f"مشاركة الشبكة: <font color='#F87171'><b>مكشوف عبر مشاركة الشبكة المحلية باسم '{share_name}'</b></font>")
            else:
                self.lbl_acl_share.setText("مشاركة الشبكة: غير مكشوف على شبكة LAN (محلي فقط)")
        else:
            self.lbl_acl_share.setText("مشاركة الشبكة: ملف منفرد")

        # Warnings
        if info.warnings:
            self.lbl_acl_warnings.setText("<br>".join([f"⚠️ {w}" for w in info.warnings]))
        else:
            self.lbl_acl_warnings.setText("✅ لا توجد أذونات كتابة عامة غير مقيدة أو تحذيرات أمنية على هذا المسار.")
            self.lbl_acl_warnings.setStyleSheet("color: #34D399; font-size: 12px;")

        # Table rows
        entries = info.entries
        self.table_acl.setRowCount(len(entries))
        for idx, e in enumerate(entries):
            ident = e.get("identity", "")
            rights = e.get("rights", "")
            act = e.get("type", "")
            inh = "نعم" if e.get("inherited") else "لا (صريحة)"

            it_id = QTableWidgetItem(ident)
            if "everyone" in ident.lower() or "الجميع" in ident.lower():
                it_id.setForeground(QColor("#F87171"))

            it_r = QTableWidgetItem(rights)
            it_act = QTableWidgetItem(act)
            it_inh = QTableWidgetItem(inh)

            self.table_acl.setItem(idx, 0, it_id)
            self.table_acl.setItem(idx, 1, it_r)
            self.table_acl.setItem(idx, 2, it_act)
            self.table_acl.setItem(idx, 3, it_inh)
