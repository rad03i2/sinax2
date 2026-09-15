# -*- coding: utf-8 -*-
"""
SINAX Installed Application Unified Data Model
Represents any desktop, Store, MSI, or WinGet application discovered on Windows.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
from typing import Any, Dict, List, Optional


@dataclass
class InstalledApp:
    """Unified application entity."""
    # Identification
    id: str  # Deterministic unique hash
    name: str  # Display name
    version: str = "Unknown"  # Version string
    publisher: str = "Unknown"  # Vendor / Publisher
    architecture: str = "x64"  # x64, x86, ARM64, Neutral

    # Location & Sizes
    install_location: Optional[str] = None
    main_executable: Optional[str] = None
    installed_size: int = 0  # Registered size in bytes (from EstimatedSize * 1024)
    calculated_size: Optional[int] = None  # True scanned disk size in bytes

    # Dates
    install_date: Optional[str] = None  # YYYYMMDD or formatted string
    date_reliable: bool = False  # False if inferred or changed by patch

    # Source & IDs
    source: str = "exe"  # winget, store, msi, exe, msix, unknown
    package_id: Optional[str] = None  # e.g. VideoLAN.VLC
    product_code: Optional[str] = None  # MSI GUID e.g. {12345...}
    package_full_name: Optional[str] = None  # MSIX PackageFullName

    # Commands
    uninstall_string: Optional[str] = None
    quiet_uninstall_string: Optional[str] = None
    modify_path: Optional[str] = None
    repair_path: Optional[str] = None
    display_icon: Optional[str] = None
    help_link: Optional[str] = None
    url_info_about: Optional[str] = None
    registry_key_path: Optional[str] = None

    # Status Flags
    update_available: bool = False
    available_version: Optional[str] = None
    is_system_component: bool = False
    is_runtime_or_driver: bool = False  # VC++ redist, .NET, DirectX, driver
    is_broken: bool = False  # Uninstaller or executable missing
    is_running: bool = False  # Currently running process found
    running_pids: List[int] = field(default_factory=list)
    is_startup: bool = False  # Runs at Windows startup
    is_pinned: bool = False  # WinGet update pinned

    # Capabilities
    can_uninstall: bool = True
    can_repair: bool = False
    can_reset: bool = False
    uninstall_type: str = "custom"  # msi, msix, winget, inno, nsis, custom

    @staticmethod
    def generate_id(name: str, publisher: str = "", location: str = "") -> str:
        """Generates a stable unique hash identifier for an application."""
        raw = f"{name.strip().lower()}|{publisher.strip().lower()}|{location.strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

    @property
    def display_size(self) -> str:
        """Returns best human-readable size string (calculated if available, else installed)."""
        sz = self.calculated_size if self.calculated_size is not None and self.calculated_size > 0 else self.installed_size
        return format_bytes(sz)

    @property
    def effective_size_bytes(self) -> int:
        """Returns the best known size in bytes."""
        if self.calculated_size is not None and self.calculated_size > 0:
            return self.calculated_size
        return self.installed_size

    @property
    def formatted_install_date(self) -> str:
        """Formats the install date into a readable string or 'غير مؤكد'."""
        if not self.install_date:
            return "غير معروف"
        s = str(self.install_date).strip()
        # Common registry format YYYYMMDD
        if len(s) == 8 and s.isdigit():
            try:
                dt = datetime.strptime(s, "%Y%m%d")
                suffix = "" if self.date_reliable else " (تقريبي)"
                return f"{dt.strftime('%Y-%m-%d')}{suffix}"
            except Exception:
                pass
        return s

    def to_dict(self) -> Dict[str, Any]:
        """Serializes entity to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InstalledApp":
        """Deserializes entity from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def format_bytes(b: int) -> str:
    """Formats bytes into human readable format."""
    if not b or b <= 0:
        return "غير معروف"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024.0:
            return f"{b:.1f} {unit}" if unit in ["MB", "GB", "TB"] else f"{int(b)} {unit}"
        b /= 1024.0
    return f"{b:.1f} PB"
