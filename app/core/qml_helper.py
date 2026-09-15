# -*- coding: utf-8 -*-
"""
SINAX QML Helper & Resource Resolver
Resolves QML URLs via Qt Resources (qrc:/) or local development filesystem fallbacks.
Configures QQmlEngine instances with singletons, icon providers, and import paths.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtCore import QUrl, QFile, Qt
from PySide6.QtQml import QQmlEngine
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QStackedLayout
)
from PySide6.QtQuickWidgets import QQuickWidget

from app.ui.qml_icon_provider import SinaxIconProvider
from app.controllers.navigation_controller import navigation_controller
from app.controllers.theme_controller import theme_controller
from app.controllers.job_controller import job_controller
from app.controllers.command_palette_controller import command_palette_controller
from app.controllers.quick_about_controller import quick_about_controller
from app.core.logger import get_logger

logger = get_logger("qml_helper")

# Map of controller property names to (module_path, attribute_name)
_CONTROLLER_MAP = {
    "dashboardController": ("app.controllers.dashboard_controller", "dashboard_controller"),
    "fileManagementController": ("app.controllers.file_management_controller", "file_management_controller"),
    "systemStorageController": ("app.controllers.system_storage_controller", "system_storage_controller"),
    "devicesController": ("app.controllers.devices_controller", "devices_controller"),
    "backupSyncController": ("app.controllers.backup_sync_controller", "backup_sync_controller"),
    "maintenanceController": ("app.controllers.maintenance_controller", "maintenance_controller"),
    "quickToolsController": ("app.controllers.quick_tools_controller", "quick_tools_controller"),
    "pdfController": ("app.controllers.pdf_controller", "pdf_controller"),
    "imageController": ("app.controllers.image_controller", "image_controller"),
    "videoController": ("app.controllers.video_controller", "video_controller"),
    "audioController": ("app.controllers.audio_controller", "audio_controller"),
    "appsController": ("app.controllers.apps_controller", "apps_controller"),
    "networkController": ("app.controllers.network_controller", "network_controller"),
    "privacyController": ("app.controllers.privacy_controller", "privacy_controller"),
    "historyController": ("app.controllers.history_controller", "history_controller"),
    "settingsController": ("app.controllers.settings_controller", "settings_controller"),
}

_QML_FILE_TO_CONTROLLER = {
    "Dashboard.qml": "dashboardController",
    "FileManagerPage.qml": "fileManagementController",
    "SystemStoragePage.qml": "systemStorageController",
    "DevicesPage.qml": "devicesController",
    "BackupSyncPage.qml": "backupSyncController",
    "MaintenancePage.qml": "maintenanceController",
    "QuickToolsPage.qml": "quickToolsController",
    "PdfCenterPage.qml": "pdfController",
    "ImageCenterPage.qml": "imageController",
    "VideoCenterPage.qml": "videoController",
    "AudioCenterPage.qml": "audioController",
    "AppsManagementPage.qml": "appsController",
    "NetworkCenterPage.qml": "networkController",
    "PrivacySecurityPage.qml": "privacyController",
    "HistoryPage.qml": "historyController",
    "SettingsPage.qml": "settingsController",
}

_LOADED_CONTROLLERS = {}


def get_controller(prop_name: str):
    """Returns controller instance, importing and caching lazily on first access."""
    if prop_name in _LOADED_CONTROLLERS:
        return _LOADED_CONTROLLERS[prop_name]
    if prop_name in _CONTROLLER_MAP:
        mod_name, attr_name = _CONTROLLER_MAP[prop_name]
        try:
            mod = __import__(mod_name, fromlist=[attr_name])
            ctrl = getattr(mod, attr_name)
            _LOADED_CONTROLLERS[prop_name] = ctrl
            return ctrl
        except Exception as e:
            logger.error(f"Failed to lazy load controller {prop_name}: {e}")
            return None
    return None


QML_ROOT = (Path(__file__).parent.parent / "ui" / "qml").resolve()


def get_qml_url(rel_path: str) -> QUrl:
    """
    Returns QUrl for a QML file, trying Qt Resource prefix first, then local filesystem.
    rel_path: e.g. 'navigation/Sidebar.qml' or 'pages/Dashboard.qml'
    """
    # 1. Check if resource is registered in Qt Resource system
    qrc_path = f":/../ui/qml/{rel_path}"
    if QFile.exists(qrc_path):
        return QUrl(f"qrc{qrc_path[1:]}")

    # 2. Local filesystem resolution
    local_path = QML_ROOT / rel_path
    return QUrl.fromLocalFile(str(local_path))


def configure_qml_engine(engine: QQmlEngine, controller_hint: Optional[str] = None):
    """
    Configures QQmlEngine with icon provider, import paths, and controllers.
    Controllers are loaded lazily to preserve lightning-fast startup.
    controller_hint: Property name (e.g. 'pdfController') or QML path (e.g. 'pages/PdfCenterPage.qml')
    """
    if not engine.imageProvider("sinax"):
        engine.addImageProvider("sinax", SinaxIconProvider())

    qml_dir_str = str(QML_ROOT)
    if qml_dir_str not in engine.importPathList():
        engine.addImportPath(qml_dir_str)

    root_ctx = engine.rootContext()

    # Universal core context properties always available
    root_ctx.setContextProperty("navController", navigation_controller)
    root_ctx.setContextProperty("themeController", theme_controller)
    root_ctx.setContextProperty("commandPaletteController", command_palette_controller)
    root_ctx.setContextProperty("jobController", job_controller)
    root_ctx.setContextProperty("quickAboutController", quick_about_controller)

    # Determine requested controller from hint
    requested_prop = None
    if controller_hint:
        if controller_hint in _CONTROLLER_MAP:
            requested_prop = controller_hint
        else:
            filename = Path(controller_hint).name
            requested_prop = _QML_FILE_TO_CONTROLLER.get(filename)

    if requested_prop:
        ctrl = get_controller(requested_prop)
        if ctrl is not None:
            root_ctx.setContextProperty(requested_prop, ctrl)

    # Register all controllers that have been loaded so far
    for prop_name, ctrl in _LOADED_CONTROLLERS.items():
        root_ctx.setContextProperty(prop_name, ctrl)


class QmlErrorBoundaryWidget(QWidget):
    """
    Error-resilient QML widget wrapper acting as a QML Error Boundary.
    Catches QML syntax, import, and runtime errors, rendering an elegant fallback
    card with reload and diagnostic options instead of crashing the application.
    """
    def __init__(self, rel_path: str, parent=None):
        super().__init__(parent)
        self.rel_path = rel_path
        self._init_ui()

    def _init_ui(self):
        self.stack_layout = QStackedLayout(self)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)

        # 0: QuickWidget
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        configure_qml_engine(self.quick_widget.engine(), self.rel_path)
        self.quick_widget.statusChanged.connect(self._on_status_changed)

        # 1: Fallback Error Card
        self.error_card = QFrame(self)
        self.error_card.setStyleSheet("""
            QFrame {
                background-color: #1A1D24;
                border-radius: 12px;
                border: 1px solid #FF4D4F;
            }
        """)
        card_layout = QVBoxLayout(self.error_card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)
        card_layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel("⚠️", self.error_card)
        icon_lbl.setStyleSheet("font-size: 42px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_lbl)

        title_lbl = QLabel("تعذر تحميل واجهة هذا المركز", self.error_card)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        title_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "تم التقاط الخطأ عبر جدار الحماية (QML Error Boundary). "
            "بقية أقسام البرنامج تعمل بكامل طاقتها وأمانها دون تأثر.",
            self.error_card
        )
        desc_lbl.setStyleSheet("font-size: 13px; color: #9CA3AF;")
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setWordWrap(True)
        card_layout.addWidget(desc_lbl)

        self.error_text = QTextEdit(self.error_card)
        self.error_text.setReadOnly(True)
        self.error_text.setStyleSheet("""
            QTextEdit {
                background-color: #0F1115;
                color: #FF8F8F;
                border: 1px solid #2D3139;
                border-radius: 8px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        self.error_text.setMaximumHeight(160)
        card_layout.addWidget(self.error_text)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.setAlignment(Qt.AlignCenter)

        reload_btn = QPushButton(" إعادة تحميل الصفحة", self.error_card)
        reload_btn.setCursor(Qt.PointingHandCursor)
        reload_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        reload_btn.clicked.connect(self.reload)
        btn_layout.addWidget(reload_btn)

        copy_btn = QPushButton("نسخ تفاصيل الخطأ", self.error_card)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        copy_btn.clicked.connect(self._copy_error)
        btn_layout.addWidget(copy_btn)

        card_layout.addLayout(btn_layout)

        self.stack_layout.addWidget(self.quick_widget)
        self.stack_layout.addWidget(self.error_card)

        self.load()

    def load(self):
        url = get_qml_url(self.rel_path)
        self.quick_widget.setSource(url)

    def reload(self):
        self.quick_widget.engine().clearComponentCache()
        self.load()

    def _on_status_changed(self, status):
        if status == QQuickWidget.Error:
            err_msgs = [e.toString() for e in self.quick_widget.errors()]
            joined_err = "\n".join(err_msgs) if err_msgs else "Unknown QML runtime error."
            self.error_text.setPlainText(joined_err)
            self.stack_layout.setCurrentIndex(1)
        elif status == QQuickWidget.Ready:
            self.stack_layout.setCurrentIndex(0)

    def _copy_error(self):
        from PySide6.QtGui import QGuiApplication
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setText(self.error_text.toPlainText())

    def engine(self):
        return self.quick_widget.engine()

    def rootObject(self):
        return self.quick_widget.rootObject()


def create_qml_widget(rel_path: str, parent=None) -> QWidget:
    """Factory creating a safe QmlErrorBoundaryWidget for any QML page."""
    return QmlErrorBoundaryWidget(rel_path, parent)

