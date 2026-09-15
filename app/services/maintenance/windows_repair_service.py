# -*- coding: utf-8 -*-
"""
Windows Repair Service for SINAX Maintenance & Repair Center.
Implements the official Microsoft Servicing Pipeline:
1. DISM /CheckHealth (Instant sanity check)
2. DISM /ScanHealth (Deep component store inspection)
3. DISM /RestoreHealth (Component store repair with optional custom ISO source)
4. SFC /verifyonly (Non-destructive file integrity check)
5. SFC /scannow (System file repair)
Includes precise output and progress parsing with clear Arabic translations.
"""

import os
import re
import subprocess
from typing import Callable, Dict, Optional, Tuple


class WindowsRepairService:
    """Manages DISM and SFC system file repair operations."""

    @staticmethod
    def run_dism_check_health() -> Dict[str, str]:
        """
        Runs: DISM /Online /Cleanup-Image /CheckHealth
        Checks if the image has been flagged as corrupted by a previous process.
        """
        if os.name != "nt":
            return {"status": "unsupported", "message_ar": "هذه الأداة متوفرة فقط على أنظمة Windows."}

        cmd = ["dism.exe", "/Online", "/Cleanup-Image", "/CheckHealth"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            out = res.stdout or ""

            if "No component store corruption detected" in out or "لم يتم اكتشاف أي تلف في مخزن المكونات" in out:
                return {
                    "status": "healthy",
                    "status_code": "0",
                    "message_ar": "مستودع مكونات Windows سليم تماماً ولم يتم تسجيل أي تلف.",
                    "raw_output": out,
                }
            elif "The component store is repairable" in out or "يمكن إصلاح مخزن المكونات" in out:
                return {
                    "status": "repairable",
                    "status_code": "1",
                    "message_ar": "تم رصد تلف مسجل في مستودع المكونات، والإصلاح ممكن عبر RestoreHealth.",
                    "raw_output": out,
                }
            elif "The component store cannot be repaired" in out:
                return {
                    "status": "corrupt_unrepairable",
                    "status_code": "2",
                    "message_ar": "تم رصد تلف شديد لا يمكن إصلاحه تلقائياً دون مصدر خارجي.",
                    "raw_output": out,
                }
            else:
                return {
                    "status": "unknown",
                    "status_code": str(res.returncode),
                    "message_ar": "اكتمل الفحص السريع لمستودع المكونات.",
                    "raw_output": out,
                }
        except Exception as e:
            return {"status": "error", "message_ar": f"حدث خطأ أثناء فحص DISM: {e}"}

    @staticmethod
    def run_sfc_verify_only(
        progress_cb: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, str]:
        """
        Runs: sfc /verifyonly
        Verifies the integrity of all protected system files without making repairs.
        """
        if os.name != "nt":
            return {"status": "unsupported", "message_ar": "متوفر فقط على نظام Windows."}

        cmd = ["sfc.exe", "/verifyonly"]
        return WindowsRepairService._execute_sfc_command(cmd, is_repair=False, progress_cb=progress_cb)

    @staticmethod
    def run_sfc_scannow(
        progress_cb: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, str]:
        """
        Runs: sfc /scannow
        Scans all protected system files and repairs damaged files using clean cached copies.
        Requires Administrator privileges.
        """
        if os.name != "nt":
            return {"status": "unsupported", "message_ar": "متوفر فقط على نظام Windows."}

        cmd = ["sfc.exe", "/scannow"]
        return WindowsRepairService._execute_sfc_command(cmd, is_repair=True, progress_cb=progress_cb)

    @staticmethod
    def _execute_sfc_command(
        cmd: list, is_repair: bool, progress_cb: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, str]:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            full_output = []
            re_progress = re.compile(r"(\d+)%")

            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    full_output.append(line)
                    match = re_progress.search(line)
                    if match and progress_cb:
                        pct = int(match.group(1))
                        progress_cb(pct, f"جاري فحص ملفات النظام... {pct}%")

            process.wait()
            out_str = "".join(full_output)

            # Translation of official SFC outcomes
            if "did not find any integrity violations" in out_str or "لم يعثر على أية انتهاكات" in out_str:
                return {
                    "status": "healthy",
                    "code": 0,
                    "message_ar": "سليم: لم يعثر فحص حماية موارد Windows (SFC) على أي تلف في ملفات النظام.",
                    "raw_output": out_str,
                }
            elif "found corrupt files and successfully repaired them" in out_str or "بإصلاحها بنجاح" in out_str:
                return {
                    "status": "repaired",
                    "code": 1,
                    "message_ar": "تم الإصلاح: عثرت الأداة على ملفات تالفة وأصلحتها بنجاح باستخدام النسخ النظيفة.",
                    "raw_output": out_str,
                }
            elif "found corrupt files but was unable to fix" in out_str or "تعذر عليه إصلاح بعضها" in out_str:
                return {
                    "status": "corrupt_unrepaired",
                    "code": 2,
                    "message_ar": "تلف معلق: عثر الفحص على ملفات تالفة لكن تعذر إصلاح بعضها (ينصح بتشغيل DISM RestoreHealth أولاً ثم مراجعة سجل CBS).",
                    "raw_output": out_str,
                }
            elif "could not perform the requested operation" in out_str or "يتطلب تشغيل كمسؤول" in out_str:
                return {
                    "status": "access_denied",
                    "code": 3,
                    "message_ar": "تعذر التنفيذ: تتطلب الأداة صلاحيات مسؤول (Run as Administrator) أو تشغيلها في وضع الأمان Safe Mode.",
                    "raw_output": out_str,
                }
            else:
                return {
                    "status": "completed",
                    "code": process.returncode,
                    "message_ar": f"اكتمل الفحص (رمز الخروج {process.returncode}). راجع التفاصيل.",
                    "raw_output": out_str,
                }
        except Exception as e:
            return {"status": "error", "code": -1, "message_ar": f"فشل تشغيل أداة SFC: {e}"}

    @staticmethod
    def run_dism_restore_health(
        custom_source: Optional[str] = None,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, str]:
        """
        Runs: DISM /Online /Cleanup-Image /RestoreHealth [/Source:<path> /LimitAccess]
        Repairs Windows component store using Windows Update or specified source.
        """
        if os.name != "nt":
            return {"status": "unsupported", "message_ar": "متوفر فقط على نظام Windows."}

        cmd = ["dism.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"]
        if custom_source and os.path.exists(custom_source):
            cmd.extend([f"/Source:{custom_source}", "/LimitAccess"])

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            full_output = []
            re_progress = re.compile(r"(\d+\.?\d*)%")

            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    full_output.append(line)
                    match = re_progress.search(line)
                    if match and progress_cb:
                        pct = int(float(match.group(1)))
                        progress_cb(pct, f"جاري إصلاح صورة Windows عبر DISM... {pct}%")

            process.wait()
            out_str = "".join(full_output)

            # Error code mappings
            if "0x800f081f" in out_str:
                return {
                    "status": "source_not_found",
                    "code": "0x800f081f",
                    "message_ar": "تعذر العثور على ملفات المصدر (0x800f081f). يرجى التأكد من اتصال الإنترنت أو تحديد ملف Windows ISO كمصدر.",
                    "raw_output": out_str,
                }
            elif "The restore operation completed successfully" in out_str or "تمت عملية الاستعادة بنجاح" in out_str:
                return {
                    "status": "success",
                    "code": 0,
                    "message_ar": "تم إصلاح مستودع مكونات Windows بنجاح تام.",
                    "raw_output": out_str,
                }
            elif process.returncode == 0:
                return {
                    "status": "success",
                    "code": 0,
                    "message_ar": "اكتملت عملية صيانة DISM بنجاح.",
                    "raw_output": out_str,
                }
            else:
                return {
                    "status": "failed",
                    "code": process.returncode,
                    "message_ar": f"تعذر إكمال إصلاح DISM (رمز الخطأ {process.returncode}). راجع سجل DISM.",
                    "raw_output": out_str,
                }
        except Exception as e:
            return {"status": "error", "code": -1, "message_ar": f"فشل تشغيل أداة DISM: {e}"}
