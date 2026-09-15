# -*- coding: utf-8 -*-
"""
Troubleshooter & System Helpers Service for SINAX Maintenance & Repair Center.
Integrates official Windows Get Help and Settings troubleshooters,
time synchronization (w32tm), and safe service restarting (e.g. Print Spooler).
Strictly avoids fake 'Service Optimizers' or unguided disabling of system services.
"""

import os
import subprocess
from typing import Dict, Optional, Tuple


class TroubleshooterService:
    """Manages official Windows troubleshooters and targeted service actions."""

    # 1. Native Troubleshooter Launchers
    @staticmethod
    def open_network_troubleshooter():
        try:
            subprocess.Popen(["start", "ms-settings:network-status"], shell=True)
        except Exception:
            pass

    @staticmethod
    def open_audio_troubleshooter():
        try:
            subprocess.Popen(["start", "ms-settings:sound"], shell=True)
        except Exception:
            pass

    @staticmethod
    def open_printers_settings():
        try:
            subprocess.Popen(["start", "ms-settings:printers"], shell=True)
        except Exception:
            pass

    @staticmethod
    def open_bluetooth_settings():
        try:
            subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)
        except Exception:
            pass

    @staticmethod
    def open_windows_troubleshoot_hub():
        try:
            subprocess.Popen(["start", "ms-settings:troubleshoot"], shell=True)
        except Exception:
            pass

    @staticmethod
    def open_device_manager():
        try:
            subprocess.Popen(["devmgmt.msc"])
        except Exception:
            pass

    # 2. Time Synchronization
    @staticmethod
    def sync_system_time() -> Tuple[bool, str]:
        """
        Synchronizes system clock via Windows Time service (w32tm /resync).
        """
        if os.name != "nt":
            return False, "متوفر فقط على أنظمة Windows."

        try:
            # Ensure w32time service is running
            subprocess.run(["net", "start", "w32time"], capture_output=True, timeout=5)
            res = subprocess.run(
                ["w32tm.exe", "/resync"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            out = res.stdout or ""
            if "The command completed successfully" in out or "تمت العملية بنجاح" in out or res.returncode == 0:
                return True, "تمت مزامنة توقيت النظام وساعة الحاسوب بنجاح مع خوادم التوقيت الرسمية."
            else:
                return False, f"تعذر إكمال المزامنة: {out.strip() or res.stderr.strip()}"
        except Exception as e:
            return False, f"فشل تشغيل مزامنة التوقيت: {e}"

    # 3. Targeted Service Restart (Only problem-specific services)
    @staticmethod
    def restart_service(service_name: str) -> Tuple[bool, str]:
        """
        Restarts a specific, pre-approved system service (e.g. Spooler for printers).
        """
        allowed_services = {
            "spooler": "مخزن مؤقت للطباعة (Print Spooler)",
            "wuauserv": "تحديثات Windows (Windows Update)",
            "dnscache": "عميل DNS (DNS Client)",
            "dhcp": "عميل DHCP",
            "w32time": "وقت Windows (Windows Time)",
        }

        s_key = service_name.strip().lower()
        if s_key not in allowed_services:
            return False, f"الخدمة '{service_name}' غير مصرح بإدارتها من هذا القسم لأسباب أمنية."

        s_title = allowed_services[s_key]

        try:
            subprocess.run(["net", "stop", s_key, "/y"], capture_output=True, timeout=10)
            res = subprocess.run(["net", "start", s_key], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, f"تمت إعادة تشغيل خدمة {s_title} بنجاح."
            else:
                return False, f"تعذر بدء الخدمة: {res.stderr.strip() or res.stdout.strip()}"
        except Exception as e:
            return False, f"فشل إعادة تشغيل الخدمة: {e}"
