# -*- coding: utf-8 -*-
"""
Explorer Repair Service for SINAX Maintenance & Repair Center.
Provides safe tools to resolve common Windows desktop/shell issues:
- Graceful restart of Windows Explorer (taskbar/desktop refresh)
- Safe rebuild of Explorer Thumbnail Cache
- Safe rebuild of Icon Cache
- Opening official Folder Options control panel.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Tuple


class ExplorerRepairService:
    """Repairs Windows Explorer glitches, icon corruptions, and broken thumbnails."""

    @staticmethod
    def restart_explorer() -> Tuple[bool, str]:
        """
        Gracefully terminates and restarts explorer.exe process.
        Taskbar will briefly disappear and reappear.
        """
        if os.name != "nt":
            return False, "هذه الأداة متوفرة على أنظمة Windows فقط."

        try:
            # 1. Kill explorer
            subprocess.run(["taskkill.exe", "/F", "/IM", "explorer.exe"], capture_output=True, timeout=5)
            time.sleep(1.0)
            # 2. Restart explorer
            subprocess.Popen(["explorer.exe"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            return True, "تمت إعادة تشغيل مستكشف Windows بنجاح وتحديث سطح المكتب وشريط المهام."
        except Exception as e:
            return False, f"حدث خطأ أثناء إعادة تشغيل Explorer: {e}"

    @staticmethod
    def rebuild_thumbnail_cache() -> Tuple[bool, str]:
        """
        Terminates explorer, deletes thumbcache_*.db files, and restarts explorer.
        Windows will automatically regenerate clean thumbnails without affecting original photos.
        """
        if os.name != "nt":
            return False, "متوفر فقط على نظام Windows."

        local_app = os.environ.get("LOCALAPPDATA", "")
        if not local_app:
            return False, "تعذر الوصول إلى مجلد LocalAppData."

        thumb_dir = Path(local_app) / "Microsoft" / "Windows" / "Explorer"

        try:
            # Stop explorer so files are unlocked
            subprocess.run(["taskkill.exe", "/F", "/IM", "explorer.exe"], capture_output=True, timeout=5)
            time.sleep(1.0)

            deleted_count = 0
            if thumb_dir.exists():
                for f in thumb_dir.glob("thumbcache_*.db"):
                    try:
                        f.unlink()
                        deleted_count += 1
                    except Exception:
                        pass

            # Relaunch explorer
            subprocess.Popen(["explorer.exe"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            return True, f"تم حذف {deleted_count} ملف كاش للمصغرات وإعادة تشغيل Explorer لبناء المصغرات الجديدة تلقائياً."
        except Exception as e:
            # Ensure explorer is brought back
            subprocess.Popen(["explorer.exe"])
            return False, f"فشل تنظيف كاش المصغرات: {e}"

    @staticmethod
    def rebuild_icon_cache() -> Tuple[bool, str]:
        """
        Rebuilds corrupted Windows Icon Cache (IconCache.db & iconcache_*.db).
        Resolves blank, wrong, or broken desktop/app icons.
        """
        if os.name != "nt":
            return False, "متوفر فقط على نظام Windows."

        local_app = os.environ.get("LOCALAPPDATA", "")
        if not local_app:
            return False, "تعذر الوصول إلى LocalAppData."

        old_icon_cache = Path(local_app) / "IconCache.db"
        new_icon_dir = Path(local_app) / "Microsoft" / "Windows" / "Explorer"

        try:
            # Terminate Explorer
            subprocess.run(["taskkill.exe", "/F", "/IM", "explorer.exe"], capture_output=True, timeout=5)
            time.sleep(1.0)

            count = 0
            if old_icon_cache.exists():
                try:
                    old_icon_cache.unlink()
                    count += 1
                except Exception:
                    pass

            if new_icon_dir.exists():
                for f in new_icon_dir.glob("iconcache_*.db"):
                    try:
                        f.unlink()
                        count += 1
                    except Exception:
                        pass

            # Relaunch Explorer
            subprocess.Popen(["explorer.exe"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            return True, f"تم حذف {count} من قواعد بيانات كاش الأيقونات، وسيقوم Windows بإعادة بنائها بصور سليمة."
        except Exception as e:
            subprocess.Popen(["explorer.exe"])
            return False, f"فشل إعادة بناء كاش الأيقونات: {e}"

    @staticmethod
    def open_folder_options():
        """Opens native Windows Folder Options control panel applet."""
        try:
            subprocess.Popen(["control.exe", "folders"])
        except Exception:
            pass
