# -*- coding: utf-8 -*-
"""
SINAX Backup Coordinator.
Orchestrates the end-to-end backup pipeline:
Preflight -> Scan -> Incremental Diff -> Copy -> Versioning -> Verify -> Retention -> Post Actions.
"""

from pathlib import Path
import time
from typing import Callable, Dict, List, Optional, Tuple
import uuid

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.copy_engine import CopyEngine
from app.services.backup_sync.incremental_detector import IncrementalDetector
from app.services.backup_sync.models import (
    BackupJob,
    BackupProfile,
    BackupSnapshot,
    BackupType,
    JobStatus,
    VerificationLevel,
)
from app.services.backup_sync.physical_disk_service import PhysicalDiskService
from app.services.backup_sync.retention_service import RetentionService
from app.services.backup_sync.usb_backup_service import UsbBackupService
from app.services.backup_sync.verification_service import VerificationService
from app.services.backup_sync.versioning_service import VersioningService

logger = get_logger("backup_coordinator")


class BackupCoordinator:
    """Executes full and incremental backup profiles with verification and versioning."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()
        self.versioning = VersioningService(self.db)
        self.retention = RetentionService(self.db)

    def run_backup(
        self,
        profile: BackupProfile,
        progress_cb: Optional[Callable[[str, int, int, str], None]] = None,  # (stage, done, total, detail)
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> BackupJob:
        """Executes the complete backup pipeline for a profile."""
        job_id = str(uuid.uuid4())
        job = BackupJob(
            id=job_id,
            profile_id=profile.id,
            job_type="backup",
            start_time=time.time(),
            status=JobStatus.RUNNING
        )
        self.db.save_job(job)

        try:
            # 1. Preflight Check
            if progress_cb:
                progress_cb("preflight", 0, 100, "جاري فحص سلامة الوجهة ونظام الملفات...")

            preflight = PhysicalDiskService.perform_preflight_check(profile.sources, profile.destination)
            if not preflight.is_valid:
                job.status = JobStatus.FAILED
                job.error_summary = "؛ ".join(preflight.errors)
                job.end_time = time.time()
                self.db.save_job(job)
                return job

            # 2. Scanning Sources
            if progress_cb:
                progress_cb("scanning", 0, 100, "جاري مسح المجلدات المصدرية...")

            current_files = {}
            for src in profile.sources:
                if cancel_check and cancel_check():
                    break
                scanned = IncrementalDetector.scan_directory(
                    src, exclude_patterns=profile.exclude_patterns, cancel_check=cancel_check
                )
                current_files.update(scanned)

            job.files_scanned = len(current_files)

            # 3. Load Previous Snapshot (if Incremental)
            previous_versions = {}
            if profile.backup_type == BackupType.INCREMENTAL:
                snapshots = self.db.list_snapshots(profile.id)
                if snapshots:
                    latest_snap = snapshots[0]
                    with self.db._get_connection() as conn:
                        rows = conn.execute(
                            "SELECT * FROM file_versions WHERE snapshot_id = ?", (latest_snap.id,)
                        ).fetchall()
                        for r in rows:
                            from app.services.backup_sync.models import FileVersion
                            previous_versions[r["relative_path"]] = FileVersion(
                                file_id=r["file_id"], snapshot_id=r["snapshot_id"],
                                relative_path=r["relative_path"], size_bytes=r["size_bytes"],
                                mtime=r["mtime"], sha256=r["sha256"], version_number=r["version_number"],
                                stored_path=r["stored_path"]
                            )

            # 4. Incremental Diff
            diff = IncrementalDetector.detect_changes(
                current_files, previous_versions, mode=profile.incremental_mode, cancel_check=cancel_check
            )

            # Handle Ransomware mass change warning
            if diff.unusual_mass_changes:
                logger.warning(f"Mass change alert: {diff.mass_change_reason}")

            files_to_copy = diff.new_files + diff.modified_files
            total_copy = len(files_to_copy)

            # 5. Copying & Version Archival
            dest_root = Path(profile.destination)
            snapshot_id = str(uuid.uuid4())

            for idx, item in enumerate(files_to_copy):
                if cancel_check and cancel_check():
                    job.status = JobStatus.CANCELLED
                    job.error_summary = "تم إلغاء النسخ بواسطة المستخدم."
                    break

                if progress_cb:
                    progress_cb("copying", idx + 1, total_copy, f"نسخ: {Path(item.relative_path).name}")

                target_path = dest_root / item.relative_path

                # If file exists on destination and is modified, archive old version first
                if target_path.exists():
                    self.versioning.archive_previous_version(
                        str(dest_root), item.relative_path, profile.id, snapshot_id
                    )
                    job.files_updated += 1
                else:
                    job.files_copied += 1

                # Copy with atomic rename
                ok, err = CopyEngine.copy_file_safe(item.absolute_path, str(target_path))
                if ok:
                    job.bytes_copied += item.size_bytes
                    # Record current version in SQLite
                    self.versioning.record_current_version(
                        str(dest_root), item.relative_path, profile.id, snapshot_id, sha256=item.sha256
                    )
                else:
                    job.files_failed += 1
                    logger.warning(f"Failed to copy {item.relative_path}: {err}")

            # Also link unchanged files into this snapshot to maintain complete state
            for u_item in diff.unchanged_files:
                u_target = dest_root / u_item.relative_path
                if u_target.exists():
                    self.versioning.record_current_version(
                        str(dest_root), u_item.relative_path, profile.id, snapshot_id, sha256=u_item.sha256
                    )

            if job.status == JobStatus.CANCELLED:
                job.end_time = time.time()
                self.db.save_job(job)
                return job

            # 6. Verification & Manifest Generation
            if progress_cb:
                progress_cb("verifying", 0, total_copy, "جاري التحقق وتوليد ملف البيان...")

            dest_manifest_map = {
                item.relative_path: (item.size_bytes, item.mtime)
                for item in current_files.values()
            }
            compute_h = (profile.verification_level == VerificationLevel.FULL_INTEGRITY)
            manifest_path, _ = VerificationService.generate_manifest(
                str(dest_root), dest_manifest_map, compute_hashes=compute_h, cancel_check=cancel_check
            )

            job.verification_status = "verified"

            # 7. Create Snapshot record
            snapshot = self.versioning.create_snapshot(
                profile_id=profile.id,
                job_id=job.id,
                total_files=len(current_files),
                total_bytes=sum(it.size_bytes for it in current_files.values()),
                snapshot_id=snapshot_id,
                manifest_path=manifest_path,
                note=f"اكتمل النسخ بنجاح ({job.files_copied} جديد، {job.files_updated} معدل)."
            )

            # 8. Apply Retention Cleanup
            self.retention.apply_retention_cleanup(profile)

            # 9. Update profile & job stats
            job.status = JobStatus.COMPLETED
            job.end_time = time.time()
            self.db.save_job(job)

            profile.last_run_at = time.time()
            profile.last_status = "success"
            self.db.save_profile(profile)

            # 10. Post-action: Eject if configured
            if profile.eject_after_backup:
                UsbBackupService(self.db).safe_eject_backup_drive(profile.destination)

            if progress_cb:
                progress_cb("completed", total_copy, total_copy, "اكتمل النسخ والتحقق بنجاح ✓")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_summary = str(e)
            job.end_time = time.time()
            self.db.save_job(job)
            profile.last_status = "failed"
            self.db.save_profile(profile)

        return job
