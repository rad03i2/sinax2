# -*- coding: utf-8 -*-
"""
SINAX MSIX / AppX Package Provider
Queries modern Windows Universal / Store packages via PowerShell.
"""

import json
import logging
import os
import subprocess
from typing import List, Optional

from app.services.apps_manager.app_model import InstalledApp

logger = logging.getLogger("SINAX.apps_manager.msix_provider")


class MsixProvider:
    """Discovers modern Windows packages (MSIX, AppX, Store Apps)."""

    @classmethod
    def get_installed_apps(cls) -> List[InstalledApp]:
        """Queries non-framework AppX / MSIX packages via PowerShell."""
        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command",
            "Get-AppxPackage | Where-Object { -not $_.IsFramework } | "
            "Select-Object Name, PackageFullName, Version, Publisher, InstallLocation, NonRemovable | "
            "ConvertTo-Json -Compress"
        ]

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=12,
                startupinfo=startupinfo,
            )

            if res.returncode != 0 or not res.stdout.strip():
                logger.warning(f"Get-AppxPackage returned code {res.returncode}: {res.stderr}")
                return []

            data = json.loads(res.stdout)
            if isinstance(data, dict):
                data = [data]

            apps: List[InstalledApp] = []
            for item in data:
                app = cls._parse_package(item)
                if app:
                    apps.append(app)

            logger.info(f"MsixProvider discovered {len(apps)} MSIX/AppX packages.")
            return apps

        except subprocess.TimeoutExpired:
            logger.warning("Get-AppxPackage timed out after 12s.")
            return []
        except Exception as e:
            logger.error(f"Error querying MSIX packages: {e}")
            return []

    @classmethod
    def _parse_package(cls, item: dict) -> Optional[InstalledApp]:
        name = item.get("Name")
        package_full_name = item.get("PackageFullName")
        if not name or not package_full_name:
            return None

        # Filter out purely internal Windows system containers with raw GUID names
        if len(name) == 36 and name.count("-") == 4:
            # Internal GUID-named system component
            return None

        version = str(item.get("Version") or "1.0.0.0")
        raw_publisher = str(item.get("Publisher") or "")
        publisher = cls._clean_publisher(raw_publisher)
        install_loc = item.get("InstallLocation")
        non_removable = bool(item.get("NonRemovable", False))

        is_sys = non_removable or (install_loc and "systemapps" in install_loc.lower())
        source = "msix" if not is_sys else "system"

        display_name = cls._humanize_name(name)
        app_id = InstalledApp.generate_id(display_name, publisher, package_full_name)

        return InstalledApp(
            id=app_id,
            name=display_name,
            version=version,
            publisher=publisher,
            architecture="x64",
            install_location=install_loc,
            installed_size=0,
            source="store" if not is_sys else "msix",
            package_full_name=package_full_name,
            package_id=name,
            is_system_component=is_sys,
            can_uninstall=not is_sys,
            can_repair=False,
            can_reset=not is_sys,  # Support Reset-AppxPackage
            uninstall_type="msix",
        )

    @staticmethod
    def _clean_publisher(raw: str) -> str:
        """Extracts human readable publisher from CN=..., O=..., C=..."""
        if not raw:
            return "Microsoft Corporation"
        for part in raw.split(","):
            part = part.strip()
            if part.startswith("O="):
                return part[2:].strip('"')
            if part.startswith("CN="):
                cn = part[3:].strip('"')
                if not cn.isdigit():
                    return cn
        return "Microsoft Corporation"

    @staticmethod
    def _humanize_name(raw_name: str) -> str:
        """Cleans internal package names into readable titles."""
        # e.g. Microsoft.WindowsTerminal -> Windows Terminal
        if raw_name.startswith("Microsoft."):
            suffix = raw_name[10:]
            # insert space before capital letters if CamelCase
            res = []
            for i, ch in enumerate(suffix):
                if ch.isupper() and i > 0 and not suffix[i - 1].isupper():
                    res.append(" ")
                res.append(ch)
            cleaned = "".join(res).strip()
            return f"Microsoft {cleaned}"
        return raw_name
