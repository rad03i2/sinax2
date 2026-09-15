# -*- coding: utf-8 -*-
"""
SINAX Device Manager & Driver Center Service (خدمة إدارة الأجهزة والتعريفات)
Queries system PnP hardware tree by class, detects unknown/problem devices,
copies hardware IDs for driver search, executes driver package backups via pnputil,
and provides safe device toggle with elevation protection.
"""

import collections
import os
import re
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.devices.hardware_models import DriverDetails, PnpDeviceInfo

logger = get_logger("driver_service")

# Classes prohibited from being disabled to avoid bricking input/display/system
PROTECTED_DEVICE_CLASSES = {
    "keyboard", "mouse", "display", "system", "scsiadapter",
    "hdc", "processor", "diskdrive", "volume", "volumemanager"
}


class DriverService:
    """Manages Device Manager tree, driver information, backups, and device toggles."""

    @classmethod
    def get_all_pnp_devices(cls) -> List[PnpDeviceInfo]:
        """Queries all PnP devices on the system organized by hardware class."""
        devices: List[PnpDeviceInfo] = []
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            query = "SELECT Name, PNPClass, Status, ConfigManagerErrorCode, DeviceID, Manufacturer, HardwareID FROM Win32_PnPEntity"
            for d in wmi.ExecQuery(query):
                name = getattr(d, "Name", "") or ""
                if not name:
                    continue

                pnp_class = getattr(d, "PNPClass", "Other") or "Other"
                status = getattr(d, "Status", "OK") or "OK"
                err_code = int(getattr(d, "ConfigManagerErrorCode", 0) or 0)
                dev_id = getattr(d, "DeviceID", "") or ""
                manuf = getattr(d, "Manufacturer", "غير محدد") or "غير محدد"
                hw_ids_raw = getattr(d, "HardwareID", None)
                hw_ids = list(hw_ids_raw) if hw_ids_raw else []

                is_prob = (err_code != 0) or (status != "OK")

                devices.append(PnpDeviceInfo(
                    name=name,
                    device_class=pnp_class,
                    status=status if not is_prob else f"خطأ ({err_code})",
                    error_code=err_code,
                    hardware_ids=hw_ids,
                    instance_id=dev_id,
                    manufacturer=manuf,
                    is_problem=is_prob
                ))
        except Exception as e:
            logger.warning(f"Error querying Win32_PnPEntity: {e}")

        return devices

    @classmethod
    def get_problem_devices(cls) -> List[PnpDeviceInfo]:
        """Returns only unknown devices or devices with error codes."""
        all_devs = cls.get_all_pnp_devices()
        return [d for d in all_devs if d.is_problem or d.device_class.lower() in ("unknown", "other")]

    @classmethod
    def export_driver_packages(
        cls,
        destination_folder: str
    ) -> Tuple[bool, int, str]:
        """
        Exports all installed third-party and system driver packages to destination_folder
        using the official Windows pnputil tool (`pnputil /export-driver * <dest>`).
        """
        if not os.path.exists(destination_folder):
            try:
                os.makedirs(destination_folder, exist_ok=True)
            except Exception as e:
                return False, 0, f"تعذر إنشاء مجلد الوجهة: {e}"

        cmd = ["pnputil.exe", "/export-driver", "*", destination_folder]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120.0
            )

            # Count exported .inf files
            inf_files = [f for f in os.listdir(destination_folder) if f.lower().endswith(".inf")]
            count = len(inf_files)

            if res.returncode == 0 or count > 0:
                return True, count, f"تم تصدير ({count}) حزمة تعريفات بنجاح إلى:\n{destination_folder} ✓"
            else:
                return False, 0, f"فشل تصدير التعريفات: {res.stderr or res.stdout}"
        except Exception as e:
            return False, 0, f"خطأ أثناء تصدير التعريفات: {e}"

    @classmethod
    def can_safely_disable(cls, device: PnpDeviceInfo) -> Tuple[bool, str]:
        """Checks if a device can be safely disabled without crashing basic user input/display."""
        cls_name = device.device_class.strip().lower()
        if cls_name in PROTECTED_DEVICE_CLASSES:
            return False, f"لا يمكن تعطيل أجهزة فئة ({device.device_class}) لأنها لازمة لعمل النظام الأساسي والشاشة ووحدات الإدخال!"
        return True, ""

    @classmethod
    def set_device_state(cls, instance_id: str, enable: bool) -> Tuple[bool, str]:
        """
        Enables or disables a device via pnputil with administrator elevation.
        Requires UAC elevation.
        """
        action = "/enable-device" if enable else "/disable-device"
        try:
            # Run elevated via powershell Start-Process
            ps_cmd = f'Start-Process pnputil -ArgumentList "{action} \\"{instance_id}\\"" -Verb RunAs -Wait'
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=15)
            if res.returncode == 0:
                state_txt = "تم تفعيل" if enable else "تم تعطيل"
                return True, f"{state_txt} الجهاز بنجاح ✓"
            return False, "تم إلغاء العملية أو لم يتم منح صلاحيات المسؤول."
        except Exception as e:
            return False, f"خطأ أثناء تعديل حالة الجهاز: {e}"

    @classmethod
    def open_device_manager(cls) -> bool:
        """Launches the native Windows Device Manager (devmgmt.msc)."""
        try:
            subprocess.Popen(["devmgmt.msc"], shell=False)
            return True
        except Exception:
            return False

    @classmethod
    def get_pnp_tree(cls) -> Dict[str, List[PnpDeviceInfo]]:
        """Groups all PnP devices by device class."""
        devices = cls.get_all_pnp_devices()
        tree: Dict[str, List[PnpDeviceInfo]] = collections.defaultdict(list)
        for d in devices:
            tree[d.device_class].append(d)
        return dict(tree)

    @classmethod
    def backup_drivers(cls, destination_folder: str, progress_cb: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Convenience wrapper for exporting drivers via pnputil."""
        if progress_cb:
            progress_cb("جاري تصدير حزم التعريفات عبر pnputil...")
        ok, count, msg = cls.export_driver_packages(destination_folder)
        return {
            "success": ok,
            "exported_count": count,
            "message_ar": msg,
            "destination_dir": destination_folder
        }
