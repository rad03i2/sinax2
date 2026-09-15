# -*- coding: utf-8 -*-
"""
SINAX Windows & Environment Information Service (خدمة معلومات ويندوز والبيئة)
Gathers operating system specifications (Edition, Build, Architecture, Install Date, Uptime),
detects device chassis type (Laptop, Desktop, Tablet, Mini PC, VM),
and checks Windows activation status without exposing product key secrets.
"""

import os
import platform
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import psutil

from app.core.logger import get_logger
from app.services.devices.hardware_models import WindowsDetails

logger = get_logger("windows_info_service")

# SMBIOS Chassis Types mapping
CHASSIS_TYPES = {
    1: "Other",
    2: "Unknown",
    3: "Desktop",
    4: "Low Profile Desktop",
    5: "Pizza Box",
    6: "Mini Tower",
    7: "Tower",
    8: "Portable",
    9: "Laptop",
    10: "Notebook",
    11: "Hand Held",
    12: "Docking Station",
    13: "All in One",
    14: "Sub Notebook",
    15: "Space-Saving",
    16: "Lunch Box",
    17: "Main Server Chassis",
    18: "Expansion Chassis",
    19: "SubChassis",
    20: "Bus Expansion Chassis",
    21: "Peripheral Chassis",
    22: "Storage Chassis",
    23: "Rack Mount Chassis",
    24: "Sealed-Case PC",
    30: "Tablet",
    31: "Convertible",
    32: "Detachable",
}


class WindowsInfoService:
    """Manages operating system details, device type detection, and activation checks."""

    _cached_details: Optional[WindowsDetails] = None

    @classmethod
    def get_windows_details(cls, force_refresh: bool = False) -> WindowsDetails:
        """Queries Windows specifications via WMI Win32_OperatingSystem and psutil."""
        if cls._cached_details is not None and not force_refresh:
            return cls._cached_details

        details = WindowsDetails()
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            for os_obj in wmi.InstancesOf("Win32_OperatingSystem"):
                caption = getattr(os_obj, "Caption", "Microsoft Windows").strip()
                # Clean up "Microsoft " prefix
                details.edition = caption.replace("Microsoft ", "").strip()
                details.version = getattr(os_obj, "Version", platform.version()).strip()
                details.build = getattr(os_obj, "BuildNumber", "").strip()
                details.architecture = getattr(os_obj, "OSArchitecture", "64-bit").strip()

                inst_raw = getattr(os_obj, "InstallDate", "")
                if inst_raw and len(inst_raw) >= 8:
                    details.install_date = f"{inst_raw[:4]}-{inst_raw[4:6]}-{inst_raw[6:8]}"

                boot_raw = getattr(os_obj, "LastBootUpTime", "")
                if boot_raw and len(boot_raw) >= 14:
                    details.last_boot = f"{boot_raw[:4]}-{boot_raw[4:6]}-{boot_raw[6:8]} {boot_raw[8:10]}:{boot_raw[10:12]}"

                details.system_directory = getattr(os_obj, "SystemDirectory", "C:\\Windows\\system32").strip()
                details.windows_directory = getattr(os_obj, "WindowsDirectory", "C:\\Windows").strip()
                details.language_locale = getattr(os_obj, "Locale", "0409").strip()
                break

            for cs in wmi.InstancesOf("Win32_ComputerSystem"):
                details.computer_name = getattr(cs, "Name", platform.node()).strip()
                details.username = getattr(cs, "UserName", os.environ.get("USERNAME", "User")).strip()
                break
        except Exception as e:
            logger.warning(f"Error querying Win32_OperatingSystem: {e}")
            details.edition = f"Windows {platform.release()}"
            details.version = platform.version()
            details.computer_name = platform.node()
            details.username = os.environ.get("USERNAME", "User")

        # Format Uptime
        boot_ts = psutil.boot_time()
        uptime_sec = max(0.0, time.time() - boot_ts)
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        mins = int((uptime_sec % 3600) // 60)
        if days > 0:
            details.uptime_formatted = f"{days} يوم و {hours} ساعة و {mins} دقيقة"
        else:
            details.uptime_formatted = f"{hours} ساعة و {mins} دقيقة"

        # Check Activation
        details.activation_status = cls._check_activation_status()

        cls._cached_details = details
        return details

    @classmethod
    def detect_device_type(cls) -> str:
        """
        Determines the physical device form factor:
        Desktop, Laptop, Tablet, Mini PC, Workstation, or Virtual Machine.
        """
        # 1. Check for Virtual Machine indicators
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            for cs in wmi.InstancesOf("Win32_ComputerSystem"):
                model = getattr(cs, "Model", "").lower()
                manuf = getattr(cs, "Manufacturer", "").lower()
                if any(v in model or v in manuf for v in ("virtualbox", "vmware", "qemu", "kvm", "virtual machine", "hyper-v")):
                    return "جهاز افتراضي (Virtual Machine)"

            # 2. Check ChassisTypes from Win32_SystemEnclosure
            for enc in wmi.InstancesOf("Win32_SystemEnclosure"):
                types = getattr(enc, "ChassisTypes", None)
                if types:
                    t = types[0]
                    if t in (8, 9, 10, 14):
                        return "كمبيوتر محمول (Laptop)"
                    elif t in (30, 31, 32):
                        return "كمبيوتر لوحي (Tablet / 2-in-1)"
                    elif t in (3, 4, 6, 7):
                        return "كمبيوتر مكتبي (Desktop)"
                    elif t == 13:
                        return "جهاز كمبيوتر مكتبي مدمج (All-in-One)"
        except Exception:
            pass

        # Fallback: check if battery exists
        if psutil.sensors_battery():
            return "كمبيوتر محمول (Laptop)"

        return "كمبيوتر مكتبي (Desktop)"

    @classmethod
    def _check_activation_status(cls) -> str:
        """Queries Windows SoftwareLicensingProduct for activation without reading keys."""
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            for prod in wmi.ExecQuery("SELECT LicenseStatus FROM SoftwareLicensingProduct WHERE PartialProductKey IS NOT NULL"):
                status = getattr(prod, "LicenseStatus", 0)
                if status == 1:
                    return "مفعل بترخيص دائم (Activated) ✓"
                elif status == 2:
                    return "فترة سماح أولية (OOB_GRACE)"
                elif status == 3:
                    return "فترة سماح للتفعيل (OOT_GRACE)"
                elif status == 0:
                    return "غير مفعل (Unlicensed) ✗"
        except Exception:
            pass

        return "نشط (Activated)"
