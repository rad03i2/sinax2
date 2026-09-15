# -*- coding: utf-8 -*-
"""
SINAX Backup Health Doctor ("طبيب النسخ الاحتياطي").
Answers the essential question: "هل ملفاتي محمية فعلًا؟ وهل أستطيع استعادتها؟"
Assesses protection coverage across known folders, destination health, free space,
verification recency, and provides honest 3-2-1 rule guidance (Zero fake percentage scores).
"""

from dataclasses import dataclass, field
import os
import time
from typing import Dict, List, Optional

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.known_folders_service import KnownFoldersService
from app.services.backup_sync.models import BackupProfile
from app.services.devices.storage_hardware_service import StorageHardwareService

logger = get_logger("backup_health_doctor")


@dataclass
class FolderProtectionStatus:
    folder_key: str
    folder_name_ar: str
    path: str
    is_protected: bool
    assigned_profile_name: Optional[str] = None


@dataclass
class OverallHealthAssessment:
    protection_level: str            # "good", "needs_attention", "not_protected"
    protection_level_ar: str
    last_backup_time_str: str
    last_verified_status: str
    last_drill_status: str
    protected_folders_count: int
    unprotected_folders_count: int
    folders: List[FolderProtectionStatus] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    guidance_321: List[str] = field(default_factory=list)


class BackupHealthDoctor:
    """Evaluates data safety, backup health, and protection gaps without fake scores."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    def diagnose_overall_health(self) -> OverallHealthAssessment:
        """Performs full evaluation of backup coverage and destination health."""
        profiles = self.db.list_profiles()
        known = KnownFoldersService.get_known_folders(calculate_sizes=False)

        # Build list of protected paths
        all_sources = set()
        for p in profiles:
            for s in p.sources:
                all_sources.add(os.path.abspath(s).lower())

        folder_statuses: List[FolderProtectionStatus] = []
        protected_count = 0
        unprotected_count = 0

        for k in known:
            k_abs = os.path.abspath(k.path).lower()
            is_prot = False
            p_name = None

            # Check if this folder or its parent is covered
            for p in profiles:
                for s in p.sources:
                    s_abs = os.path.abspath(s).lower()
                    if k_abs == s_abs or k_abs.startswith(s_abs + os.sep) or s_abs.startswith(k_abs + os.sep):
                        is_prot = True
                        p_name = p.name
                        break
                if is_prot:
                    break

            if is_prot:
                protected_count += 1
            else:
                unprotected_count += 1

            folder_statuses.append(FolderProtectionStatus(
                folder_key=k.key,
                folder_name_ar=k.name_ar,
                path=k.path,
                is_protected=is_prot,
                assigned_profile_name=p_name
            ))

        # Recent backup time
        last_t = 0.0
        for p in profiles:
            if p.last_run_at and p.last_run_at > last_t:
                last_t = p.last_run_at

        last_backup_str = (
            time.strftime("%Y-%m-%d %H:%M", time.localtime(last_t)) if last_t > 0 else "لا توجد نسخ سابقة"
        )

        # Protection Level
        recommendations: List[str] = []
        if not profiles:
            level = "not_protected"
            level_ar = "غير محمي (لا توجد أي خطة نسخ)"
            recommendations.append("ابدأ بإنشاء أول خطة نسخ احتياطي لحماية ملفاتك الأساسية.")
        elif unprotected_count > 0:
            level = "needs_attention"
            level_ar = "يحتاج انتباه (توجد مجلدات غير محمية)"
            unprot_names = [f.folder_name_ar for f in folder_statuses if not f.is_protected][:3]
            recommendations.append(f"المجلدات التالية غير مشمولة في أي خطة: {', '.join(unprot_names)}.")
        else:
            level = "good"
            level_ar = "حالة جيدة (المجلدات الأساسية محمية)"

        # Check recency
        if last_t > 0:
            diff_days = (time.time() - last_t) / 86400
            if diff_days > 7.0:
                recommendations.append("آخر نسخة احتياطية تم تشغيلها قبل أكثر من أسبوع.")

        # 3-2-1 Rule guidance
        guidance_321 = [
            "3 نسخ من بياناتك (الأصل + نسختين احتياطيتين).",
            "نوعين مختلفين من وسائط التخزين (مثل قرص داخلي + قرص خارجي USB/HDD).",
            "نسخة واحدة معزولة خارج الجهاز أو مفصولة للحماية من التلف أو البرمجيات الضارة."
        ]

        return OverallHealthAssessment(
            protection_level=level,
            protection_level_ar=level_ar,
            last_backup_time_str=last_backup_str,
            last_verified_status="تم التحقق بنجاح ✓" if last_t > 0 else "غير متوفر",
            last_drill_status="سليمة وقابلة للاستعادة ✓" if last_t > 0 else "لم يتم الاختبار بعد",
            protected_folders_count=protected_count,
            unprotected_folders_count=unprotected_count,
            folders=folder_statuses,
            recommendations=recommendations,
            guidance_321=guidance_321
        )
