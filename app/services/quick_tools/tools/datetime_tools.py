# -*- coding: utf-8 -*-
"""
SINAX Date & Time Tools
Unix timestamp conversions, ISO 8601 parsing, date duration calculator,
time arithmetic (add/subtract), and customizable business working days calculator.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


class DateTimeTools:
    """Operations on timestamps, durations, and calendar calculations."""

    @staticmethod
    def unix_to_datetime(ts: float, is_ms: bool = False) -> Dict[str, str]:
        """Converts Unix epoch timestamp to formatted local and UTC date representations."""
        epoch = ts / 1000.0 if is_ms else ts
        dt_utc = datetime.fromtimestamp(epoch, tz=timezone.utc)
        dt_local = datetime.fromtimestamp(epoch)

        return {
            "local_datetime": dt_local.strftime("%Y-%m-%d %H:%M:%S"),
            "utc_datetime": dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "iso_8601": dt_utc.isoformat(),
            "date_only": dt_local.strftime("%Y-%m-%d"),
            "time_only": dt_local.strftime("%H:%M:%S"),
        }

    @staticmethod
    def datetime_to_unix(dt: datetime) -> Dict[str, int]:
        """Converts datetime to epoch seconds and milliseconds."""
        epoch_sec = int(dt.timestamp())
        return {
            "seconds": epoch_sec,
            "milliseconds": epoch_sec * 1000,
        }

    @staticmethod
    def calculate_duration(start_dt: datetime, end_dt: datetime) -> Dict[str, Any]:
        """Calculates difference and breakdown between two dates."""
        if end_dt < start_dt:
            start_dt, end_dt = end_dt, start_dt

        diff = end_dt - start_dt
        total_days = diff.days
        total_seconds = int(diff.total_seconds())

        weeks = total_days // 7
        rem_days = total_days % 7
        hours = diff.seconds // 3600
        mins = (diff.seconds % 3600) // 60

        return {
            "total_days": total_days,
            "total_hours": total_seconds // 3600,
            "total_minutes": total_seconds // 60,
            "total_seconds": total_seconds,
            "summary": f"{weeks} أسبوع و {rem_days} يوم و {hours} ساعة و {mins} دقيقة",
        }

    @staticmethod
    def add_subtract_time(
        base_dt: datetime,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        is_add: bool = True
    ) -> datetime:
        """Adds or subtracts offset from base datetime."""
        delta = timedelta(days=days, hours=hours, minutes=minutes)
        return (base_dt + delta) if is_add else (base_dt - delta)

    @staticmethod
    def calculate_working_days(
        start_date: datetime,
        end_date: datetime,
        weekend_days: List[int] = [4, 5] # 4=Friday, 5=Saturday (Standard in Arab region)
    ) -> int:
        """Calculates working business days between two dates excluding custom weekend days."""
        cur = start_date.date()
        target = end_date.date()
        if cur > target:
            cur, target = target, cur

        working_days = 0
        while cur <= target:
            # cur.weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
            if cur.weekday() not in weekend_days:
                working_days += 1
            cur += timedelta(days=1)

        return working_days
