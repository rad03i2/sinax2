# -*- coding: utf-8 -*-
"""
SINAX Apps & Programs Manager Services Package
"""

from app.services.apps_manager.app_model import InstalledApp, format_bytes
from app.services.apps_manager.app_size_service import AppSizeService
from app.services.apps_manager.app_snapshot_service import AppSnapshotService
from app.services.apps_manager.backup_restore_service import BackupRestoreService
from app.services.apps_manager.broken_entries_service import BrokenEntriesService
from app.services.apps_manager.inventory_service import InventoryService
from app.services.apps_manager.leftover_scanner import LeftoverItem, LeftoverScanner
from app.services.apps_manager.repair_service import RepairService
from app.services.apps_manager.uninstall_service import BatchUninstallReport, UninstallResult, UninstallService
from app.services.apps_manager.update_service import BatchUpdateReport, UpdateResult, UpdateService

__all__ = [
    "InstalledApp",
    "format_bytes",
    "AppSizeService",
    "AppSnapshotService",
    "BackupRestoreService",
    "BrokenEntriesService",
    "InventoryService",
    "LeftoverItem",
    "LeftoverScanner",
    "RepairService",
    "UninstallResult",
    "BatchUninstallReport",
    "UninstallService",
    "UpdateResult",
    "BatchUpdateReport",
    "UpdateService",
]
