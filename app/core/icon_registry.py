# -*- coding: utf-8 -*-
"""
SINAX Centralized Icon Registry & IconService
Single Source of Truth for all visual symbols, icons, RTL metadata, and theme tinting.
Adheres strictly to Microsoft Fluent UI System Icons architecture (MIT License).
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QTransform
from PySide6.QtSvg import QSvgRenderer

# Path constants
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICONS_BASE_DIR = os.path.join(PROJECT_ROOT, "resources", "icons")


@dataclass
class IconEntry:
    name: str
    category: str
    relative_path: str
    filled_path: Optional[str] = None
    rtl_mirror: bool = False
    aliases: List[str] = field(default_factory=list)
    description: str = ""


class IconRegistry:
    """Central registry declaring all canonical semantic icons, categories, variants, and RTL flags."""

    _ENTRIES: Dict[str, IconEntry] = {
        # 1. Navigation & Centers
        "home": IconEntry("home", "navigation", "navigation/home.svg", "navigation/home_filled.svg", False, ["dashboard", "main"], "الرئيسية"),
        "folder": IconEntry("folder", "navigation", "navigation/folder.svg", "navigation/folder_filled.svg", False, ["files", "file_manager", "directory"], "إدارة الملفات"),
        "media": IconEntry("media", "navigation", "navigation/media.svg", "navigation/media_filled.svg", False, ["multimedia", "media_tools"], "الوسائط المتعددة"),
        "storage": IconEntry("storage", "navigation", "navigation/storage.svg", "navigation/storage_filled.svg", False, ["disk", "drive", "harddrive", "system_storage"], "النظام والتخزين"),
        "devices": IconEntry("devices", "navigation", "navigation/devices.svg", "navigation/devices_filled.svg", False, ["device", "hardware", "hardware_info"], "الأجهزة والمعلومات"),
        "apps": IconEntry("apps", "navigation", "navigation/apps.svg", "navigation/apps_filled.svg", False, ["applications", "apps_manager", "programs"], "إدارة البرامج والتطبيقات"),
        "network": IconEntry("network", "navigation", "navigation/network.svg", "navigation/network_filled.svg", False, ["internet", "web", "lan"], "الشبكة والإنترنت"),
        "shield": IconEntry("shield", "navigation", "navigation/shield.svg", "navigation/shield_filled.svg", False, ["security", "privacy", "privacy_security", "protection"], "الخصوصية والأمان"),
        "backup": IconEntry("backup", "navigation", "navigation/backup.svg", "navigation/backup_filled.svg", False, ["backup_sync", "archive_save"], "النسخ الاحتياطي والمزامنة"),
        "maintenance": IconEntry("maintenance", "navigation", "navigation/maintenance.svg", None, False, ["repair_center", "service"], "مركز الصيانة والإصلاح"),
        "toolbox": IconEntry("toolbox", "navigation", "navigation/toolbox.svg", None, False, ["tools", "quick_tools", "utilities"], "الأدوات السريعة"),
        "history": IconEntry("history", "navigation", "navigation/history.svg", None, False, ["log", "operation_history", "recent"], "سجل العمليات"),
        "settings": IconEntry("settings", "navigation", "navigation/settings.svg", None, False, ["config", "preferences", "options"], "الإعدادات"),
        "info": IconEntry("info", "navigation", "navigation/info.svg", "navigation/info_filled.svg", False, ["about", "details", "help"], "حول البرنامج"),

        # 2. Actions & Navigation Directionals (RTL sensitive)
        "add": IconEntry("add", "actions", "actions/add.svg", None, False, ["plus", "new", "create"], "إضافة"),
        "delete": IconEntry("delete", "actions", "actions/delete.svg", None, False, ["trash", "remove", "uninstall", "apps_uninstall"], "حذف"),
        "edit": IconEntry("edit", "actions", "actions/edit.svg", None, False, ["rename", "modify", "pencil"], "تعديل أو إعادة تسمية"),
        "copy": IconEntry("copy", "actions", "actions/copy.svg", None, False, ["duplicate_file"], "نسخ"),
        "cut": IconEntry("cut", "actions", "actions/cut.svg", None, False, ["scissors"], "قص"),
        "paste": IconEntry("paste", "actions", "actions/paste.svg", None, False, ["clipboard_paste"], "لصق"),
        "save": IconEntry("save", "actions", "actions/save.svg", None, False, ["floppy", "store"], "حفظ"),
        "refresh": IconEntry("refresh", "actions", "actions/refresh.svg", None, False, ["reload", "update", "apps_updates"], "تحديث"),
        "sync": IconEntry("sync", "actions", "actions/sync.svg", None, False, ["synchronize", "live_sync"], "مزامنة"),
        "search": IconEntry("search", "actions", "actions/search.svg", None, False, ["find", "lookup", "search_analysis"], "بحث"),
        "filter": IconEntry("filter", "actions", "actions/filter.svg", None, False, ["funnel"], "تصفية"),
        "sort": IconEntry("sort", "actions", "actions/sort.svg", None, False, ["order", "traffic"], "ترتيب"),
        "download": IconEntry("download", "actions", "actions/download.svg", None, False, ["fetch", "restore_down"], "تنزيل أو استعادة"),
        "upload": IconEntry("upload", "actions", "actions/upload.svg", None, False, ["send", "export"], "رفع أو تصدير"),
        "share": IconEntry("share", "actions", "actions/share.svg", None, False, ["network_share"], "مشاركة"),
        "dismiss": IconEntry("dismiss", "actions", "actions/dismiss.svg", None, False, ["close", "cancel", "clear"], "إغلاق أو إلغاء"),
        "check": IconEntry("check", "actions", "actions/check.svg", None, False, ["checkmark", "done", "ok"], "تأكيد أو تم"),
        "menu": IconEntry("menu", "actions", "actions/menu.svg", None, False, ["hamburger", "bars", "sidebar_toggle"], "القائمة الجانبية"),
        "star": IconEntry("star", "actions", "actions/star.svg", "actions/star_filled.svg", False, ["favorite", "fav", "bookmark"], "المفضلة"),
        "pin": IconEntry("pin", "actions", "actions/pin.svg", "actions/pin_filled.svg", False, ["pinned"], "تثبيت"),
        "more_horizontal": IconEntry("more_horizontal", "actions", "actions/more_horizontal.svg", None, False, ["more", "options_menu"], "المزيد"),
        "sun": IconEntry("sun", "actions", "actions/sun.svg", None, False, ["weather_sunny", "light_mode", "theme_light"], "الوضع الفاتح"),
        "moon": IconEntry("moon", "actions", "actions/moon.svg", None, False, ["weather_moon", "dark_mode", "theme_dark"], "الوضع الداكن"),
        "monitor": IconEntry("monitor", "actions", "actions/monitor.svg", None, False, ["desktop", "display", "system_mode", "theme_system"], "وضع النظام"),

        # Directional navigation actions (STRICTLY RTL MIRRORED)
        "back": IconEntry("back", "actions", "actions/back.svg", None, True, ["arrow_left", "prev"], "رجوع للخلف"),
        "forward": IconEntry("forward", "actions", "actions/forward.svg", None, True, ["arrow_right", "next"], "تقدم للأمام"),
        "chevron_left": IconEntry("chevron_left", "actions", "actions/chevron_left.svg", None, True, ["arrow_prev"], "سهم لليسار"),
        "chevron_right": IconEntry("chevron_right", "actions", "actions/chevron_right.svg", None, True, ["arrow_next"], "سهم لليمين"),
        "chevron_up": IconEntry("chevron_up", "actions", "actions/chevron_up.svg", None, False, ["arrow_up", "collapse"], "سهم لأعلى"),
        "chevron_down": IconEntry("chevron_down", "actions", "actions/chevron_down.svg", None, False, ["arrow_down", "expand"], "سهم لأسفل"),
        "undo": IconEntry("undo", "actions", "actions/undo.svg", None, True, ["revert"], "تراجع عن العملية"),
        "redo": IconEntry("redo", "actions", "actions/redo.svg", None, True, ["repeat"], "إعادة تطبيق العملية"),

        # 3. Files & Formats
        "file": IconEntry("file", "files", "files/file.svg", None, False, ["document"], "ملف"),
        "pdf": IconEntry("pdf", "files", "files/pdf.svg", None, False, ["pdf_center", "document_pdf"], "ملف PDF"),
        "convert": IconEntry("convert", "files", "files/convert.svg", None, False, ["exchange", "converter"], "تحويل التنسيق"),
        "merge": IconEntry("merge", "files", "files/merge.svg", None, False, ["combine", "merge_files"], "دمج الملفات"),
        "split": IconEntry("split", "files", "files/split.svg", None, False, ["separate", "extract_pages"], "تقسيم الملفات"),
        "organize": IconEntry("organize", "files", "files/organize.svg", None, False, ["smart_organize", "grid_organize"], "التنظيم الذكي"),
        "duplicate": IconEntry("duplicate", "files", "files/duplicate.svg", None, False, ["duplicate_copy", "clones"], "النسخ والنقل والتكرار"),

        # 4. Media Controls
        "image": IconEntry("image", "media", "media/image.svg", None, False, ["photo", "picture", "image_center"], "الصور"),
        "video": IconEntry("video", "media", "media/video.svg", None, False, ["film", "movie", "video_center"], "الفيديو"),
        "audio": IconEntry("audio", "media", "media/audio.svg", None, False, ["sound", "speaker", "audio_center"], "الصوت"),
        "play": IconEntry("play", "media", "media/play.svg", None, False, ["start_media"], "تشغيل"),
        "pause": IconEntry("pause", "media", "media/pause.svg", None, False, ["pause_media"], "إيقاف مؤقت"),
        "crop": IconEntry("crop", "media", "media/crop.svg", None, False, ["trim_image"], "اقتصاص"),
        "rotate": IconEntry("rotate", "media", "media/rotate.svg", None, False, ["orient"], "تدوير"),

        # 5. System, Diagnostic & Storage
        "cpu": IconEntry("cpu", "system", "system/cpu.svg", None, False, ["processor", "devices_cpu"], "المعالج"),
        "performance": IconEntry("performance", "system", "system/performance.svg", None, False, ["speedometer", "gauge", "system_storage_performance"], "مراقبة الأداء"),
        "clean": IconEntry("clean", "system", "system/clean.svg", None, False, ["broom", "clean_sweep", "system_storage_cleanup", "apps_leftovers"], "التنظيف الآمن"),
        "startup": IconEntry("startup", "system", "system/startup.svg", None, False, ["rocket", "system_storage_startup"], "بدء التشغيل"),
        "chart": IconEntry("chart", "system", "system/chart.svg", None, False, ["graph", "stats", "treemap"], "المخططات البيانية"),

        # 6. Devices
        "doctor": IconEntry("doctor", "devices", "devices/doctor.svg", None, False, ["stethoscope", "pulse", "diagnostics", "maintenance_doctor", "network_doctor"], "طبيب الفحص والتشخيص"),
        "ram": IconEntry("ram", "devices", "devices/ram.svg", None, False, ["memory", "devices_ram"], "الذاكرة العشوائية"),

        # 7. Network
        "wifi": IconEntry("wifi", "network", "network/wifi.svg", None, False, ["wireless", "network_wifi"], "الشبكة اللاسلكية Wi-Fi"),

        # 8. Security & Privacy
        "lock": IconEntry("lock", "security", "security/lock.svg", None, False, ["secure", "protect"], "قفل أو تشفير"),
        "key": IconEntry("key", "security", "security/key.svg", None, False, ["password", "privacy_passwords"], "كلمات المرور والمفاتيح"),
        "eye": IconEntry("eye", "security", "security/eye.svg", None, False, ["inspect", "privacy_file_safety"], "فحص وخصوصية الملفات"),
        "vault": IconEntry("vault", "security", "security/vault.svg", None, False, ["safe", "privacy_vault"], "التشفير والخزنة الآمنة"),

        # 9. Tools
        "calculator": IconEntry("calculator", "tools", "tools/calculator.svg", None, False, ["calc"], "آلة حاسبة"),
        "code": IconEntry("code", "tools", "tools/code.svg", None, False, ["developer", "xml", "syntax"], "أدوات المطور والشيفرة"),

        # 10. Status & Indicators
        "success": IconEntry("success", "status", "status/success.svg", "status/success_filled.svg", False, ["status_success", "verified", "passed"], "نجاح أو معتمد"),
        "warning": IconEntry("warning", "status", "status/warning.svg", "status/warning_filled.svg", False, ["status_warning", "caution", "alert"], "تحذير أو انتباه"),
        "error": IconEntry("error", "status", "status/error.svg", "status/error_filled.svg", False, ["status_error", "danger", "failed"], "خطأ أو فشل"),
        "question": IconEntry("question", "status", "status/question.svg", "status/question_filled.svg", False, ["status_unknown", "unknown", "fallback"], "غير معروف أو مساعدة"),
    }

    _ALIAS_MAP: Dict[str, str] = {}

    @classmethod
    def _init_aliases(cls):
        if not cls._ALIAS_MAP:
            for canonical, entry in cls._ENTRIES.items():
                cls._ALIAS_MAP[canonical.lower()] = canonical
                for alias in entry.aliases:
                    cls._ALIAS_MAP[alias.lower()] = canonical

            # Additional common aliases for tool categories and semantic variants
            extra_aliases = {
                "star-fill": "star",
                "star_filled": "star",
                "compress": "split",
                "extract": "split",
                "number": "calculator",
                "watermark": "image",
                "unlock": "lock",
                "reorder": "sort",
                "margin": "crop",
                "flatten": "merge",
                "redact": "eye",
                "text": "file",
                "compare": "duplicate",
                "print": "file",
                "ocr": "search",
                "arrow-down": "chevron_down",
                "file_pdf": "pdf",
                "resize": "crop",
                "wand": "clean",
                "palette": "edit",
                "workflow": "performance",
                "file_image": "image",
                "qr_code": "code",
                "qr": "code",
                "theme_system": "monitor",
                "theme_light": "sun",
                "theme_dark": "moon",
                "process": "cpu",
                "repair": "maintenance",
                "leftover": "clean",
                "restore": "download",
                "speedtest": "network",
                "connections": "network",
                "dns": "network",
                "adapters": "network",
                "gpu": "devices",
                "hash": "lock",
                "signature": "check",
                "shred": "delete",
                "report": "chart",
                "arrow-left": "chevron_left",
                "link": "network",
                "system": "settings",
                "clock": "history",
                "clipboard": "paste",
                "arrow_back": "back",
                "folder_open": "folder",
                "globe": "network",
                "certificate": "check",
                "firewall": "shield",
                "external_link": "forward",
            }
            for alias, target in extra_aliases.items():
                cls._ALIAS_MAP[alias.lower()] = target

    @classmethod
    def resolve(cls, name: str) -> str:
        if not name:
            return ""
        cls._init_aliases()
        cleaned = name.strip().lower()
        return cls._ALIAS_MAP.get(cleaned, cleaned)

    @classmethod
    def get_entry(cls, name: str) -> Optional[IconEntry]:
        canonical = cls.resolve(name)
        return cls._ENTRIES.get(canonical)

    @classmethod
    def is_rtl_mirrored(cls, name: str) -> bool:
        entry = cls.get_entry(name)
        return entry.rtl_mirror if entry else False

    @classmethod
    def get_all(cls) -> Dict[str, IconEntry]:
        return dict(cls._ENTRIES)

    @classmethod
    def get_aliases(cls) -> Dict[str, str]:
        cls._init_aliases()
        return {alias: target for alias, target in cls._ALIAS_MAP.items() if alias != target}

    @classmethod
    def get_categories(cls) -> List[str]:
        return sorted(list({entry.category for entry in cls._ENTRIES.values()}))

    @classmethod
    def get_rtl_mirrorable_icons(cls) -> List[str]:
        return [entry.name for entry in cls._ENTRIES.values() if entry.rtl_mirror]

    @classmethod
    def get_all_entries(cls) -> List[Dict]:
        cls._init_aliases()
        result = []
        for canonical, entry in cls._ENTRIES.items():
            result.append({
                "name": entry.name,
                "category": entry.category,
                "relative_path": entry.relative_path,
                "has_filled": entry.filled_path is not None,
                "rtl_mirror": entry.rtl_mirror,
                "aliases": entry.aliases,
                "description": entry.description
            })
        return result


ICON_CATEGORIES = ["navigation", "actions", "files", "media", "system", "devices", "network", "security", "tools", "status"]
RTL_MIRRORABLE_ICONS = ["back", "forward", "chevron_left", "chevron_right", "undo", "redo"]


class IconService:
    """Production service for on-demand SVG loading, dynamic recoloring, pixmap caching, and QIcon provision."""

    _svg_cache: Dict[str, str] = {}
    _pixmap_cache: Dict[Tuple, QPixmap] = {}
    _max_cache_size = 300

    @classmethod
    def get_file_path(cls, name: str, variant: str = "regular") -> Tuple[str, bool]:
        """
        Resolves canonical icon name to absolute filesystem path.
        Returns (path, exists). If missing, logs in dev and returns fallback icon.
        """
        if not name or not name.strip():
            fallback_entry = IconRegistry.get_entry("question")
            return os.path.join(ICONS_BASE_DIR, fallback_entry.relative_path.replace("/", os.sep)), False

        entry = IconRegistry.get_entry(name)
        if not entry:
            entry = IconRegistry.get_entry("question")
            if os.environ.get("SINAX_ENV") != "production":
                print(f"[IconService] WARNING: Missing semantic icon '{name}', using fallback 'question'.", file=sys.stderr)

        rel = entry.filled_path if (variant == "filled" and entry.filled_path) else entry.relative_path
        full_path = os.path.join(ICONS_BASE_DIR, rel.replace("/", os.sep))
        if not os.path.exists(full_path):
            # Fallback to question
            fallback_entry = IconRegistry.get_entry("question")
            full_path = os.path.join(ICONS_BASE_DIR, fallback_entry.relative_path.replace("/", os.sep))
            return full_path, False
        return full_path, True

    @classmethod
    def get_svg_content(cls, name: str, color_hex: Optional[str] = None, variant: str = "regular", color: Optional[str] = None) -> str:
        """Retrieves raw SVG XML, applying dynamic tinting if requested."""
        if color is not None:
            color_hex = color
        path, _ = cls.get_file_path(name, variant)
        if path not in cls._svg_cache:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cls._svg_cache[path] = f.read()
            except Exception as e:
                return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="{color_hex or "#CCCCCC"}"/></svg>'

        raw_svg = cls._svg_cache[path]
        if color_hex:
            # Clean hex string
            c = color_hex if color_hex.startswith("#") else f"#{color_hex}"
            return raw_svg.replace("currentColor", c)
        return raw_svg

    @classmethod
    def get_pixmap(cls, name: str, color_hex: str = "#CCCCCC", size: int = 20, variant: str = "regular", mirrored: bool = False, color: Optional[str] = None) -> QPixmap:
        """Renders crisp vector pixmap at exact pixel size with optional RTL horizontal flip."""
        if color is not None:
            color_hex = color

        if name in ("logo", "sinax_logo", "signx_logo"):
            cache_key = ("logo", "", size, "", False)
            if cache_key in cls._pixmap_cache:
                return cls._pixmap_cache[cache_key]
            from app.ui.icons import create_sinax_logo
            pm = create_sinax_logo(size).pixmap(size, size)
            cls._pixmap_cache[cache_key] = pm
            return pm

        cache_key = (name, color_hex, size, variant, mirrored)
        if cache_key in cls._pixmap_cache:
            return cls._pixmap_cache[cache_key]

        svg_str = cls.get_svg_content(name, color_hex, variant)
        renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))

        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)

        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if mirrored and IconRegistry.is_rtl_mirrored(name):
            transform = QTransform()
            transform.scale(-1, 1)
            transform.translate(-size, 0)
            painter.setTransform(transform)

        renderer.render(painter)
        painter.end()

        # Evict oldest entry if cache exceeds limit
        if len(cls._pixmap_cache) > cls._max_cache_size:
            first_key = next(iter(cls._pixmap_cache))
            del cls._pixmap_cache[first_key]

        cls._pixmap_cache[cache_key] = pm
        return pm

    @classmethod
    def get_qicon(cls, name: str, color_hex: Optional[str] = "#0078D4", size: int = 32, variant: str = "regular", color: Optional[str] = None) -> QIcon:
        """Provides a modern QIcon for legacy Qt Widgets, Dialogs, and Tray."""
        if color is not None:
            color_hex = color
        if name in ("logo", "sinax_logo", "signx_logo"):
            from app.ui.icons import create_sinax_logo
            return create_sinax_logo(size)

        pm = cls.get_pixmap(name, color_hex or "#0078D4", size, variant, mirrored=False)
        return QIcon(pm)

    @classmethod
    def audit_icons(cls) -> Dict:
        """Validates all registered icons against physical files, checking for missing or orphaned SVGs."""
        missing = []
        found = []
        for canonical, entry in IconRegistry._ENTRIES.items():
            reg_path = os.path.join(ICONS_BASE_DIR, entry.relative_path.replace("/", os.sep))
            if not os.path.exists(reg_path):
                missing.append(entry.relative_path)
            else:
                found.append(entry.relative_path)

            if entry.filled_path:
                fill_path = os.path.join(ICONS_BASE_DIR, entry.filled_path.replace("/", os.sep))
                if not os.path.exists(fill_path):
                    missing.append(entry.filled_path)
                else:
                    found.append(entry.filled_path)

        return {
            "total_registered": len(IconRegistry._ENTRIES),
            "found_files": len(found),
            "missing_files": missing,
            "status": "PASS" if not missing else "FAIL"
        }
