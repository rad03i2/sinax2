# -*- coding: utf-8 -*-
"""
SINAX Application Repair & Reset Service
Supports MSI Repair (/fa), Modify/Change paths, WinGet repair, and MSIX App Reset.
"""

import logging
import subprocess
from typing import Tuple

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.uninstall_service import UninstallService

logger = logging.getLogger("SINAX.apps_manager.repair_service")


class RepairService:
    """Manages application repair and MSIX reset operations."""

    @classmethod
    def can_repair(cls, app: InstalledApp) -> bool:
        """Determines if the application has an official repair or modify method."""
        return bool(app.product_code or app.repair_path or app.modify_path or (app.source == "winget" and app.package_id))

    @classmethod
    def can_reset(cls, app: InstalledApp) -> bool:
        """Determines if the application is an MSIX/Store app supporting Reset."""
        return bool(app.uninstall_type == "msix" and app.package_full_name and not app.is_system_component)

    @classmethod
    def repair_app(cls, app: InstalledApp) -> Tuple[bool, str]:
        """Executes official repair on the target application."""
        # 1. MSI Repair
        if app.product_code:
            cmd = ["msiexec.exe", "/fa", app.product_code, "/qb"]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if res.returncode in (0, 3010):
                    return True, "تمت عملية إصلاح البرنامج بنجاح."
                return False, f"فشل إصلاح البرنامج. كود الخطأ: {res.returncode}"
            except Exception as e:
                return False, f"تعذر تشغيل أمر الإصلاح: {e}"

        # 2. RepairPath / ModifyPath
        raw_cmd = app.repair_path or app.modify_path
        if raw_cmd:
            exe, args = UninstallService.tokenize_command(raw_cmd)
            if exe:
                try:
                    res = subprocess.run([exe] + args, capture_output=True, text=True, timeout=300)
                    if res.returncode in (0, 3010):
                        return True, "تم تشغيل معالج الإصلاح/التعديل بنجاح."
                    return False, f"فشل معالج الإصلاح. كود الخطأ: {res.returncode}"
                except Exception as e:
                    return False, f"تعذر تشغيل المعالج: {e}"

        # 3. WinGet Repair
        if app.source == "winget" and app.package_id:
            try:
                res = subprocess.run(
                    ["winget", "repair", "--id", app.package_id, "--accept-source-agreements"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if res.returncode == 0:
                    return True, "تم إصلاح حزمة WinGet بنجاح."
                return False, f"فشلت عملية WinGet repair: {res.stderr.strip() or res.stdout.strip()}"
            except Exception as e:
                return False, f"تعذر استدعاء WinGet: {e}"

        return False, "لا يدعم هذا البرنامج آلية إصلاح رسمية معروفة."

    @classmethod
    def reset_app(cls, app: InstalledApp) -> Tuple[bool, str]:
        """
        Resets an MSIX/Store application to its initial state using PowerShell Reset-AppxPackage.
        WARNING: Deletes application settings and local cache data.
        """
        if not cls.can_reset(app):
            return False, "إعادة الضبط متاحة فقط لتطبيقات متجر ويندوز وحزم MSIX."

        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f'Reset-AppxPackage -Package "{app.package_full_name}"',
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                return True, "تمت إعادة ضبط التطبيق بنجاح وحذف بياناته المؤقتة."
            return False, f"فشلت إعادة الضبط: {res.stderr.strip() or res.stdout.strip()}"
        except Exception as e:
            return False, f"خطأ في تنفيذ أمر إعادة الضبط: {e}"
