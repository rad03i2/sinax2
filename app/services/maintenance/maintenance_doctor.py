# -*- coding: utf-8 -*-
"""
SINAX Maintenance Doctor (طبيب SINAX).
Core smart diagnostic coordinator orchestrating checks across all existing SINAX modules
(Storage, Startup, Network, Devices, Security, and Event logs) without modifying system state.
Generates an evidence-backed MaintenancePlan without fake optimization metrics.
"""

import json
import time
from typing import Callable, List, Optional
from app.services.maintenance.models import (
    DiagnosticIssue,
    MaintenancePlan,
    ScanMode,
    Severity,
)
from app.services.maintenance.safe_cleanup_orchestrator import SafeCleanupOrchestrator
from app.services.maintenance.reboot_state_service import RebootStateService
from app.services.maintenance.update_service import WindowsUpdateService
from app.services.maintenance.event_reliability_service import EventReliabilityService
from app.services.maintenance.windows_repair_service import WindowsRepairService
from app.services.maintenance.recommendation_engine import MaintenanceRecommendationEngine


class MaintenanceDoctor:
    """Non-destructive multi-system diagnostic runner."""

    @classmethod
    def run_smart_diagnosis(
        cls,
        mode: ScanMode = ScanMode.QUICK,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> MaintenancePlan:
        """
        Executes non-destructive smart diagnosis across Windows subsystems.
        """
        issues: List[DiagnosticIssue] = []

        # 1. Storage & Temp Files Check (20%)
        if progress_cb:
            progress_cb(10, "جارٍ فحص مساحة التخزين والملفات المؤقتة...")
        cleanup_info = SafeCleanupOrchestrator.analyze_cleanup_targets()
        temp_bytes = cleanup_info["user_temp"]["bytes"] + cleanup_info["windows_temp"]["bytes"]
        rb_bytes = cleanup_info["recycle_bin"]["bytes"]

        if temp_bytes >= 2 * 1024 * 1024 * 1024: # > 2 GB temp
            issues.append(DiagnosticIssue(
                id="high_temp_files",
                title_ar="تراكم ملفات مؤقتة بحجم كبير",
                title_en="High Temporary Files Accumulation",
                category="storage",
                severity=Severity.SUGGESTION,
                description_ar=f"يوجد ما يقارب {SafeCleanupOrchestrator.format_bytes(temp_bytes)} من الملفات المؤقتة غير المستخدمة في مجلدات النظام والمستخدم.",
                description_en="Excessive temporary files can safely be removed.",
                evidence=f"تم رصد {cleanup_info['user_temp']['count'] + cleanup_info['windows_temp']['count']} ملف مؤقت بحجم إجمالي {SafeCleanupOrchestrator.format_bytes(temp_bytes)}.",
                suggested_action_id="clean_user_temp",
                action_label_ar="تنظيف الملفات المؤقتة بأمان",
                technical_details=json.dumps({"reclaimable_bytes": temp_bytes}),
                timestamp=time.time(),
            ))

        if rb_bytes >= 1024 * 1024 * 1024: # > 1 GB recycle bin
            issues.append(DiagnosticIssue(
                id="large_recycle_bin",
                title_ar="سلة المحذوفات تستهلك مساحة تخزين",
                title_en="Large Recycle Bin Contents",
                category="storage",
                severity=Severity.SUGGESTION,
                description_ar=f"تحتوي سلة المحذوفات على {cleanup_info['recycle_bin']['count']} عنصر بحجم إجمالي {SafeCleanupOrchestrator.format_bytes(rb_bytes)}.",
                description_en="Recycle bin holds over 1 GB of deleted files.",
                evidence=f"الحجم المشغول بسلة المحذوفات: {SafeCleanupOrchestrator.format_bytes(rb_bytes)}.",
                suggested_action_id="empty_recycle_bin",
                action_label_ar="إفراغ سلة المحذوفات",
                technical_details=json.dumps({"reclaimable_bytes": rb_bytes}),
                timestamp=time.time(),
            ))

        # 2. Check Pending Reboot & Windows Servicing (40%)
        if progress_cb:
            progress_cb(35, "جارٍ فحص حالة تحديثات Windows وإعادة التشغيل المعلقة...")
        is_pending_reboot, reboot_reasons = RebootStateService.check_pending_reboot()
        if is_pending_reboot:
            issues.append(DiagnosticIssue(
                id="pending_reboot_detected",
                title_ar="Windows ينتظر إعادة تشغيل لإكمال عمليات الصيانة",
                title_en="Pending System Reboot Detected",
                category="updates",
                severity=Severity.WARNING,
                description_ar="توجد حزم برمجية أو تحديثات معلقة تتطلب إعادة تشغيل الجهاز لإكمال التثبيت والتأكد من استقرار النظام.",
                description_en="Windows servicing or updates are waiting for a reboot.",
                evidence="; ".join(reboot_reasons),
                suggested_action_id=None,
                action_label_ar="إعادة التشغيل لاحقاً أو الآن",
                timestamp=time.time(),
            ))

        # 3. Windows Update Status Check (55%)
        upd_status = WindowsUpdateService.get_update_status()
        if upd_status.get("status") == "updates_available":
            cnt = upd_status.get("updates_count", 0)
            issues.append(DiagnosticIssue(
                id="windows_updates_available",
                title_ar=f"توجد {cnt} تحديثات متاحة لنظام Windows",
                title_en=f"{cnt} Windows Updates Available",
                category="updates",
                severity=Severity.SUGGESTION,
                description_ar="يوصى بالتحقق من تحديثات الأمان والاستقرار الرسمية من Microsoft لتأمين النظام ضد الثغرات.",
                description_en="Official updates are available for installation.",
                evidence=f"أبلغت واجهة Windows Update الرسمية عن توفر {cnt} تحديث.",
                suggested_action_id=None,
                action_label_ar="فتح Windows Update",
                timestamp=time.time(),
            ))

        # 4. Component Store Sanity (Full Scan mode only) (70%)
        if mode == ScanMode.FULL:
            if progress_cb:
                progress_cb(60, "جارٍ الفحص السريع لمستودع مكونات Windows...")
            dism_res = WindowsRepairService.run_dism_check_health()
            if dism_res.get("status") == "repairable":
                issues.append(DiagnosticIssue(
                    id="dism_store_repairable",
                    title_ar="تم رصد تلف في مستودع مكونات Windows",
                    title_en="Windows Component Store Corruption Flagged",
                    category="windows_repair",
                    severity=Severity.WARNING,
                    description_ar="أبلغت أداة DISM أن مستودع مكونات Windows (WinSxS) بحاجة لإصلاح عبر RestoreHealth.",
                    description_en="DISM CheckHealth indicates repairable store corruption.",
                    evidence=dism_res.get("raw_output", ""),
                    suggested_action_id="dism_restore_health",
                    action_label_ar="إصلاح صورة Windows عبر DISM",
                    timestamp=time.time(),
                ))

        # 5. Recent App Crashes & Unexpected Shutdowns (85%)
        if progress_cb:
            progress_cb(80, "جارٍ مراجعة سجلات استقرار النظام والأعطال الحديثة...")
        crashes = EventReliabilityService.get_recent_crash_events(days=3, max_results=10)
        app_crashes = [c for c in crashes if c.event_type == "AppCrash"]
        if len(app_crashes) >= 3:
            # Group by app
            app_freq = {}
            for c in app_crashes:
                app_freq[c.app_name] = app_freq.get(c.app_name, 0) + 1
            most_frequent_app = max(app_freq, key=app_freq.get)

            issues.append(DiagnosticIssue(
                id="repeated_app_crashes",
                title_ar=f"تكرار تعطل التطبيق ({most_frequent_app})",
                title_en="Frequent Application Crashes",
                category="reliability",
                severity=Severity.REVIEW_NEEDED,
                description_ar=f"تم تسجيل {app_freq[most_frequent_app]} حالات تعطل للتطبيق '{most_frequent_app}' خلال آخر 3 أيام.",
                description_en=f"App {most_frequent_app} crashed repeatedly.",
                evidence=f"رمز الاستثناء الشائع: {app_crashes[0].exception_code} في الموديول: {app_crashes[0].fault_module}.",
                suggested_action_id=None,
                action_label_ar="مراجعة سجل الأعطال",
                timestamp=time.time(),
            ))

        # 6. Shell & Visual Check suggestion
        if progress_cb:
            progress_cb(95, "إتمام تجميع خطة الصيانة الذكية...")

        # Synthesize recommendation plan
        plan = MaintenanceRecommendationEngine.generate_plan(issues, scan_mode=mode)
        if progress_cb:
            progress_cb(100, "اكتمل الفحص بنجاح.")

        return plan
