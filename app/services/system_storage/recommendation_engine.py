# -*- coding: utf-8 -*-
"""
SINAX Recommendation Engine
Generates truthful, actionable insights based on real system storage, performance,
and hardware conditions — zero fake optimizer claims or deceptive scare tactics.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.logger import get_logger
from app.services.system_storage.cleanup_service import CleanupService
from app.services.system_storage.disk_health_service import DiskHealthService, LogicalDriveInfo, PhysicalDiskInfo
from app.services.system_storage.startup_service import StartupService
from app.services.system_storage.storage_scanner import format_bytes

logger = get_logger("recommendation_engine")


@dataclass
class RecommendationCard:
    id: str
    title_ar: str
    description_ar: str
    severity: str               # "info", "warning", "critical"
    severity_label_ar: str
    action_id: str              # e.g. "go_cleanup", "go_analyzer", "go_startup", "go_processes"
    action_label_ar: str
    icon: str = "storage"


class RecommendationEngine:
    """Evaluates live system diagnostics and produces priority recommendations."""

    @classmethod
    def evaluate_system(
        cls,
        drives: Optional[List[LogicalDriveInfo]] = None,
        physical_disks: Optional[List[PhysicalDiskInfo]] = None,
        ram_percent: Optional[float] = None
    ) -> List[RecommendationCard]:
        """Evaluate drive capacities, cleanup opportunities, startup bloat, and disk health."""
        cards: List[RecommendationCard] = []

        # 1. Drive capacity checks
        if drives is None:
            drives = DiskHealthService.get_logical_drives()

        for d in drives:
            # Check C: or system drive
            free_gb = d.free_bytes / (1024.0 ** 3)
            if d.percent_used >= 88.0 or free_gb < 15.0:
                cards.append(RecommendationCard(
                    id=f"low_space_{d.drive_letter}",
                    title_ar=f"مساحة القرص ({d.drive_letter}) منخفضة جداً",
                    description_ar=f"المساحة المتبقية {format_bytes(d.free_bytes)} فقط ({100 - d.percent_used:.1f}% متاح). يُنصح بتحليل الملفات وحذف المخلفات لتفادي بطء النظام.",
                    severity="critical",
                    severity_label_ar="أولوية قصوى",
                    action_id="go_analyzer",
                    action_label_ar="تحليل أين ذهبت المساحة",
                    icon="storage"
                ))
            elif d.percent_used >= 75.0:
                cards.append(RecommendationCard(
                    id=f"moderate_space_{d.drive_letter}",
                    title_ar=f"القرص ({d.drive_letter}) يقترب من الامتلاء",
                    description_ar=f"تم استهلاك {d.percent_used:.1f}% من مساحة القرص. يمكنك فحص أكبر الملفات والمجلدات.",
                    severity="warning",
                    severity_label_ar="تنبيه",
                    action_id="go_analyzer",
                    action_label_ar="فحص المساحة",
                    icon="storage"
                ))

        # 2. Recycle Bin Check
        rb_bytes, rb_items = CleanupService.query_recycle_bin()
        if rb_bytes > 2 * (1024 ** 3):  # > 2 GB
            cards.append(RecommendationCard(
                id="recycle_bin_heavy",
                title_ar="سلة المحذوفات تحتوي مساحة غير مستغلة",
                description_ar=f"توجد {rb_items} ملفات تشغل {format_bytes(rb_bytes)} في سلة المحذوفات تنتظر التفريغ النهائي.",
                severity="info",
                severity_label_ar="تحسين موصى به",
                action_id="go_cleanup",
                action_label_ar="تفريغ سلة المحذوفات",
                icon="clean"
            ))

        # 3. Startup items bloat
        try:
            startup_items = StartupService.list_startup_items()
            enabled_count = sum(1 for s in startup_items if s.is_enabled)
            broken_count = sum(1 for s in startup_items if s.is_broken)

            if broken_count > 0:
                cards.append(RecommendationCard(
                    id="broken_startup",
                    title_ar=f"تم رصد {broken_count} عناصر إقلاع معطلة أو مفقودة",
                    description_ar="برامج محذوفة لا تزال مسجلة في قائمة الإقلاع وتبحث عنها ويندوز دون فائدة.",
                    severity="info",
                    severity_label_ar="ملاحظة",
                    action_id="go_startup",
                    action_label_ar="مراجعة عناصر الإقلاع",
                    icon="startup"
                ))
            elif enabled_count > 8:
                cards.append(RecommendationCard(
                    id="many_startup",
                    title_ar="تطبيقات بدء تشغيل متعددة تؤثر على وقت الإقلاع",
                    description_ar=f"يعمل {enabled_count} برنامج تلقائياً مع تشغيل الجهاز. يمكنك تعطيل التطبيقات غير الضرورية لتسريع إقلاع ويندوز.",
                    severity="warning",
                    severity_label_ar="تنبيه",
                    action_id="go_startup",
                    action_label_ar="إدارة بدء التشغيل",
                    icon="startup"
                ))
        except Exception:
            pass

        # 4. S.M.A.R.T. Health status check
        if physical_disks is None:
            try:
                physical_disks = DiskHealthService.get_physical_disks()
            except Exception:
                physical_disks = []

        for p in physical_disks:
            if p.health_status.lower() in ("warning", "unhealthy"):
                cards.append(RecommendationCard(
                    id=f"smart_warn_{p.device_id}",
                    title_ar=f"تحذير صحة وحدة التخزين ({p.name})",
                    description_ar=f"أظهر نظام الفحص حالة: '{p.health_status_ar}'. ننصح بعمل نسخة احتياطية فورية لبياناتك الهامة.",
                    severity="critical",
                    severity_label_ar="حرج جداً",
                    action_id="go_health",
                    action_label_ar="فحص تقرير S.M.A.R.T.",
                    icon="storage"
                ))

        # 5. High RAM pressure
        if ram_percent is not None and ram_percent >= 85.0:
            cards.append(RecommendationCard(
                id="high_ram",
                title_ar=f"استهلاك مرتفع للذاكرة العشوائية ({ram_percent}%)",
                description_ar="البرامج الحالية تستهلك معظم ذاكرة الجهاز. تحقق من العمليات الأكثر استهلاكاً.",
                severity="warning",
                severity_label_ar="تنبيه",
                action_id="go_processes",
                action_label_ar="فحص مدير العمليات",
                icon="ram"
            ))

        return cards
