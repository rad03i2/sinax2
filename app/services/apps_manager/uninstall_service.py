# -*- coding: utf-8 -*-
"""
SINAX Safe Application Uninstallation Service
Handles single and sequential batch uninstallation of MSI, MSIX, WinGet, and Win32 applications.
Strictly avoids shell=True, guards system runtimes/drivers, and detects restart requirements.
"""

from dataclasses import dataclass, field
import logging
import os
import shlex
import subprocess
import time
from typing import Callable, List, Optional, Tuple

from app.services.apps_manager.app_model import InstalledApp

logger = logging.getLogger("SINAX.apps_manager.uninstall_service")


@dataclass
class UninstallResult:
    """Outcome of an uninstallation attempt."""
    app_id: str
    app_name: str
    success: bool
    exit_code: int = 0
    restart_required: bool = False
    message: str = ""
    technical_details: str = ""


@dataclass
class BatchUninstallReport:
    """Summary report for a sequential batch uninstallation job."""
    total_requested: int = 0
    succeeded: List[UninstallResult] = field(default_factory=list)
    failed: List[UninstallResult] = field(default_factory=list)
    skipped: List[UninstallResult] = field(default_factory=list)
    restart_required: bool = False
    cancelled_early: bool = False


class UninstallService:
    """Safely executes program uninstallation using native Windows mechanisms."""

    @classmethod
    def uninstall_app(cls, app: InstalledApp, silent: bool = False) -> UninstallResult:
        """Uninstalls a single application using its appropriate native provider."""
        # 1. Guard System Components & Drivers
        if app.is_system_component:
            return UninstallResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message="مرفوض: هذا التطبيق مكون أساسي من نظام ويندوز ولا يمكن حذفه بأمان.",
            )

        if app.is_runtime_or_driver:
            return UninstallResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message="مرفوض: هذه الحزمة حزمة برمجية أساسية (Runtime) أو برنامج تشغيل عتاد (Driver) وإزالتها قد تعطل برامج أخرى.",
            )

        # 2. Strategy: MSIX / Store App
        if app.uninstall_type == "msix" and app.package_full_name:
            return cls._uninstall_msix(app)

        # 3. Strategy: MSI Installer
        if app.product_code:
            return cls._uninstall_msi(app, silent=silent)

        # 4. Strategy: WinGet Package
        if app.source == "winget" and app.package_id:
            return cls._uninstall_winget(app)

        # 5. Strategy: Win32 Custom Uninstaller
        if app.uninstall_string:
            return cls._uninstall_win32(app, silent=silent)

        return UninstallResult(
            app_id=app.id,
            app_name=app.name,
            success=False,
            exit_code=-1,
            message="لم يتم العثور على أمر أو مسار برنامج إزالة التثبيت الرسمي لهذا التطبيق.",
        )

    @classmethod
    def execute_batch(
        cls,
        apps: List[InstalledApp],
        progress_cb: Optional[Callable[[int, int, InstalledApp, str], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> BatchUninstallReport:
        """
        Executes batch uninstallation sequentially (one by one) to avoid msiexec concurrency locks.
        """
        report = BatchUninstallReport(total_requested=len(apps))

        for idx, app in enumerate(apps):
            if cancel_token and cancel_token():
                report.cancelled_early = True
                logger.info("Batch uninstallation cancelled by user.")
                # Mark remaining as skipped
                for rem in apps[idx:]:
                    report.skipped.append(
                        UninstallResult(
                            app_id=rem.id,
                            app_name=rem.name,
                            success=False,
                            message="تم التخطي لإلغاء العملية من قبل المستخدم.",
                        )
                    )
                break

            if progress_cb:
                progress_cb(idx + 1, len(apps), app, f"جارٍ إزالة: {app.name}...")

            res = cls.uninstall_app(app, silent=False)
            if res.success:
                report.succeeded.append(res)
                if res.restart_required:
                    report.restart_required = True
            else:
                report.failed.append(res)

            # Short cooldown between sequential uninstallers
            time.sleep(1.0)

        return report

    @classmethod
    def _uninstall_msix(cls, app: InstalledApp) -> UninstallResult:
        """Removes an AppX/MSIX package via PowerShell."""
        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f'Remove-AppxPackage -Package "{app.package_full_name}"',
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                return UninstallResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=True,
                    message="تمت إزالة تطبيق المتجر بنجاح.",
                )
            return UninstallResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=res.returncode,
                message="فشلت إزالة حزمة MSIX.",
                technical_details=res.stderr.strip() or res.stdout.strip(),
            )
        except Exception as e:
            return UninstallResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message=f"خطأ أثناء استدعاء PowerShell: {e}",
            )

    @classmethod
    def _uninstall_msi(cls, app: InstalledApp, silent: bool = False) -> UninstallResult:
        """Uninstalls an MSI package via msiexec."""
        args = ["msiexec.exe", "/x", app.product_code]
        if silent:
            args.append("/qn")
        else:
            args.append("/qb")

        return cls._run_native_process(app, args[0], args[1:])

    @classmethod
    def _uninstall_winget(cls, app: InstalledApp) -> UninstallResult:
        """Uninstalls a package via WinGet CLI."""
        args = ["winget", "uninstall", "--id", app.package_id, "--accept-source-agreements"]
        return cls._run_native_process(app, args[0], args[1:])

    @classmethod
    def _uninstall_win32(cls, app: InstalledApp, silent: bool = False) -> UninstallResult:
        """Safely parses and executes a standard Win32 uninstall command without shell=True."""
        raw_cmd = app.quiet_uninstall_string if (silent and app.quiet_uninstall_string) else app.uninstall_string
        if not raw_cmd:
            return UninstallResult(app_id=app.id, app_name=app.name, success=False, message="أمر الإزالة فارغ.")

        exe, args = cls.tokenize_command(raw_cmd)
        if not exe:
            return UninstallResult(app_id=app.id, app_name=app.name, success=False, message="تعذر استخراج ملف الإزالة التنفيذي.")

        # If executable does not exist, check if it's msiexec
        if not os.path.exists(exe):
            if os.path.basename(exe).lower() in ("msiexec", "msiexec.exe"):
                exe = "msiexec.exe"
            else:
                return UninstallResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=False,
                    exit_code=-1,
                    message=f"ملف برنامج الإزالة غير موجود على القرص: {exe}",
                )

        return cls._run_native_process(app, exe, args)

    @classmethod
    def _run_native_process(cls, app: InstalledApp, executable: str, args: List[str]) -> UninstallResult:
        """Runs the uninstaller process with elevation fallback."""
        full_cmd = [executable] + args
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=300)
            code = res.returncode

            # Standard Windows Installer Exit Codes:
            # 0: ERROR_SUCCESS
            # 3010: ERROR_SUCCESS_REBOOT_REQUIRED
            # 1602: ERROR_INSTALL_USEREXIT (Cancelled by user)
            # 1603: ERROR_INSTALL_FAILURE (Fatal error)
            # 1618: ERROR_INSTALL_ALREADY_RUNNING
            if code == 0:
                return UninstallResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=True,
                    exit_code=0,
                    message="تمت إزالة البرنامج بنجاح.",
                )
            elif code == 3010:
                return UninstallResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=True,
                    exit_code=3010,
                    restart_required=True,
                    message="تمت إزالة البرنامج بنجاح ولكن يتطلب إعادة تشغيل ويندوز لاكتمال التغييرات.",
                )
            elif code == 1602:
                return UninstallResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=False,
                    exit_code=1602,
                    message="تم إلغاء عملية الإزالة من قبل المستخدم في واجهة برنامج التثبيت.",
                )
            else:
                return UninstallResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=False,
                    exit_code=code,
                    message=f"فشلت عملية الإزالة. كود الخطأ: {code}",
                    technical_details=res.stderr.strip() or res.stdout.strip(),
                )

        except PermissionError:
            # Requires elevation (UAC)
            return cls._run_elevated_shell(app, executable, args)
        except subprocess.TimeoutExpired:
            return UninstallResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message="استغرقت عملية الإزالة وقتاً أطول من المسموح (أكثر من 5 دقائق).",
            )
        except Exception as e:
            return UninstallResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message=f"تعذر تشغيل برنامج الإزالة: {e}",
            )

    @classmethod
    def _run_elevated_shell(cls, app: InstalledApp, executable: str, args: List[str]) -> UninstallResult:
        """Executes a process requesting UAC elevation via ctypes ShellExecuteExW."""
        try:
            import ctypes
            from ctypes import wintypes

            params = " ".join(f'"{a}"' if " " in a else a for a in args)

            # ShellExecuteW(hwnd, lpOperation, lpFile, lpParameters, lpDirectory, nShowCmd)
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                executable,
                params,
                None,
                1,  # SW_SHOWNORMAL
            )
            # HINSTANCE > 32 indicates success
            if ret > 32:
                return UninstallResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=True,
                    message="تم تشغيل برنامج الإزالة بصلاحيات المسؤول (UAC).",
                )
            else:
                return UninstallResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=False,
                    exit_code=ret,
                    message="تم رفض صلاحيات المسؤول (UAC) أو تعذر تشغيل العملية.",
                )
        except Exception as e:
            return UninstallResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message=f"فشل تشغيل المسؤول: {e}",
            )

    @classmethod
    def tokenize_command(cls, cmd_line: str) -> Tuple[Optional[str], List[str]]:
        """
        Safely tokenizes a Windows command line string into (executable_path, [arguments]).
        Handles quotes, spaces, and Windows-style slashes.
        """
        if not cmd_line or not cmd_line.strip():
            return None, []

        s = cmd_line.strip()
        exe = None
        rem = ""

        # Case 1: Wrapped in quotes
        if s.startswith('"'):
            end_q = s.find('"', 1)
            if end_q != -1:
                exe = s[1:end_q].strip()
                rem = s[end_q + 1:].strip()
        else:
            # Case 2: Unquoted path. Might contain spaces like C:\Program Files\App\unins.exe /SILENT
            tokens = s.split()
            cand_path = ""
            for i, token in enumerate(tokens):
                cand_path = f"{cand_path} {token}".strip() if cand_path else token
                if os.path.exists(cand_path) or cand_path.lower().endswith((".exe", ".bat", ".cmd")):
                    exe = cand_path
                    rem = " ".join(tokens[i + 1:])
                    break
            if not exe:
                exe = tokens[0] if tokens else None
                rem = " ".join(tokens[1:]) if len(tokens) > 1 else ""

        args = []
        if rem:
            try:
                # Use shlex with posix=False for Windows compatibility
                args = shlex.split(rem, posix=False)
                # Clean quotes from parsed args
                args = [a.strip('"') for a in args if a.strip()]
            except Exception:
                args = rem.split()

        return exe, args
