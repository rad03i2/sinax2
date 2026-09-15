# -*- coding: utf-8 -*-
"""
SINAX USB Backup & Auto-Connect Service.
Pairs profiles with Trusted Backup Drives, handles "Backup on Connect" workflow
with a 15-second grace countdown notification, and provides optional safe ejection.
"""

from dataclasses import dataclass
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.device_identity_service import DeviceIdentityService
from app.services.backup_sync.models import BackupProfile
from app.services.devices.usb_service import UsbService

logger = get_logger("usb_backup_service")


class UsbBackupService:
    """Manages trusted backup drives and insertion triggers."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    def pair_drive_as_trusted(self, drive_path: str, profile_id: Optional[str] = None) -> Tuple[bool, str]:
        """Registers a drive as a Trusted Backup Drive and optionally links to a profile."""
        ident = DeviceIdentityService.get_drive_identity(drive_path)
        if not ident.volume_serial:
            return False, "تعذر استخراج المعرف الفريد للقرص (Volume Serial Number)."

        self.db.register_trusted_drive(
            serial=ident.volume_serial,
            label=ident.volume_label,
            model=ident.filesystem
        )

        if profile_id:
            profile = self.db.get_profile(profile_id)
            if profile:
                profile.trusted_drive_serial = ident.volume_serial
                self.db.save_profile(profile)

        return True, f"تم تسجيل القرص بنجاح كقرص نسخ احتياطي موثوق ({ident.volume_serial}) ✓"

    def check_drive_for_profiles(self, drive_path: str) -> List[BackupProfile]:
        """Finds all profiles assigned to this specific physical drive."""
        serial = DeviceIdentityService.get_volume_serial_number(drive_path)
        if not serial:
            return []

        all_profiles = self.db.list_profiles()
        matched = [p for p in all_profiles if p.trusted_drive_serial and p.trusted_drive_serial.upper() == serial.upper()]
        return matched

    def safe_eject_backup_drive(self, drive_path: str) -> Tuple[bool, str]:
        """Ejects the backup drive safely after completion."""
        drive_letter = DeviceIdentityService.get_drive_identity(drive_path).drive_letter
        if not drive_letter:
            return False, "حرف محرك الأقراص غير متاح."

        res = UsbService.eject_usb_device(drive_letter)
        return res.get("success", False), res.get("message_ar", "")
