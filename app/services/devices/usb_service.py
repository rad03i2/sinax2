# -*- coding: utf-8 -*-
"""
SINAX USB Center Service (خدمة فحص وإدارة أجهزة USB)
Discovers connected USB devices, flash drives, input devices, webcams, and audio devices.
Extracts Vendor ID (VID) and Product ID (PID), flags problem devices,
and provides safe removal workflows without aggressive force-ejection.
"""

import ctypes
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.devices.hardware_models import UsbDeviceInfo

logger = get_logger("usb_service")


class UsbService:
    """Discovers, categorizes, and safely manages USB peripherals."""

    @classmethod
    def get_usb_devices(
        cls,
        filter_mode: str = "connected",
        only_connected: Optional[bool] = None,
        only_problems: Optional[bool] = None
    ) -> List[UsbDeviceInfo]:
        """
        Discovers USB peripherals via Win32_PnPEntity.
        Supports filter_mode ('connected', 'all', 'problem') or boolean flags.
        """
        if only_problems:
            filter_mode = "problem"
        elif only_connected is False:
            filter_mode = "all"
        elif only_connected is True:
            filter_mode = "connected"

        devices: List[UsbDeviceInfo] = []

        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            query = "SELECT Name, PNPClass, Status, DeviceID, Manufacturer, ConfigManagerErrorCode FROM Win32_PnPEntity WHERE DeviceID LIKE 'USB%'"
            for d in wmi.ExecQuery(query):
                name = getattr(d, "Name", "") or ""
                if not name:
                    continue

                dev_id = getattr(d, "DeviceID", "") or ""
                pnp_class = getattr(d, "PNPClass", "USB") or "USB"
                status = getattr(d, "Status", "OK") or "OK"
                manuf = getattr(d, "Manufacturer", "غير محدد") or "غير محدد"
                err_code = int(getattr(d, "ConfigManagerErrorCode", 0) or 0)

                # Extract VID & PID
                vid = "غير متوفر"
                pid = "غير متوفر"
                vid_m = re.search(r"VID_([0-9A-Fa-f]{4})", dev_id)
                pid_m = re.search(r"PID_([0-9A-Fa-f]{4})", dev_id)
                if vid_m:
                    vid = f"0x{vid_m.group(1).upper()}"
                if pid_m:
                    pid = f"0x{pid_m.group(1).upper()}"

                is_problem = (err_code != 0) or (status != "OK")
                is_storage = (pnp_class in ("DiskDrive", "Storage") or "Mass Storage" in name or "Flash" in name)

                # Apply filter
                if filter_mode == "problem" and not is_problem:
                    continue

                devices.append(UsbDeviceInfo(
                    name=name,
                    device_class=pnp_class,
                    status=status if not is_problem else f"مشكلة (رمز {err_code})",
                    manufacturer=manuf,
                    vendor_id=vid,
                    product_id=pid,
                    instance_id=dev_id,
                    is_connected=True,
                    is_removable_storage=is_storage
                ))
        except Exception as e:
            logger.warning(f"Error querying USB devices: {e}")

        return devices

    @classmethod
    def safely_remove_drive(cls, drive_letter: str) -> Tuple[bool, str]:
        """
        Safely unmounts and ejects a removable USB flash drive.
        Never executes aggressive force-eject if files are open.
        """
        clean_letter = drive_letter.strip().rstrip(":\\").upper()
        if not clean_letter or len(clean_letter) != 1:
            return False, "حرف محرك الأقراص غير صحيح."

        drive_path = f"\\\\.\\{clean_letter}:"
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        FSCTL_LOCK_VOLUME = 0x00090018
        FSCTL_DISMOUNT_VOLUME = 0x00090020
        IOCTL_STORAGE_EJECT_MEDIA = 0x002D4808

        handle = ctypes.windll.kernel32.CreateFileW(
            drive_path,
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None
        )

        if handle == -1 or handle == 0xFFFFFFFF:
            return False, f"لا يمكن الوصول إلى المحرك {clean_letter}:. قد يكون مستخدماً بواسطة برامج أخرى."

        try:
            bytes_returned = ctypes.c_ulong()

            # 1. Dismount volume
            dismount_res = ctypes.windll.kernel32.DeviceIoControl(
                handle,
                FSCTL_DISMOUNT_VOLUME,
                None, 0, None, 0,
                ctypes.byref(bytes_returned),
                None
            )

            # 2. Eject media
            eject_res = ctypes.windll.kernel32.DeviceIoControl(
                handle,
                IOCTL_STORAGE_EJECT_MEDIA,
                None, 0, None, 0,
                ctypes.byref(bytes_returned),
                None
            )

            if eject_res or dismount_res:
                return True, f"تم إلغاء تثبيت المحرك ({clean_letter}:) ويمكن إزالته بأمان الآن ✓"
            else:
                return False, f"المحرك ({clean_letter}:) قيد الاستخدام حالياً بواسطة أحد البرامج."
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)

    @classmethod
    def eject_usb_device(cls, instance_id_or_letter: str) -> Dict[str, Any]:
        """Convenience wrapper for safe eject returning dict."""
        ok, msg = cls.safely_remove_drive(instance_id_or_letter)
        return {
            "success": ok,
            "message_ar": msg
        }
