# -*- coding: utf-8 -*-
"""
CHKDSK Service for SINAX Maintenance & Repair Center.
Provides structured volume file system inspection using Windows chkdsk utility:
- Read-only scan mode (no modifications)
- Repair mode (requires Admin; handles offline schedule warning on drive C:)
- Structured output parser (file system, corruption found, bad sectors, action needed)
- Strictly never forces reboot.
"""

import os
import re
import subprocess
from typing import Callable, Dict, Optional, Tuple


class ChkdskService:
    """Manages file system integrity checks via chkdsk."""

    @staticmethod
    def run_chkdsk_scan_only(
        drive_letter: str = "C:",
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> Dict[str, any]:
        """
        Runs a read-only chkdsk /scan on the specified drive.
        Safe, non-destructive, does not require dismounting the volume.
        """
        if os.name != "nt":
            return {"status": "unsupported", "message_ar": "متوفر فقط على نظام Windows."}

        clean_drive = drive_letter.strip().upper()
        if not clean_drive.endswith(":"):
            clean_drive += ":"

        cmd = ["chkdsk.exe", clean_drive, "/scan"]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            full_output = []
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    full_output.append(line)
                    if progress_cb:
                        progress_cb(line.strip())

            process.wait()
            raw_text = "".join(full_output)
            parsed = ChkdskService.parse_chkdsk_output(raw_text)
            parsed["raw_output"] = raw_text
            return parsed
        except Exception as e:
            return {
                "status": "error",
                "message_ar": f"فشل تشغيل فحص chkdsk: {e}",
                "file_system": "غير محدد",
                "has_errors": False,
                "bad_sectors_kb": 0,
                "raw_output": str(e),
            }

    @staticmethod
    def schedule_chkdsk_repair_on_reboot(drive_letter: str = "C:") -> Dict[str, any]:
        """
        Schedules a chkdsk /f on the system drive upon next reboot using autochk.
        Sends 'Y' to the prompt: 'Would you like to schedule this volume to be checked the next time the system restarts? (Y/N)'
        """
        clean_drive = drive_letter.strip().upper()
        if not clean_drive.endswith(":"):
            clean_drive += ":"

        cmd = ["chkdsk.exe", clean_drive, "/f"]
        try:
            # We provide 'Y\n' as stdin in case it asks to dismount or schedule on reboot
            res = subprocess.run(
                cmd,
                input="Y\n",
                capture_output=True,
                text=True,
                timeout=25,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            out = res.stdout or ""

            if "scheduled to be checked" in out or "سيتم فحص هذا وحدة التخزين" in out or "تمت جدولة" in out:
                return {
                    "success": True,
                    "scheduled": True,
                    "message_ar": f"تمت جدولة فحص وإصلاح القرص {clean_drive} بنجاح عند إعادة تشغيل Windows القادمة.",
                    "raw_output": out,
                }
            elif "Windows has scanned the file system and found no problems" in out or "لم يتم العثور على أية مشاكل" in out:
                return {
                    "success": True,
                    "scheduled": False,
                    "message_ar": f"نظام الملفات على القرص {clean_drive} سليم ولا يتطلب إصلاحاً.",
                    "raw_output": out,
                }
            elif "Access Denied" in out or "رفض الوصول" in out:
                return {
                    "success": False,
                    "scheduled": False,
                    "message_ar": "يتطلب تشغيل الفحص والإصلاح صلاحيات مسؤول (Run as Administrator).",
                    "raw_output": out,
                }
            else:
                return {
                    "success": res.returncode == 0,
                    "scheduled": "schedule" in out.lower(),
                    "message_ar": "تم إرسال أمر فحص القرص. راجع التفاصيل أدناه.",
                    "raw_output": out,
                }
        except Exception as e:
            return {"success": False, "scheduled": False, "message_ar": f"تعذر جدولة فحص القرص: {e}"}

    @staticmethod
    def parse_chkdsk_output(text: str) -> Dict[str, any]:
        """Parses raw console output of chkdsk into friendly structured data."""
        # 1. File system type
        fs = "NTFS"
        fs_match = re.search(r"type of the file system is (\w+)", text, re.I)
        if fs_match:
            fs = fs_match.group(1).upper()

        # 2. Bad sectors
        bad_sectors_kb = 0
        bad_match = re.search(r"(\d+)\s+KB in bad sectors", text, re.I)
        if bad_match:
            bad_sectors_kb = int(bad_match.group(1))

        # 3. Errors found
        has_errors = False
        if (
            "Windows found problems that each require" in text
            or "Windows has found errors" in text
            or "وجد Windows أخطاء" in text
            or "corruption was found" in text
            or "Please run chkdsk /scan to find the problems" in text
        ):
            has_errors = True

        is_clean = (
            "Windows has scanned the file system and found no problems" in text
            or "Windows has checked the file system and found no problems" in text
            or "No further action is required" in text
            or "لم يتم العثور على أية مشاكل" in text
        )

        status_ar = "سليم: نظام الملفات لا يعاني من أي أخطاء أو قطاعات تالفة."
        if has_errors:
            status_ar = "تم العثور على أخطاء في بنية نظام الملفات، يوصى بجدولة الفحص والإصلاح."
        elif bad_sectors_kb > 0:
            status_ar = f"تنبيه: تم رصد {bad_sectors_kb} KB قطاعات تالفة (Bad Sectors) على القرص."
        elif not is_clean:
            status_ar = "اكتمل الفحص (راجع السجل للتفاصيل)."

        return {
            "file_system": fs,
            "has_errors": has_errors,
            "is_clean": is_clean,
            "bad_sectors_kb": bad_sectors_kb,
            "message_ar": status_ar,
        }
