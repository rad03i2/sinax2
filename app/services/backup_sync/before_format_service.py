# -*- coding: utf-8 -*-
"""
SINAX Before-Format Preparation Service (تجهيز الجهاز قبل الفورمات).
Assembles a complete, structured restore package prior to formatting Windows:
1. Personal data from Known Folders & Custom directories.
2. Installed software inventory & WinGet restoration script.
3. System hardware driver packages via pnputil export.
4. SINAX configuration, preferences, and backup profiles.
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import time
from typing import Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.apps_manager.inventory_service import InventoryService
from app.services.backup_sync.copy_engine import CopyEngine
from app.services.backup_sync.known_folders_service import KnownFoldersService
from app.services.devices.driver_service import DriverService

logger = get_logger("before_format_service")


@dataclass
class BeforeFormatReport:
    is_success: bool = True
    destination_package_dir: str = ""
    files_backed_up_count: int = 0
    total_bytes_backed_up: int = 0
    programs_cataloged_count: int = 0
    drivers_exported_count: int = 0
    settings_saved: bool = False
    error_summary: str = ""


class BeforeFormatService:
    """Orchestrates comprehensive system preparation before formatting Windows."""

    @classmethod
    def execute_before_format_package(
        cls,
        destination_folder: str,
        include_folders: List[str],
        export_apps: bool = True,
        export_drivers: bool = True,
        export_sinax_settings: bool = True,
        progress_cb: Optional[Callable[[str, float], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> BeforeFormatReport:
        """Packages files, applications, drivers, and settings into a structured directory."""
        report = BeforeFormatReport()
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        package_root = Path(destination_folder) / f"SINAX_Before_Format_Backup_{timestamp_str}"
        report.destination_package_dir = str(package_root)

        try:
            package_root.mkdir(parents=True, exist_ok=True)

            # 1. Back up Personal Files
            files_dir = package_root / "Personal_Files"
            files_dir.mkdir(parents=True, exist_ok=True)
            if progress_cb:
                progress_cb("جاري نسخ الملفات والمستندات الشخصية المحددة...", 0.10)

            for folder in include_folders:
                if cancel_check and cancel_check():
                    report.is_success = False
                    report.error_summary = "تم إلغاء العملية بواسطة المستخدم."
                    return report

                folder_p = Path(folder)
                if not folder_p.exists():
                    continue

                target_sub = files_dir / folder_p.name
                target_sub.mkdir(parents=True, exist_ok=True)

                if folder_p.is_file():
                    CopyEngine.copy_file_safe(str(folder_p), str(target_sub / folder_p.name))
                    report.files_backed_up_count += 1
                    report.total_bytes_backed_up += folder_p.stat().st_size
                else:
                    for root, _, files in os.walk(str(folder_p)):
                        for f in files:
                            src_f = Path(root) / f
                            rel = src_f.relative_to(folder_p)
                            dst_f = target_sub / rel
                            dst_f.parent.mkdir(parents=True, exist_ok=True)
                            ok, _ = CopyEngine.copy_file_safe(str(src_f), str(dst_f))
                            if ok:
                                report.files_backed_up_count += 1
                                try:
                                    report.total_bytes_backed_up += src_f.stat().st_size
                                except OSError:
                                    pass

            # 2. Export Installed Programs Inventory & WinGet Script
            if export_apps:
                if progress_cb:
                    progress_cb("جاري جرد البرامج وتوليد سكريبت استعادة WinGet...", 0.50)

                apps_dir = package_root / "Installed_Applications"
                apps_dir.mkdir(parents=True, exist_ok=True)

                apps = InventoryService().get_installed_applications(force_refresh=False)
                report.programs_cataloged_count = len(apps)

                # Save JSON
                apps_list_json = [
                    {
                        "name": a.name,
                        "version": a.version,
                        "publisher": a.publisher,
                        "install_date": a.install_date,
                        "package_type": a.package_type,
                        "winget_id": getattr(a, "winget_id", "")
                    }
                    for a in apps
                ]
                with open(apps_dir / "programs_inventory.json", "w", encoding="utf-8") as f:
                    json.dump(apps_list_json, f, indent=2, ensure_ascii=False)

                # Generate WinGet restore batch script
                winget_lines = ["@echo off", "chcp 65001 > nul", "echo === SINAX WinGet Restore Script ==="]
                for a in apps:
                    wid = getattr(a, "winget_id", "")
                    if wid:
                        winget_lines.append(f"winget install --id {wid} -e --accept-source-agreements --accept-package-agreements")
                with open(apps_dir / "restore_winget_apps.bat", "w", encoding="utf-8") as f:
                    f.write("\n".join(winget_lines))

            # 3. Export Hardware Drivers via pnputil
            if export_drivers:
                if progress_cb:
                    progress_cb("جاري تصدير حزم تعريفات العتاد (Drivers)...", 0.75)

                drivers_dir = package_root / "Hardware_Drivers"
                drivers_dir.mkdir(parents=True, exist_ok=True)

                ok, count, msg = DriverService.export_all_drivers(str(drivers_dir))
                report.drivers_exported_count = count

            # 4. Save SINAX Settings & Profiles
            if export_sinax_settings:
                if progress_cb:
                    progress_cb("جاري حفظ إعدادات وخطط SINAX...", 0.90)

                settings_dir = package_root / "SINAX_Configuration"
                settings_dir.mkdir(parents=True, exist_ok=True)

                sinax_home = Path.home() / ".sinax"
                if sinax_home.exists():
                    for item in sinax_home.glob("*.json"):
                        try:
                            shutil.copy2(str(item), str(settings_dir / item.name))
                        except Exception:
                            pass
                report.settings_saved = True

            # 5. Write Guide & Manifest
            instructions = f"""======================================================================
حزمة التجهيز قبل الفورمات - SINAX Before-Format Restore Package
تاريخ الإنشاء: {time.strftime('%Y-%m-%d %H:%M:%S')}
======================================================================

محتويات الحزمة:
1. مجلد Personal_Files:
   يحتوي على جميع ملفاتك ومستنداتك المهمة مقسمة بنفس هيكلها الأصلي.
2. مجلد Installed_Applications:
   يحتوي على قائمة شاملة بكل البرامج التي كانت مثبتة قبل الفورمات،
   بالإضافة إلى ملف (restore_winget_apps.bat) لإعادة تثبيتها بنقرة واحدة عبر WinGet.
3. مجلد Hardware_Drivers:
   يحتوي على ({report.drivers_exported_count}) حزمة تعريفات للقطع والعتاد الداخلي للجهاز.
4. مجلد SINAX_Configuration:
   يحتوي على إعدادات وخطط SINAX السابقة.

تم تجهيز هذه الحزمة بنجاح عبر SINAX Backup & Sync Center.
"""
            with open(package_root / "RESTORE_INSTRUCTIONS_AR.txt", "w", encoding="utf-8") as f:
                f.write(instructions)

            if progress_cb:
                progress_cb("اكتمل تجهيز الحزمة بنجاح ✓", 1.0)

            report.is_success = True

        except Exception as e:
            report.is_success = False
            report.error_summary = f"حدث خطأ أثناء إعداد الحزمة: {e}"

        return report
