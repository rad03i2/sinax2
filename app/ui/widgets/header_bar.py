# -*- coding: utf-8 -*-
"""
SINAX Header Bar
Top navigation bar featuring page breadcrumb, back navigation, and global tools.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtQuickWidgets import QQuickWidget

from app.core.qml_helper import configure_qml_engine, get_qml_url
from app.controllers.navigation_controller import navigation_controller
from app.controllers.theme_controller import theme_controller
from app.ui.icons import get_icon
from app.ui.themes.theme_manager import theme_manager


class HeaderBar(QFrame):
    """
    Modern QML-Powered TopBar with 100% Backward Compatibility.
    Renders TopBar.qml via QQuickWidget while preserving all legacy attributes and signals.
    """
    back_requested = Signal()
    settings_requested = Signal()
    about_requested = Signal()
    open_job_center_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderFrame")
        self.setFixedHeight(50)
        self._init_compatibility_elements()
        self._init_qml_ui()

    def _init_compatibility_elements(self):
        # Compatibility widgets retained for any legacy test or inspection
        self.back_btn = QPushButton(self)
        self.back_btn.clicked.connect(self.back_requested.emit)

        self.title_label = QLabel("إدارة الملفات", self)
        self.subtitle_label = QLabel("", self)

        self.theme_btn = QPushButton(self)
        self.theme_btn.clicked.connect(self._on_toggle_theme)

        self.settings_btn = QPushButton(self)
        self.settings_btn.clicked.connect(self.settings_requested.emit)

        self.about_btn = QPushButton(self)
        self.about_btn.clicked.connect(self.about_requested.emit)

        # Ensure compatibility widgets never render or intercept pointer events
        for w in [self.back_btn, self.title_label, self.subtitle_label, self.theme_btn, self.settings_btn, self.about_btn]:
            w.hide()
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def _init_qml_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine())
        self.quick_widget.setSource(get_qml_url("navigation/TopBar.qml"))
        layout.addWidget(self.quick_widget)
        self.quick_widget.raise_()

        root_obj = self.quick_widget.rootObject()
        if root_obj and hasattr(root_obj, "openJobCenter"):
            root_obj.openJobCenter.connect(self.open_job_center_requested.emit)

        navigation_controller.routeRequested.connect(self._on_controller_route)

    def _on_controller_route(self, route: str):
        if route == "settings":
            self.settings_requested.emit()
        elif route == "about":
            self.about_requested.emit()

    def set_title(self, title: str, subtitle: str = "", show_back: bool = False, breadcrumb = None):
        if breadcrumb and len(breadcrumb) > 1:
            parent_part = f"<span style='color: #888888; font-weight: normal;'>{breadcrumb[0]}</span>"
            sep_part = "<span style='color: #555555;'>  ›  </span>"
            child_part = f"<span style='color: #FFFFFF; font-weight: bold;'>{breadcrumb[1]}</span>"
            self.title_label.setText(f"{parent_part}{sep_part}{child_part}")
        else:
            self.title_label.setText(title)

        self.subtitle_label.setText(subtitle)
        # self.back_btn remains hidden as TopBar.qml handles back button

    def _update_theme_icon(self):
        curr = theme_manager.current_theme
        if curr == "dark":
            self.theme_btn.setIcon(get_icon("sun", "#FFD700", 18))
        else:
            self.theme_btn.setIcon(get_icon("moon", "#0078D4", 18))

    def _on_toggle_theme(self):
        theme_manager.toggle_theme()
        self._update_theme_icon()
