# -*- coding: utf-8 -*-
"""
Diagnostic Package Service for SINAX Maintenance & Repair Center.
Generates privacy-masked technical support diagnostic reports (HTML / JSON / ZIP):
masks username, computer name, serials, IPs, MAC addresses, and private personal paths.
Strictly never includes user files, browser history, or passwords.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class DiagnosticPackageService:
    """Generates privacy-safe technical support bundles."""

    @classmethod
    def generate_diagnostic_data(cls) -> Dict[str, Any]:
        """Collects raw technical state across subsystems."""
        from app.services.maintenance.reboot_state_service import RebootStateService
        from app.services.maintenance.update_service import WindowsUpdateService
        from app.services.maintenance.event_reliability_service import EventReliabilityService
        from app.services.maintenance.safe_cleanup_orchestrator import SafeCleanupOrchestrator

        is_pending_reboot, reboot_reasons = RebootStateService.check_pending_reboot()
        upd_status = WindowsUpdateService.get_update_status()
        events = EventReliabilityService.get_recent_crash_events(days=3, max_results=10)
        cleanup = SafeCleanupOrchestrator.analyze_cleanup_targets()

        raw_data = {
            "timestamp": time.time(),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "os_environment": {
                "computer_name": os.environ.get("COMPUTERNAME", "PC"),
                "username": os.environ.get("USERNAME", "User"),
                "userprofile": os.environ.get("USERPROFILE", ""),
                "os_name": os.name,
            },
            "servicing_and_reboot": {
                "is_pending_reboot": is_pending_reboot,
                "reboot_reasons": reboot_reasons,
            },
            "windows_update": {
                "status": upd_status.get("status", "unknown"),
                "count": upd_status.get("updates_count", 0),
                "last_search": upd_status.get("last_search_time", ""),
            },
            "storage_summary": {
                "user_temp_bytes": cleanup["user_temp"]["bytes"],
                "windows_temp_bytes": cleanup["windows_temp"]["bytes"],
                "recycle_bin_bytes": cleanup["recycle_bin"]["bytes"],
                "total_reclaimable_bytes": cleanup["total_reclaimable_bytes"],
            },
            "recent_crashes": [
                {
                    "type": ev.event_type,
                    "app": ev.app_name,
                    "module": ev.fault_module,
                    "code": ev.exception_code,
                    "time": ev.timestamp_str,
                }
                for ev in events
            ],
        }

        return cls._apply_privacy_mask(raw_data)

    @classmethod
    def _apply_privacy_mask(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deep masks sensitive personal identifiers."""
        username = data.get("os_environment", {}).get("username", "")
        computer_name = data.get("os_environment", {}).get("computer_name", "")
        userprofile = data.get("os_environment", {}).get("userprofile", "")

        json_str = json.dumps(data, ensure_ascii=False)

        # 1. Mask username & userprofile
        if userprofile:
            json_str = json_str.replace(userprofile, "C:\\Users\\<USER_REDACTED>")
        if username:
            json_str = re.sub(rf"\b{re.escape(username)}\b", "<USER>", json_str, flags=re.I)

        # 2. Mask Computer Name
        if computer_name:
            json_str = re.sub(rf"\b{re.escape(computer_name)}\b", "<COMPUTER_NAME>", json_str, flags=re.I)

        # 3. Mask IPv4
        json_str = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP_REDACTED>", json_str)

        # 4. Mask MAC addresses
        json_str = re.sub(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b", "<MAC_REDACTED>", json_str)

        masked_dict = json.loads(json_str)
        # Explicit override on environment section
        masked_dict["os_environment"]["username"] = "<USER_REDACTED>"
        masked_dict["os_environment"]["computer_name"] = "<COMPUTER_REDACTED>"
        masked_dict["os_environment"]["userprofile"] = "C:\\Users\\<USER_REDACTED>"
        return masked_dict

    @classmethod
    def export_package_to_file(cls, output_dir: Optional[str] = None) -> str:
        """Exports diagnostic JSON report with Privacy Mode enabled."""
        data = cls.generate_diagnostic_data()
        date_tag = time.strftime("%Y-%m-%d_%H%M%S")

        if not output_dir:
            output_dir = str(Path.home() / "Desktop")

        file_path = os.path.join(output_dir, f"SINAX_Diagnostic_{date_tag}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return file_path
