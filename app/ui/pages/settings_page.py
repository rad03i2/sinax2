# -*- coding: utf-8 -*-
"""
SINAX Settings Page
Preferences management: themes, confirm behavior, recent history, and system guards.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QGroupBox, QScrollArea, QFrame, QSpacerItem, QSizePolicy, QMessageBox, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtQuickWidgets import QQuickWidget
from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.core.config import config
from app.controllers.settings_controller import settings_controller
from app.ui.themes.theme_manager import theme_manager
from app.ui.icons import get_icon

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.stack = QStackedWidget(self)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.stack)

        # Page 0: Modern QML Settings
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)

        # Register the settings controller explicitly on this QML engine.
        # The generic lazy resolver remains in place, but this direct binding is
        # intentional: update buttons must never render as inert controls in a
        # frozen/PyInstaller build if lazy controller discovery fails.
        engine = self.quick_widget.engine()
        configure_qml_engine(engine, "settingsController")
        engine.rootContext().setContextProperty("settingsController", settings_controller)

        self.quick_widget.setSource(get_qml_url("pages/SettingsPage.qml"))
        self.stack.addWidget(self.quick_widget)

        # Page 1: Legacy Scroll Area (for test compatibility)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.verticalScrollBar().setSingleStep(28)
        self.stack.addWidget(scroll)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 24, 30, 48)
        layout.setSpacing(18)

        # Title
        title_lbl = QLabel("إعدادات البرنامج والتفضيلات")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(title_lbl)

        # 1. Appearance Group
        app_box = QGroupBox("المظهر والواجهة")
        app_layout = QVBoxLayout(app_box)
        app_layout.setSpacing(12)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("مظهر التطبيق:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("تلقائي (حسب سمة النظام - System)", "system")
        self.theme_combo.addItem("الوضع الفاتح (Light Mode)", "light")
        self.theme_combo.addItem("الوضع الداكن (Dark Mode)", "dark")
        
        # Set active mode
        curr_mode = theme_manager.theme_mode
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == curr_mode:
                self.theme_combo.setCurrentIndex(i)
                break
        self.theme_combo.currentIndexChanged.connect(self._on_theme_combo_changed)
        theme_row.addWidget(self.theme_combo)
        app_layout.addLayout(theme_row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("لغة الواجهة:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("العربية (Arabic - RTL)", "ar")
        self.lang_combo.addItem("English (قريباً في التحديثات القادمة)", "en")
        self.lang_combo.setEnabled(False)
        lang_row.addWidget(self.lang_combo)
        app_layout.addLayout(lang_row)

        layout.addWidget(app_box)

        # 2. Safety & Confirmations
        safe_box = QGroupBox("الأمان والتأكيد")
        safe_layout = QVBoxLayout(safe_box)
        safe_layout.setSpacing(12)

        self.confirm_cb = QCheckBox("إظهار نافذة تأكيد قبل تنفيذ العمليات الكبيرة")
        self.confirm_cb.setChecked(config.get("confirm_sensitive_ops", True))
        self.confirm_cb.toggled.connect(lambda v: config.set("confirm_sensitive_ops", v))
        safe_layout.addWidget(self.confirm_cb)

        self.recycle_cb = QCheckBox("استخدام سلة محذوفات ويندوز (Recycle Bin) عند الحذف بدلاً من الحذف النهائي")
        self.recycle_cb.setChecked(config.get("use_recycle_bin", True))
        self.recycle_cb.toggled.connect(lambda v: config.set("use_recycle_bin", v))
        safe_layout.addWidget(self.recycle_cb)

        layout.addWidget(safe_box)

        # 3. Folders & Memory
        mem_box = QGroupBox("الذاكرة والمجلدات الأخيرة")
        mem_layout = QVBoxLayout(mem_box)
        mem_layout.setSpacing(12)

        self.remember_cb = QCheckBox("تذكر آخر مجلد تم فتحه عند تشغيل البرنامج")
        self.remember_cb.setChecked(config.get("remember_last_folder", True))
        self.remember_cb.toggled.connect(lambda v: config.set("remember_last_folder", v))
        mem_layout.addWidget(self.remember_cb)

        clear_recent_btn = QPushButton("مسح قائمة المجلدات الأخيرة")
        clear_recent_btn.setIcon(get_icon("trash", "#FF4D4F", 14))
        clear_recent_btn.setFixedWidth(200)
        clear_recent_btn.clicked.connect(self._on_clear_recents)
        mem_layout.addWidget(clear_recent_btn)

        layout.addWidget(mem_box)

        # 4. Storage & Paths Info
        info_box = QGroupBox("بيانات النظام والتخزين")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(8)

        cfg_path_lbl = QLabel(f"مسار حفظ الإعدادات:\n{config.config_file}")
        cfg_path_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(cfg_path_lbl)

        log_path_lbl = QLabel(f"مسار سجلات البرنامج:\n{config.config_dir / 'logs' / 'sinax.log'}")
        log_path_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(log_path_lbl)

        layout.addWidget(info_box)
        layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _on_theme_combo_changed(self, idx: int):
        new_mode = self.theme_combo.itemData(idx)
        if new_mode:
            theme_manager.set_theme_mode(new_mode)

    def apply_theme(self, theme_name: str):
        if hasattr(self, "theme_combo"):
            self.theme_combo.blockSignals(True)
            mode = theme_manager.theme_mode
            for i in range(self.theme_combo.count()):
                if self.theme_combo.itemData(i) == mode:
                    self.theme_combo.setCurrentIndex(i)
                    break
            self.theme_combo.blockSignals(False)

    def _on_clear_recents(self):
        config.set("recent_folders", [], auto_save=True)
        QMessageBox.information(self, "تم المسح", "تم مسح قائمة المجلدات الأخيرة بنجاح.")
