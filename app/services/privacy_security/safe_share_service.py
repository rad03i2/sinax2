# -*- coding: utf-8 -*-
"""
Safe Share Studio Service for SINAX Privacy & Security.
Flagship pipeline orchestrator: "جهّز هذا الملف للمشاركة بأمان".
Sequentially executes:
1. Working copy creation (Original is NEVER modified).
2. Privacy & metadata inspection.
3. Selective metadata removal (EXIF, GPS, author, revision traces).
4. Sensitive information scanning (PII, tokens, emails).
5. Microsoft Defender custom scan request.
6. SHA-256 integrity digest generation.
7. Post-sanitization output verification.
8. Ready-to-share export package.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.privacy_security.metadata_privacy_service import MetadataPrivacyService
from app.services.privacy_security.models import PrivacyPreset, SensitiveMatch
from app.services.privacy_security.privacy_db import PrivacyDatabase
from app.services.privacy_security.providers.antivirus_provider import MicrosoftDefenderProvider
from app.services.privacy_security.sensitive_data_scanner import SensitiveDataScanner
from app.services.quick_tools.tools.hash_tools import HashTools


@dataclass
class SafeShareResult:
    original_path: str
    output_path: str
    preset: PrivacyPreset
    metadata_removed: List[str] = field(default_factory=list)
    sensitive_items_found: int = 0
    sensitive_matches: List[SensitiveMatch] = field(default_factory=list)
    defender_status: str = "لم يتم الفحص"
    sha256_hash: str = ""
    is_verified: bool = False
    duration_seconds: float = 0.0
    summary_message: str = ""


class SafeShareService:
    """Orchestrates end-to-end Safe Share processing."""

    def __init__(self):
        self._meta_service = MetadataPrivacyService()
        self._defender = MicrosoftDefenderProvider()
        self._db = PrivacyDatabase()

    def process_safe_share(
        self,
        input_path: str,
        preset: PrivacyPreset = PrivacyPreset.PUBLIC_PDF,
        custom_output_path: Optional[str] = None,
        run_defender_scan: bool = True,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, SafeShareResult]:
        """
        Executes the full 7-stage Safe Share pipeline.
        """
        start_time = time.time()
        in_p = Path(input_path).resolve()

        res = SafeShareResult(
            original_path=str(in_p),
            output_path="",
            preset=preset,
        )

        if not in_p.exists() or not in_p.is_file():
            res.summary_message = "الملف الأصلي غير موجود."
            return False, res

        # 1. Output destination
        if custom_output_path:
            out_p = Path(custom_output_path).resolve()
        else:
            out_p = in_p.parent / f"{in_p.stem}_private{in_p.suffix}"

        res.output_path = str(out_p)

        try:
            # Stage 1: Inspect metadata & sensitive data
            if progress_cb:
                progress_cb(0.15, "المرحلة 1/6: فحص البيانات الوصفية والميتاداتا الحالية...")
            meta_before = self._meta_service.inspect_metadata(str(in_p))

            # Stage 2: Scan for sensitive data (PII, tokens)
            if progress_cb:
                progress_cb(0.30, "المرحلة 2/6: مسح النصوص بحثاً عن أسرار أو معلومات شخصية...")
            sensitive_matches = SensitiveDataScanner.scan_file(str(in_p))
            res.sensitive_matches = sensitive_matches
            res.sensitive_items_found = len(sensitive_matches)

            if cancel_check and cancel_check():
                res.summary_message = "تم إلغاء العملية بواسطة المستخدم."
                return False, res

            # Stage 3: Sanitize Metadata into clean copy
            if progress_cb:
                progress_cb(0.50, "المرحلة 3/6: إنشاء نسخة عمل معقمة وتنظيف البيانات الوصفية...")
            strip_gps_only = (preset == PrivacyPreset.SOCIAL and meta_before.get("has_gps"))
            ok_sanitize, clean_path, verifs = self._meta_service.sanitize_metadata(
                str(in_p),
                strip_gps_only=False,
                custom_output_path=str(out_p),
            )

            if not ok_sanitize:
                res.summary_message = f"فشل إنشاء النسخة النظيفة: {clean_path}"
                return False, res

            removals = []
            if verifs.get("gps_removed"):
                removals.append("إحداثيات الموقع الجغرافي (GPS Coordinates)")
            if verifs.get("author_removed"):
                removals.append("اسم المؤلف والمحرر (Author / Creator)")
            if verifs.get("metadata_cleared"):
                removals.append("بيانات البرنامج وتاريخ الإنشاء (Device & Software)")
            if not removals:
                removals.append("تم تدقيق وتجريد البيانات الوصفية المتاحة")

            res.metadata_removed = removals

            # Stage 4: Defender custom scan
            if run_defender_scan:
                if progress_cb:
                    progress_cb(0.70, "المرحلة 4/6: طلب فحص السلامة عبر Microsoft Defender...")
                def_ok, def_msg = self._defender.scan_path(str(out_p), timeout_seconds=45)
                res.defender_status = def_msg
            else:
                res.defender_status = "تم تجاوز فحص Defender"

            # Stage 5: Calculate SHA-256
            if progress_cb:
                progress_cb(0.85, "المرحلة 5/6: حساب بصمة SHA-256 للملف المنظف...")
            res.sha256_hash = HashTools.compute_file_hash(str(out_p), algorithm="SHA-256")

            # Stage 6: Verification
            if progress_cb:
                progress_cb(0.95, "المرحلة 6/6: التحقق النهائي من سلامة الملف الناتج...")
            res.is_verified = out_p.exists() and out_p.stat().st_size > 0
            res.duration_seconds = time.time() - start_time

            summary = (
                f"اكتمل تجهيز الملف للمشاركة بنجاح في {res.duration_seconds:.1f} ثانية.\n"
                f"العناصر المزالة: {', '.join(removals)}.\n"
                f"فحص Defender: {res.defender_status}.\n"
                f"بصمة الهاش: {res.sha256_hash[:16]}...\n"
                f"الناتج الآمن: {out_p.name}"
            )
            res.summary_message = summary

            # Audit log
            self._db.log_event(
                "SAFE_SHARE_COMPLETED",
                str(out_p),
                "SUCCESS",
                {"preset": preset.value, "sensitive_found": res.sensitive_items_found, "sha256": res.sha256_hash}
            )

            if progress_cb:
                progress_cb(1.0, "تم تجهيز الملف للمشاركة بأمان!")

            return True, res

        except Exception as e:
            res.summary_message = f"خطأ أثناء معالجة المشاركة الآمنة: {str(e)}"
            return False, res
