# -*- coding: utf-8 -*-
"""
SINAX Navigation Structure & Route Definitions
Centralized data-driven structure for sections, routes, and child tools.
"""

NAVIGATION_SECTIONS = [
    {
        "id": "dashboard",
        "title": "الرئيسية",
        "icon": "logo",
        "type": "item"
    },
    {
        "id": "file_manager",
        "title": "إدارة الملفات",
        "icon": "folder",
        "type": "section",
        "children": [
            {"id": "batch_rename", "title": "إعادة تسمية الملفات", "icon": "rename"},
            {"id": "converter", "title": "المحوّل الشامل", "icon": "convert"},
            {"id": "merge_files", "title": "دمج وتجميع الملفات", "icon": "merge"},
            {"id": "smart_organize", "title": "التنظيم الذكي للملفات", "icon": "organize"},
            {"id": "search_analysis", "title": "البحث والتحليل المتقدم", "icon": "search"},
            {"id": "duplicate_copy", "title": "النسخ والنقل والتكرار", "icon": "duplicate"},
            {"id": "pdf_center", "title": "مركز PDF", "icon": "pdf"},
        ]
    },
    {
        "id": "multimedia",
        "title": "الوسائط المتعددة",
        "icon": "image",
        "type": "section",
        "children": [
            {"id": "image_center", "title": "الصور", "icon": "image"},
            {"id": "video_center", "title": "الفيديو", "icon": "video"},
            {"id": "audio_center", "title": "الصوت", "icon": "audio"},
            {"id": "media_tools", "title": "أدوات الوسائط (قريباً)", "icon": "convert", "upcoming": True},
        ]
    },
    {
        "id": "system_storage",
        "title": "النظام والتخزين",
        "icon": "storage",
        "type": "section",
        "children": [
            {"id": "system_storage_overview", "title": "نظرة عامة", "icon": "storage"},
            {"id": "system_storage_analyzer", "title": "محلل التخزين", "icon": "treemap"},
            {"id": "system_storage_cleanup", "title": "التنظيف الآمن", "icon": "clean"},
            {"id": "system_storage_health", "title": "صحة الأقراص", "icon": "storage"},
            {"id": "system_storage_performance", "title": "مراقبة الأداء", "icon": "performance"},
            {"id": "system_storage_processes", "title": "إدارة العمليات", "icon": "process"},
            {"id": "system_storage_startup", "title": "بدء التشغيل", "icon": "startup"},
            {"id": "system_storage_device", "title": "مواصفات الجهاز", "icon": "chart"},
        ]
    },
    {
        "id": "apps_manager",
        "title": "إدارة البرامج والتطبيقات",
        "icon": "apps",
        "type": "section",
        "children": [
            {"id": "apps_overview", "title": "نظرة عامة", "icon": "apps"},
            {"id": "apps_inventory", "title": "كل البرامج", "icon": "apps"},
            {"id": "apps_updates", "title": "التحديثات", "icon": "update"},
            {"id": "apps_uninstall", "title": "إزالة البرامج", "icon": "uninstall"},
            {"id": "apps_large", "title": "البرامج الكبيرة", "icon": "chart"},
            {"id": "apps_repair", "title": "الإصلاح وإعادة الضبط", "icon": "repair"},
            {"id": "apps_leftovers", "title": "البقايا", "icon": "leftover"},
            {"id": "apps_before_format", "title": "قبل الفورمات", "icon": "backup"},
            {"id": "apps_restore", "title": "استعادة البرامج", "icon": "restore"},
        ]
    },
    {
        "id": "network",
        "title": "الشبكة والإنترنت",
        "icon": "network",
        "type": "section",
        "children": [
            {"id": "network_overview", "title": "نظرة عامة", "icon": "network"},
            {"id": "network_speedtest", "title": "اختبار السرعة", "icon": "speedtest"},
            {"id": "network_doctor", "title": "تشخيص الاتصال", "icon": "doctor"},
            {"id": "network_wifi", "title": "Wi-Fi", "icon": "wifi"},
            {"id": "network_lan_devices", "title": "الأجهزة المحلية", "icon": "devices"},
            {"id": "network_traffic", "title": "استهلاك الإنترنت", "icon": "traffic"},
            {"id": "network_connections", "title": "الاتصالات والمنافذ", "icon": "connections"},
            {"id": "network_dns", "title": "DNS", "icon": "dns"},
            {"id": "network_share", "title": "مشاركة الملفات", "icon": "share"},
            {"id": "network_adapters", "title": "معلومات الشبكة", "icon": "adapters"},
            {"id": "network_tools", "title": "أدوات متقدمة", "icon": "tools"},
        ]
    },
    {
        "id": "devices",
        "title": "إدارة الأجهزة والمعلومات",
        "icon": "devices",
        "type": "section",
        "children": [
            {"id": "devices_overview", "title": "نظرة عامة", "icon": "devices"},
            {"id": "devices_cpu", "title": "المعالج", "icon": "cpu"},
            {"id": "devices_gpu", "title": "كرت الشاشة", "icon": "gpu"},
            {"id": "devices_ram", "title": "الذاكرة RAM", "icon": "ram"},
            {"id": "devices_motherboard", "title": "اللوحة الأم وBIOS", "icon": "devices"},
            {"id": "devices_storage", "title": "التخزين", "icon": "storage"},
            {"id": "devices_battery", "title": "البطارية والطاقة", "icon": "devices"},
            {"id": "devices_displays", "title": "الشاشات", "icon": "devices"},
            {"id": "devices_usb", "title": "USB والأجهزة", "icon": "devices"},
            {"id": "devices_drivers", "title": "التعريفات", "icon": "devices"},
            {"id": "devices_sensors", "title": "الحساسات والحرارة", "icon": "devices"},
            {"id": "devices_windows", "title": "معلومات Windows", "icon": "devices"},
            {"id": "devices_quick_check", "title": "الفحص السريع", "icon": "doctor"},
            {"id": "devices_reports", "title": "التقارير والمقارنة", "icon": "devices"},
        ]
    },
    {
        "id": "privacy_security",
        "title": "الخصوصية والأمان",
        "icon": "shield",
        "type": "section",
        "children": [
            {"id": "privacy_overview", "title": "نظرة عامة", "icon": "shield"},
            {"id": "privacy_file_safety", "title": "فحص الملفات", "icon": "eye"},
            {"id": "privacy_integrity", "title": "سلامة الملفات", "icon": "hash"},
            {"id": "privacy_signature", "title": "التوقيع الرقمي", "icon": "signature"},
            {"id": "privacy_clean", "title": "تنظيف الخصوصية", "icon": "clean_sweep"},
            {"id": "privacy_safe_share", "title": "المشاركة الآمنة", "icon": "share"},
            {"id": "privacy_vault", "title": "التشفير والخزنة", "icon": "vault"},
            {"id": "privacy_secure_delete", "title": "الحذف الآمن", "icon": "shred"},
            {"id": "privacy_file_monitor", "title": "مراقبة التغييرات", "icon": "doctor"},
            {"id": "privacy_passwords", "title": "كلمات المرور", "icon": "key"},
            {"id": "privacy_windows_security", "title": "حماية Windows", "icon": "security"},
            {"id": "privacy_advanced_tools", "title": "أدوات متقدمة", "icon": "tools"},
            {"id": "privacy_reports", "title": "التقارير", "icon": "report"},
        ]
    },
    {
        "id": "maintenance",
        "title": "مركز الصيانة والإصلاح",
        "icon": "doctor",
        "type": "section",
        "children": [
            {"id": "maintenance_overview", "title": "نظرة عامة", "icon": "doctor"},
            {"id": "maintenance_doctor", "title": "طبيب SINAX", "icon": "doctor"},
            {"id": "maintenance_cleanup", "title": "التنظيف الآمن", "icon": "clean"},
            {"id": "maintenance_windows_repair", "title": "إصلاح Windows", "icon": "tools"},
            {"id": "maintenance_storage_disk", "title": "التخزين والقرص", "icon": "storage"},
            {"id": "maintenance_updates", "title": "التحديثات والإقلاع", "icon": "update"},
            {"id": "maintenance_startup", "title": "بدء التشغيل", "icon": "startup"},
            {"id": "maintenance_network", "title": "مشاكل الشبكة", "icon": "network"},
            {"id": "maintenance_apps", "title": "مشاكل التطبيقات", "icon": "apps"},
            {"id": "maintenance_devices", "title": "مشاكل الأجهزة", "icon": "devices"},
            {"id": "maintenance_reliability", "title": "السجل والموثوقية", "icon": "doctor"},
            {"id": "maintenance_advanced", "title": "أدوات متقدمة", "icon": "tools"},
        ]
    },
    {
        "id": "backup_sync",
        "title": "النسخ الاحتياطي والمزامنة",
        "icon": "duplicate",
        "type": "section",
        "children": [
            {"id": "backup_sync_overview", "title": "نظرة عامة", "icon": "duplicate"},
            {"id": "backup_sync_wizard", "title": "معالج النسخ الذكي", "icon": "tools"},
            {"id": "backup_sync_quick_backup", "title": "احمِ ملفاتي المهمة", "icon": "shield"},
            {"id": "backup_sync_before_format", "title": "تجهيز قبل الفورمات", "icon": "storage"},
            {"id": "backup_sync_sync", "title": "المزامنة الحية", "icon": "network"},
            {"id": "backup_sync_restore", "title": "استعادة الملفات", "icon": "history"},
            {"id": "backup_sync_versions", "title": "سجل الإصدارات", "icon": "file"},
            {"id": "backup_sync_health_drill", "title": "صحة النسخ والاستعادة", "icon": "doctor"},
            {"id": "backup_sync_destinations", "title": "أقراص النسخ (USB)", "icon": "devices"},
            {"id": "backup_sync_schedules", "title": "الجدولة التلقائية", "icon": "startup"},
            {"id": "backup_sync_history_reports", "title": "سجل العمليات والتقارير", "icon": "report"},
        ]
    },
    {
        "id": "quick_tools",
        "title": "الأدوات السريعة",
        "icon": "quick_tools",
        "type": "item"
    },
    {
        "id": "history",
        "title": "سجل العمليات",
        "icon": "history",
        "type": "item"
    }
]
