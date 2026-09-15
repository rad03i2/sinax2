# -*- coding: utf-8 -*-
"""
Windows Update Service for SINAX Maintenance & Repair Center.
Queries Windows Update status using official Windows COM API (Microsoft.Update.Session)
or PowerShell fallback. Links to native Windows Update settings and official troubleshooters.
Strictly never deletes SoftwareDistribution as routine cleanup.
"""

import json
import os
import subprocess
from typing import Any, Dict, List, Optional


class WindowsUpdateService:
    """Interacts with official Windows Update APIs and settings."""

    _cached_status: Optional[Dict[str, Any]] = None
    _last_check_time: float = 0.0

    @classmethod
    def get_update_status(cls, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Queries Windows Update status and returns structured information.
        Uses 60-second caching to avoid repeated blocking COM calls.
        """
        import time
        now = time.time()
        if not force_refresh and cls._cached_status and (now - cls._last_check_time < 60.0):
            return cls._cached_status

        if os.name != "nt":
            return {
                "status": "unknown",
                "status_ar": "غير متوفر على هذا النظام",
                "updates_count": 0,
                "updates_list": [],
                "last_search_time": "",
            }

        ps_script = """
        $result = @{
            Status = "unknown"
            StatusAr = "جاري التحقق..."
            Count = 0
            Updates = @()
            LastSearch = ""
        }
        try {
            $Session = New-Object -ComObject Microsoft.Update.Session
            $Searcher = $Session.CreateUpdateSearcher()
            $HistoryCount = $Searcher.GetTotalHistoryCount()
            if ($HistoryCount -gt 0) {
                $LastHistory = $Searcher.QueryHistory(0, 1)
                if ($LastHistory.Count -gt 0) {
                    $result.LastSearch = $LastHistory[0].Date.ToString("yyyy-MM-dd HH:mm")
                }
            }

            # Search for missing updates without downloading
            $SearchCriteria = "IsInstalled=0 and Type='Software' and IsHidden=0"
            $SearchResult = $Searcher.Search($SearchCriteria)
            $count = $SearchResult.Updates.Count
            $result.Count = $count

            $list = @()
            for ($i = 0; $i -lt [Math]::Min($count, 15); $i++) {
                $u = $SearchResult.Updates.Item($i)
                $kbList = @()
                foreach ($kb in $u.KBArticleIDs) { $kbList += "KB$kb" }
                $kbStr = if ($kbList.Count -gt 0) { $kbList -join ", " } else { "غير محدد" }

                $list += @{
                    Title = $u.Title
                    KB = $kbStr
                    IsMandatory = $u.IsMandatory
                    RebootRequired = $u.RebootRequired
                }
            }
            $result.Updates = $list

            if ($count -eq 0) {
                $result.Status = "up_to_date"
                $result.StatusAr = "النظام محدث بالكامل"
            } else {
                $result.Status = "updates_available"
                $result.StatusAr = "توجد $count تحديثات متاحة للتثبيت"
            }
        } catch {
            $result.Status = "unknown"
            $result.StatusAr = "تعذر قراءة حالة التحديثات مباشرة (راجع إعدادات Windows)"
        }

        $result | ConvertTo-Json -Depth 3
        """

        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=12,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                cls._cached_status = {
                    "status": data.get("Status", "unknown"),
                    "status_ar": data.get("StatusAr", "غير معروف"),
                    "updates_count": data.get("Count", 0),
                    "updates_list": data.get("Updates", []),
                    "last_search_time": data.get("LastSearch", ""),
                }
                cls._last_check_time = now
                return cls._cached_status
        except Exception:
            pass

        fallback = {
            "status": "unknown",
            "status_ar": "لم يتم الفحص بعد (اضغط فحص التحديثات)",
            "updates_count": 0,
            "updates_list": [],
            "last_search_time": "",
        }
        cls._cached_status = fallback
        cls._last_check_time = now
        return fallback

    @staticmethod
    def open_windows_update():
        """Opens official Windows Update settings page."""
        try:
            subprocess.Popen(["start", "ms-settings:windowsupdate"], shell=True)
        except Exception:
            pass

    @staticmethod
    def open_update_history():
        """Opens Windows Update History."""
        try:
            subprocess.Popen(["start", "ms-settings:windowsupdate-history"], shell=True)
        except Exception:
            pass

    @staticmethod
    def open_update_troubleshooter():
        """Opens official Windows Update Troubleshooter via Get Help or Settings."""
        try:
            subprocess.Popen(["start", "ms-settings:troubleshoot"], shell=True)
        except Exception:
            pass
