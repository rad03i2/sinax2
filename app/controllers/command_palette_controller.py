# -*- coding: utf-8 -*-
"""
SINAX Global Command Palette Controller (لوحة الأوامر الموحدة Ctrl+K)
Indexes all tools, pages, settings, and instant utilities across SINAX.
Provides fast keyword matching and keyboard navigation for QML CommandPalette.
"""

from typing import Dict, List, Any, Optional
from PySide6.QtCore import (
    QObject, Signal, Property, Slot, QAbstractListModel, QModelIndex, Qt
)
from app.controllers.navigation_controller import navigation_controller
from app.core.logger import get_logger

logger = get_logger("command_palette_controller")


class CommandItem:
    def __init__(
        self,
        route: str,
        title: str,
        subtitle: str = "",
        category: str = "التنقل",
        icon: str = "tools",
        shortcut: str = "",
        aliases: Optional[List[str]] = None
    ):
        self.route = route
        self.title = title
        self.subtitle = subtitle
        self.category = category
        self.icon = icon
        self.shortcut = shortcut
        self.aliases = aliases or []


class CommandPaletteModel(QAbstractListModel):
    RouteRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    SubtitleRole = Qt.UserRole + 3
    CategoryRole = Qt.UserRole + 4
    IconRole = Qt.UserRole + 5
    ShortcutRole = Qt.UserRole + 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[CommandItem] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items)):
            return None

        item = self._items[index.row()]
        if role == self.RouteRole:
            return item.route
        elif role == self.TitleRole:
            return item.title
        elif role == self.SubtitleRole:
            return item.subtitle
        elif role == self.CategoryRole:
            return item.category
        elif role == self.IconRole:
            return item.icon
        elif role == self.ShortcutRole:
            return item.shortcut
        return None

    def roleNames(self) -> Dict[int, bytes]:
        return {
            self.RouteRole: b"route",
            self.TitleRole: b"title",
            self.SubtitleRole: b"subtitle",
            self.CategoryRole: b"category",
            self.IconRole: b"icon",
            self.ShortcutRole: b"shortcut",
        }

    def set_items(self, items: List[CommandItem]):
        self.beginResetModel()
        self._items = items
        self.endResetModel()


