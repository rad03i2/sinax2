# -*- coding: utf-8 -*-
"""
SINAX MainWindow
Central desktop window orchestrating sidebar navigation, responsive stacked pages,
drag-and-drop ingestion, and status reporting.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox,
    QFrame, QLabel, QPushButton
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QKeySequence, QShortcut

from app.core.constants import APP_NAME, APP_NAME_AR, APP_VERSION
from app.core.config import config
from app.core.crash_recovery import crash_recovery_manager
from app.controllers.command_palette_controller import command_palette_controller
from app.controllers.navigation_controller import navigation_controller
from app.ui.widgets.sidebar import Sidebar
from app.ui.widgets.header_bar import HeaderBar
from app.ui.widgets.status_bar import StatusBar
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.command_palette_dialog import CommandPaletteDialog
from app.ui.dialogs.job_center_dialog import JobCenterDialog
from app.ui.dialogs.quick_about_dialog import QuickAboutDialog
from app.ui.dialogs.sidebar_flyout_dialog import SidebarFlyoutDialog
from app.ui.design_system import AnimatedStackedWidget
from app.ui.icons import create_sinax_logo
from app.core.logger import get_logger

logger = get_logger("main_window")

class MainWindow(QMainWindow):
    _ATTR_TO_INDEX = {
        "dashboard_page": 0,
        "file_manager_page": 1,
        "batch_rename_page": 2,
        "merge_page": 3,
        "organize_page": 4,
        "search_page": 5,
        "duplicate_page": 6,
        "history_page": 7,
        "settings_page": 8,
        "converter_page": 9,
        "pdf_center_page": 10,
        "image_center_page": 11,
        "video_center_page": 12,
        "audio_center_page": 13,
        "system_storage_page": 14,
        "apps_manager_page": 15,
        "network_page": 16,
        "devices_page": 17,
        "quick_tools_page": 18,
        "privacy_security_page": 19,
        "maintenance_page": 20,
        "backup_sync_page": 21,
        "about_page": 22,
        "icon_gallery_page": 23,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_NAME_AR} | نظام إدارة الحاسوب والملفات")
        self.setWindowIcon(create_sinax_logo(32))
        self.setMinimumSize(980, 680)
        self.setAcceptDrops(True)
        self.setLayoutDirection(Qt.RightToLeft)
        self._nav_history = []
        self._pending_batch_dir = None

        # Lazy loading state
        self._loaded_pages = {}
        self._page_registry = {}

        self._init_ui()
        self._restore_geometry()
        from app.ui.themes.theme_manager import theme_manager
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def __getattr__(self, name: str):
        """Transparent lazy loading accessor for page attributes."""
        if name in MainWindow._ATTR_TO_INDEX:
            idx = MainWindow._ATTR_TO_INDEX[name]
            page = self.ensure_page_loaded(idx)
            if page is not None:
                return page
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def is_page_loaded(self, idx_or_name) -> bool:
        """Checks if a page has already been instantiated without triggering lazy load."""
        if isinstance(idx_or_name, int):
            return idx_or_name in self._loaded_pages
        idx = self._ATTR_TO_INDEX.get(idx_or_name)
        return idx is not None and idx in self._loaded_pages

    def get_page(self, idx_or_name):
        """Returns the page widget, triggering lazy loading if not yet loaded."""
        if isinstance(idx_or_name, int):
            return self.ensure_page_loaded(idx_or_name)
        idx = self._ATTR_TO_INDEX.get(idx_or_name)
        if idx is not None:
            return self.ensure_page_loaded(idx)
        return None

    def _init_ui(self):
        self.setUpdatesEnabled(False)
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        # Main horizontal layout: Sidebar + Content Area
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_selected.connect(self._on_sidebar_nav)
        root_layout.addWidget(self.sidebar)

        # Content Vertical Container: Header + Pages + Status Bar
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header Bar
        self.header_bar = HeaderBar()
        self.header_bar.back_requested.connect(self._go_back)
        self.header_bar.settings_requested.connect(lambda: self.navigate_to("settings"))
        self.header_bar.about_requested.connect(self._show_about)
        content_layout.addWidget(self.header_bar)

        # Safe UI Mode Banner
        if crash_recovery_manager.should_enter_safe_mode():
            self._safe_banner = QFrame()
            self._safe_banner.setStyleSheet("""
                QFrame {
                    background-color: #2D2305;
                    border-bottom: 2px solid #D97706;
                }
            """)
            banner_layout = QHBoxLayout(self._safe_banner)
            banner_layout.setContentsMargins(16, 6, 16, 6)
            banner_layout.setSpacing(12)

            banner_text = QLabel("⚠️ وضع الإقلاع الآمن (Safe UI Mode) نشط: تم تقليل تسريع الرسوميات للمساعدة في الاستقرار وتشخيص الأعطال.")
            banner_text.setStyleSheet("color: #FCD34D; font-weight: bold; font-size: 13px;")
            banner_layout.addWidget(banner_text, 1)

            logs_btn = QPushButton("سجلات الأخطاء")
            logs_btn.setCursor(Qt.PointingHandCursor)
            logs_btn.setStyleSheet("background-color: #451A03; color: #FDE68A; border: 1px solid #78350F; border-radius: 4px; padding: 4px 10px; font-size: 12px;")
            logs_btn.clicked.connect(self._open_logs_dir)
            banner_layout.addWidget(logs_btn)

            repair_btn = QPushButton("إصلاح ذاتي للواجهة")
            repair_btn.setCursor(Qt.PointingHandCursor)
            repair_btn.setStyleSheet("background-color: #1E3A8A; color: #BFDBFE; border: 1px solid #1D4ED8; border-radius: 4px; padding: 4px 10px; font-size: 12px;")
            repair_btn.clicked.connect(self._trigger_self_repair)
            banner_layout.addWidget(repair_btn)

            content_layout.addWidget(self._safe_banner)

        # Phase 2: Command Palette (Ctrl+K) & Job Center Drawer Overlays
        self.command_palette_dialog = CommandPaletteDialog(self)
        self.job_center_dialog = JobCenterDialog(self)
        self.quick_about_dialog = QuickAboutDialog(self)
        self.sidebar_flyout_dialog = SidebarFlyoutDialog(self, sidebar_widget=self.sidebar)
        self.palette_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self.palette_shortcut.activated.connect(command_palette_controller.toggle)
        self.header_bar.open_job_center_requested.connect(self.job_center_dialog.show_drawer)
        navigation_controller.routeRequested.connect(self.navigate_to)

        # Pages Stack
        self.stack = AnimatedStackedWidget()

        # Page 0: Executive Command Dashboard (Eagerly loaded in ~150ms)
        self.dashboard_page = DashboardPage()
        self.dashboard_page.navigate_requested.connect(self.navigate_to)
        self.stack.addWidget(self.dashboard_page)
        self._loaded_pages[0] = self.dashboard_page

        # Register lazy factories for Pages 1..23 and fill stack with lightweight placeholders
        self._setup_page_factories()
        for _ in range(1, 24):
            self.stack.addWidget(QWidget())

        content_layout.addWidget(self.stack, 1)

        # Status Bar
        self.status_bar = StatusBar()
        self.status_bar.cancel_requested.connect(self._on_cancel_requested)
        content_layout.addWidget(self.status_bar)

        root_layout.addWidget(content_container, 1)

        # Check last folder preference
        if config.get("remember_last_folder", True):
            last_f = config.get("last_folder", "")
            if last_f and Path(last_f).exists():
                self._pending_batch_dir = Path(last_f)

        # Start on Executive Dashboard
        self.navigate_to("dashboard", record_history=False)
        self.setUpdatesEnabled(True)

    def _setup_page_factories(self):
        """Defines lazy construction recipes for all application pages."""
        self._page_registry = {
            1: {"attr": "file_manager_page", "factory": self._create_file_manager_page},
            2: {"attr": "batch_rename_page", "factory": self._create_batch_rename_page},
            3: {"attr": "merge_page", "factory": self._create_merge_page},
            4: {"attr": "organize_page", "factory": self._create_organize_page},
            5: {"attr": "search_page", "factory": self._create_search_page},
            6: {"attr": "duplicate_page", "factory": self._create_duplicate_page},
            7: {"attr": "history_page", "factory": self._create_history_page},
            8: {"attr": "settings_page", "factory": self._create_settings_page},
            9: {"attr": "converter_page", "factory": self._create_converter_page},
            10: {"attr": "pdf_center_page", "factory": self._create_pdf_center_page},
            11: {"attr": "image_center_page", "factory": self._create_image_center_page},
            12: {"attr": "video_center_page", "factory": self._create_video_center_page},
            13: {"attr": "audio_center_page", "factory": self._create_audio_center_page},
            14: {"attr": "system_storage_page", "factory": self._create_system_storage_page},
            15: {"attr": "apps_manager_page", "factory": self._create_apps_manager_page},
            16: {"attr": "network_page", "factory": self._create_network_page},
            17: {"attr": "devices_page", "factory": self._create_devices_page},
            18: {"attr": "quick_tools_page", "factory": self._create_quick_tools_page},
            19: {"attr": "privacy_security_page", "factory": self._create_privacy_security_page},
            20: {"attr": "maintenance_page", "factory": self._create_maintenance_page},
            21: {"attr": "backup_sync_page", "factory": self._create_backup_sync_page},
            22: {"attr": "about_page", "factory": self._create_about_page},
            23: {"attr": "icon_gallery_page", "factory": self._create_icon_gallery_page},
        }

    # ==================== Lazy Factory Callables ====================

    def _create_file_manager_page(self):
        from app.ui.pages.file_manager_page import FileManagerPage
        page = FileManagerPage()
        page.open_tool_requested.connect(self._on_hub_tool_selected)
        return page

    def _create_batch_rename_page(self):
        from app.ui.pages.batch_rename_page import BatchRenamePage
        page = BatchRenamePage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        if self._pending_batch_dir:
            page.set_directory(self._pending_batch_dir)
        return page

    def _create_merge_page(self):
        from app.ui.pages.merge_files_page import MergeFilesPage
        page = MergeFilesPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        page.back_to_hub_requested.connect(lambda: self.navigate_to("file_manager"))
        return page

    def _create_organize_page(self):
        from app.ui.pages.smart_organize_page import SmartOrganizePage
        page = SmartOrganizePage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        page.back_to_hub_requested.connect(lambda: self.navigate_to("file_manager"))
        return page

    def _create_search_page(self):
        from app.ui.pages.search_analysis_page import SearchAnalysisPage
        page = SearchAnalysisPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        page.back_to_hub_requested.connect(lambda: self.navigate_to("file_manager"))
        return page

    def _create_duplicate_page(self):
        from app.ui.pages.duplicate_copy_page import DuplicateCopyPage
        page = DuplicateCopyPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        page.back_to_hub_requested.connect(lambda: self.navigate_to("file_manager"))
        return page

    def _create_history_page(self):
        from app.ui.pages.history_page import HistoryPage
        return HistoryPage()

    def _create_settings_page(self):
        from app.ui.pages.settings_page import SettingsPage
        return SettingsPage()

    def _create_converter_page(self):
        from app.ui.pages.universal_converter_page import UniversalConverterPage
        page = UniversalConverterPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        page.back_to_hub_requested.connect(lambda: self.navigate_to("file_manager"))
        return page

    def _create_pdf_center_page(self):
        from app.ui.pages.pdf_center_page import PDFCenterPage
        page = PDFCenterPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        page.back_to_hub_requested.connect(lambda: self.navigate_to("file_manager"))
        return page

    def _create_image_center_page(self):
        from app.ui.pages.image_center_page import ImageCenterPage
        page = ImageCenterPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        return page

    def _create_video_center_page(self):
        from app.ui.pages.video_center_page import VideoCenterPage
        page = VideoCenterPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        return page

    def _create_audio_center_page(self):
        from app.ui.pages.audio_center_page import AudioCenterPage
        page = AudioCenterPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        return page

    def _create_system_storage_page(self):
        from app.ui.pages.system_storage_page import SystemStoragePage
        page = SystemStoragePage()
        page.subpage_changed.connect(self._on_system_storage_subpage_changed)
        return page

    def _create_apps_manager_page(self):
        from app.ui.pages.apps_manager_page import AppsManagerPage
        page = AppsManagerPage()
        page.subpage_changed.connect(self._on_apps_manager_subpage_changed)
        page.open_startup_manager_requested.connect(lambda: self.navigate_to("system_storage_startup"))
        return page

    def _create_network_page(self):
        from app.ui.pages.network_page import NetworkPage
        page = NetworkPage()
        page.subpage_changed.connect(self._on_network_subpage_changed)
        return page

    def _create_devices_page(self):
        from app.ui.pages.devices_page import DevicesPage
        page = DevicesPage()
        page.subpage_changed.connect(self._on_devices_subpage_changed)
        page.external_navigate_requested.connect(self.navigate_to)
        return page

    def _create_quick_tools_page(self):
        from app.ui.pages.quick_tools.quick_tools_page import QuickToolsPage
        page = QuickToolsPage()
        page.status_changed.connect(self._on_page_status)
        page.progress_changed.connect(self._on_page_progress)
        return page

    def _create_privacy_security_page(self):
        from app.ui.pages.privacy_security_page import PrivacySecurityPage
        page = PrivacySecurityPage()
        page.subpage_changed.connect(self._on_privacy_security_subpage_changed)
        return page

    def _create_maintenance_page(self):
        from app.ui.pages.maintenance_page import MaintenancePage
        page = MaintenancePage()
        page.subpage_changed.connect(self._on_maintenance_subpage_changed)
        page.external_navigate_requested.connect(self.navigate_to)
        return page

    def _create_backup_sync_page(self):
        from app.ui.pages.backup_sync_page import BackupSyncPage
        page = BackupSyncPage()
        page.subpage_changed.connect(self._on_backup_sync_subpage_changed)
        page.external_navigate_requested.connect(self.navigate_to)
        return page

    def _create_about_page(self):
        from app.core.qml_helper import create_qml_widget
        return create_qml_widget("pages/AboutPage.qml")

    def _create_icon_gallery_page(self):
        from app.core.qml_helper import create_qml_widget
        return create_qml_widget("pages/DeveloperIconGalleryPage.qml")

    def _open_logs_dir(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        log_dir = config.config_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))

    def _trigger_self_repair(self):
        res = crash_recovery_manager.perform_self_repair()
        if res.get("success"):
            items_str = "\n• ".join(res.get("items", []))
            QMessageBox.information(
                self,
                "اكتمل الإصلاح الذاتي",
                f"تم تنفيذ إجراءات الصيانة التالية بنجاح:\n• {items_str}\n\nيمكنك الآن إعادة تشغيل البرنامج بالوضع الطبيعي."
            )
        else:
            QMessageBox.warning(self, "تنبيه الإصلاح", f"تعذر إكمال بعض عمليات الإصلاح:\n{res.get('error')}")

    # ==================== Lazy Instantiation ====================

    def ensure_page_loaded(self, idx: int):
        """Instantiates and attaches a page widget if not yet loaded."""
        if idx in self._loaded_pages:
            return self._loaded_pages[idx]

        if idx not in self._page_registry:
            return None

        entry = self._page_registry[idx]
        factory = entry["factory"]
        attr_name = entry["attr"]

        logger.info(f"Lazy-loading page index {idx} ({attr_name})...")
        page = factory()
        setattr(self, attr_name, page)
        self._loaded_pages[idx] = page

        # Replace placeholder widget in stack while preserving exact index
        old_widget = self.stack.widget(idx)
        if old_widget is not None:
            self.stack.removeWidget(old_widget)
            old_widget.deleteLater()
        self.stack.insertWidget(idx, page)

        # Apply current effective theme immediately to avoid any visual flash
        from app.ui.themes.theme_manager import theme_manager
        current_theme = theme_manager.effective_theme
        if hasattr(page, "apply_theme"):
            page.apply_theme(current_theme)
        elif hasattr(page, "_apply_theme"):
            page._apply_theme(current_theme)
        elif hasattr(page, "_on_theme_changed"):
            page._on_theme_changed(current_theme)

        return page

    def _on_theme_changed(self, theme_name: str):
        """Notifies all instantiated and cached pages of theme changes."""
        for idx, page in self._loaded_pages.items():
            if hasattr(page, "apply_theme"):
                page.apply_theme(theme_name)
            elif hasattr(page, "_apply_theme"):
                page._apply_theme(theme_name)
            elif hasattr(page, "_on_theme_changed"):
                page._on_theme_changed(theme_name)

    def navigate_to(self, page_id: str, record_history: bool = True):
        page_map = {
            "dashboard": (0, "الرئيسية", "نظرة عامة على النظام", False, ["الرئيسية"]),
            "file_manager": (1, "إدارة الملفات", "المركز الرئيسي لإدارة المستندات والوسائط", False, ["إدارة الملفات"]),
            "batch_rename": (2, "إعادة تسمية الملفات الجماعية", "تغيير الأسماء الذكي والمعاينة الحية", True, ["إدارة الملفات", "إعادة تسمية الملفات الجماعية"]),
            "converter": (9, "المحوّل الشامل للملفات", "تحويل فوري لأكثر من 50 صيغة مستندات وصور وصوت وفيديو وجداول", True, ["إدارة الملفات", "المحوّل الشامل للملفات"]),
            "merge_files": (3, "دمج وتجميع الملفات", "توحيد المستندات والجداول والصور في ملف واحد", True, ["إدارة الملفات", "دمج وتجميع الملفات"]),
            "smart_organize": (4, "التنظيم الذكي للملفات", "فرز وتصنيف المجلدات بدقة وأمان فائق", True, ["إدارة الملفات", "التنظيم الذكي للملفات"]),
            "search_analysis": (5, "البحث والتحليل المتقدم", "بحث ذكي وتعبيرات نمطية وتحليل تفصيلي لمساحة التخزين", True, ["إدارة الملفات", "البحث والتحليل المتقدم"]),
            "duplicate_copy": (6, "النسخ والنقل والتكرار", "كشف فوري للملفات المتطابقة والصور المتشابهة ونقل جماعي آمن", True, ["إدارة الملفات", "النسخ والنقل وكشف التكرار"]),
            "pdf_center": (10, "مركز PDF", "كل ما تحتاجه لإنشاء وتعديل وتنظيم وتحسين وحماية وتوقيع ملفات PDF", True, ["إدارة الملفات", "مركز PDF"]),
            "image_center": (11, "مركز الصور", "أدوات متقدمة لمعالجة وتحويل وضغط وتحسين وتنظيم آلاف الصور بسهولة", True, ["الوسائط المتعددة", "مركز الصور"]),
            "video_center": (12, "مركز الفيديو", "منظومة متكاملة لمعالجة وتحويل وضغط وتقطيع ودمج وتحسين مقاطع الفيديو محلياً", True, ["الوسائط المتعددة", "مركز الفيديو"]),
            "audio_center": (13, "مركز الصوت", "المحطة الشاملة لمعالجة وتحويل وضغط وتنقية وهندسة الصوتيات والبودكاست", True, ["الوسائط المتعددة", "مركز الصوت"]),
            "system_storage": (14, "النظام والتخزين", "منظومة تحليل مساحة القرص ومراقبة الأداء وإدارة العمليات وبدء التشغيل", False, ["النظام والتخزين"]),
            "system_storage_overview": (14, "نظرة عامة - النظام والتخزين", "لوحة قيادة سعة الأقراص والتوصيات الذكية الشاملة", True, ["النظام والتخزين", "نظرة عامة"]),
            "system_storage_analyzer": (14, "محلل التخزين", "تحليل شجري وتفاعلي لمساحة الأقراص والمجلدات وأكبر الملفات", True, ["النظام والتخزين", "محلل التخزين"]),
            "system_storage_cleanup": (14, "التنظيف الآمن", "تنظيف شفاف وآمن للملفات المؤقتة وسلة المحذوفات والكاش", True, ["النظام والتخزين", "التنظيف الآمن"]),
            "system_storage_health": (14, "صحة الأقراص و S.M.A.R.T.", "مؤشرات سلامة العتاد ودرجة الحرارة وساعات التشغيل", True, ["النظام والتخزين", "صحة الأقراص"]),
            "system_storage_performance": (14, "مراقبة الأداء الحي", "رسوم بيانية حية لاستهلاك المعالج والذاكرة وحركة القرص", True, ["النظام والتخزين", "مراقبة الأداء"]),
            "system_storage_processes": (14, "إدارة العمليات وقفل الملفات", "مراقبة العمليات النشطة وأداة كشف قفل الملفات", True, ["النظام والتخزين", "إدارة العمليات"]),
            "system_storage_startup": (14, "إدارة بدء التشغيل", "التحكم الآمن في البرامج التي تبدأ مع إقلاع ويندوز", True, ["النظام والتخزين", "بدء التشغيل"]),
            "system_storage_device": (14, "مواصفات الجهاز والتقارير", "تقرير تفصيلي لمواصفات العتاد ونظام التشغيل وتصدير التقارير", True, ["النظام والتخزين", "مواصفات الجهاز"]),
            "apps_manager": (15, "إدارة البرامج والتطبيقات", "المركز الشامل لجرد وتحديث وإلغاء تثبيت البرامج واستعادتها", False, ["إدارة البرامج والتطبيقات"]),
            "apps_overview": (15, "نظرة عامة - إدارة البرامج", "لوحة قيادة وإحصائيات البرامج المثبتة والتوصيات", True, ["إدارة البرامج والتطبيقات", "نظرة عامة"]),
            "apps_inventory": (15, "كل البرامج المثبتة", "جرد شامل وتفاصيل الحزم والمثبتات والبحث المتقدم", True, ["إدارة البرامج والتطبيقات", "كل البرامج"]),
            "apps_updates": (15, "تحديثات البرامج", "اكتشاف التحديثات الجديدة وتثبيتها عبر WinGet", True, ["إدارة البرامج والتطبيقات", "التحديثات"]),
            "apps_uninstall": (15, "إلغاء تثبيت البرامج الجماعي", "إزالة البرامج بالتتابع دون تعارض في معالجات التثبيت", True, ["إدارة البرامج والتطبيقات", "إزالة البرامج"]),
            "apps_large": (15, "البرامج الكبيرة", "البرامج الأكثر استهلاكاً لمساحة التخزين", True, ["إدارة البرامج والتطبيقات", "البرامج الكبيرة"]),
            "apps_repair": (15, "مركز الإصلاح وإعادة الضبط", "إصلاح ملفات البرامج وإعادة ضبط تطبيقات المتجر", True, ["إدارة البرامج والتطبيقات", "الإصلاح وإعادة الضبط"]),
            "apps_leftovers": (15, "كشف وتنظيف البقايا", "البحث الذكي عن الملفات والمجلدات المتروكة بعد الإزالة", True, ["إدارة البرامج والتطبيقات", "البقايا"]),
            "apps_before_format": (15, "تجهيز البرامج قبل الفورمات", "حفظ قائمة البرامج ومعرفات استعادتها التلقائية", True, ["إدارة البرامج والتطبيقات", "قبل الفورمات"]),
            "apps_restore": (15, "استعادة البرامج بعد الفورمات", "إعادة تثبيت قائمة البرامج دفعة واحدة بعد الفورمات", True, ["إدارة البرامج والتطبيقات", "استعادة البرامج"]),
            "network": (16, "الشبكة والإنترنت", "مركز تحكم وتشخيص ومراقبة ومشاركة الشبكة والإنترنت", False, ["الشبكة والإنترنت"]),
            "network_overview": (16, "نظرة عامة - الشبكة والإنترنت", "لوحة قيادة الاتصال وحالة الإنترنت الحالية", True, ["الشبكة والإنترنت", "نظرة عامة"]),
            "network_speedtest": (16, "اختبار سرعة الإنترنت الحقيقي", "قياس سرعة التحميل والرفع والـ Ping والـ Jitter مع تقدير النقل", True, ["الشبكة والإنترنت", "اختبار السرعة"]),
            "network_doctor": (16, "طبيب تشخيص أعطال الاتصال", "فحص تسلسلي من 5 مراحل مع الإصلاح الآمن بنقرة واحدة", True, ["الشبكة والإنترنت", "تشخيص الاتصال"]),
            "network_wifi": (16, "مركز Wi-Fi ومحلل القنوات", "تحليل قوة الإشارة وازدحام القنوات والشبكات المجاورة", True, ["الشبكة والإنترنت", "Wi-Fi"]),
            "network_lan_devices": (16, "الأجهزة المحلية على الشبكة", "اكتشاف أجهزة الشبكة ومصنعي بطاقات الشبكة والراوتر", True, ["الشبكة والإنترنت", "الأجهزة المحلية"]),
            "network_traffic": (16, "مراقبة استهلاك البيانات والسرعة", "رسم بياني حي لسرعة النقل واستهلاك محولات الشبكة", True, ["الشبكة والإنترنت", "استهلاك الإنترنت"]),
            "network_connections": (16, "الاتصالات النشطة والمنافذ", "كشف الاتصالات المفتوحة وربطها بالبرامج وفحص المنافذ", True, ["الشبكة والإنترنت", "الاتصالات والمنافذ"]),
            "network_dns": (16, "مركز واستعلامات DNS", "فحص سجلات النطاقات ومقارنة سرعة خوادم DNS العالمية", True, ["الشبكة والإنترنت", "DNS"]),
            "network_share": (16, "مشاركة الملفات SINAX Share", "نقل الملفات السريع محلياً بين الحواسيب والهاتف عبر QR", True, ["الشبكة والإنترنت", "مشاركة الملفات"]),
            "network_adapters": (16, "معلومات محولات الشبكة والتوجيه", "تفاصيل البطاقات وجدول التوجيه وجدار الحماية والوكيل", True, ["الشبكة والإنترنت", "معلومات الشبكة"]),
            "network_tools": (16, "أدوات متقدمة والتقارير الفنية", "Ping مستمر، تتبع المسار Traceroute، فحص المنافذ والتقارير", True, ["الشبكة والإنترنت", "أدوات متقدمة"]),
            "devices": (17, "إدارة الأجهزة والمعلومات", "مركز استعلام وتشخيص ومراقبة عتاد الحاسوب", False, ["إدارة الأجهزة والمعلومات"]),
            "devices_overview": (17, "نظرة عامة - الأجهزة", "لوحة قيادة ومواصفات الجهاز الأساسية", True, ["إدارة الأجهزة والمعلومات", "نظرة عامة"]),
            "devices_cpu": (17, "المعالج المركزي (CPU)", "الأنوية والترددات وسجل الاستهلاك وفحص الثبات", True, ["إدارة الأجهزة والمعلومات", "المعالج"]),
            "devices_gpu": (17, "كرت الشاشة (GPU)", "كروت الرسوميات المدمجة والمنفصلة وذاكرة VRAM", True, ["إدارة الأجهزة والمعلومات", "كرت الشاشة"]),
            "devices_ram": (17, "الذاكرة العشوائية (RAM)", "الشرائح الفيزيائية ومنافذ اللوحة ومساعد الترقية", True, ["إدارة الأجهزة والمعلومات", "الذاكرة RAM"]),
            "devices_motherboard": (17, "اللوحة الأم وBIOS", "البرامج الثابتة ونمط UEFI والإقلاع الآمن وTPM", True, ["إدارة الأجهزة والمعلومات", "اللوحة الأم وBIOS"]),
            "devices_storage": (17, "وسائط التخزين الفيزيائية", "الأقراص ومؤشرات SMART وسرعة القراءة المتتابعة", True, ["إدارة الأجهزة والمعلومات", "التخزين"]),
            "devices_battery": (17, "البطارية والطاقة", "سعة الشحن التصميمية ودورات الشحن وتقرير البطارية الرسمي", True, ["إدارة الأجهزة والمعلومات", "البطارية والطاقة"]),
            "devices_displays": (17, "الشاشات ومواصفات العرض", "مخطط الشاشات ومعلومات لوحات العرض وEDID", True, ["إدارة الأجهزة والمعلومات", "الشاشات"]),
            "devices_usb": (17, "منافذ USB والملحقات", "الأجهزة المتصلة ومعرفات VID/PID والإخراج الآمن", True, ["إدارة الأجهزة والمعلومات", "USB والأجهزة"]),
            "devices_drivers": (17, "التعريفات ومدير الأجهزة", "شجرة العتاد وحزم التعريفات والنسخ الاحتياطي عبر pnputil", True, ["إدارة الأجهزة والمعلومات", "التعريفات"]),
            "devices_sensors": (17, "الحساسات والحرارة", "قراءات الحساسات وسجل الجلسة ومصادر البيانات", True, ["إدارة الأجهزة والمعلومات", "الحساسات والحرارة"]),
            "devices_windows": (17, "نظام التشغيل والبيئة", "بيئة Windows وتفاصيل البناء والتنشيط ووقت التشغيل", True, ["إدارة الأجهزة والمعلومات", "معلومات Windows"]),
            "devices_quick_check": (17, "الفحص السريع للعتاد", "طبيب العتاد الشامل لفحص 9 مكونات حيوية", True, ["إدارة الأجهزة والمعلومات", "الفحص السريع"]),
            "devices_reports": (17, "تقارير العتاد ولقطات التغيير", "تصدير التقارير متعددة الصيغ وحفظ ومقارنة لقطات العتاد", True, ["إدارة الأجهزة والمعلومات", "التقارير والمقارنة"]),
            "privacy_security": (19, "الخصوصية والأمان", "المركز الشامل لحماية النظام وخصوصية الملفات", False, ["الخصوصية والأمان"]),
            "privacy_overview": (19, "نظرة عامة - الخصوصية والأمان", "لوحة القيادة الأمنية الموحدة وحالة حماية Windows محلياً", True, ["الخصوصية والأمان", "نظرة عامة"]),
            "privacy_file_safety": (19, "فحص الملفات", "فحص استاتيكي دقيق للملفات وكشف الامتدادات المزيفة دون تنفيذها", True, ["الخصوصية والأمان", "فحص الملفات"]),
            "privacy_integrity": (19, "سلامة الملفات والمانيفست", "تدقيق بصمات الهاش الرقمية للمجلدات لكشف أي تعديل", True, ["الخصوصية والأمان", "سلامة الملفات"]),
            "privacy_signature": (19, "التوقيع الرقمي", "التحقق من صحة التواقيع الرقمية Authenticode وشهادات X.509", True, ["الخصوصية والأمان", "التوقيع الرقمي"]),
            "privacy_clean": (19, "تنظيف الخصوصية", "تطهير البيانات الوصفية EXIF و GPS من الصور ومستندات Office و PDF", True, ["الخصوصية والأمان", "تنظيف الخصوصية"]),
            "privacy_safe_share": (19, "المشاركة الآمنة", "استوديو تجهيز وتأمين الملفات قبل إرسالها ومشاركتها", True, ["الخصوصية والأمان", "المشاركة الآمنة"]),
            "privacy_vault": (19, "التشفير والخزنة الآمنة", "حاويات .sinaxvault المشفرة بمعيار AES-256-GCM واشتقاق مفاتيح scrypt", True, ["الخصوصية والأمان", "التشفير والخزنة"]),
            "privacy_secure_delete": (19, "الحذف الآمن", "حذف واعٍ بالعتاد وتنبيهات NIST 800-88 لأقراص SSD و NVMe", True, ["الخصوصية والأمان", "الحذف الآمن"]),
            "privacy_file_monitor": (19, "مراقبة التغييرات", "مراقبة حية وتنبيهات فورية عند تعديل أو حذف ملفات المجلدات الحساسة", True, ["الخصوصية والأمان", "مراقبة التغييرات"]),
            "privacy_passwords": (19, "كلمات المرور والحافظة", "حماية الحافظة ومسحها التلقائي وإعادة استخدام مولد كلمات المرور", True, ["الخصوصية والأمان", "كلمات المرور"]),
            "privacy_windows_security": (19, "حماية Windows", "لوحة حماية Windows المتقدمة وتحديثات استخبارات الأمان", True, ["الخصوصية والأمان", "حماية Windows"]),
            "privacy_advanced_tools": (19, "أدوات متقدمة", "فحص تدفقات ADS وسوم MOTW وأذونات وصلاحيات NTFS", True, ["الخصوصية والأمان", "أدوات متقدمة"]),
            "privacy_reports": (19, "تقارير الأمان", "توليد وتصدير تقارير التدقيق الأمني مع نمط حجب البيانات الحساسة", True, ["الخصوصية والأمان", "التقارير"]),
            "maintenance": (20, "مركز الصيانة والإصلاح", "التشخيص الذكي، إصلاح Windows، وصيانة النظام", False, ["مركز الصيانة والإصلاح"]),
            "maintenance_overview": (20, "نظرة عامة - مركز الصيانة", "المؤشرات الحية لحالة النظام والإطلاق السريع", True, ["مركز الصيانة والإصلاح", "نظرة عامة"]),
            "maintenance_doctor": (20, "طبيب SINAX", "الفحص والتشخيص الذكي الشامل وخطة الصيانة", True, ["مركز الصيانة والإصلاح", "طبيب SINAX"]),
            "maintenance_cleanup": (20, "التنظيف الآمن ومراجعة التنزيلات", "تنظيف الكاش والملفات المؤقتة ومراجعة التنزيلات", True, ["مركز الصيانة والإصلاح", "التنظيف الآمن"]),
            "maintenance_windows_repair": (20, "إصلاح Windows", "معالج DISM و SFC وتحليل سجلات CBS", True, ["مركز الصيانة والإصلاح", "إصلاح Windows"]),
            "maintenance_storage_disk": (20, "التخزين والقرص", "فحص نظام الملفات CHKDSK وتشخيص انخفاض المساحة", True, ["مركز الصيانة والإصلاح", "التخزين والقرص"]),
            "maintenance_updates": (20, "التحديثات والإقلاع", "حالة Windows Update وإعادة التشغيل المعلقة", True, ["مركز الصيانة والإصلاح", "التحديثات والإقلاع"]),
            "maintenance_startup": (20, "بدء التشغيل ومساعد Clean Boot", "مراجعة البرامج ذات الأثر المرتفع وعزل التعارضات", True, ["مركز الصيانة والإصلاح", "بدء التشغيل"]),
            "maintenance_network": (20, "مشاكل وإصلاح الشبكة", "فحص الاتصال ومسح DNS ومصحح ويندوز الرسمي", True, ["مركز الصيانة والإصلاح", "مشاكل الشبكة"]),
            "maintenance_apps": (20, "مشاكل التطبيقات", "البرامج غير المستجيبة وإنهاء العمليات المعلقة بأمان", True, ["مركز الصيانة والإصلاح", "مشاكل التطبيقات"]),
            "maintenance_devices": (20, "مشاكل الأجهزة والملحقات", "إعادة تشغيل Print Spooler ومصححات الصوت والبلوتوث", True, ["مركز الصيانة والإصلاح", "مشاكل الأجهزة"]),
            "maintenance_reliability": (20, "السجل والموثوقية", "سجل الأعطال المفاجئة وملفات تفريغ الشاشة الزرقاء BSOD", True, ["مركز الصيانة والإصلاح", "السجل والموثوقية"]),
            "maintenance_advanced": (20, "أدوات الصيانة المتقدمة", "إصلاح Explorer، مزامنة الوقت، وسجل الصيانة", True, ["مركز الصيانة والإصلاح", "أدوات متقدمة"]),
            "backup_sync": (21, "النسخ الاحتياطي والمزامنة", "المركز الشامل للنسخ الاحتياطي، المزامنة، والاستعادة المضمونة", False, ["النسخ الاحتياطي والمزامنة"]),
            "backup_sync_overview": (21, "نظرة عامة - النسخ والمزامنة", "المؤشرات الحية لحالة النسخ وصحة البيانات واختبارات الاستعادة", True, ["النسخ الاحتياطي والمزامنة", "نظرة عامة"]),
            "backup_sync_wizard": (21, "معالج النسخ الذكي", "معالج خطوة بخطوة لإنشاء وتخصيص مهام النسخ الاحتياطي", True, ["النسخ الاحتياطي والمزامنة", "معالج النسخ"]),
            "backup_sync_quick_backup": (21, "احمِ ملفاتي المهمة", "نسخ فوري بنقرة واحدة لسطح المكتب والمستندات والصور المهمة", True, ["النسخ الاحتياطي والمزامنة", "احمِ ملفاتي"]),
            "backup_sync_before_format": (21, "تجهيز الجهاز قبل الفورمات", "حزمة شاملة للملفات الشخصية وقائمة البرامج والتعريفات وإعدادات SINAX", True, ["النسخ الاحتياطي والمزامنة", "قبل الفورمات"]),
            "backup_sync_sync": (21, "المزامنة ثنائية الاتجاه", "مزامنة مرنة ومطابقة بين المجلدات مع معاينة حية للتغييرات", True, ["النسخ الاحتياطي والمزامنة", "المزامنة"]),
            "backup_sync_restore": (21, "استعادة الملفات المحفوظة", "استكشاف واستعادة الملفات والنسخ السابقة والملفات المحذوفة بأمان", True, ["النسخ الاحتياطي والمزامنة", "استعادة الملفات"]),
            "backup_sync_versions": (21, "سجل الإصدارات والتاريخ", "تصفح ومقارنة الإصدارات الزمنية السابقة لكل ملف وتاريخ التعديل", True, ["النسخ الاحتياطي والمزامنة", "سجل الإصدارات"]),
            "backup_sync_health_drill": (21, "صحة النسخ واختبار الاستعادة", "طبيب النسخ الاحتياطي واختبار الاستعادة العشوائي الفعلي", True, ["النسخ الاحتياطي والمزامنة", "صحة النسخ"]),
            "backup_sync_destinations": (21, "الأقراص وأجهزة النسخ", "إدارة وحدات التخزين الخارجية الموثوقة والنسخ عند التوصيل", True, ["النسخ الاحتياطي والمزامنة", "أقراص النسخ"]),
            "backup_sync_schedules": (21, "الجدولة التلقائية", "إدارة المواعيد المجدولة والتكامل مع مهام Windows", True, ["النسخ الاحتياطي والمزامنة", "الجدولة"]),
            "backup_sync_history_reports": (21, "سجل العمليات والتقارير", "سجل تدقيق كامل لعمليات النسخ والمزامنة وتقارير PDF/HTML", True, ["النسخ الاحتياطي والمزامنة", "التقارير"]),
            "quick_tools": (18, "الأدوات السريعة", "مختبر الأدوات السريعة، الحسابات، والترميز", False, ["الأدوات السريعة"]),
            "history": (7, "سجل العمليات", "سجل التغييرات وإمكانية التراجع", False, ["سجل العمليات"]),
            "settings": (8, "الإعدادات", "تخصيص البرنامج والمظهر", False, ["الإعدادات"]),
            "about": (22, "حول البرنامج", "معلومات الإصدار والمحركات والتراخيص والمصادر المفتوحة", False, ["حول البرنامج"]),
            "icon_gallery": (23, "معرض الأيقونات للمطورين", "استعراض ومطابقة نظام الأيقونات الموحد Microsoft Fluent UI", True, ["أدوات المطور", "معرض الأيقونات"]),
        }

        if page_id == "universal_converter":
            page_id = "converter"
        elif page_id in ("about", "about_sinax", "about_page"):
            page_id = "about"
        elif page_id in ("quick", "tools", "utility", "quick_tools_page"):
            page_id = "quick_tools"
        elif page_id in ("pdf", "pdf_tools", "pdf_center_page"):
            page_id = "pdf_center"
        elif page_id in ("image", "images", "image_center_page"):
            page_id = "image_center"
        elif page_id in ("video", "videos", "video_tools", "video_center_page"):
            page_id = "video_center"
        elif page_id in ("audio", "audios", "audio_tools", "audio_center_page"):
            page_id = "audio_center"
        elif page_id in ("media_tools",):
            self.status_bar.set_status("قسم قادم قريباً في التحديثات القادمة", "info")
            return

        if page_id not in page_map:
            return

        idx, title, subtitle, show_back, breadcrumb = page_map[page_id]

        # Ensure page is loaded lazily before configuring subpages
        self.ensure_page_loaded(idx)

        # Handle subpage switching
        if page_id.startswith("system_storage_"):
            sub = page_id[len("system_storage_"):]
            self.system_storage_page.switch_subpage(sub)
        elif page_id == "system_storage":
            self.system_storage_page.switch_subpage("overview")
        elif page_id.startswith("apps_"):
            sub = page_id[len("apps_"):]
            self.apps_manager_page.switch_subpage(sub)
        elif page_id == "apps_manager":
            self.apps_manager_page.switch_subpage("overview")
        elif page_id.startswith("network_"):
            sub = page_id[len("network_"):]
            self.network_page.switch_subpage(sub)
        elif page_id == "network":
            self.network_page.switch_subpage("overview")
        elif page_id.startswith("devices_"):
            sub = page_id[len("devices_"):]
            self.devices_page.switch_subpage(sub)
        elif page_id == "devices":
            self.devices_page.switch_subpage("overview")
        elif page_id.startswith("privacy_"):
            sub = page_id[len("privacy_"):]
            self.privacy_security_page.switch_subpage(sub)
        elif page_id == "privacy_security":
            self.privacy_security_page.switch_subpage("overview")
        elif page_id.startswith("maintenance_"):
            sub = page_id[len("maintenance_"):]
            self.maintenance_page.switch_subpage(sub)
        elif page_id == "maintenance":
            self.maintenance_page.switch_subpage("overview")
        elif page_id.startswith("backup_sync_"):
            sub = page_id[len("backup_sync_"):]
            self.backup_sync_page.switch_subpage(sub)
        elif page_id == "backup_sync":
            self.backup_sync_page.switch_subpage("overview")

        current_idx = self.stack.currentIndex()
        if record_history and current_idx != idx:
            self._nav_history.append(current_idx)

        self.stack.setCurrentIndex(idx)
        self.header_bar.set_title(
            title=title,
            subtitle=subtitle,
            show_back=(show_back or len(self._nav_history) > 0),
            breadcrumb=breadcrumb
        )
        self.sidebar.set_active_page(page_id)
        if navigation_controller.currentRoute != page_id:
            navigation_controller._set_active_route(page_id)

    def _go_back(self):
        # Workspaces and subpage nested navigation checks
        if self.stack.currentIndex() == 9 and self.is_page_loaded(9) and self.converter_page.is_in_workspace():
            self.converter_page.close_workspace()
            return
        if self.stack.currentIndex() == 11 and self.is_page_loaded(11) and self.image_center_page.is_in_workspace():
            self.image_center_page.close_workspace()
            return
        if self.stack.currentIndex() == 12 and self.is_page_loaded(12) and self.video_center_page.is_in_workspace():
            self.video_center_page.close_workspace()
            return
        if self.stack.currentIndex() == 13 and self.is_page_loaded(13) and self.audio_center_page.is_in_workspace():
            self.audio_center_page.close_workspace()
            return
        if self.stack.currentIndex() == 19 and self.is_page_loaded(19) and self.privacy_security_page.stack.currentIndex() != 0:
            self.privacy_security_page.switch_subpage("overview")
            return
        if self.stack.currentIndex() == 20 and self.is_page_loaded(20) and self.maintenance_page.stack.currentIndex() != 0:
            self.maintenance_page.switch_subpage("overview")
            return
        if self.stack.currentIndex() == 21 and self.is_page_loaded(21) and self.backup_sync_page.stack.currentIndex() != 0:
            self.backup_sync_page.switch_subpage("overview")
            return

        if self._nav_history:
            prev_idx = self._nav_history.pop()
            rev_map = {
                0: "dashboard",
                1: "file_manager",
                2: "batch_rename",
                3: "merge_files",
                4: "smart_organize",
                5: "search_analysis",
                6: "duplicate_copy",
                7: "history",
                8: "settings",
                9: "converter",
                10: "pdf_center",
                11: "image_center",
                12: "video_center",
                13: "audio_center",
                14: "system_storage",
                15: "apps_manager",
                16: "network",
                17: "devices",
                18: "quick_tools",
                19: "privacy_security",
                20: "maintenance",
                21: "backup_sync",
                22: "about",
            }
            target_id = rev_map.get(prev_idx, "dashboard")
            self.navigate_to(target_id, record_history=False)
        else:
            self.navigate_to("dashboard", record_history=False)

    def _on_system_storage_subpage_changed(self, key: str, label_ar: str):
        full_id = f"system_storage_{key}"
        self.header_bar.set_title(
            title=label_ar,
            subtitle="قسم النظام والتخزين",
            show_back=True,
            breadcrumb=["النظام والتخزين", label_ar]
        )
        self.sidebar.set_active_page(full_id)

    def _on_apps_manager_subpage_changed(self, key: str, label_ar: str):
        full_id = f"apps_{key}"
        self.header_bar.set_title(
            title=label_ar,
            subtitle="إدارة البرامج والتطبيقات",
            show_back=True,
            breadcrumb=["إدارة البرامج والتطبيقات", label_ar]
        )
        self.sidebar.set_active_page(full_id)

    def _on_network_subpage_changed(self, key: str, label_ar: str):
        full_id = f"network_{key}"
        self.header_bar.set_title(
            title=label_ar,
            subtitle="مركز الشبكة والإنترنت",
            show_back=True,
            breadcrumb=["الشبكة والإنترنت", label_ar]
        )
        self.sidebar.set_active_page(full_id)

    def _on_devices_subpage_changed(self, key: str, label_ar: str):
        full_id = f"devices_{key}"
        self.header_bar.set_title(
            title=label_ar,
            subtitle="مركز الأجهزة ومعلومات الحاسوب",
            show_back=True,
            breadcrumb=["إدارة الأجهزة والمعلومات", label_ar]
        )
        self.sidebar.set_active_page(full_id)

    def _on_privacy_security_subpage_changed(self, key: str, label_ar: str):
        full_id = f"privacy_{key}"
        self.header_bar.set_title(
            title=label_ar,
            subtitle="مركز الخصوصية والأمان",
            show_back=True,
            breadcrumb=["الخصوصية والأمان", label_ar]
        )
        self.sidebar.set_active_page(full_id)

    def _on_maintenance_subpage_changed(self, key: str, label_ar: str):
        full_id = f"maintenance_{key}"
        self.header_bar.set_title(
            title=label_ar,
            subtitle="مركز الصيانة والإصلاح",
            show_back=True,
            breadcrumb=["مركز الصيانة والإصلاح", label_ar]
        )
        self.sidebar.set_active_page(full_id)

    def _on_backup_sync_subpage_changed(self, key: str, label_ar: str):
        full_id = f"backup_sync_{key}"
        self.header_bar.set_title(
            title=label_ar,
            subtitle="النسخ الاحتياطي والمزامنة",
            show_back=True,
            breadcrumb=["النسخ الاحتياطي والمزامنة", label_ar]
        )
        self.sidebar.set_active_page(full_id)

    def _on_sidebar_nav(self, page_id: str):
        if page_id == "about":
            self._show_about()
        else:
            self.navigate_to(page_id)

    def _on_hub_tool_selected(self, tool_id: str):
        self.navigate_to(tool_id)

    def _show_about(self):
        self.navigate_to("about")

    def _on_page_status(self, message: str, is_loading: bool = False, is_error: bool = False):
        self.status_bar.set_status(message, is_loading, is_error)

    def _on_page_progress(self, current: int, total: int):
        if total > 0 and current < total:
            self.status_bar.show_progress(current, total)
        else:
            self.status_bar.hide_progress()

    def _on_cancel_requested(self):
        if self.is_page_loaded(2):
            if self.batch_rename_page.rename_worker and self.batch_rename_page.rename_worker.isRunning():
                self.batch_rename_page.rename_worker.cancel()
                self.status_bar.set_status("جاري إلغاء العملية بأمان...", True, False)
                return
        if self.is_page_loaded(4):
            if hasattr(self.organize_page, 'organize_worker') and self.organize_page.organize_worker and self.organize_page.organize_worker.isRunning():
                self.organize_page.organize_worker.cancel()
                self.status_bar.set_status("جاري إلغاء التنظيم بأمان...", True, False)
                return
        if self.is_page_loaded(5):
            if hasattr(self.search_page, 'search_worker') and self.search_page.search_worker and self.search_page.search_worker.isRunning():
                self.search_page.search_worker.cancel()
                self.status_bar.set_status("جاري إلغاء البحث بأمان...", True, False)
                return
            if hasattr(self.search_page, 'storage_worker') and self.search_page.storage_worker and self.search_page.storage_worker.isRunning():
                self.search_page.storage_worker.cancel()
                self.status_bar.set_status("جاري إلغاء تحليل المساحة...", True, False)
                return
        if self.is_page_loaded(6):
            if hasattr(self.duplicate_page, 'dup_worker') and self.duplicate_page.dup_worker and self.duplicate_page.dup_worker.isRunning():
                self.duplicate_page.dup_worker.cancel()
                self.status_bar.set_status("جاري إلغاء فحص التكرار بأمان...", True, False)
                return
            if hasattr(self.duplicate_page, 'transfer_worker') and self.duplicate_page.transfer_worker and self.duplicate_page.transfer_worker.isRunning():
                self.duplicate_page.transfer_worker.cancel()
                self.status_bar.set_status("جاري إلغاء النقل/النسخ بأمان...", True, False)
                return
        if self.is_page_loaded(9):
            if self.converter_page.current_workspace and self.converter_page.current_workspace.worker and self.converter_page.current_workspace.worker.isRunning():
                self.converter_page.current_workspace.worker.cancel()
                self.status_bar.set_status("جاري إلغاء عملية التحويل بأمان...", True, False)
                return

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        p = Path(urls[0].toLocalFile())
        self.navigate_to("batch_rename")
        if p.is_dir():
            self.batch_rename_page.set_directory(p)
        elif p.is_file():
            self.batch_rename_page.set_directory(p.parent)

    def _restore_geometry(self):
        geom = config.get("window_geometry", {})
        w = geom.get("width", 1280)
        h = geom.get("height", 820)
        self.resize(QSize(w, h))
        if geom.get("is_maximized", False):
            self.showMaximized()

    def closeEvent(self, event):
        config.set("window_geometry", {
            "width": self.width(),
            "height": self.height(),
            "is_maximized": self.isMaximized()
        }, auto_save=True)
        super().closeEvent(event)
