# -*- coding: utf-8 -*-
"""
SINAX Restore Service.
Restores individual files, historic versions, full snapshots, or files that were
deleted from the source. Default collision safety policy is "Keep Both" to prevent
accidental data overwrites.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.copy_engine import CopyEngine
from app.services.backup_sync.models import BackupSnapshot, FileVersion

logger = get_logger("restore_service")


@dataclass
class RestoreResult:
    is_success: bool = True
    files_restored: int = 0
    bytes_restored: int = 0
    conflicts_handled: int = 0
    failed_files: List[str] = field(default_factory=list)
    restored_paths: List[str] = field(default_factory=list)
    error_summary: str = ""


class RestoreService:
    """Manages secure file and snapshot restoration workflows."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    @classmethod
    def resolve_destination_path(cls, target_folder: str, relative_path: str, collision_policy: str = "keep_both") -> Optional[str]:
        """Resolves target path applying the collision policy."""
        target = Path(target_folder) / relative_path
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            return str(target)

        # File exists - Apply collision policy
        if collision_policy == "replace":
            return str(target)
        elif collision_policy == "skip":
            return None
        else:
            # "keep_both" default: generate filename (restored 2026-09-11_0200).ext
            target.parent.mkdir(parents=True, exist_ok=True)
            t_str = time.strftime("%Y-%m-%d_%H%M%S")
            candidate = target.parent / f"{target.stem} (restored {t_str}){target.suffix}"
            counter = 1
            while candidate.exists():
                candidate = target.parent / f"{target.stem} (restored {t_str}_{counter}){target.suffix}"
                counter += 1
            return str(candidate)

    def restore_file_version(
        self,
        version: FileVersion,
        target_folder: str,
        collision_policy: str = "keep_both"
    ) -> Tuple[bool, str]:
        """Restores a single historical version to target_folder."""
        src_path = version.stored_path
        if not os.path.isfile(src_path):
            return False, f"ملف النسخة المخزن غير موجود على القرص: {src_path}"

        dest_path = self.resolve_destination_path(target_folder, version.relative_path, collision_policy)
        if dest_path is None:
            return True, "تم تخطي الملف لوجود نسخة سابقة ومطابقة سياسة التخطي."

        try:
            ok, err = CopyEngine.copy_file_safe(src_path, dest_path)
            if ok:
                return True, dest_path
            return False, err
        except Exception as e:
            return False, str(e)

    def restore_snapshot(
        self,
        snapshot_id: str,
        target_folder: str,
        collision_policy: str = "keep_both",
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> RestoreResult:
        """Restores all files belonging to a specific backup snapshot."""
        result = RestoreResult()

        with self.db._get_connection() as conn:
            rows = conn.execute("SELECT * FROM file_versions WHERE snapshot_id = ?", (snapshot_id,)).fetchall()

        total = len(rows)
        for idx, r in enumerate(rows):
            if cancel_check and cancel_check():
                result.is_success = False
                result.error_summary = "تم إلغاء عملية الاستعادة بواسطة المستخدم."
                break

            ver = FileVersion(
                file_id=r["file_id"], snapshot_id=r["snapshot_id"],
                relative_path=r["relative_path"], size_bytes=r["size_bytes"],
                mtime=r["mtime"], sha256=r["sha256"], version_number=r["version_number"],
                stored_path=r["stored_path"]
            )

            ok, res_str = self.restore_file_version(ver, target_folder, collision_policy)
            if ok:
                result.files_restored += 1
                result.bytes_restored += ver.size_bytes
                if res_str and "(restored" in res_str:
                    result.conflicts_handled += 1
                result.restored_paths.append(res_str)
            else:
                result.failed_files.append(ver.relative_path)

            if progress_cb and (idx % 10 == 0 or idx == total - 1):
                progress_cb(idx + 1, total)

        if result.failed_files:
            result.is_success = False
            result.error_summary = f"فشل استعادة {len(result.failed_files)} ملفات."

        return result

    def get_deleted_files_from_source(self, profile_id: str) -> List[FileVersion]:
        """
        Discovers files that exist in the latest backup snapshot
        but are currently missing from the source folders.
        """
        profile = self.db.get_profile(profile_id)
        if not profile or not profile.sources:
            return []

        snapshots = self.db.list_snapshots(profile_id)
        if not snapshots:
            return []

        latest_snap = snapshots[0]
        with self.db._get_connection() as conn:
            rows = conn.execute("SELECT * FROM file_versions WHERE snapshot_id = ?", (latest_snap.id,)).fetchall()

        deleted_files: List[FileVersion] = []
        source_roots = [Path(s).resolve() for s in profile.sources]

        for r in rows:
            rel = r["relative_path"]
            # Check if rel exists in ANY source root
            found_in_source = False
            for src_root in source_roots:
                candidate = src_root / rel
                if candidate.exists():
                    found_in_source = True
                    break

            if not found_in_source:
                deleted_files.append(FileVersion(
                    file_id=r["file_id"], snapshot_id=r["snapshot_id"],
                    relative_path=rel, size_bytes=r["size_bytes"],
                    mtime=r["mtime"], sha256=r["sha256"], version_number=r["version_number"],
                    stored_path=r["stored_path"]
                ))

        return deleted_files
