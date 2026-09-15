# -*- coding: utf-8 -*-
"""
SINAX Motherboard & BIOS Service (خدمة اللوحة الأم والـ BIOS وUEFI)
Queries motherboard hardware details (Win32_BaseBoard), BIOS/UEFI firmware (Win32_BIOS),
detects UEFI vs Legacy mode, Secure Boot status, and TPM security hardware status.
"""

import subprocess
import winreg
from typing import Any, Dict, Optional, Tuple

from app.core.logger import get_logger
from app.services.devices.hardware_models import BiosInfo, MotherboardInfo

logger = get_logger("motherboard_bios_service")


class MotherboardBiosService:
    """Manages motherboard and BIOS firmware queries."""

    _cached_mb: Optional[MotherboardInfo] = None
    _cached_bios: Optional[BiosInfo] = None

    @classmethod
    def get_motherboard_info(cls, force_refresh: bool = False) -> MotherboardInfo:
        """Queries motherboard manufacturer, product, version, and serial."""
        if cls._cached_mb is not None and not force_refresh:
            return cls._cached_mb

        mb = MotherboardInfo()
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            for b in wmi.InstancesOf("Win32_BaseBoard"):
                mb.manufacturer = getattr(b, "Manufacturer", "غير محدد").strip()
                mb.product = getattr(b, "Product", "غير محدد").strip()
                mb.version = getattr(b, "Version", "غير متوفر").strip()
                mb.serial_number = getattr(b, "SerialNumber", "غير متوفر").strip()
                break

            for cs in wmi.InstancesOf("Win32_ComputerSystem"):
                mb.system_sku = getattr(cs, "SystemSKUNumber", "غير متوفر").strip()
                break
        except Exception as e:
            logger.warning(f"Error querying motherboard: {e}")

        cls._cached_mb = mb
        return mb

    @classmethod
    def get_bios_info(cls, force_refresh: bool = False) -> BiosInfo:
        """Queries BIOS firmware details, UEFI mode, Secure Boot, and TPM."""
        if cls._cached_bios is not None and not force_refresh:
            return cls._cached_bios

        binfo = BiosInfo()
        try:
            import win32com.client
            wmi = win32com.client.GetObject("winmgmts:")
            for bio in wmi.InstancesOf("Win32_BIOS"):
                binfo.manufacturer = getattr(bio, "Manufacturer", "غير محدد").strip()
                binfo.version = getattr(bio, "SMBIOSBIOSVersion", "غير متوفر").strip()
                rel_raw = getattr(bio, "ReleaseDate", "")
                if rel_raw and len(rel_raw) >= 8:
                    binfo.release_date = f"{rel_raw[:4]}-{rel_raw[4:6]}-{rel_raw[6:8]}"
                else:
                    binfo.release_date = rel_raw or "غير متوفر"

                maj = getattr(bio, "SMBIOSMajorVersion", 0)
                min_v = getattr(bio, "SMBIOSMinorVersion", 0)
                if maj:
                    binfo.smbios_version = f"{maj}.{min_v}"
                break
        except Exception as e:
            logger.warning(f"Error querying BIOS: {e}")

        # 1. Detect UEFI vs Legacy Mode
        binfo.bios_mode = cls._detect_bios_mode()

        # 2. Check Secure Boot State
        binfo.secure_boot = cls._detect_secure_boot()

        # 3. Query TPM Status
        tpm_detected, tpm_ver, tpm_status = cls._detect_tpm()
        binfo.tpm_detected = tpm_detected
        binfo.tpm_version = tpm_ver
        binfo.tpm_status_ar = tpm_status

        cls._cached_bios = binfo
        return binfo

    @classmethod
    def _detect_bios_mode(cls) -> str:
        """Determines if the system booted in UEFI mode or Legacy BIOS."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control"
            )
            val, _ = winreg.QueryValueEx(key, "PEFirmwareType")
            winreg.CloseKey(key)
            if val == 2:
                return "UEFI"
            elif val == 1:
                return "Legacy (BIOS)"
        except Exception:
            pass

        # Fallback check via bcdedit / enum
        try:
            res = subprocess.run(
                ["bcdedit"],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if "winload.efi" in res.stdout.lower():
                return "UEFI"
            elif "winload.exe" in res.stdout.lower():
                return "Legacy (BIOS)"
        except Exception:
            pass

        return "UEFI"

    @classmethod
    def _detect_secure_boot(cls) -> str:
        """Queries Windows Secure Boot registry flag."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\SecureBoot\State"
            )
            val, _ = winreg.QueryValueEx(key, "UEFISecureBootEnabled")
            winreg.CloseKey(key)
            if val == 1:
                return "مفعل (Enabled) ✓"
            elif val == 0:
                return "معطل (Disabled) ✗"
        except Exception:
            pass
        return "غير مدعوم أو غير محدد"

    @classmethod
    def _detect_tpm(cls) -> Tuple[bool, str, str]:
        """Queries TPM security hardware module presence and version."""
        try:
            import win32com.client
            wmi = win32com.client.GetObject(r"winmgmts:\\.\root\cimv2\Security\MicrosoftTpm")
            for tpm in wmi.InstancesOf("Win32_Tpm"):
                is_enabled = bool(getattr(tpm, "IsEnabled_InitialValue", False))
                is_ready = bool(getattr(tpm, "IsReady_InitialValue", False))
                spec = getattr(tpm, "SpecVersion", "2.0")
                if isinstance(spec, str):
                    ver = spec.split(",")[0].strip()
                else:
                    ver = "2.0"

                status = "جاهز ومفعل بالكامل ✓" if (is_enabled and is_ready) else "مكتشف (غير مفعل بالكامل)"
                return True, f"TPM {ver}", status
        except Exception:
            pass

        return False, "غير متوفر", "لم يتم العثور على شريحة TPM"
