# -*- coding: utf-8 -*-
"""
SINAX Windows Startup Items Manager
Manages applications and tasks configured to run at Windows boot:
- Reads HKCU / HKLM / WOW6432Node Run keys and Startup folders
- Non-destructive toggle (Enable / Disable) via Windows standard StartupApproved binary flags
- Broken entry detection (checks if target executable actually exists)
- Automatic JSON snapshot backup before any changes
"""

import json
import os
import re
import shlex
import time
import winreg
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import get_logger

logger = get_logger("startup_service")

# Registry Paths
RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APPROVED_RUN = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
STARTUP_APPROVED_FOLDER = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"


@dataclass
class StartupItem:
    id: str
    name: str
    command: str
    exe_path: str
    location_type: str          # "registry_user", "registry_machine", "registry_wow64", "folder_user", "folder_common"
    location_label_ar: str
    is_enabled: bool = True
    is_broken: bool = False
    is_publisher_verified: bool = False
    file_size: int = 0
    raw_reg_key: str = ""
    raw_reg_hive: str = ""      # "HKCU" or "HKLM"
    file_path: Optional[str] = None


class StartupService:
    """Provides safe reading, toggling, and backup of Windows startup entries."""

    @staticmethod
    def _extract_exe_path(command: str) -> str:
        """Extract valid executable path from a complex startup command line."""
        cmd = command.strip()
        if not cmd:
            return ""

        # Check quoted string: "C:\Path\To\app.exe" --arg
        match = re.match(r'^"([^"]+)"', cmd)
        if match:
            return match.group(1)

        # Unquoted: try finding existing file path by tokenizing
        tokens = cmd.split()
        candidate = ""
        for token in tokens:
            candidate = f"{candidate} {token}".strip() if candidate else token
            if os.path.isfile(candidate) or candidate.lower().endswith(".exe"):
                return candidate

        return tokens[0] if tokens else ""

    @staticmethod
    def _is_approved(hive, approved_path: str, value_name: str) -> bool:
        """Check Windows StartupApproved binary flag. 0x02 = Enabled, 0x03 = Disabled."""
        try:
            with winreg.OpenKey(hive, approved_path, 0, winreg.KEY_READ) as key:
                data, val_type = winreg.QueryValueEx(key, value_name)
                if val_type == winreg.REG_BINARY and len(data) > 0:
                    # First byte: 0x02 = enabled, 0x03 = disabled
                    return data[0] != 3
        except OSError:
            pass
        # Default is enabled if not found in StartupApproved
        return True

    @staticmethod
    def _set_approved_state(hive, approved_path: str, value_name: str, enable: bool) -> bool:
        """Set Windows StartupApproved binary flag non-destructively."""
        try:
            with winreg.CreateKeyEx(hive, approved_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                existing_data = bytearray(b"\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
                try:
                    data, _ = winreg.QueryValueEx(key, value_name)
                    if isinstance(data, (bytes, bytearray)) and len(data) >= 1:
                        existing_data = bytearray(data)
                except OSError:
                    pass

                existing_data[0] = 0x02 if enable else 0x03
                winreg.SetValueEx(key, value_name, 0, winreg.REG_BINARY, bytes(existing_data))
                return True
        except Exception as e:
            logger.error(f"Failed to set StartupApproved flag for {value_name}: {e}")
            return False

    @classmethod
    def list_startup_items(cls) -> List[StartupItem]:
        """Query all Windows startup entries from registry and startup folders."""
        items: List[StartupItem] = []

        # 1. HKCU Run
        cls._query_registry_run(
            hive=winreg.HKEY_CURRENT_USER,
            hive_name="HKCU",
            path=RUN_PATH,
            loc_type="registry_user",
            loc_ar="سجل النظام (المستخدم الحالي)",
            items=items
        )

        # 2. HKLM Run
        cls._query_registry_run(
            hive=winreg.HKEY_LOCAL_MACHINE,
            hive_name="HKLM",
            path=RUN_PATH,
            loc_type="registry_machine",
            loc_ar="سجل النظام (كافة المستخدمين)",
            items=items
        )

        # 3. HKLM WOW6432Node Run
        cls._query_registry_run(
            hive=winreg.HKEY_LOCAL_MACHINE,
            hive_name="HKLM",
            path=r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
            loc_type="registry_wow64",
            loc_ar="سجل النظام (تطبيقات 32-بت)",
            items=items
        )

        # 4. User Startup Folder
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            user_startup = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            cls._query_startup_folder(user_startup, "folder_user", "مجلد بدء التشغيل (المستخدم الحالي)", items)

        # 5. Common Startup Folder
        program_data = os.environ.get("ProgramData", "C:\\ProgramData")
        if program_data:
            common_startup = os.path.join(program_data, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
            cls._query_startup_folder(common_startup, "folder_common", "مجلد بدء التشغيل العام", items)

        return items

    @classmethod
    def _query_registry_run(
        cls, hive, hive_name: str, path: str, loc_type: str, loc_ar: str, items: List[StartupItem]
    ):
        """Read registry Run key."""
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                idx = 0
                while True:
                    try:
                        val_name, val_data, _ = winreg.EnumValue(key, idx)
                        idx += 1
                        if not val_name:
                            continue

                        cmd_str = str(val_data)
                        exe_path = cls._extract_exe_path(cmd_str)
                        is_broken = bool(exe_path and not os.path.exists(exe_path))

                        # Check enabled state from HKCU StartupApproved
                        is_enabled = cls._is_approved(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_RUN, val_name)

                        f_size = 0
                        if exe_path and os.path.exists(exe_path):
                            try:
                                f_size = os.path.getsize(exe_path)
                            except OSError:
                                pass

                        items.append(StartupItem(
                            id=f"{hive_name}_{val_name}",
                            name=val_name,
                            command=cmd_str,
                            exe_path=exe_path,
                            location_type=loc_type,
                            location_label_ar=loc_ar,
                            is_enabled=is_enabled,
                            is_broken=is_broken,
                            file_size=f_size,
                            raw_reg_key=path,
                            raw_reg_hive=hive_name
                        ))
                    except OSError:
                        break
        except OSError:
            pass

    @classmethod
    def _query_startup_folder(cls, folder_path: str, loc_type: str, loc_ar: str, items: List[StartupItem]):
        """Scan Windows Startup directory shortcuts."""
        if not os.path.exists(folder_path):
            return

        try:
            for fname in os.listdir(folder_path):
                if fname.lower() == "desktop.ini":
                    continue
                fp = os.path.join(folder_path, fname)
                is_enabled = cls._is_approved(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_FOLDER, fname)
                f_size = 0
                try:
                    f_size = os.path.getsize(fp)
                except OSError:
                    pass

                items.append(StartupItem(
                    id=f"folder_{fname}",
                    name=fname,
                    command=fp,
                    exe_path=fp,
                    location_type=loc_type,
                    location_label_ar=loc_ar,
                    is_enabled=is_enabled,
                    is_broken=not os.path.exists(fp),
                    file_size=f_size,
                    file_path=fp
                ))
        except Exception as e:
            logger.debug(f"Error scanning startup folder {folder_path}: {e}")

    @classmethod
    def backup_startup_state(cls, backup_dir: Optional[str] = None) -> str:
        """Create a full JSON snapshot of all current startup entries."""
        if not backup_dir:
            from app.core.config import get_data_dir
            backup_dir = str(get_data_dir() / "startup_backups")

        os.makedirs(backup_dir, exist_ok=True)
        items = cls.list_startup_items()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"startup_backup_{timestamp}.json")

        data = {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "items": [asdict(item) for item in items]
        }

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Startup items backed up to: {backup_file}")
        return backup_file

    @classmethod
    def toggle_item(cls, item: StartupItem, enable: bool) -> tuple[bool, str]:
        """Enable or disable startup item via official StartupApproved binary flags."""
        # Backup first
        try:
            cls.backup_startup_state()
        except Exception as e:
            logger.warning(f"Failed to create startup backup: {e}")

        # If it's a folder item
        if "folder" in item.location_type:
            res = cls._set_approved_state(
                winreg.HKEY_CURRENT_USER,
                STARTUP_APPROVED_FOLDER,
                item.name,
                enable
            )
        else:
            res = cls._set_approved_state(
                winreg.HKEY_CURRENT_USER,
                STARTUP_APPROVED_RUN,
                item.name,
                enable
            )

        if res:
            item.is_enabled = enable
            action_text = "تفعيل" if enable else "تعطيل"
            return True, f"تم {action_text} تشغيل '{item.name}' مع بدء ويندوز."
        else:
            return False, f"تعذر تعديل حالة العنصر '{item.name}'."
