# -*- coding: utf-8 -*-
"""
SINAX Privacy & Security Center Master Page (صفحة مركز الخصوصية والأمان الرئيسية)
Coordinates and hosts 13 specialized subpages:
0: overview (نظرة عامة - لوحة القيادة)
1: file_safety (فحص الملفات)
2: integrity (سلامة الملفات)
3: signature (التوقيع الرقمي)
4: clean (تنظيف الخصوصية)
5: safe_share (المشاركة الآمنة)
6: vault (التشفير والخزنة)
7: secure_delete (الحذف الآمن)
8: file_monitor (مراقبة التغييرات)
9: passwords (كلمات المرور)
10: windows_security (حماية Windows)
11: advanced_tools (أدوات متقدمة)
12: reports (التقارير)
"""

from typing import Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.icons import get_icon
from app.ui.pages.privacy_security.subpages.overview_subpage import OverviewSubpage
from app.ui.pages.privacy_security.subpages.file_safety_subpage import FileSafetySubpage
from app.ui.pages.privacy_security.subpages.integrity_subpage import IntegritySubpage
from app.ui.pages.privacy_security.subpages.signature_subpage import SignatureSubpage
from app.ui.pages.privacy_security.subpages.metadata_clean_subpage import MetadataCleanSubpage
from app.ui.pages.privacy_security.subpages.safe_share_subpage import SafeShareSubpage
from app.ui.pages.privacy_security.subpages.vault_subpage import VaultSubpage
from app.ui.pages.privacy_security.subpages.secure_delete_subpage import SecureDeleteSubpage
from app.ui.pages.privacy_security.subpages.file_monitor_subpage import FileMonitorSubpage
from app.ui.pages.privacy_security.subpages.passwords_subpage import PasswordsSubpage
from app.ui.pages.privacy_security.subpages.windows_security_subpage import WindowsSecuritySubpage
from app.ui.pages.privacy_security.subpages.advanced_tools_subpage import AdvancedToolsSubpage
from app.ui.pages.privacy_security.subpages.reports_subpage import ReportsSubpage
from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url


class QMLPrivacySecurityOverview(QWidget):
    tool_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), "privacyController")
        self.quick_widget.setSource(get_qml_url("pages/PrivacySecurityPage.qml"))
        layout.addWidget(self.quick_widget)


