# -*- coding: utf-8 -*-
"""
SINAX Windows Registry Application Provider
Scans 64-bit and 32-bit HKLM and HKCU uninstall keys via native winreg.
"""

import logging
import os
import re
from typing import List, Optional
import winreg

from app.services.apps_manager.app_model import InstalledApp

logger = logging.getLogger("SINAX.apps_manager.registry_provider")

# Known runtime / driver keywords
RUNTIME_KEYWORDS = [
    "visual c++",
    "redistributable",
    ".net runtime",
    ".net framework",
    "asp.net core",
    "directx",
    "driver package",
    "حزمة برامج تشغيل",
    "windows software development kit",
    "vulkan run time",
    "opencl runtime",
]

# Known critical system publishers / keywords
SYSTEM_KEYWORDS = [
    "windows security",
    "windows defender",
    "microsoft windows operating system",
]


class RegistryProvider:
    """Discovers installed software registered in Windows Uninstall Registry."""

    @classmethod
    def get_installed_apps(cls) -> List[InstalledApp]:
        """Scans all primary Windows registry uninstall locations."""
        targets = [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY, "x64"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_32KEY, "x86"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", 0, "current_user"),
        ]

        discovered: List[InstalledApp] = []
        seen_keys = set()

        for hive, subkey_path, flags, arch in targets:
            try:
                with winreg.OpenKey(hive, subkey_path, 0, winreg.KEY_READ | flags) as root_key:
                    num_subkeys = winreg.QueryInfoKey(root_key)[0]
                    for i in range(num_subkeys):
                        try:
                            key_name = winreg.EnumKey(root_key, i)
                            full_reg_path = f"{'HKLM' if hive == winreg.HKEY_LOCAL_MACHINE else 'HKCU'}\\{subkey_path}\\{key_name}"
                            if full_reg_path in seen_keys:
                                continue
                            seen_keys.add(full_reg_path)

                            with winreg.OpenKey(root_key, key_name, 0, winreg.KEY_READ | flags) as app_key:
                                app = cls._parse_key(app_key, key_name, full_reg_path, arch)
                                if app:
                                    discovered.append(app)
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError) as e:
                logger.debug(f"Failed to open registry key {subkey_path}: {e}")

        logger.info(f"RegistryProvider discovered {len(discovered)} applications.")
        return discovered

    @classmethod
    def _parse_key(cls, app_key, key_name: str, full_reg_path: str, default_arch: str) -> Optional[InstalledApp]:
        """Extracts and normalizes application metadata from an open registry key."""
        name = cls._get_reg_value(app_key, "DisplayName")
        if not name or not str(name).strip():
            return None

        name = str(name).strip()
        version = str(cls._get_reg_value(app_key, "DisplayVersion") or "غير محدد").strip()
        publisher = str(cls._get_reg_value(app_key, "Publisher") or "غير معروف").strip()
        install_location = cls._get_reg_value(app_key, "InstallLocation")
        if install_location:
            install_location = os.path.normpath(str(install_location).strip().strip('"'))
            if not os.path.exists(install_location):
                # Check if it was empty string or invalid
                if not install_location:
                    install_location = None

        # Estimated size: stored in KB in registry
        raw_size = cls._get_reg_value(app_key, "EstimatedSize")
        installed_size = 0
        if raw_size and isinstance(raw_size, (int, float)) and raw_size > 0:
            installed_size = int(raw_size) * 1024

        install_date = cls._get_reg_value(app_key, "InstallDate")
        date_reliable = bool(install_date and len(str(install_date).strip()) == 8)

        uninstall_string = cls._get_reg_value(app_key, "UninstallString")
        quiet_uninstall_string = cls._get_reg_value(app_key, "QuietUninstallString")
        modify_path = cls._get_reg_value(app_key, "ModifyPath")
        repair_path = cls._get_reg_value(app_key, "RepairPath")
        display_icon = cls._get_reg_value(app_key, "DisplayIcon")
        help_link = cls._get_reg_value(app_key, "HelpLink")
        url_info_about = cls._get_reg_value(app_key, "URLInfoAbout")

        system_component = bool(cls._get_reg_value(app_key, "SystemComponent") == 1)
        windows_installer = bool(cls._get_reg_value(app_key, "WindowsInstaller") == 1)

        # Check MSI GUID
        is_guid = bool(re.match(r"^\{[0-9a-fA-F\-]{36}\}$", key_name))
        is_msi = windows_installer or is_guid
        product_code = key_name if is_guid else None

        source = "msi" if is_msi else "exe"
        uninstall_type = "msi" if is_msi else "custom"
        can_repair = bool(is_msi or modify_path or repair_path)

        # Classify Runtimes & Drivers
        name_lower = name.lower()
        is_runtime_or_driver = any(k in name_lower for k in RUNTIME_KEYWORDS)
        is_sys = system_component or any(k in name_lower for k in SYSTEM_KEYWORDS)

        # Check Broken Entry
        is_broken = False
        if uninstall_string:
            exe_cand = cls._extract_executable_path(uninstall_string)
            if exe_cand and not os.path.exists(exe_cand):
                # Uninstaller binary missing
                if not install_location or not os.path.exists(install_location):
                    is_broken = True

        # Candidate main executable
        main_executable = None
        if display_icon:
            icon_cand = cls._extract_executable_path(display_icon)
            if icon_cand and icon_cand.lower().endswith(".exe") and os.path.exists(icon_cand):
                main_executable = icon_cand

        app_id = InstalledApp.generate_id(name, publisher, install_location or key_name)

        return InstalledApp(
            id=app_id,
            name=name,
            version=version,
            publisher=publisher,
            architecture="x64" if default_arch == "x64" else ("x86" if default_arch == "x86" else "x64"),
            install_location=install_location,
            main_executable=main_executable,
            installed_size=installed_size,
            install_date=str(install_date).strip() if install_date else None,
            date_reliable=date_reliable,
            source=source,
            product_code=product_code,
            uninstall_string=str(uninstall_string).strip() if uninstall_string else None,
            quiet_uninstall_string=str(quiet_uninstall_string).strip() if quiet_uninstall_string else None,
            modify_path=str(modify_path).strip() if modify_path else None,
            repair_path=str(repair_path).strip() if repair_path else None,
            display_icon=str(display_icon).strip() if display_icon else None,
            help_link=str(help_link).strip() if help_link else None,
            url_info_about=str(url_info_about).strip() if url_info_about else None,
            registry_key_path=full_reg_path,
            is_system_component=is_sys,
            is_runtime_or_driver=is_runtime_or_driver,
            is_broken=is_broken,
            can_uninstall=not is_sys and not is_runtime_or_driver,
            can_repair=can_repair,
            uninstall_type=uninstall_type,
        )

    @staticmethod
    def _get_reg_value(key, name: str) -> Optional[any]:
        """Safely queries a registry value."""
        try:
            val, _ = winreg.QueryValueEx(key, name)
            return val
        except (OSError, FileNotFoundError):
            return None

    @staticmethod
    def _extract_executable_path(cmd_str: str) -> Optional[str]:
        """Extracts candidate executable path from a Windows command line string."""
        if not cmd_str:
            return None
        s = cmd_str.strip()
        # If wrapped in quotes: "C:\path\to.exe" /args
        if s.startswith('"'):
            end_q = s.find('"', 1)
            if end_q != -1:
                return s[1:end_q].strip()
        # If separated by comma (e.g. DisplayIcon "C:\path\to.exe,0")
        if "," in s:
            parts = s.split(",", 1)
            cand = parts[0].strip().strip('"')
            if cand.lower().endswith((".exe", ".ico", ".dll")):
                return cand
        # First token before space
        tokens = s.split()
        if tokens:
            cand = tokens[0].strip().strip('"')
            if cand.lower().endswith((".exe", ".ico")):
                return cand
        return None
