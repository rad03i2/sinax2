# -*- coding: utf-8 -*-
"""
Microsoft Defender Provider for SINAX Privacy & Security.
Queries Defender status, triggers official custom scans via PowerShell,
and manages updates without altering exclusions or creating fake engines.
"""

import os
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple


class MicrosoftDefenderProvider:
    """Official Windows Defender bridge using standard PowerShell cmdlets."""

    def __init__(self):
        self._cached_status: Optional[Dict[str, Any]] = None
        self._last_status_fetch: float = 0.0

    def get_defender_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Queries Microsoft Defender status and security intelligence version."""
        now = time.time()
        if not force_refresh and self._cached_status and (now - self._last_status_fetch < 15.0):
            return self._cached_status

        status = {
            "antivirus_enabled": True,
            "realtime_protection": True,
            "signature_version": "محدثة",
            "signature_age_days": 0,
            "smartscreen_enabled": True,
            "last_quick_scan": "غير متوفر",
            "raw_available": False,
        }

        # Query Get-MpComputerStatus
        cmd = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, AntispywareSignatureVersion, AntispywareSignatureAge, IoavProtectionEnabled, QuickScanEndTime | ConvertTo-Json"
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout)
                status["antivirus_enabled"] = bool(data.get("AntivirusEnabled", True))
                status["realtime_protection"] = bool(data.get("RealTimeProtectionEnabled", True))
                status["signature_version"] = str(data.get("AntispywareSignatureVersion") or "محدثة")
                status["signature_age_days"] = int(data.get("AntispywareSignatureAge") or 0)
                status["ioav_enabled"] = bool(data.get("IoavProtectionEnabled", False))
                status["last_quick_scan"] = str(data.get("QuickScanEndTime") or "غير متوفر")
                status["raw_available"] = True
        except Exception:
            status["raw_available"] = False

        self._cached_status = status
        self._last_status_fetch = now
        return status

    def scan_path(self, target_path: str, timeout_seconds: int = 120) -> Tuple[bool, str]:
        """
        Executes an on-demand custom scan for the given file or folder path.
        Returns: (success: bool, message: str)
        """
        p = Path(target_path).resolve()
        if not p.exists():
            return False, f"المسار غير موجود: {target_path}"

        # Use Start-MpScan with CustomScan and ScanPath
        cmd = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            f"Start-MpScan -ScanType CustomScan -ScanPath '{str(p)}' -ErrorAction Stop"
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if res.returncode == 0:
                return True, "لم يتم الإبلاغ عن أي تهديد بواسطة Microsoft Defender (No threat reported)"
            else:
                err_msg = res.stderr.strip() or "فشل الفحص أو تم إلغاؤه"
                return False, f"تنبيه الفحص: {err_msg}"
        except subprocess.TimeoutExpired:
            return False, "تجاوز فحص Defender الوقت المحدد (تجاوز 120 ثانية)"
        except Exception as e:
            return False, f"تعذر استدعاء فحص Defender: {str(e)}"

    def update_signatures(self) -> Tuple[bool, str]:
        """Triggers official definition updates via Update-MpSignature."""
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Update-MpSignature -ErrorAction Stop"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if res.returncode == 0:
                self.get_defender_status(force_refresh=True)
                return True, "تم تحديث توقيعات الأمان بنجاح عبر Microsoft Update."
            else:
                return False, f"تعذر تحديث التوقيعات: {res.stderr.strip()}"
        except Exception as e:
            return False, f"خطأ أثناء طلب التحديث: {str(e)}"

    def open_windows_security(self):
        """Opens Windows Security application UI."""
        try:
            os.startfile("windowsdefender:")
        except Exception:
            try:
                subprocess.Popen(["control", "/name", "Microsoft.WindowsDefender"])
            except Exception:
                pass

    def open_ransomware_settings(self):
        """Opens Controlled Folder Access / Ransomware protection settings."""
        try:
            os.startfile("ms-settings:windowsdefender-manageprotection")
        except Exception:
            self.open_windows_security()