class PrivacySecurityPage(QWidget):
    """Master container page for SINAX Privacy & Security Center."""

    subpage_changed = Signal(str, str)  # (key, label_ar)

    SUBPAGE_KEYS = [
        ("overview", "نظرة عامة", "shield"),
        ("file_safety", "فحص الملفات", "eye"),
        ("integrity", "سلامة الملفات", "hash"),
        ("signature", "التوقيع الرقمي", "signature"),
        ("clean", "تنظيف الخصوصية", "clean_sweep"),
        ("safe_share", "المشاركة الآمنة", "share"),
        ("vault", "التشفير والخزنة", "vault"),
        ("secure_delete", "الحذف الآمن", "shred"),
        ("file_monitor", "مراقبة التغييرات", "doctor"),
        ("passwords", "كلمات المرور", "key"),
        ("windows_security", "حماية Windows", "security"),
        ("advanced_tools", "أدوات متقدمة", "tools"),
        ("reports", "التقارير", "report"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self._buttons: Dict[str, QPushButton] = {}
        self._key_to_index: Dict[str, int] = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Subpage Navigation Bar (Scrollable for full responsiveness)
        self.nav_scroll = QScrollArea(self)
        self.nav_scroll.setFixedHeight(54)
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setFrameShape(QFrame.NoFrame)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        nav_bar = QWidget()
        nav_bar.setStyleSheet("background: transparent;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(16, 6, 16, 6)
        nav_layout.setSpacing(6)

        for idx, (key, label, icon_name) in enumerate(self.SUBPAGE_KEYS):
            btn = QPushButton(f" {label}")
            btn.setIcon(get_icon(icon_name, color="#8B949E"))
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda checked=False, k=key: self.switch_subpage(k))
            self.btn_group.addButton(btn, idx)
            self._buttons[key] = btn
            self._key_to_index[key] = idx
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)
        self.nav_scroll.setWidget(nav_bar)
        main_layout.addWidget(self.nav_scroll)

        # 2. Stacked Subpages
        self.stack = QStackedWidget(self)
        self._subpages: Dict[int, QWidget] = {}

        # Page 0: Modern QML Overview Dashboard (immediate)
        self.qml_overview = QMLPrivacySecurityOverview(self)
        self.qml_overview.tool_selected.connect(self._on_registry_tool_selected)
        self.stack.addWidget(self.qml_overview)
        self._subpages[0] = self.qml_overview
        self._overview_subpage_instance = None

        # Pages 1..12: Lazy placeholder widgets
        self._factories = {
            1: lambda: FileSafetySubpage(self),
            2: lambda: IntegritySubpage(self),
            3: lambda: SignatureSubpage(self),
            4: lambda: MetadataCleanSubpage(self),
            5: lambda: SafeShareSubpage(self),
            6: lambda: VaultSubpage(self),
            7: lambda: SecureDeleteSubpage(self),
            8: lambda: FileMonitorSubpage(self),
            9: lambda: PasswordsSubpage(self),
            10: lambda: WindowsSecuritySubpage(self),
            11: lambda: AdvancedToolsSubpage(self),
            12: lambda: ReportsSubpage(self),
        }
        for _ in range(1, 13):
            self.stack.addWidget(QWidget())

        main_layout.addWidget(self.stack, 1)

        from app.ui.themes.theme_manager import theme_manager
        theme_manager.theme_changed.connect(self.apply_theme)
        self.apply_theme(theme_manager.effective_theme)

    def apply_theme(self, theme_name: str = "dark"):
        """Propagates theme across nav_scroll, buttons, stack, and active subpages."""
        is_light = (theme_name == "light")
        bg_color = "#F8FAFC" if is_light else "#0D1117"
        border_color = "#E2E8F0" if is_light else "#21262D"
        stack_bg = "#FFFFFF" if is_light else "#0D1117"
        btn_color = "#475569" if is_light else "#8B949E"
        btn_hover_bg = "#E2E8F0" if is_light else "#161B22"
        btn_hover_color = "#0F172A" if is_light else "#F0F6FC"
        btn_checked_bg = "#E0F2FE" if is_light else "#1E293B"
        btn_checked_color = "#0284C7" if is_light else "#38BDF8"
        scrollbar_handle = "#CBD5E1" if is_light else "#334155"

        if hasattr(self, "nav_scroll") and self.nav_scroll is not None:
            self.nav_scroll.setStyleSheet(f"""
                QScrollArea {{
                    background: {bg_color};
                    border-bottom: 1px solid {border_color};
                }}
                QScrollBar:horizontal {{
                    height: 4px;
                    background: {bg_color};
                }}
                QScrollBar::handle:horizontal {{
                    background: {scrollbar_handle};
                    border-radius: 2px;
                }}
            """)
        if hasattr(self, "stack") and self.stack is not None:
            self.stack.setStyleSheet(f"background: {stack_bg};")

        btn_qss = f"""
            QPushButton {{
                background: transparent;
                color: {btn_color};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {btn_hover_bg};
                color: {btn_hover_color};
            }}
            QPushButton:checked {{
                background: {btn_checked_bg};
                color: {btn_checked_color};
                border-bottom: 2px solid {btn_checked_color};
            }}
        """
        for key, btn in self._buttons.items():
            btn.setStyleSheet(btn_qss)
            icon_name = next((ic for k, _, ic in self.SUBPAGE_KEYS if k == key), "shield")
            btn.setIcon(get_icon(icon_name, color=btn_color))

        for sub in self._subpages.values():
            if hasattr(sub, "apply_theme") and callable(sub.apply_theme):
                sub.apply_theme(theme_name)

    _SUBPAGE_ATTRS = {
        "file_safety_subpage": 1,
        "integrity_subpage": 2,
        "signature_subpage": 3,
        "clean_subpage": 4,
        "safe_share_subpage": 5,
        "vault_subpage": 6,
        "secure_delete_subpage": 7,
        "file_monitor_subpage": 8,
        "passwords_subpage": 9,
        "windows_security_subpage": 10,
        "advanced_tools_subpage": 11,
        "reports_subpage": 12,
    }

    @property
    def overview_subpage(self):
        if self._overview_subpage_instance is None:
            self._overview_subpage_instance = OverviewSubpage(self)
            self._overview_subpage_instance.tool_selected.connect(self._on_registry_tool_selected)
        return self._overview_subpage_instance

    def _ensure_subpage_loaded(self, idx: int) -> QWidget:
        if idx not in self._subpages and idx in self._factories:
            w = self._factories[idx]()
            if hasattr(w, "back_requested"):
                w.back_requested.connect(lambda: self.switch_subpage("overview"))
            old_w = self.stack.widget(idx)
            self.stack.removeWidget(old_w)
            old_w.deleteLater()
            self.stack.insertWidget(idx, w)
            self._subpages[idx] = w
            from app.ui.themes.theme_manager import theme_manager
            if hasattr(w, "apply_theme") and callable(w.apply_theme):
                w.apply_theme(theme_manager.effective_theme)
        return self._subpages.get(idx, self.qml_overview)

    def __getattr__(self, name: str):
        if "_SUBPAGE_ATTRS" in type(self).__dict__ and name in self._SUBPAGE_ATTRS:
            idx = self._SUBPAGE_ATTRS[name]
            return self._ensure_subpage_loaded(idx)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def switch_subpage(self, key: str):
        """Switches the active subpage and emits subpage_changed."""
        # Normalize keys if needed
        key_alias_map = {
            "privacy_overview": "overview",
            "privacy_file_safety": "file_safety",
            "privacy_integrity": "integrity",
            "privacy_signature": "signature",
            "privacy_clean": "clean",
            "privacy_safe_share": "safe_share",
            "privacy_vault": "vault",
            "privacy_secure_delete": "secure_delete",
            "privacy_file_monitor": "file_monitor",
            "privacy_passwords": "passwords",
            "privacy_windows_security": "windows_security",
            "privacy_advanced_tools": "advanced_tools",
            "privacy_reports": "reports",
        }
        target_key = key_alias_map.get(key, key)

        if target_key in self._key_to_index:
            idx = self._key_to_index[target_key]
            self._ensure_subpage_loaded(idx)
            self.stack.setCurrentIndex(idx)

            btn = self._buttons.get(target_key)
            if btn:
                btn.setChecked(True)

            label_ar = next((lbl for k, lbl, _ in self.SUBPAGE_KEYS if k == target_key), "الخصوصية والأمان")
            self.subpage_changed.emit(target_key, label_ar)

    def _on_registry_tool_selected(self, tool_id: str):
        """Routes clicks from the Dashboard registry cards to corresponding subpages."""
        tool_to_subpage = {
            "file_safety_inspector": "file_safety",
            "defender_scanner": "file_safety",
            "authenticode_verifier": "signature",
            "integrity_manifest_builder": "integrity",
            "realtime_file_monitor": "file_monitor",
            "metadata_sanitizer": "clean",
            "safe_share_studio": "safe_share",
            "sensitive_data_scanner": "safe_share",
            "portable_vault_crypto": "vault",
            "dpapi_windows_crypto": "vault",
            "secure_shredder": "secure_delete",
            "windows_security_dashboard": "windows_security",
            "ads_stream_inspector": "advanced_tools",
            "ntfs_permissions_inspector": "advanced_tools",
            "clipboard_privacy_guard": "passwords",
            "privacy_audit_reporter": "reports",
        }
        sub = tool_to_subpage.get(tool_id, "overview")
        self.switch_subpage(sub)
