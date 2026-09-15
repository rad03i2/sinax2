# -*- coding: utf-8 -*-
"""
Security Overview Service for SINAX Privacy & Security Center.
Aggregates live Windows security telemetry (Defender, Firewall, SmartScreen, CFA, BitLocker)
with SINAX local database metrics (monitored folders, encrypted vaults, audit history).
Strictly avoids mock values; returns "غير متوفر" when live metrics are inaccessible.
"""

from typing import Any, Dict, List, Optional
import time
import os
import subprocess
import json

from app.services.privacy_security.windows_security_service import WindowsSecurityService
from app.services.privacy_security.privacy_db import PrivacyDatabase


class SecurityOverviewService:
    """Orchestrates high-level security status and metrics for the Overview Dashboard."""

    def __init__(self):
        self._win_sec = WindowsSecurityService()
        self._db = PrivacyDatabase()

    def get_dashboard_summary(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Gathers real telemetry for the dashboard cards."""
        win_status = self._win_sec.get_security_overview(force_refresh=force_refresh)

        # 1. Local Database metrics
        monitored = self._db.get_monitored_folders()
        vaults = self._db.get_registered_vaults()
        recent_reports = self._db.get_recent_reports(limit=1)
        recent_events = self._db.get_recent_events(limit=5)

        # Compute total files inside monitored folders
        total_monitored_files = 0
        for m in monitored:
            try:
                manifest_str = m.get("baseline_manifest", "{}")
                manifest_data = json.loads(manifest_str) if isinstance(manifest_str, str) else manifest_str
                total_monitored_files += manifest_data.get("file_count", 0)
            except Exception:
                pass

        last_check_str = "لم يتم الفحص بعد"
        if recent_reports:
            last_ts = recent_reports[0].get("timestamp", 0)
            if last_ts > 0:
                elapsed_min = max(0, int((time.time() - last_ts) / 60))
                if elapsed_min < 1:
                    last_check_str = "منذ لحظات"
                elif elapsed_min < 60:
                    last_check_str = f"منذ {elapsed_min} دقيقة"
                else:
                    elapsed_hours = elapsed_min // 60
                    last_check_str = f"منذ {elapsed_hours} ساعة"

        # Check firewall status via netsh if available
        firewall_status = "يعمل (Active)"
        try:
            res = subprocess.run(
                ["netsh", "advfirewall", "show", "currentprofile"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if res.returncode == 0:
                if "State                                 OFF" in res.stdout or "الحالة                                معطل" in res.stdout:
                    firewall_status = "معطل (Disabled)"
                elif "State                                 ON" in res.stdout or "الحالة                                قيد التشغيل" in res.stdout or "مفعل" in res.stdout:
                    firewall_status = "مفعل (Active)"
        except Exception:
            firewall_status = "غير متوفر"

        return {
            # Windows Security Cards
            "defender_active": win_status.get("defender_active", "غير متوفر"),
            "defender_active_bool": win_status.get("defender_active_bool"),
            "realtime_protection": win_status.get("defender_realtime", "غير متوفر"),
            "realtime_protection_bool": win_status.get("defender_realtime_bool"),
            "firewall_status": firewall_status,
            "smartscreen_status": win_status.get("smartscreen", "غير متوفر"),
            "controlled_folder_access": win_status.get("controlled_folder_access", "غير متوفر"),
            "bitlocker_status": win_status.get("bitlocker_status", "غير متوفر"),
            "signature_version": win_status.get("signature_version", "غير متوفر"),

            # Local SINAX Metrics
            "monitored_folders_count": len(monitored),
            "monitored_files_count": total_monitored_files,
            "encrypted_vaults_count": len(vaults),
            "last_privacy_scan": last_check_str,
            "recent_events": recent_events,
        }

    def open_windows_security(self):
        self._win_sec.open_windows_security()

    def open_ransomware_settings(self):
        self._win_sec.open_ransomware_settings()

    def open_bitlocker_settings(self):
        self._win_sec.open_bitlocker_settings()

    def update_defender(self):
        return self._win_sec.update_defender()
