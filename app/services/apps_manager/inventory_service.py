# -*- coding: utf-8 -*-
"""
SINAX Installed Application Inventory & Aggregator Service
Coordinates Registry, MSIX, and WinGet providers with intelligent deduplication,
cross-referencing (running processes, startup entries), filtering, and sorting.
"""

import logging
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional
import psutil

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.providers.msix_provider import MsixProvider
from app.services.apps_manager.providers.registry_provider import RegistryProvider
from app.services.apps_manager.providers.winget_provider import WingetProvider
from app.services.system_storage.startup_service import StartupService

logger = logging.getLogger("SINAX.apps_manager.inventory_service")


class InventoryService:
    """Master aggregator for all installed applications."""

    _cached_apps: List[InstalledApp] = []
    _last_refresh_time: float = 0.0
    CACHE_TTL_SECONDS = 300.0  # 5 minutes

    @classmethod
    def get_all_apps(cls, force_refresh: bool = False, progress_cb: Optional[Callable[[str], None]] = None) -> List[InstalledApp]:
        """Returns unified and correlated installed applications."""
        now = time.time()
        if not force_refresh and cls._cached_apps and (now - cls._last_refresh_time) < cls.CACHE_TTL_SECONDS:
            return list(cls._cached_apps)

        if progress_cb:
            progress_cb("جرد البرامج من سجل ويندوز (Registry)...")
        reg_apps = RegistryProvider.get_installed_apps()

        if progress_cb:
            progress_cb("جرد حزم MSIX وتطبيقات متجر مايكروسوفت...")
        msix_apps = MsixProvider.get_installed_apps()

        if progress_cb:
            progress_cb("فحص تحديثات WinGet وحزم النظام...")
        winget_available = WingetProvider.is_available()
        winget_packages = WingetProvider.get_installed_packages() if winget_available else []
        winget_upgrades = WingetProvider.get_available_upgrades() if winget_available else {}
        winget_pins = set(p.lower() for p in WingetProvider.get_pins()) if winget_available else set()

        if progress_cb:
            progress_cb("دمج ومطابقة مصادر البرامج...")
        merged_apps = cls._correlate_and_deduplicate(reg_apps, msix_apps, winget_packages, winget_upgrades, winget_pins)

        if progress_cb:
            progress_cb("فحص العمليات النشطة وعناصر بدء التشغيل...")
        cls._enrich_with_runtime_data(merged_apps)

        cls._cached_apps = merged_apps
        cls._last_refresh_time = now
        logger.info(f"InventoryService refreshed successfully with {len(merged_apps)} total applications.")
        return list(cls._cached_apps)

    @classmethod
    def get_summary_stats(cls, apps: Optional[List[InstalledApp]] = None) -> Dict[str, Any]:
        """Calculates dashboard diagnostic counters."""
        app_list = apps if apps is not None else cls._cached_apps
        if not app_list:
            app_list = cls.get_all_apps(force_refresh=False)

        total_apps = len(app_list)
        updates_count = sum(1 for a in app_list if a.update_available)
        total_size_bytes = sum(a.effective_size_bytes for a in app_list)
        startup_count = sum(1 for a in app_list if a.is_startup)
        large_count = sum(1 for a in app_list if a.effective_size_bytes >= (1024 * 1024 * 1024))  # >= 1GB
        broken_count = sum(1 for a in app_list if a.is_broken)

        return {
            "total_apps": total_apps,
            "updates_count": updates_count,
            "total_size_bytes": total_size_bytes,
            "startup_count": startup_count,
            "large_count": large_count,
            "broken_count": broken_count,
        }

    @classmethod
    def filter_apps(
        cls,
        apps: List[InstalledApp],
        query: str = "",
        category: str = "all",
        sort_by: str = "name",
        sort_desc: bool = False,
    ) -> List[InstalledApp]:
        """Applies real-time search, category filtering, and sorting."""
        filtered = apps

        # 1. Text Search
        if query and query.strip():
            q = query.strip().lower()
            filtered = [
                a for a in filtered
                if q in a.name.lower()
                or q in a.publisher.lower()
                or (a.package_id and q in a.package_id.lower())
                or q in a.version.lower()
            ]

        # 2. Category Filter
        if category == "desktop":
            filtered = [a for a in filtered if a.source in ("exe", "msi") and not a.is_system_component]
        elif category == "store":
            filtered = [a for a in filtered if a.source in ("store", "msix")]
        elif category == "msi":
            filtered = [a for a in filtered if a.source == "msi"]
        elif category == "exe":
            filtered = [a for a in filtered if a.source == "exe"]
        elif category == "64bit":
            filtered = [a for a in filtered if a.architecture == "x64"]
        elif category == "32bit":
            filtered = [a for a in filtered if a.architecture == "x86"]
        elif category == "updates":
            filtered = [a for a in filtered if a.update_available]
        elif category == "large":
            filtered = [a for a in filtered if a.effective_size_bytes >= (1024 * 1024 * 1024)]
        elif category == "startup":
            filtered = [a for a in filtered if a.is_startup]
        elif category == "running":
            filtered = [a for a in filtered if a.is_running]
        elif category == "broken":
            filtered = [a for a in filtered if a.is_broken]
        elif category == "system":
            filtered = [a for a in filtered if a.is_system_component or a.is_runtime_or_driver]

        # 3. Sorting
        def sort_key(app: InstalledApp):
            if sort_by == "size":
                return app.effective_size_bytes
            elif sort_by == "install_date":
                return app.install_date or ""
            elif sort_by == "publisher":
                return app.publisher.lower()
            elif sort_by == "version":
                return app.version.lower()
            elif sort_by == "update":
                return 1 if app.update_available else 0
            return app.name.lower()

        filtered = sorted(filtered, key=sort_key, reverse=sort_desc)
        return filtered

    @classmethod
    def _correlate_and_deduplicate(
        cls,
        reg_apps: List[InstalledApp],
        msix_apps: List[InstalledApp],
        winget_packages: List[Dict[str, str]],
        winget_upgrades: Dict[str, Dict[str, str]],
        winget_pins: set,
    ) -> List[InstalledApp]:
        """Merges disparate application records avoiding duplicates."""
        combined: Dict[str, InstalledApp] = {}
        name_to_id_map: Dict[str, str] = {}

        # 1. Index Registry Apps first (rich in native uninstall metadata)
        for app in reg_apps:
            combined[app.id] = app
            clean_name = cls._normalize_name(app.name)
            name_to_id_map[clean_name] = app.id

        # 2. Correlate with WinGet Packages
        for wp in winget_packages:
            w_name = wp.get("Name", "")
            w_id = wp.get("Id", "")
            w_ver = wp.get("Version", "")
            w_src = wp.get("Source", "").lower()

            clean_w_name = cls._normalize_name(w_name)
            matched_app_id = name_to_id_map.get(clean_w_name)

            if matched_app_id and matched_app_id in combined:
                # Merge into existing registry entry
                app = combined[matched_app_id]
                if w_id and not w_id.startswith("ARP\\"):
                    app.package_id = w_id
                if w_src == "winget":
                    app.source = "winget"
                if w_ver and (app.version == "غير محدد" or not app.version):
                    app.version = w_ver
            else:
                # Only add as new if not an internal ARP entry
                if not w_id.startswith("ARP\\") and not w_id.startswith("MSIX\\"):
                    new_id = InstalledApp.generate_id(w_name, "", w_id)
                    combined[new_id] = InstalledApp(
                        id=new_id,
                        name=w_name,
                        version=w_ver or "1.0",
                        publisher="WinGet Package",
                        package_id=w_id,
                        source="winget",
                        uninstall_type="winget",
                        can_uninstall=True,
                    )
                    name_to_id_map[clean_w_name] = new_id

        # 3. Add MSIX Apps
        for ma in msix_apps:
            clean_ma_name = cls._normalize_name(ma.name)
            matched_app_id = name_to_id_map.get(clean_ma_name)
            if matched_app_id and matched_app_id in combined:
                app = combined[matched_app_id]
                app.package_full_name = ma.package_full_name
                app.can_reset = ma.can_reset
            else:
                combined[ma.id] = ma
                name_to_id_map[clean_ma_name] = ma.id

        # 4. Attach Available Upgrades and Pins
        for app in combined.values():
            # Check by package_id
            upgrade_info = None
            if app.package_id and app.package_id.lower() in winget_upgrades:
                upgrade_info = winget_upgrades[app.package_id.lower()]
            elif app.name.lower() in winget_upgrades:
                upgrade_info = winget_upgrades[app.name.lower()]

            if upgrade_info:
                avail_ver = upgrade_info.get("Available", "").strip()
                if avail_ver and avail_ver != app.version:
                    app.update_available = True
                    app.available_version = avail_ver

            if app.package_id and app.package_id.lower() in winget_pins:
                app.is_pinned = True

        return list(combined.values())

    @classmethod
    def _enrich_with_runtime_data(cls, apps: List[InstalledApp]):
        """Detects running processes and startup integration."""
        # 1. Scan running processes
        running_exes = {}  # exe_name_lower -> list of pids
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                p_name = (proc.info.get("name") or "").lower()
                p_pid = proc.info.get("pid")
                if p_name and p_pid:
                    running_exes.setdefault(p_name, []).append(p_pid)
                p_exe = proc.info.get("exe")
                if p_exe:
                    running_exes.setdefault(os.path.normpath(p_exe).lower(), []).append(p_pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 2. Scan startup items
        startup_names = set()
        try:
            startup_items = StartupService.get_startup_items()
            for s in startup_items:
                startup_names.add(cls._normalize_name(s.name))
                if s.command:
                    cand = os.path.basename(s.command.strip().strip('"')).lower()
                    startup_names.add(cand)
        except Exception as e:
            logger.debug(f"Could not load startup items: {e}")

        # 3. Match against apps
        for app in apps:
            # Check running
            pids = []
            if app.main_executable:
                norm_exe = os.path.normpath(app.main_executable).lower()
                if norm_exe in running_exes:
                    pids.extend(running_exes[norm_exe])
                exe_base = os.path.basename(norm_exe)
                if exe_base in running_exes:
                    pids.extend(running_exes[exe_base])
            else:
                # Approximate by app name + .exe
                cand_base = f"{re.sub(r'[^a-zA-Z0-9]', '', app.name).lower()}.exe"
                if cand_base in running_exes:
                    pids.extend(running_exes[cand_base])

            if pids:
                app.is_running = True
                app.running_pids = sorted(list(set(pids)))

            # Check startup
            norm_name = cls._normalize_name(app.name)
            if norm_name in startup_names:
                app.is_startup = True

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Strips architecture suffixes, versions, and extra whitespace for fuzzy matching."""
        s = name.lower()
        # Remove (x86), (x64), 32-bit, 64-bit, v1.0, etc.
        s = re.sub(r"\(x(86|64)\)|32-bit|64-bit|x86|x64", "", s)
        s = re.sub(r"v?\d+(\.\d+)+", "", s)
        s = re.sub(r"[^a-zA-Z0-9\u0600-\u06FF]", "", s)
        return s.strip()