class CommandPaletteController(QObject):
    isOpenChanged = Signal(bool)
    resultsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_open = False
        self._model = CommandPaletteModel(self)
        self._all_commands: List[CommandItem] = []
        self._init_index()

    def _init_index(self):
        """Builds the comprehensive in-memory command index."""
        self._all_commands = [
            # Core Centers
            CommandItem("dashboard", "الرئيسية", "لوحة التحكم التنفيذية والمؤشرات الحية", "المراكز الأساسية", "home", aliases=["home", "رئيسية", "داشبورد"]),
            CommandItem("file_manager", "إدارة الملفات", "المركز الرئيسي لإدارة المستندات والوسائط", "إدارة الملفات", "folder", aliases=["files", "ملفات", "مجلدات"]),
            CommandItem("batch_rename", "إعادة تسمية الملفات الجماعية", "160 نمطاً للتسمية والمعاينة الذكية", "إدارة الملفات", "rename", aliases=["rename", "تسمية", "اسم"]),
            CommandItem("converter", "المحوّل الشامل للملفات", "تحويل فوري لأكثر من 50 صيغة ملفات", "إدارة الملفات", "convert", aliases=["convert", "تحويل", "صيغ"]),
            CommandItem("merge_files", "دمج وتجميع الملفات", "دمج ملفات PDF وWord وExcel وأرشيف ZIP", "إدارة الملفات", "merge", aliases=["merge", "دمج", "تجميع"]),
            CommandItem("smart_organize", "التنظيم الذكي للملفات", "فرز وتصنيف المجلدات حسب الامتداد والتاريخ", "إدارة الملفات", "organize", aliases=["organize", "تنظيم", "ترتيب", "فرز"]),
            CommandItem("search_analysis", "البحث والتحليل المتقدم", "بحث ذكي وتعبيرات نمطية وتحليل المساحة", "إدارة الملفات", "search", aliases=["search", "بحث", "استعلام"]),
            CommandItem("duplicate_copy", "النسخ والنقل وكشف التكرار", "كشف الملفات المكررة عبر SHA-256", "إدارة الملفات", "duplicate", aliases=["duplicate", "تكرار", "مكرر", "نسخ"]),
            
            # Phase 3 Migrated Centers
            CommandItem("pdf_center", "مركز PDF الشامل", "دمج وتقسيم وضغط وحماية ملفات PDF", "الوسائط والمستندات", "pdf", aliases=["pdf", "بي دي اف", "ضغط pdf", "ocr"]),
            CommandItem("image_center", "مركز الصور والتصميم", "ضغط وتحويل وتغيير أبعاد وإزالة خلفية الصور", "الوسائط والمستندات", "image", aliases=["image", "صور", "صورة", "خلفية", "photo", "png", "jpg"]),
            CommandItem("video_center", "مركز الفيديو والمونتاج", "ضغط وتحويل وقص وترجمة وسائط الفيديو مع التسريع العتادي", "الوسائط والمستندات", "video", aliases=["video", "فيديو", "قص", "مونتاج", "mp4", "ffmpeg"]),
            CommandItem("audio_center", "مركز الصوتيات", "تحويل وضغط وتنقية وقص الملفات الصوتية وعرض الموجة", "الوسائط والمستندات", "audio", aliases=["audio", "صوت", "صوتيات", "بودكاست", "mp3", "wav"]),
            CommandItem("apps_manager", "إدارة البرامج والتطبيقات", "استعراض البرامج وإلغاء التثبيت الآمن وكشف البقايا", "إدارة النظام", "apps", aliases=["apps", "برامج", "تطبيقات", "حذف", "uninstall"]),
            CommandItem("network", "مركز الشبكة والإنترنت", "فحص السرعة وتشخيص الاتصال والمشاركة المحلية", "إدارة النظام", "network", aliases=["network", "شبكة", "انترنت", "واي فاي", "wifi", "ip", "speedtest"]),
            CommandItem("privacy_security", "الخصوصية والأمان", "فحص أمان الملفات والتوقيعات الرقمية والخزنة المشفرة", "إدارة النظام", "shield", aliases=["privacy", "security", "امان", "خصوصية", "تشفير", "حماية", "vault", "defender"]),
            
            # System & Maintenance Centers
            CommandItem("system_storage", "النظام والتخزين", "منظومة تحليل مساحة القرص ومراقبة الأداء", "النظام والتخزين", "storage", aliases=["storage", "قرص", "ذاكرة", "تخزين", "رام"]),
            CommandItem("system_storage_analyzer", "محلل التخزين", "أين ذهبت مساحة جهازي وتوزيع السعة", "النظام والتخزين", "treemap", aliases=["محلل", "سعة", "مساحة"]),
            CommandItem("system_storage_cleanup", "التنظيف الآمن", "تنظيف الكاش والملفات المؤقتة بأمان", "النظام والتخزين", "clean", aliases=["clean", "تنظيف", "مخلفات", "كاش"]),
            CommandItem("devices", "إدارة الأجهزة والمعلومات", "مواصفات المعالج والذاكرة والكرت واللوحة", "العتاد والأجهزة", "devices", aliases=["devices", "عتاد", "معالج", "مواصفات", "cpu", "ram"]),
            CommandItem("backup_sync", "النسخ الاحتياطي والمزامنة", "حماية البيانات واستعادتها وجدولة المهام", "النسخ والمزامنة", "backup", aliases=["backup", "نسخ احتياطي", "مزامنة", "استعادة"]),
            CommandItem("maintenance", "مركز الصيانة والإصلاح", "طبيب Windows وتشخيص الأعطال والإصلاح", "الصيانة والإصلاح", "doctor", aliases=["maintenance", "صيانة", "اصلاح", "طبيب", "doctor"]),
            CommandItem("quick_tools", "الأدوات السريعة", "مختبر الأدوات الفورية وحساب الهاشات والتجزئات", "الأدوات السريعة", "tools", aliases=["tools", "ادوات", "هاش", "hash", "base64", "qr"]),
            CommandItem("history", "سجل العمليات", "تاريخ جميع العمليات المنجزة والتراجع الفوري", "النظام", "history", aliases=["history", "سجل", "عمليات", "تراجع"]),
            CommandItem("settings", "الإعدادات", "تخصيص المظهر والسمات والأداء والأمان", "النظام", "settings", aliases=["settings", "اعدادات", "مظهر", "سمة", "dark", "light"]),
            CommandItem("about", "حول SINAX", "معلومات الإصدار والمحركات والتراخيص القانونية", "النظام", "info", aliases=["about", "حول", "اصدار", "version", "ترخيص"]),
        ]
        self._model.set_items(self._all_commands)

    @Property(QObject, constant=True)
    def model(self) -> CommandPaletteModel:
        return self._model

    @Property(int, notify=resultsChanged)
    def filteredCount(self) -> int:
        return self._model.rowCount()

    @Property(bool, notify=isOpenChanged)
    def isOpen(self) -> bool:
        return self._is_open

    @Slot()
    def toggle(self):
        self.setOpen(not self._is_open)

    @Slot(bool)
    def setOpen(self, open_state: bool):
        if self._is_open != open_state:
            self._is_open = open_state
            if open_state:
                self.search("")  # Reset to all
            self.isOpenChanged.emit(open_state)

    @Slot(str)
    def search(self, query: str):
        query = query.strip().lower()
        if not query:
            self._model.set_items(self._all_commands)
            return

        filtered = []
        for cmd in self._all_commands:
            match_score = 0
            if query in cmd.title.lower():
                match_score += 10
            if query in cmd.subtitle.lower():
                match_score += 5
            if query in cmd.category.lower():
                match_score += 3
            if query in cmd.route.lower():
                match_score += 8
            if any(query in a.lower() for a in cmd.aliases):
                match_score += 9

            if match_score > 0:
                filtered.append(cmd)

        self._model.set_items(filtered)
        self.resultsChanged.emit()

    @Slot(str)
    def selectCommand(self, route: str):
        self.setOpen(False)
        navigation_controller.openRoute(route)


# Singleton
command_palette_controller = CommandPaletteController()
