# -*- coding: utf-8 -*-
"""
SINAX System Micro Utilities
Quick access to Windows environment variables, path expansion, PATH duplicate inspector,
computer identity shortcuts, and special folder openers.
"""

import os
from pathlib import Path
import socket
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


SPECIAL_FOLDERS = {
    "Temp": os.environ.get("TEMP", ""),
    "AppData (Roaming)": os.environ.get("APPDATA", ""),
    "AppData (Local)": os.environ.get("LOCALAPPDATA", ""),
    "ProgramData": os.environ.get("ProgramData", "C:\\ProgramData"),
    "Startup": os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"),
    "Desktop": os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
    "Downloads": os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
    "Documents": os.path.join(os.environ.get("USERPROFILE", ""), "Documents"),
    "Pictures": os.path.join(os.environ.get("USERPROFILE", ""), "Pictures"),
}


class SystemTools:
    """Micro utilities for Windows environment queries and folder navigation."""

    @staticmethod
    def get_system_quick_identifiers() -> Dict[str, str]:
        """Returns standard computer identifiers for quick copying."""
        comp_name = os.environ.get("COMPUTERNAME", socket.gethostname())
        user_name = os.environ.get("USERNAME", "")

        # Local IP (non-blocking)
        local_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass

        return {
            "computer_name": comp_name,
            "username": user_name,
            "local_ip": local_ip,
            "windows_version": sys.getwindowsversion().platform if hasattr(sys, "getwindowsversion") else "Windows",
            "os_build": str(getattr(sys.getwindowsversion(), "build", 0)),
        }

    @staticmethod
    def get_environment_variables() -> List[Tuple[str, str]]:
        """Returns sorted list of all active environment variables."""
        return sorted([(k, v) for k, v in os.environ.items()], key=lambda x: x[0].upper())

    @staticmethod
    def expand_env_string(env_str: str) -> str:
        """Expands variables like %TEMP% or %USERPROFILE% into resolved disk paths."""
        return os.path.expandvars(env_str.strip())

    @staticmethod
    def inspect_path_variable() -> Dict[str, Any]:
        """Splits Windows PATH into individual entries, checking existence and detecting duplicates."""
        raw_path = os.environ.get("PATH", "")
        entries = [e.strip() for e in raw_path.split(";") if e.strip()]

        seen = set()
        duplicates = []
        valid_entries = []
        missing_entries = []

        for e in entries:
            key = e.lower()
            if key in seen:
                duplicates.append(e)
            else:
                seen.add(key)

            if os.path.exists(e):
                valid_entries.append(e)
            else:
                missing_entries.append(e)

        return {
            "total_entries": len(entries),
            "valid_count": len(valid_entries),
            "missing_count": len(missing_entries),
            "duplicate_count": len(duplicates),
            "entries": entries,
            "missing": missing_entries,
            "duplicates": duplicates,
        }

    @staticmethod
    def open_special_folder(folder_name: str) -> bool:
        """Opens a special system folder in Windows File Explorer."""
        path = SPECIAL_FOLDERS.get(folder_name)
        if path and os.path.isdir(path):
            try:
                os.startfile(path)
                return True
            except Exception:
                pass
        return False
