# -*- coding: utf-8 -*-
"""
SINAX WinGet Provider
Interacts with the native Windows Package Manager (winget CLI).
Provides package discovery, upgrade detection, pinning, and export/import.
"""

import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SINAX.apps_manager.winget_provider")


class WingetProvider:
    """Manages interactions with WinGet CLI."""

    _is_available_cache: Optional[bool] = None

    @classmethod
    def is_available(cls) -> bool:
        """Checks if WinGet CLI is installed and responsive on the system."""
        if cls._is_available_cache is not None:
            return cls._is_available_cache

        winget_path = shutil.which("winget")
        if not winget_path:
            # Check default WindowsApps location
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            cand = os.path.join(local_app_data, r"Microsoft\WindowsApps\winget.exe")
            if os.path.exists(cand):
                winget_path = cand

        if not winget_path:
            cls._is_available_cache = False
            return False

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            res = subprocess.run(
                [winget_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                startupinfo=startupinfo,
            )
            cls._is_available_cache = (res.returncode == 0)
        except Exception as e:
            logger.debug(f"WinGet availability check failed: {e}")
            cls._is_available_cache = False

        return cls._is_available_cache

    @classmethod
    def get_installed_packages(cls) -> List[Dict[str, str]]:
        """Parses `winget list` output into structured package records."""
        if not cls.is_available():
            return []

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            res = subprocess.run(
                ["winget", "list", "--accept-source-agreements"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=25,
                startupinfo=startupinfo,
            )
            if res.returncode != 0:
                logger.warning(f"winget list returned code {res.returncode}")
                return []

            return cls._parse_fixed_width_table(res.stdout)
        except Exception as e:
            logger.error(f"Failed to execute winget list: {e}")
            return []

    @classmethod
    def get_available_upgrades(cls) -> Dict[str, Dict[str, str]]:
        """
        Runs `winget upgrade` to discover all applications with pending updates.
        Returns a dictionary keyed by Package ID (lowercased) mapping to update details.
        """
        if not cls.is_available():
            return {}

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            res = subprocess.run(
                ["winget", "upgrade", "--accept-source-agreements"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=25,
                startupinfo=startupinfo,
            )

            # returncode 0 = updates found or clean exit; returncode 2 = no updates
            records = cls._parse_fixed_width_table(res.stdout)
            upgrades = {}
            for r in records:
                pkg_id = r.get("Id", "")
                avail = r.get("Available", "")
                if pkg_id and avail:
                    upgrades[pkg_id.lower()] = r
                    # Also key by app name for fallback matching
                    if "Name" in r:
                        upgrades[r["Name"].lower()] = r

            logger.info(f"WinGet discovered {len(upgrades)} upgradeable packages.")
            return upgrades
        except Exception as e:
            logger.error(f"Failed to check winget upgrade: {e}")
            return {}

    @classmethod
    def get_pins(cls) -> List[str]:
        """Returns list of currently pinned Package IDs."""
        if not cls.is_available():
            return []
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

            res = subprocess.run(
                ["winget", "pin", "list"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                startupinfo=startupinfo,
            )
            records = cls._parse_fixed_width_table(res.stdout)
            return [r.get("Id", "") for r in records if r.get("Id")]
        except Exception:
            return []

    @classmethod
    def pin_package(cls, package_id: str) -> bool:
        """Pins a package version to prevent automated upgrades."""
        if not cls.is_available() or not package_id:
            return False
        try:
            res = subprocess.run(
                ["winget", "pin", "add", "--id", package_id, "--blocking"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def unpin_package(cls, package_id: str) -> bool:
        """Removes a pin from a package."""
        if not cls.is_available() or not package_id:
            return False
        try:
            res = subprocess.run(
                ["winget", "pin", "remove", "--id", package_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def export_packages(cls, output_json_path: str) -> bool:
        """Exports installed packages into a WinGet-compatible JSON file."""
        if not cls.is_available():
            return False
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
            res = subprocess.run(
                [
                    "winget", "export",
                    "-o", output_json_path,
                    "--accept-source-agreements",
                    "--include-versions"
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            return res.returncode == 0 and os.path.exists(output_json_path)
        except Exception as e:
            logger.error(f"winget export error: {e}")
            return False

    @classmethod
    def _parse_fixed_width_table(cls, stdout: str) -> List[Dict[str, str]]:
        """
        Parses fixed-width column tables produced by WinGet CLI.
        Detects header column boundaries from the dashed separator line.
        """
        lines = stdout.splitlines()
        header_idx = -1
        sep_idx = -1

        for idx, line in enumerate(lines):
            # The separator line consists of series of dashes separated by spaces
            stripped = line.strip()
            if stripped and set(stripped).issubset({"-", " "}) and "---" in stripped:
                sep_idx = idx
                header_idx = idx - 1
                break

        if header_idx < 0 or sep_idx < 0:
            return []

        header_line = lines[header_idx]
        sep_line = lines[sep_idx]

        # Determine column spans from separator line
        # e.g. "----------------------  ----------------  --------"
        spans = []
        in_col = False
        start = 0
        for pos, ch in enumerate(sep_line):
            if ch == "-" and not in_col:
                in_col = True
                start = pos
            elif ch != "-" and in_col:
                in_col = False
                spans.append((start, pos))
        if in_col:
            spans.append((start, len(sep_line)))

        # Extract column names from header_line
        columns = []
        for start, end in spans:
            col_name = header_line[start:end].strip()
            columns.append((col_name, start, end))

        results: List[Dict[str, str]] = []
        for line in lines[sep_idx + 1:]:
            if not line.strip():
                continue
            # Check for summary lines like "14 upgrades available." or "<truncated>"
            if "upgrades available" in line.lower() or "have pins" in line.lower():
                continue

            record = {}
            for idx, (col_name, start, end) in enumerate(columns):
                # For last column, take remaining line
                if idx == len(columns) - 1:
                    val = line[start:].strip() if len(line) > start else ""
                else:
                    val = line[start:end].strip() if len(line) > start else ""
                record[col_name] = val

            if record.get("Name") or record.get("Id"):
                results.append(record)

        return results
