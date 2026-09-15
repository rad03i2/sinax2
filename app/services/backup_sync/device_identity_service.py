# -*- coding: utf-8 -*-
"""
SINAX Device Identity Service.
Discovers and tracks storage devices by their persistent Volume Serial Number,
Volume Label, and Hardware Model, rather than volatile drive letters (E:, F:).
"""

import ctypes
import os
from pathlib import Path
from typing import Dict, List, Optional

import psutil
from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.models import DriveIdentity

logger = get_logger("device_identity_service")


class DeviceIdentityService:
    """Provides persistent identification of USB and external backup drives."""

    @classmethod
    def get_volume_serial_number(cls, drive_path: str) -> str:
        """Returns hex-formatted Volume Serial Number like '38A1-4F90'."""
        try:
            drive_root = os.path.splitdrive(os.path.abspath(drive_path))[0].upper() + "\\"
            vol_name = ctypes.create_unicode_buffer(1024)
            fs_name = ctypes.create_unicode_buffer(1024)
            serial = ctypes.c_ulong()
            max_len = ctypes.c_ulong()
            flags = ctypes.c_ulong()
            res = ctypes.windll.kernel32.GetVolumeInformationW(
                drive_root, vol_name, 1024, ctypes.byref(serial),
                ctypes.byref(max_len), ctypes.byref(flags), fs_name, 1024
            )
            if res and serial.value:
                raw_hex = f"{serial.value:08X}"
                return f"{raw_hex[:4]}-{raw_hex[4:]}"
        except Exception as e:
            logger.debug(f"Failed to query volume serial for {drive_path}: {e}")
        return ""

    @classmethod
    def get_drive_identity(cls, drive_path: str) -> DriveIdentity:
        """Constructs full DriveIdentity for a given path."""
        p = os.path.abspath(drive_path)
        drive_letter = os.path.splitdrive(p)[0].upper()
        serial = cls.get_volume_serial_number(drive_path)

        label = ""
        fs_type = "NTFS"
        is_removable = False
        total_b = 0
        free_b = 0

        try:
            for part in psutil.disk_partitions(all=False):
                if part.mountpoint.upper().startswith(drive_letter):
                    fs_type = part.fstype
                    if "removable" in part.opts.lower():
                        is_removable = True
                    break
            usage = psutil.disk_usage(drive_letter + "\\")
            total_b = usage.total
            free_b = usage.free
        except Exception:
            pass

        # Check if trusted in DB
        db = BackupDatabase()
        is_trusted = db.is_drive_trusted(serial) if serial else False

        return DriveIdentity(
            volume_serial=serial,
            volume_label=label,
            filesystem=fs_type,
            drive_letter=drive_letter,
            total_bytes=total_b,
            free_bytes=free_b,
            is_trusted=is_trusted,
            is_removable=is_removable
        )

    @classmethod
    def find_drive_by_serial(cls, target_serial: str) -> Optional[str]:
        """Finds the current mounted drive root (e.g. 'E:\\') matching the volume serial."""
        if not target_serial:
            return None
        try:
            for part in psutil.disk_partitions(all=False):
                mount = part.mountpoint
                serial = cls.get_volume_serial_number(mount)
                if serial and serial.upper() == target_serial.upper():
                    return mount
        except Exception as e:
            logger.debug(f"Error finding drive by serial {target_serial}: {e}")
        return None

    @classmethod
    def list_connected_external_drives(cls) -> List[DriveIdentity]:
        """Lists all currently connected external/removable storage drives."""
        drives: List[DriveIdentity] = []
        try:
            for part in psutil.disk_partitions(all=False):
                if "cdrom" in part.opts.lower() or part.fstype == "":
                    continue
                ident = cls.get_drive_identity(part.mountpoint)
                # If removable or not on system drive
                sys_drive = os.environ.get("SystemDrive", "C:").upper()
                if ident.is_removable or (ident.drive_letter and ident.drive_letter != sys_drive):
                    drives.append(ident)
        except Exception:
            pass
        return drives
