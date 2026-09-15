# -*- coding: utf-8 -*-
"""
Event & Reliability Service for SINAX Maintenance & Repair Center.
Safely queries Windows Event Logs (System and Application) in read-only mode to extract:
- Application crashes (Event ID 1000)
- Unexpected shutdowns (Event ID 6008, Kernel-Power 41)
- Storage errors (Event ID 7, 51)
- Minidump / BSOD records from C:\\Windows\\Minidump
Translates cryptic Event IDs into user-friendly diagnostic explanations.
"""

import glob
import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional
from app.services.maintenance.models import CrashEvent


class EventReliabilityService:
    """Extracts high-level crash telemetry and stability insights from Windows logs."""

    @staticmethod
    def get_recent_crash_events(days: int = 7, max_results: int = 30) -> List[CrashEvent]:
        """
        Queries Application log for Event ID 1000 (Application Crash)
        and System log for Event ID 6008 / 41 (Unexpected Shutdown).
        """
        if os.name != "nt":
            return []

        ps_script = f"""
        $days = {days}
        $after = (Get-Date).AddDays(-$days)
        $events = @()

        # 1. App Crashes (Event ID 1000)
        try {{
            Get-WinEvent -FilterHashtable @{{
                LogName='Application'
                Id=1000
                StartTime=$after
            }} -MaxEvents {max_results} -ErrorAction SilentlyContinue | ForEach-Object {{
                $xml = [xml]$_.ToXml()
                $app = ""
                $module = ""
                $ex = ""
                foreach ($d in $xml.Event.EventData.Data) {{
                    if ($d.Name -eq "AppName") {{ $app = $d.'#text' }}
                    elseif ($d.Name -eq "ModuleName") {{ $module = $d.'#text' }}
                    elseif ($d.Name -eq "ExceptionCode") {{ $ex = $d.'#text' }}
                }}
                if (-not $app) {{ $app = $_.Message.Split("`n")[0] }}

                $events += @{{
                    Type = "AppCrash"
                    Timestamp = ([DateTimeOffset]$_.TimeCreated).ToUnixTimeSeconds()
                    TimeStr = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm")
                    AppName = $app
                    FaultModule = $module
                    ExceptionCode = $ex
                    Details = "تعطل غير متوقع للتطبيق (رمز الخطأ: $ex)"
                }}
            }}
        }} catch {{}}

        # 2. Unexpected Shutdowns (Event ID 6008 / Kernel-Power 41)
        try {{
            Get-WinEvent -FilterHashtable @{{
                LogName='System'
                Id=6008, 41
                StartTime=$after
            }} -MaxEvents 10 -ErrorAction SilentlyContinue | ForEach-Object {{
                $events += @{{
                    Type = "UnexpectedShutdown"
                    Timestamp = ([DateTimeOffset]$_.TimeCreated).ToUnixTimeSeconds()
                    TimeStr = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm")
                    AppName = "Windows System"
                    FaultModule = "Kernel"
                    ExceptionCode = "PowerLoss / BlueScreen"
                    Details = "تم رصد إيقاف تشغيل غير متوقع أو انقطاع مفاجئ للطاقة"
                }}
            }}
        }} catch {{}}

        $events | Sort-Object -Property Timestamp -Descending | ConvertTo-Json -Depth 3
        """

        results: List[CrashEvent] = []
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
                if isinstance(data, dict):
                    data = [data]
                for item in data[:max_results]:
                    results.append(CrashEvent(
                        timestamp=float(item.get("Timestamp", 0)),
                        timestamp_str=item.get("TimeStr", ""),
                        event_type=item.get("Type", "AppCrash"),
                        app_name=item.get("AppName", "Unknown"),
                        fault_module=item.get("FaultModule", ""),
                        exception_code=item.get("ExceptionCode", ""),
                        details=item.get("Details", "")
                    ))
        except Exception:
            pass

        return results

    @staticmethod
    def get_bsod_minidump_records() -> List[Dict[str, Any]]:
        """
        Inspects C:\\Windows\\Minidump for crash dumps (*.dmp).
        Extracts file name, creation date, and size without full debugger attachment.
        """
        minidump_path = r"C:\Windows\Minidump"
        dumps: List[Dict[str, Any]] = []

        if not os.path.exists(minidump_path):
            return dumps

        try:
            pattern = os.path.join(minidump_path, "*.dmp")
            for fpath in glob.glob(pattern):
                try:
                    st = os.stat(fpath)
                    dumps.append({
                        "filename": os.path.basename(fpath),
                        "path": fpath,
                        "size_bytes": st.st_size,
                        "size_str": f"{st.st_size / (1024 * 1024):.2f} MB",
                        "date_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)),
                        "timestamp": st.st_mtime,
                    })
                except Exception:
                    pass
        except Exception:
            pass

        return sorted(dumps, key=lambda x: x["timestamp"], reverse=True)

    @staticmethod
    def open_minidump_folder():
        """Opens C:\\Windows\\Minidump in Windows Explorer."""
        minidump_path = r"C:\Windows\Minidump"
        if os.path.exists(minidump_path):
            try:
                subprocess.Popen(["explorer.exe", minidump_path])
            except Exception:
                pass
        else:
            try:
                subprocess.Popen(["explorer.exe", r"C:\Windows"])
            except Exception:
                pass

    @staticmethod
    def get_event_summary_stats(days: int = 7) -> Dict[str, int]:
        """Returns summarized event counts for dashboard cards."""
        crashes = EventReliabilityService.get_recent_crash_events(days=days)
        app_crash_count = sum(1 for c in crashes if c.event_type == "AppCrash")
        shutdown_count = sum(1 for c in crashes if c.event_type == "UnexpectedShutdown")
        dumps = EventReliabilityService.get_bsod_minidump_records()

        return {
            "app_crashes": app_crash_count,
            "unexpected_shutdowns": shutdown_count,
            "bsod_dumps_count": len(dumps),
        }
