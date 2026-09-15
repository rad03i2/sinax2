# -*- coding: utf-8 -*-
"""
Maintenance Tool Registry for SINAX Maintenance & Repair Center.
Defines the single source of truth for all diagnostic checks and repair operations:
metadata, risk tiers, prerequisites, reversibility, and descriptions.
"""

from typing import Dict, List, Optional
from app.services.maintenance.models import MaintenanceAction, RiskLevel


class MaintenanceRegistry:
    """Central catalog of pre-approved, safe system maintenance operations."""

    _actions: Dict[str, MaintenanceAction] = {}

    @classmethod
    def register_action(cls, action: MaintenanceAction) -> None:
        cls._actions[action.id] = action

    @classmethod
    def get_action(cls, action_id: str) -> Optional[MaintenanceAction]:
        return cls._actions.get(action_id)

    @classmethod
    def get_all_actions(cls) -> List[MaintenanceAction]:
        return list(cls._actions.values())

    @classmethod
    def get_actions_by_category(cls, category: str) -> List[MaintenanceAction]:
        return [a for a in cls._actions.values() if a.category == category]


# Initialize predefined maintenance actions
_ACTIONS = [
    # 1. Cleanup Actions
    MaintenanceAction(
        id="clean_user_temp",
        title_ar="تنظيف ملفات المستخدم المؤقتة",
        title_en="Clean User Temp Files",
        category="cleanup",
        description_ar="حذف الملفات المؤقتة القديمة والمتروكة في مجلد %TEMP% للمستخدم الحالي مع تخطي الملفات قيد الاستخدام بأمان.",
        description_en="Safely removes orphaned temporary files from user temp directory.",
        what_will_it_do_ar="يقوم بمسح ملفات البرامج المؤقتة المنتهية في %TEMP%. الملفات المفتوحة حالياً يتم تخطيها تلقائياً دون أي خطأ.",
        expected_outcome_ar="تحرير مساحة تخزينية على القرص C دون أي تأثير على برامجك أو بياناتك.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_1_LOW_RISK,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=8,
        estimated_duration_str="عدة ثوانٍ",
        is_reversible=False,
        is_safe_default=True,
    ),
    MaintenanceAction(
        id="empty_recycle_bin",
        title_ar="إفراغ سلة المحذوفات",
        title_en="Empty Recycle Bin",
        category="cleanup",
        description_ar="تفريغ كافة العناصر المحذوفة الموجودة داخل سلة المحذوفات بشكل نهائي عبر واجهة ويندوز الرسمية.",
        description_en="Permanently empties all deleted items from the Windows Recycle Bin.",
        what_will_it_do_ar="يقوم بتفريغ محتويات سلة المحذوفات لجميع الأقراص نهائياً.",
        expected_outcome_ar="استعادة المساحة التخزينية المحجوزة للملفات المحذوفة مسبقاً.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_1_LOW_RISK,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=5,
        estimated_duration_str="لحظات",
        is_reversible=False,
        is_safe_default=False, # Requires explicit user confirmation
    ),
    MaintenanceAction(
        id="rebuild_thumbnail_cache",
        title_ar="إصلاح كاش الصور المصغرة",
        title_en="Rebuild Thumbnail Cache",
        category="cleanup",
        description_ar="حل مشكلة عدم ظهور صور المعاينة أو ظهورها بصور سوداء أو خاطئة عبر إعادة بناء كاش المستكشف.",
        description_en="Resolves broken or blank thumbnail previews by regenerating Windows thumbcache.",
        what_will_it_do_ar="يعيد تشغيل Explorer ويمسح قواعد بيانات thumbcache_*.db فقط.",
        expected_outcome_ar="يقوم Windows تلقائياً بإعادة إنشاء معاينات سليمة لصورك وفيديوهاتك. لا يمس الصور الأصلية.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_1_LOW_RISK,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=6,
        estimated_duration_str="ثوانٍ قليلة",
        is_reversible=False,
        is_safe_default=True,
    ),
    MaintenanceAction(
        id="rebuild_icon_cache",
        title_ar="إعادة بناء كاش الأيقونات",
        title_en="Rebuild Icon Cache",
        category="cleanup",
        description_ar="إصلاح الأيقونات البيضاء أو التالفة لبرامج سطح المكتب وشريط المهام.",
        description_en="Repairs broken, blank, or incorrect app and desktop icons.",
        what_will_it_do_ar="يحذف ملفات IconCache.db ويعيد تشغيل مستكشف Windows لبناء الأيقونات من مصادرها الأصلية.",
        expected_outcome_ar="عودة الأيقونات الرسمية لجميع التطبيقات والملفات.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_1_LOW_RISK,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=6,
        estimated_duration_str="ثوانٍ معدودة",
        is_reversible=False,
        is_safe_default=True,
    ),

    # 2. Windows Repair Actions
    MaintenanceAction(
        id="dism_check_health",
        title_ar="فحص سريع لمستودع مكونات Windows (DISM)",
        title_en="DISM CheckHealth",
        category="windows_repair",
        description_ar="فحص فوري لمعرفة هل صورة النظام ومستودع المكونات تم تعليمها مسبقاً كتالفة.",
        description_en="Quick check to see if the Windows image is flagged as corrupted.",
        what_will_it_do_ar="يتحقق من سجل حالة Component Store في ثوانٍ دون إجراء أي تعديل.",
        expected_outcome_ar="تقرير يوضح ما إذا كان المستودع سليماً أو يحتاج إصلاح.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_0_READ_ONLY,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=10,
        estimated_duration_str="10 ثوانٍ",
        is_reversible=True,
        is_safe_default=True,
    ),
    MaintenanceAction(
        id="sfc_verify_only",
        title_ar="التحقق من سلامة ملفات النظام (SFC VerifyOnly)",
        title_en="SFC VerifyOnly",
        category="windows_repair",
        description_ar="فحص شامل لجميع ملفات النظام المحمية للتأكد من مطابقتها وتكاملها دون تعديل أي ملف.",
        description_en="Scans integrity of all protected system files without replacing any file.",
        what_will_it_do_ar="يقوم بمقارنة هاش وتكامل ملفات النظام مع النسخ المرجعية دون كتابة أو تغيير.",
        expected_outcome_ar="كشف ما إذا كانت هناك ملفات تالفة تستدعي الإصلاح عبر SFC Scannow.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_0_READ_ONLY,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=180,
        estimated_duration_str="2 إلى 5 دقائق",
        is_reversible=True,
        is_safe_default=True,
    ),
    MaintenanceAction(
        id="sfc_scannow",
        title_ar="فحص وإصلاح ملفات النظام التالفة (SFC Scannow)",
        title_en="SFC Scannow Repair",
        category="windows_repair",
        description_ar="إصلاح رسمي لملفات نظام Windows التالفة واستبدالها بنسخ نظيفة من مخزن WinSxS.",
        description_en="Repairs corrupted system files using clean cached copies.",
        what_will_it_do_ar="يفحص ملفات DLL وملفات النظام الحيوية، وفي حال العثور على أي ملف تالف يستبدله فوراً بنسخة سليمة.",
        expected_outcome_ar="استعادة استقرار نظام التشغيل وحل مشاكل تعطل الخدمات والبرامج.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_2_SYSTEM_CHANGE,
        requires_admin=True,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=240,
        estimated_duration_str="3 إلى 6 دقائق",
        is_reversible=False,
        backup_supported=True,
        is_safe_default=True,
    ),
    MaintenanceAction(
        id="dism_restore_health",
        title_ar="إصلاح صورة ومستودع مكونات Windows (DISM RestoreHealth)",
        title_en="DISM RestoreHealth",
        category="windows_repair",
        description_ar="إعادة بناء مستودع المكونات WinSxS التالف باستخدام ملفات Windows Update أو ملف ISO محلي.",
        description_en="Repairs damaged component store using Windows Update or local ISO source.",
        what_will_it_do_ar="يقوم بتنزيل حزم المكونات الأصلية السليمة واستبدال الحزم المعطوبة في نظام التشغيل.",
        expected_outcome_ar="إصلاح جذري لمستودع Windows الأساسي يتيح لاحقاً لـ SFC العمل بكفاءة 100%.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_2_SYSTEM_CHANGE,
        requires_admin=True,
        requires_restart=False,
        requires_internet=True,
        estimated_duration_sec=360,
        estimated_duration_str="5 إلى 10 دقائق",
        is_reversible=False,
        is_safe_default=False,
    ),

    # 3. File System & Disk
    MaintenanceAction(
        id="chkdsk_scan",
        title_ar="فحص نظام الملفات للقراءة فقط (CHKDSK Scan)",
        title_en="CHKDSK Scan Only",
        category="storage_disk",
        description_ar="فحص آمن غير تدخلي لبنية نظام الملفات والفهارس على القرص دون الحاجة لفصل القرص أو إعادة التشغيل.",
        description_en="Safe read-only online scan of the file system structure.",
        what_will_it_do_ar="يفحص جداول الملفات الرئيسية (MFT) ويكتشف أي أخطاء دون إجراء تعديل.",
        expected_outcome_ar="معرفة ما إذا كان القرص يحتوي على أخطاء نظام ملفات تستدعي الجدولة.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_0_READ_ONLY,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=60,
        estimated_duration_str="دقيقة إلى دقيقتين",
        is_reversible=True,
        is_safe_default=True,
    ),
    MaintenanceAction(
        id="chkdsk_schedule_repair",
        title_ar="جدولة فحص وإصلاح نظام الملفات عند إعادة التشغيل",
        title_en="Schedule CHKDSK /F on Reboot",
        category="storage_disk",
        description_ar="جدولة أداة autochk لإصلاح أي أخطاء في نظام الملفات على قرص النظام C أثناء الإقلاع القادم.",
        description_en="Schedules file system repair for system volume C: on next Windows restart.",
        what_will_it_do_ar="يضع علامة جدولة رسمية في Windows لفحص وإصلاح C: قبل تحميل النظام.",
        expected_outcome_ar="إصلاح أي فهارس متضاربة أو قطاعات غير متناسقة وضمان سلامة البيانات.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_3_REQUIRES_RESTART,
        requires_admin=True,
        requires_restart=True,
        requires_internet=False,
        estimated_duration_sec=15,
        estimated_duration_str="تتم الجدولة فوراً",
        is_reversible=True,
        is_safe_default=False,
    ),

    # 4. Network & Connectivity
    MaintenanceAction(
        id="flush_dns_cache",
        title_ar="مسح كاش نظام أسماء النطاقات (Flush DNS)",
        title_en="Flush DNS Resolver Cache",
        category="network",
        description_ar="مسح العناوين القديمة أو الخاطئة المخزنة مؤقتاً في كاش DNS المحلي لتسريع فتح المواقع وحل مشاكل الاتصال.",
        description_en="Clears local DNS resolver cache to resolve domain resolution issues.",
        what_will_it_do_ar="ينفذ أمر ipconfig /flushdns الرسمي لإفراغ ذاكرة DNS المحلية.",
        expected_outcome_ar="حل مشاكل فتح المواقع التي تغيرت عناوينها أو توقفت عن الاستجابة.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_1_LOW_RISK,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=2,
        estimated_duration_str="ثانيتان",
        is_reversible=False,
        is_safe_default=True,
    ),

    # 5. Shell & System
    MaintenanceAction(
        id="restart_explorer",
        title_ar="إعادة تشغيل مستكشف Windows (Explorer)",
        title_en="Restart Windows Explorer",
        category="explorer",
        description_ar="إنهاء وإعادة تشغيل واجهة سطح المكتب وشريط المهام لحل مشكلات التجمّد والبطء الطارئ.",
        description_en="Restarts taskbar and desktop shell to recover from freezes and visual glitches.",
        what_will_it_do_ar="يغلق عملية explorer.exe ويعيد تشغيلها فوراً. سيختفي شريط المهام لثانية واحدة ثم يعود مفعلاً.",
        expected_outcome_ar="تحديث فوري لسطح المكتب وعلاج تعليق النوافذ دون الحاجة لإعادة تشغيل الحاسوب.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_1_LOW_RISK,
        requires_admin=False,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=3,
        estimated_duration_str="3 ثوانٍ",
        is_reversible=True,
        is_safe_default=True,
    ),
    MaintenanceAction(
        id="sync_system_time",
        title_ar="مزامنة ساعة وتوقيت النظام",
        title_en="Synchronize System Time",
        category="system",
        description_ar="مزامنة ساعة Windows الرسمية عبر خوادم الوقت الرسمية لحل مشاكل شهادات SSL والإنترنت.",
        description_en="Synchronizes system clock via Windows Time service (w32tm).",
        what_will_it_do_ar="يطلب من خدمة w32time إعادة المزامنة الفورية مع خادم الوقت المحدد.",
        expected_outcome_ar="ضبط التوقيت بالثانية بدقة، مما يحل أخطاء أمان المتصفح وتوثيق المواقع المشفرة.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_1_LOW_RISK,
        requires_admin=False,
        requires_restart=False,
        requires_internet=True,
        estimated_duration_sec=5,
        estimated_duration_str="5 ثوانٍ",
        is_reversible=True,
        is_safe_default=True,
    ),
    MaintenanceAction(
        id="restart_print_spooler",
        title_ar="إعادة تشغيل مخزن الطباعة (Print Spooler)",
        title_en="Restart Print Spooler Service",
        category="devices",
        description_ar="إصلاح مشكلة تعليق أوامر الطباعة وتوقف استجابة الطابعات بإعادة تشغيل الخدمة المسؤولة.",
        description_en="Restarts Windows Print Spooler service to clear stuck print queues.",
        what_will_it_do_ar="يقوم بإيقاف ثم إعادة تشغيل خدمة Spooler الرسمية.",
        expected_outcome_ar="استئناف إرسال المستندات للطابعة وحل تعليق قائمة الانتظار.",
        does_delete_user_files=False,
        risk_level=RiskLevel.LEVEL_2_SYSTEM_CHANGE,
        requires_admin=True,
        requires_restart=False,
        requires_internet=False,
        estimated_duration_sec=6,
        estimated_duration_str="6 ثوانٍ",
        is_reversible=True,
        is_safe_default=False,
    ),
]

for _act in _ACTIONS:
    MaintenanceRegistry.register_action(_act)
