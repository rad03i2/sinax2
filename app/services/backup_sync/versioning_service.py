# -*- coding: utf-8 -*-
"""
SINAX Versioning & Snapshot Service.
Manages point-in-time snapshots and historic file versions.
Keeps current files in their native structure for direct opening, while archiving
overwritten versions into protected sidecar version storage (.sinax_versions/).
"""

import os
from pathlib import Path
import shutil
import time
from typing import Dict, List, Optional
import uuid

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.models import BackupSnapshot, FileVersion

logger = get_logger("versioning_service")


class VersioningService:
    """Handles snapshot recording, version archival, and version history lookup."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    def create_snapshot(
        self,
        profile_id: str,
        job_id: str,
        total_files: int,
        total_bytes: int,
        snapshot_id: Optional[str] = None,
        manifest_path: str = "",
        note: str = ""
    ) -> BackupSnapshot:
        """Creates and persists a new backup snapshot record."""
        snapshot = BackupSnapshot(
            id=snapshot_id or str(uuid.uuid4()),
            profile_id=profile_id,
            job_id=job_id,
            timestamp=time.time(),
            total_files=total_files,
            total_bytes=total_bytes,
            manifest_path=manifest_path,
            is_pinned=False,
            note=note
        )
        self.db.save_snapshot(snapshot)
        return snapshot

    def archive_previous_version(
        self,
        dest_root: str,
        relative_path: str,
        profile_id: str,
        snapshot_id: str
    ) -> Optional[FileVersion]:
        """
        If a file already exists at dest_root/relative_path and is about to be overwritten,
        moves it into dest_root/.sinax_versions/<rel_path>.<timestamp> and records FileVersion.
        """
        existing_file = Path(dest_root) / relative_path
        if not existing_file.exists() or not existing_file.is_file():
            return None

        stat = existing_file.stat()
        versions = self.db.get_file_versions(profile_id, relative_path)
        next_ver = len(versions) + 1

        # Target archival path
        ver_dir = Path(dest_root) / ".sinax_versions" / Path(relative_path).parent
        ver_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(stat.st_mtime))
        archived_name = f"{existing_file.stem}_{timestamp_str}_v{next_ver}{existing_file.suffix}"
        archived_target = ver_dir / archived_name

        try:
            shutil.copy2(str(existing_file), str(archived_target))
            version_record = FileVersion(
                file_id=str(uuid.uuid4()),
                snapshot_id=snapshot_id,
                relative_path=relative_path,
                size_bytes=stat.st_size,
                mtime=stat.st_mtime,
                version_number=next_ver,
                stored_path=str(archived_target)
            )
            self.db.save_file_version(version_record, profile_id)
            return version_record
        except Exception as e:
            logger.warning(f"Failed to archive previous version of {relative_path}: {e}")
            return None

    def record_current_version(
        self,
        dest_root: str,
        relative_path: str,
        profile_id: str,
        snapshot_id: str,
        sha256: Optional[str] = None
    ) -> FileVersion:
        """Records the current live backed-up file version in SQLite."""
        file_path = Path(dest_root) / relative_path
        stat = file_path.stat()

        record = FileVersion(
            file_id=str(uuid.uuid4()),
            snapshot_id=snapshot_id,
            relative_path=relative_path,
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
            sha256=sha256,
            version_number=1,
            stored_path=str(file_path)
        )
        self.db.save_file_version(record, profile_id)
        return record

    def get_file_versions(self, profile_id: str, relative_path: str) -> List[FileVersion]:
        return self.db.get_file_versions(profile_id, relative_path)

    def list_snapshots(self, profile_id: str) -> List[BackupSnapshot]:
        return self.db.list_snapshots(profile_id)

    def set_snapshot_pinned(self, snapshot_id: str, is_pinned: bool):
        self.db.set_snapshot_pinned(snapshot_id, is_pinned)
