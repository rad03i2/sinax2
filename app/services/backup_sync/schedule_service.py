# -*- coding: utf-8 -*-
"""
SINAX Backup Schedule Service.
Manages profile freshness tracking, missed backup detection, and clean Windows
Task Scheduler (schtasks) integration for running scheduled backups even when SINAX is closed.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.models import BackupProfile

logger = get_logger("schedule_service")


@dataclass
class ScheduleStatus:
    profile_id: str
    profile_name: str
    schedule_type: str
    schedule_time: str
    last_run_str: str
    next_run_str: str
    freshness: str                   # "current", "due_soon", "overdue", "never_run", "offline"
    freshness_ar: str
    is_destination_available: bool


class ScheduleService:
    """Evaluates backup freshness, missed runs, and coordinates scheduled execution."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    def get_profile_schedule_status(self, profile: BackupProfile) -> ScheduleStatus:
        """Assesses schedule freshness, next run time, and destination presence."""
        is_dest_avail = os.path.exists(profile.destination)

        if not profile.last_run_at:
            freshness = "never_run"
            freshness_ar = "لم يتم التشغيل قط"
            last_run_str = "غير متوفر"
        else:
            diff_days = (time.time() - profile.last_run_at) / 86400
            last_run_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(profile.last_run_at))

            if not is_dest_avail:
                freshness = "offline"
                freshness_ar = "الوجهة غير متصلة"
            elif diff_days > 7.0:
                freshness = "overdue"
                freshness_ar = "متأخرة جداً (> 7 أيام)"
            elif diff_days > 2.0:
                freshness = "due_soon"
                freshness_ar = "مستحقة قريباً"
            else:
                freshness = "current"
                freshness_ar = "محدثة وسليمة"

        # Calculate next run representation
        next_run_str = "يدوي"
        if profile.schedule == "daily":
            next_run_str = f"يومياً في {profile.schedule_time}"
        elif profile.schedule == "weekly":
            next_run_str = f"أسبوعياً (الجمعة {profile.schedule_time})"
        elif profile.schedule == "on_connect":
            next_run_str = "عند توصيل القرص الموثوق"

        return ScheduleStatus(
            profile_id=profile.id,
            profile_name=profile.name,
            schedule_type=profile.schedule,
            schedule_time=profile.schedule_time,
            last_run_str=last_run_str,
            next_run_str=next_run_str,
            freshness=freshness,
            freshness_ar=freshness_ar,
            is_destination_available=is_dest_avail
        )

    def register_windows_scheduled_task(self, profile: BackupProfile) -> Tuple[bool, str]:
        """
        Creates a Windows Task Scheduler job via schtasks.exe to execute
        SINAX backup profile headless.
        """
        if profile.schedule not in ("daily", "weekly"):
            return False, "الجدولة عبر مهام Windows مدعومة للمهام اليومية والأسبوعية."

        task_name = f"SINAX_Backup_{profile.id[:8]}"
        python_exe = os.path.abspath(r".venv\Scripts\python.exe") if os.path.exists(r".venv\Scripts\python.exe") else "python.exe"
        script_path = os.path.abspath("app/main.py")
        cmd_run = f'"{python_exe}" "{script_path}" --run-backup-profile {profile.id}'

        sc_type = "DAILY" if profile.schedule == "daily" else "WEEKLY"
        time_str = profile.schedule_time or "02:00"

        args = [
            "schtasks.exe", "/Create",
            "/TN", task_name,
            "/TR", cmd_run,
            "/SC", sc_type,
            "/ST", time_str,
            "/F"  # Force overwrite if exists
        ]

        try:
            res = subprocess.run(args, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, f"تم تسجيل مهمة النسخ الاحتياطي في Windows Task Scheduler بنجاح ({task_name}) ✓"
            return False, f"فشل التسجيل: {res.stderr or res.stdout}"
        except Exception as e:
            return False, f"خطأ أثناء استدعاء schtasks: {e}"

    def delete_windows_scheduled_task(self, profile_id: str) -> Tuple[bool, str]:
        task_name = f"SINAX_Backup_{profile_id[:8]}"
        try:
            res = subprocess.run(["schtasks.exe", "/Delete", "/TN", task_name, "/F"], capture_output=True, text=True, timeout=5)
            return (res.returncode == 0), res.stdout or res.stderr
        except Exception as e:
            return False, str(e)
