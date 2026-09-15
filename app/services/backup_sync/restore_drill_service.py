# -*- coding: utf-8 -*-
"""
SINAX Restore Drill Service.
Tests whether a backup is truly restorable ("هل نسختي الاحتياطية قابلة للاستعادة؟").
Extracts a random sample of files into a sandboxed temp directory, verifies byte-level
cryptographic hashes, cleans up, and generates an honest health assessment.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import random
import shutil
import tempfile
import time
from typing import Callable, List, Optional

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.copy_engine import CopyEngine
from app.services.backup_sync.models import BackupProfile
from app.services.quick_tools.tools.hash_tools import HashTools

logger = get_logger("restore_drill_service")


@dataclass
class RestoreDrillResult:
    is_healthy: bool = True
    profile_name: str = ""
    sample_tested_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    failed_files: List[str] = field(default_factory=list)
    tested_bytes: int = 0
    duration_seconds: float = 0.0
    summary_ar: str = ""


class RestoreDrillService:
    """Executes automated non-destructive sample restore drills."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    def run_drill(
        self,
        profile_id: str,
        sample_size: int = 25,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> RestoreDrillResult:
        """
        Picks random files from destination, copies to a sandbox temp folder,
        computes SHA-256 hashes, and cleans up immediately.
        """
        profile = self.db.get_profile(profile_id)
        res = RestoreDrillResult(profile_name=profile.name if profile else profile_id)
        start_t = time.time()

        if not profile:
            res.is_healthy = False
            res.summary_ar = "خطة النسخ الاحتياطي غير موجودة."
            return res

        dest = Path(profile.destination)
        if not dest.exists() or not dest.is_dir():
            res.is_healthy = False
            res.summary_ar = f"مجلد الوجهة غير متصل أو غير متاح: {profile.destination}"
            return res

        # Collect candidate files from destination (excluding .sinax_ directories)
        candidates: List[Path] = []
        for root, dirs, files in os.walk(str(dest)):
            if ".sinax" in root:
                continue
            for f in files:
                if f.startswith(".sinax"):
                    continue
                p = Path(root) / f
                if p.is_file():
                    candidates.append(p)

        if not candidates:
            res.is_healthy = False
            res.summary_ar = "لا توجد ملفات في مجلد النسخة الاحتياطية لتنفيذ اختبار الاستعادة."
            return res

        # Sample subset
        chosen_sample = random.sample(candidates, min(len(candidates), sample_size))
        res.sample_tested_count = len(chosen_sample)

        temp_sandbox = tempfile.mkdtemp(prefix="sinax_drill_")
        try:
            for idx, src_p in enumerate(chosen_sample):
                if cancel_check and cancel_check():
                    res.is_healthy = False
                    res.summary_ar = "تم إلغاء الاختبار بواسطة المستخدم."
                    break

                rel = src_p.relative_to(dest)
                if progress_cb:
                    progress_cb(idx + 1, len(chosen_sample), f"فحص: {rel.name}")

                dst_p = Path(temp_sandbox) / rel
                dst_p.parent.mkdir(parents=True, exist_ok=True)

                try:
                    # 1. Test Copy
                    ok, err = CopyEngine.copy_file_safe(str(src_p), str(dst_p))
                    if not ok:
                        res.failed_count += 1
                        res.failed_files.append(f"{rel} (فشل النسخ: {err})")
                        continue

                    # 2. Test Hash
                    src_h = HashTools.compute_file_hash(str(src_p), algorithm="SHA-256")
                    dst_h = HashTools.compute_file_hash(str(dst_p), algorithm="SHA-256")

                    if src_h.lower() == dst_h.lower():
                        res.passed_count += 1
                        res.tested_bytes += src_p.stat().st_size
                    else:
                        res.failed_count += 1
                        res.failed_files.append(f"{rel} (عدم تطابق البصمة SHA-256)")

                except Exception as e:
                    res.failed_count += 1
                    res.failed_files.append(f"{rel} ({e})")

            res.duration_seconds = time.time() - start_t
            if res.failed_count == 0 and res.passed_count > 0:
                res.is_healthy = True
                res.summary_ar = (
                    f"✓ نجح اختبار الاستعادة: تم استعادة وفحص ({res.passed_count}) ملفًا عشوائيًا "
                    f"بحجم ({res.tested_bytes / (1024**2):.1f} MB) والتحقق من تطابق بصمات SHA-256 بنسبة 100%."
                )
            else:
                res.is_healthy = False
                res.summary_ar = (
                    f"⚠ تنبيه: فشل التحقق في ({res.failed_count}) من أصل ({res.sample_tested_count}) ملفات اختبار."
                )

        finally:
            shutil.rmtree(temp_sandbox, ignore_errors=True)

        return res
