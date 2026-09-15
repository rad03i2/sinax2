# -*- coding: utf-8 -*-
"""
SINAX Application Detail Panel Widget
Displays rich metadata, executable specs, size comparisons, quick action buttons,
and collapsible advanced details for the currently selected application.
"""

import os
import subprocess
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.apps_manager.app_model import InstalledApp, format_bytes
from app.services.apps_manager.app_size_service import AppSizeService
from app.ui.icons import get_icon


class AppDetailPanel(QWidget):
    """Side drawer/panel showing details and actions for a selected app."""

    uninstall_requested = Signal(object)  # InstalledApp
    update_requested = Signal(object)  # InstalledApp
    repair_requested = Signal(object)  # InstalledApp
    reset_requested = Signal(object)  # InstalledApp
    leftover_scan_requested = Signal(object)  # InstalledApp
    open_startup_manager_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_app: Optional[InstalledApp] = None
        self.setLayoutDirection(Qt.RightToLeft)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Scroll Area for responsive height
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(14)

        # 1. Header Card (Icon, Name, Publisher, Badges)
        self.header_card = QFrame()
        self.header_card.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 14px;")
        header_layout = QHBoxLayout(self.header_card)
        header_layout.setContentsMargins(10, 10, 10, 10)
        header_layout.setSpacing(14)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(48, 48)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.lbl_icon)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(4)
        self.lbl_name = QLabel("اختر برنامجاً من القائمة")
        self.lbl_name.setStyleSheet("color: #F0F6FC; font-size: 16px; font-weight: bold;")
        self.lbl_name.setWordWrap(True)
        title_vbox.addWidget(self.lbl_name)

        self.lbl_meta = QLabel("لعرض معلوماته التفصيلية وإدارته")
        self.lbl_meta.setStyleSheet("color: #8B949E; font-size: 12px;")
        title_vbox.addWidget(self.lbl_meta)

        self.badges_layout = QHBoxLayout()
        self.badges_layout.setSpacing(6)
        title_vbox.addLayout(self.badges_layout)

        header_layout.addLayout(title_vbox, 1)
        self.content_layout.addWidget(self.header_card)

        # 2. Quick Actions Toolbar
        self.actions_card = QFrame()
        self.actions_card.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;")
        actions_vbox = QVBoxLayout(self.actions_card)
        actions_vbox.setContentsMargins(10, 10, 10, 10)
        actions_vbox.setSpacing(8)

        lbl_act = QLabel("إجراءات سريعة")
        lbl_act.setStyleSheet("color: #58A6FF; font-size: 13px; font-weight: bold;")
        actions_vbox.addWidget(lbl_act)

        act_grid = QGridLayout()
        act_grid.setSpacing(8)

        self.btn_run = self._create_btn("تشغيل البرنامج", "play", "#238636", self._on_run_app)
        self.btn_open_folder = self._create_btn("فتح موقع البرنامج", "folder", "#30363D", self._on_open_folder)
        self.btn_website = self._create_btn("موقع الناشر", "link", "#30363D", self._on_open_website)
        self.btn_update = self._create_btn("تحديث البرنامج", "update", "#1F6FEB", lambda: self._current_app and self.update_requested.emit(self._current_app))
        self.btn_repair = self._create_btn("إصلاح البرنامج", "repair", "#D29922", lambda: self._current_app and self.repair_requested.emit(self._current_app))
        self.btn_reset = self._create_btn("إعادة الضبط", "clean", "#D29922", lambda: self._current_app and self.reset_requested.emit(self._current_app))
        self.btn_uninstall = self._create_btn("إزالة البرنامج", "uninstall", "#DA3633", lambda: self._current_app and self.uninstall_requested.emit(self._current_app))
        self.btn_leftovers = self._create_btn("فحص البقايا", "clean", "#30363D", lambda: self._current_app and self.leftover_scan_requested.emit(self._current_app))

        act_grid.addWidget(self.btn_run, 0, 0)
        act_grid.addWidget(self.btn_open_folder, 0, 1)
        act_grid.addWidget(self.btn_update, 1, 0)
        act_grid.addWidget(self.btn_website, 1, 1)
        act_grid.addWidget(self.btn_repair, 2, 0)
        act_grid.addWidget(self.btn_reset, 2, 1)
        act_grid.addWidget(self.btn_uninstall, 3, 0)
        act_grid.addWidget(self.btn_leftovers, 3, 1)

        actions_vbox.addLayout(act_grid)
        self.content_layout.addWidget(self.actions_card)

        # 3. Detailed Specifications Grid
        self.specs_card = QFrame()
        self.specs_card.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;")
        specs_vbox = QVBoxLayout(self.specs_card)
        specs_vbox.setContentsMargins(10, 10, 10, 10)
        specs_vbox.setSpacing(10)

        lbl_specs_head = QLabel("المواصفات والبيانات الفنية")
        lbl_specs_head.setStyleSheet("color: #58A6FF; font-size: 13px; font-weight: bold;")
        specs_vbox.addWidget(lbl_specs_head)

        self.grid_specs = QGridLayout()
        self.grid_specs.setSpacing(8)
        self.grid_specs.setColumnStretch(0, 0)
        self.grid_specs.setColumnStretch(1, 1)

        self.fields = {}
        spec_items = [
            ("location", "مسار التثبيت:"),
            ("executable", "الملف التنفيذي:"),
            ("size_reg", "الحجم المسجل:"),
            ("size_calc", "الحجم الفعلي على القرص:"),
            ("architecture", "المعمارية:"),
            ("install_date", "تاريخ التثبيت:"),
            ("package_id", "معرف WinGet:"),
            ("product_code", "رمز المنتج (GUID):"),
            ("running_state", "الحالة الحالية:"),
            ("startup_state", "بدء التشغيل:"),
        ]

        for r, (key, label_ar) in enumerate(spec_items):
            lbl_title = QLabel(label_ar)
            lbl_title.setStyleSheet("color: #8B949E; font-size: 12px; font-weight: bold;")
            lbl_val = QLabel("-")
            lbl_val.setStyleSheet("color: #C9D1D9; font-size: 12px;")
            lbl_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl_val.setWordWrap(True)

            self.grid_specs.addWidget(lbl_title, r, 0, Qt.AlignTop | Qt.AlignRight)
            self.grid_specs.addWidget(lbl_val, r, 1, Qt.AlignTop | Qt.AlignRight)
            self.fields[key] = lbl_val

        # Add button to calculate true disk size
        self.btn_calc_size = QPushButton("حساب الحجم الفعلي")
        self.btn_calc_size.setStyleSheet("""
            QPushButton { background: #21262D; color: #58A6FF; border: 1px solid #30363D; border-radius: 4px; padding: 2px 8px; font-size: 11px; }
            QPushButton:hover { background: #30363D; }
        """)
        self.btn_calc_size.clicked.connect(self._on_calculate_real_size)
        self.grid_specs.addWidget(self.btn_calc_size, 3, 2)

        # Button to jump to Startup Manager
        self.btn_goto_startup = QPushButton("إدارة بدء التشغيل")
        self.btn_goto_startup.setStyleSheet("""
            QPushButton { background: #21262D; color: #58A6FF; border: 1px solid #30363D; border-radius: 4px; padding: 2px 8px; font-size: 11px; }
            QPushButton:hover { background: #30363D; }
        """)
        self.btn_goto_startup.clicked.connect(lambda: self.open_startup_manager_requested.emit())
        self.grid_specs.addWidget(self.btn_goto_startup, 9, 2)

        specs_vbox.addLayout(self.grid_specs)
        self.content_layout.addWidget(self.specs_card)

        # 4. Advanced Technical Details (Collapsible)
        self.adv_card = QFrame()
        self.adv_card.setStyleSheet("background: #161B22; border: 1px solid #30363D; border-radius: 10px; padding: 12px;")
        adv_vbox = QVBoxLayout(self.adv_card)
        adv_vbox.setContentsMargins(10, 10, 10, 10)
        adv_vbox.setSpacing(8)

        self.btn_toggle_adv = QPushButton("▸ التفاصيل التقنية المتقدمة للمحترفين")
        self.btn_toggle_adv.setStyleSheet("QPushButton { background: transparent; color: #8B949E; border: none; text-align: right; font-weight: bold; font-size: 12px; } QPushButton:hover { color: #58A6FF; }")
        self.btn_toggle_adv.clicked.connect(self._toggle_advanced)
        adv_vbox.addWidget(self.btn_toggle_adv)

        self.adv_content = QWidget()
        self.adv_content.setVisible(False)
        adv_grid = QGridLayout(self.adv_content)
        adv_grid.setSpacing(6)

        self.lbl_uninstall_cmd = QLabel("-")
        self.lbl_uninstall_cmd.setStyleSheet("color: #8B949E; font-size: 11px; font-family: Consolas, monospace;")
        self.lbl_uninstall_cmd.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_uninstall_cmd.setWordWrap(True)

        self.lbl_reg_path = QLabel("-")
        self.lbl_reg_path.setStyleSheet("color: #8B949E; font-size: 11px; font-family: Consolas, monospace;")
        self.lbl_reg_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_reg_path.setWordWrap(True)

        adv_grid.addWidget(QLabel("أمر الإزالة (UninstallString):"), 0, 0)
        adv_grid.addWidget(self.lbl_uninstall_cmd, 0, 1)
        adv_grid.addWidget(QLabel("مسار مفتاح السجل (Registry):"), 1, 0)
        adv_grid.addWidget(self.lbl_reg_path, 1, 1)

        adv_vbox.addWidget(self.adv_content)
        self.content_layout.addWidget(self.adv_card)

        self.content_layout.addStretch(1)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        self._update_ui_state()

    def set_app(self, app: Optional[InstalledApp]):
        """Populates the panel with details of the given application."""
        self._current_app = app
        self._update_ui_state()

    def _update_ui_state(self):
        app = self._current_app
        if not app:
            self.lbl_name.setText("اختر برنامجاً من القائمة")
            self.lbl_meta.setText("لعرض معلوماته وإدارته")
            self.lbl_icon.setPixmap(get_icon("apps", color="#30363D", size=40).pixmap(40, 40))
            self._clear_badges()
            self.btn_run.setEnabled(False)
            self.btn_open_folder.setEnabled(False)
            self.btn_website.setEnabled(False)
            self.btn_update.setEnabled(False)
            self.btn_repair.setEnabled(False)
            self.btn_reset.setEnabled(False)
            self.btn_uninstall.setEnabled(False)
            self.btn_leftovers.setEnabled(False)
            for k in self.fields:
                self.fields[k].setText("-")
            return

        self.lbl_name.setText(app.name)
        self.lbl_meta.setText(f"{app.publisher} • الإصدار {app.version}")
        self.lbl_icon.setPixmap(get_icon("apps", color="#58A6FF", size=40).pixmap(40, 40))

        # Badges
        self._clear_badges()
        if app.update_available:
            self._add_badge(f"تحديث متاح: {app.available_version}", "#1F6FEB")
        if app.is_running:
            self._add_badge(f"يعمل الآن ({len(app.running_pids)} عملية)", "#238636")
        if app.is_startup:
            self._add_badge("بدء التشغيل", "#8957E5")
        if app.is_broken:
            self._add_badge("إدخال معطوب", "#DA3633")
        if app.is_system_component:
            self._add_badge("مكون نظام محمي", "#D29922")

        # Action Buttons State
        has_exe = bool(app.main_executable and os.path.exists(app.main_executable))
        has_folder = bool(app.install_location and os.path.exists(app.install_location))
        has_link = bool(app.help_link or app.url_info_about)

        self.btn_run.setEnabled(has_exe)
        self.btn_open_folder.setEnabled(has_folder)
        self.btn_website.setEnabled(has_link)
        self.btn_update.setEnabled(app.update_available)
        self.btn_repair.setEnabled(app.can_repair)
        self.btn_reset.setEnabled(app.can_reset)
        self.btn_uninstall.setEnabled(app.can_uninstall)
        self.btn_leftovers.setEnabled(True)

        # Specifications
        self.fields["location"].setText(app.install_location or "غير مسجل")
        self.fields["executable"].setText(app.main_executable or "غير مسجل")
        self.fields["size_reg"].setText(format_bytes(app.installed_size))
        self.fields["size_calc"].setText(format_bytes(app.calculated_size) if app.calculated_size else "لم يتم الفحص بعد")
        self.fields["architecture"].setText(app.architecture.upper())
        self.fields["install_date"].setText(app.formatted_install_date)
        self.fields["package_id"].setText(app.package_id or "غير متوفر")
        self.fields["product_code"].setText(app.product_code or "غير متوفر")
        self.fields["running_state"].setText("يعمل حالياً" if app.is_running else "غير نشط")
        self.fields["startup_state"].setText("نعم" if app.is_startup else "لا")

        # Advanced
        self.lbl_uninstall_cmd.setText(app.uninstall_string or "غير متوفر")
        self.lbl_reg_path.setText(app.registry_key_path or "غير مسجل")

    def _clear_badges(self):
        while self.badges_layout.count() > 0:
            item = self.badges_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_badge(self, text: str, bg_hex: str):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background: {bg_hex}; color: white; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
        self.badges_layout.addWidget(lbl)

    def _toggle_advanced(self):
        is_vis = self.adv_content.isVisible()
        self.adv_content.setVisible(not is_vis)
        self.btn_toggle_adv.setText("▾ التفاصيل التقنية المتقدمة للمحترفين" if not is_vis else "▸ التفاصيل التقنية المتقدمة للمحترفين")

    def _on_run_app(self):
        if self._current_app and self._current_app.main_executable and os.path.exists(self._current_app.main_executable):
            try:
                os.startfile(self._current_app.main_executable)
            except Exception as e:
                QMessageBox.warning(self, "خطأ في التشغيل", f"تعذر تشغيل البرنامج: {e}")

    def _on_open_folder(self):
        if self._current_app and self._current_app.install_location and os.path.exists(self._current_app.install_location):
            try:
                os.startfile(self._current_app.install_location)
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"تعذر فتح المجلد: {e}")

    def _on_open_website(self):
        if self._current_app:
            url = self._current_app.help_link or self._current_app.url_info_about
            if url:
                QDesktopServices.openUrl(QUrl(url))

    def _on_calculate_real_size(self):
        if not self._current_app or not self._current_app.install_location:
            QMessageBox.information(self, "حساب الحجم", "مسار تثبيت البرنامج غير محدد لحساب حجمه.")
            return

        loc = self._current_app.install_location
        sz = AppSizeService.calculate_folder_size(loc)
        self._current_app.calculated_size = sz
        self.fields["size_calc"].setText(format_bytes(sz))

    def _create_btn(self, text: str, icon_name: str, bg_hex: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setIcon(get_icon(icon_name, color="#F0F6FC"))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg_hex}; color: #F0F6FC; border: none; border-radius: 6px;
                padding: 8px 12px; font-size: 12px; font-weight: bold; text-align: center;
            }}
            QPushButton:hover {{ opacity: 0.85; filter: brightness(1.15); }}
            QPushButton:disabled {{ background: #21262D; color: #484F58; }}
        """)
        btn.clicked.connect(callback)
        return btn
