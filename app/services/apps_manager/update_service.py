# -*- coding: utf-8 -*-
"""
SINAX Application Update Service
Leverages WinGet CLI for real-time update checking, single updates,
sequential batch update queues with preview dialogs, and version pinning.
"""

from dataclasses import dataclass, field
import logging
import subprocess
import time
from typing import Callable, Dict, List, Optional, Tuple

from app.services.apps_manager.app_model import InstalledApp
from app.services.apps_manager.providers.winget_provider import WingetProvider

logger = logging.getLogger("SINAX.apps_manager.update_service")


@dataclass
class UpdateResult:
    """Outcome of an application update attempt."""
    app_id: str
    app_name: str
    success: bool
    exit_code: int = 0
    restart_required: bool = False
    message: str = ""
    technical_details: str = ""


@dataclass
class BatchUpdateReport:
    """Summary report for batch application updates."""
    total_requested: int = 0
    succeeded: List[UpdateResult] = field(default_factory=list)
    failed: List[UpdateResult] = field(default_factory=list)
    skipped: List[UpdateResult] = field(default_factory=list)
    restart_required: bool = False
    cancelled_early: bool = False


class UpdateService:
    """Manages application updates and version controls."""

    @classmethod
    def check_updates(cls) -> Dict[str, Dict[str, str]]:
        """Queries WinGet for all pending application updates."""
        return WingetProvider.get_available_upgrades()

    @classmethod
    def update_app(cls, app: InstalledApp) -> UpdateResult:
        """Updates a single application via WinGet CLI."""
        target_id = app.package_id
        if not target_id:
            return UpdateResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message="لا يتوفر معرف حزمة WinGet لهذا البرنامج.",
            )

        cmd = [
            "winget", "upgrade",
            "--id", target_id,
            "--accept-source-agreements",
            "--accept-package-agreements",
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            code = res.returncode
            if code == 0:
                return UpdateResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=True,
                    exit_code=0,
                    message="تم تحديث البرنامج بنجاح إلى أحدث إصدار.",
                )
            elif code == 3010:
                return UpdateResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=True,
                    exit_code=3010,
                    restart_required=True,
                    message="تم تحديث البرنامج ولكن يتطلب إعادة تشغيل الجهاز.",
                )
            else:
                return UpdateResult(
                    app_id=app.id,
                    app_name=app.name,
                    success=False,
                    exit_code=code,
                    message=f"فشلت عملية التحديث. كود الخطأ: {code}",
                    technical_details=res.stderr.strip() or res.stdout.strip(),
                )
        except subprocess.TimeoutExpired:
            return UpdateResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message="استغرقت عملية التحديث أكثر من 10 دقائق وتوقفت.",
            )
        except Exception as e:
            return UpdateResult(
                app_id=app.id,
                app_name=app.name,
                success=False,
                exit_code=-1,
                message=f"خطأ أثناء استدعاء التحديث: {e}",
            )

    @classmethod
    def execute_batch_update(
        cls,
        apps: List[InstalledApp],
        progress_cb: Optional[Callable[[int, int, InstalledApp, str], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None,
    ) -> BatchUpdateReport:
        """Executes sequential batch updates one app at a time."""
        report = BatchUpdateReport(total_requested=len(apps))

        for idx, app in enumerate(apps):
            if cancel_token and cancel_token():
                report.cancelled_early = True
                for rem in apps[idx:]:
                    report.skipped.append(
                        UpdateResult(
                            app_id=rem.id,
                            app_name=rem.name,
                            success=False,
                            message="تم التخطي لإلغاء العملية من قبل المستخدم.",
                        )
                    )
                break

            if progress_cb:
                progress_cb(idx + 1, len(apps), app, f"جارٍ تحديث: {app.name}...")

            res = cls.update_app(app)
            if res.success:
                report.succeeded.append(res)
                if res.restart_required:
                    report.restart_required = True
            else:
                report.failed.append(res)

            time.sleep(1.0)

        return report

    @classmethod
    def pin_app(cls, app: InstalledApp) -> bool:
        """Pins an app to prevent automated upgrades."""
        if not app.package_id:
            return False
        ok = WingetProvider.pin_package(app.package_id)
        if ok:
            app.is_pinned = True
        return ok

    @classmethod
    def unpin_app(cls, app: InstalledApp) -> bool:
        """Removes an upgrade pin from an app."""
        if not app.package_id:
            return False
        ok = WingetProvider.unpin_package(app.package_id)
        if ok:
            app.is_pinned = False
        return ok
