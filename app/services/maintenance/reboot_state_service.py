# -*- coding: utf-8 -*-
"""
Pending Restart Service for SINAX Maintenance & Repair Center.
Inspects Windows Registry keys and servicing signals to determine if a system reboot
is pending (due to Windows Update, Component-Based Servicing, or Pending File Rename Operations).
Strictly transparent and non-intrusive.
"""

import os
import subprocess
from typing import Dict, List, Tuple


class RebootStateService:
    """Detects pending Windows restarts and the exact underlying cause."""

    @staticmethod
    def check_pending_reboot() -> Tuple[bool, List[str]]:
        """
        Checks official Windows registry markers for pending reboots.
        Returns: (is_pending: bool, reasons: List[str])
        """
        reasons: List[str] = []

        if os.name != "nt":
            return False, []

        import winreg

        # 1. Windows Update Reboot Required
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
                0,
                winreg.KEY_READ,
            ):
                reasons.append("تحديثات Windows تتطلب إعادة التشغيل لإكمال التثبيت (Windows Update)")
        except OSError:
            pass

        # 2. Component-Based Servicing (CBS) Reboot Pending
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
                0,
                winreg.KEY_READ,
            ):
                reasons.append("حزم صيانة نظام Windows تتطلب إعادة تشغيل (CBS Servicing)")
        except OSError:
            pass

        # 3. Session Manager - Pending File Rename Operations
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager",
                0,
                winreg.KEY_READ,
            ) as key:
                val, _ = winreg.QueryValueEx(key, "PendingFileRenameOperations")
                if val:
                    reasons.append("عمليات استبدال ملفات أثناء الإقلاع معلقة (Pending File Rename)")
        except OSError:
            pass

        # 4. Computer Rename Pending
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\ComputerName\ActiveComputerName",
                0,
                winreg.KEY_READ,
            ) as key_act:
                act_name, _ = winreg.QueryValueEx(key_act, "ComputerName")
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName",
                    0,
                    winreg.KEY_READ,
                ) as key_pend:
                    pend_name, _ = winreg.QueryValueEx(key_pend, "ComputerName")
                    if act_name != pend_name:
                        reasons.append(f"تغيير اسم الكمبيوتر معلق من '{act_name}' إلى '{pend_name}'")
        except OSError:
            pass

        return len(reasons) > 0, reasons

    @staticmethod
    def get_summary_ar() -> str:
        """Returns human-friendly Arabic summary for the dashboard."""
        is_pending, reasons = RebootStateService.check_pending_reboot()
        if not is_pending:
            return "غير مطلوب (جاهز تماماً)"
        return f"مطلوب ({len(reasons)} سبب: {reasons[0]})"

    @staticmethod
    def request_restart(delay_seconds: int = 15) -> bool:
        """Initiates a graceful Windows restart after user confirmation."""
        try:
            subprocess.run(
                ["shutdown.exe", "/r", "/t", str(delay_seconds), "/c", "إعادة تشغيل مجدولة من SINAX لإكمال عمليات الصيانة"],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def cancel_restart() -> bool:
        """Cancels a scheduled restart."""
        try:
            subprocess.run(
                ["shutdown.exe", "/a"],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return True
        except Exception:
            return False
