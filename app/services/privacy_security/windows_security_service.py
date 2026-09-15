# -*- coding: utf-8 -*-
"""
Windows Security Service for SINAX Privacy & Security.
Collects and presents the operating system's native security parameters:
Defender, Firewall, SmartScreen, Controlled Folder Access (Ransomware Protection),
and BitLocker Drive Encryption status. Links to official Microsoft control panels.
"""

import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional

from app.services.privacy_security.providers.antivirus_provider import MicrosoftDefenderProvider


class WindowsSecurityService:
    """Consolidated Windows Security & Defender telemetry provider."""

    def __init__(self):
        self._defender = MicrosoftDefenderProvider()
        self._cached_overview: Optional[Dict[str, Any]] = None
        self._last_overview_time: float = 0.0

    def get_security_overview(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetches consolidated status of Windows security features."""
        now = time.time()
        if not force_refresh and self._cached_overview and (now - self._last_overview_time < 20.0):
            return self._cached_overview

        # 1. Defender status
        def_status = self._defender.get_defender_status(force_refresh=force_refresh)
        raw_avail = def_status.get("raw_available", False)

        # 2. Query CFA & BitLocker via PowerShell
        cfa_status = "غير متوفر"
        bitlocker_status = "غير متوفر"

        try:
            cmd = [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                """
                $res = @{}
                try {
                    $cfa = (Get-MpPreference).EnableControlledFolderAccess
                    $res['CFA'] = switch ($cfa) { 0 {"معطل (Disabled)"} 1 {"مفعل (Active)"} 2 {"نمط التدقيق (Audit)"} default {"غير متوفر"} }
                } catch {
                    $res['CFA'] = "غير متوفر"
                }

                try {
                    $bde = manage-bde -status C: 2>&1
                    if ($bde -match "Protection On") {
                        $res['BitLocker'] = "مفعل (قرص C:)"
                    } elseif ($bde -match "Protection Off") {
                        $res['BitLocker'] = "معطل (قرص C:)"
                    } elseif ($bde -match "denied|administrator") {
                        $res['BitLocker'] = "غير متوفر (يتطلب صلاحيات مسؤول)"
                    } else {
                        $res['BitLocker'] = "غير متوفر"
                    }
                } catch {
                    $res['BitLocker'] = "غير متوفر"
                }

                $res | ConvertTo-Json
                """
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=6,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                cfa_status = data.get("CFA", "غير متوفر")
                bitlocker_status = data.get("BitLocker", "غير متوفر")
        except Exception:
            pass

        # 3. SmartScreen detection
        smartscreen_val = "غير متوفر"
        if raw_avail:
            ioav = def_status.get("ioav_enabled", None)
            if ioav is True:
                smartscreen_val = "مفعل (Active)"
            elif ioav is False:
                smartscreen_val = "معطل (Disabled)"

        overview = {
            "defender_active": ("مفعل (Active)" if def_status.get("antivirus_enabled") else "معطل (Disabled)") if raw_avail else "غير متوفر",
            "defender_active_bool": def_status.get("antivirus_enabled") if raw_avail else None,
            "defender_realtime": ("مفعل (Active)" if def_status.get("realtime_protection") else "معطل (Disabled)") if raw_avail else "غير متوفر",
            "defender_realtime_bool": def_status.get("realtime_protection") if raw_avail else None,
            "signature_version": def_status.get("signature_version", "غير متوفر") if raw_avail else "غير متوفر",
            "smartscreen": smartscreen_val,
            "controlled_folder_access": cfa_status,
            "bitlocker_status": bitlocker_status,
        }

        self._cached_overview = overview
        self._last_overview_time = now
        return overview

    def open_bitlocker_settings(self):
        """Opens the official BitLocker Control Panel applet."""
        try:
            subprocess.Popen(["control", "/name", "Microsoft.BitLockerDriveEncryption"])
        except Exception:
            pass

    def open_windows_security(self):
        self._defender.open_windows_security()

    def open_ransomware_settings(self):
        self._defender.open_ransomware_settings()

    def update_defender(self):
        return self._defender.update_signatures()
