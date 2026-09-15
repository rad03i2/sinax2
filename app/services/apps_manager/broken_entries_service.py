# -*- coding: utf-8 -*-
"""
SINAX Broken Uninstall Entries Detector & Cleaner
Identifies orphaned uninstall registry entries (missing executable and missing folder)
and allows safe removal with mandatory .reg backups.
"""

from datetime import datetime
import logging
import os
import re
import subprocess
from typing import List, Optional, Tuple

from app.services.apps_manager.app_model import InstalledApp

logger = logging.getLogger("SINAX.apps_manager.broken_entries_service")


class BrokenEntriesService:
    """Detects and safely removes dead uninstall entries from the Windows Registry."""

    @classmethod
    def get_broken_entries(cls, apps: List[InstalledApp]) -> List[InstalledApp]:
        """Filters the application list for entries verified as broken."""
        return [a for a in apps if a.is_broken and a.registry_key_path]

    @classmethod
    def remove_broken_entry(cls, app: InstalledApp, backup_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Safely removes an orphaned uninstall entry from the registry.
        Creates an automatic .reg backup before deletion.
        """
        if not app.registry_key_path:
            return False, "لا يوجد مسار مفتاح سجل لهذا الإدخال."

        # 1. Mandatory Backup
        if not backup_dir:
            backup_dir = os.path.join(os.path.expanduser("~"), r".gemini\antigravity\backups\registry")
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", app.name)
        backup_file = os.path.join(backup_dir, f"broken_entry_{safe_name}_{timestamp}.reg")

        try:
            # Export key
            subprocess.run(
                ["reg.exe", "export", app.registry_key_path, backup_file, "/y"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Delete key
            res = subprocess.run(
                ["reg.exe", "delete", app.registry_key_path, "/f"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if res.returncode == 0:
                app.is_broken = False
                return True, f"تم حذف الإدخال المعطوب بنجاح. تم حفظ نسخة احتياطية في: {backup_file}"
            return False, f"فشل حذف مفتاح السجل: {res.stderr.strip() or res.stdout.strip()}"

        except Exception as e:
            logger.error(f"Error removing broken entry: {e}")
            return False, f"خطأ أثناء حذف الإدخال: {e}"
