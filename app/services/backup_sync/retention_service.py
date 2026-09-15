# -*- coding: utf-8 -*-
"""
SINAX Retention Service.
Applies data retention policies (Keep Count, Keep Days, GFS rotation).
Strictly adheres to the core rule: "Never Destroy Last Good Backup"
and protects pinned snapshots from deletion.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.models import BackupProfile, BackupSnapshot, RetentionPolicy

logger = get_logger("retention_service")


@dataclass
class RetentionCleanupPreview:
    snapshots_to_prune: List[BackupSnapshot] = field(default_factory=list)
    files_to_delete_count: int = 0
    estimated_bytes_to_free: int = 0
    oldest_remaining_timestamp: Optional[float] = None


class RetentionService:
    """Evaluates and safely executes retention policies."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    def evaluate_retention(self, profile: BackupProfile) -> RetentionCleanupPreview:
        """
        Determines which snapshots and versions are eligible for pruning based on profile policy.
        Never marks pinned snapshots or the latest good snapshot for deletion.
        """
        preview = RetentionCleanupPreview()
        policy = profile.retention

        if policy.keep_all:
            return preview

        snapshots = self.db.list_snapshots(profile.id)
        if len(snapshots) <= 1:
            # Always keep at least the only/last snapshot!
            return preview

        # Sort newest first
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)

        # The newest snapshot is ALWAYS protected
        latest_good = snapshots[0]
        candidates = snapshots[1:]

        now = time.time()
        max_age_seconds = policy.keep_days * 86400 if policy.keep_days > 0 else 0

        eligible_for_pruning: List[BackupSnapshot] = []
        kept_snapshots: List[BackupSnapshot] = [latest_good]

        for idx, snap in enumerate(candidates):
            # Skip pinned snapshots
            if snap.is_pinned:
                kept_snapshots.append(snap)
                continue

            prune = False

            # Check Keep Last N
            if policy.keep_last_n > 0 and len(kept_snapshots) >= policy.keep_last_n:
                prune = True

            # Check Keep Days
            if max_age_seconds > 0 and (now - snap.timestamp) > max_age_seconds:
                prune = True

            if prune:
                eligible_for_pruning.append(snap)
                preview.files_to_delete_count += snap.total_files
                preview.estimated_bytes_to_free += snap.total_bytes
            else:
                kept_snapshots.append(snap)

        preview.snapshots_to_prune = eligible_for_pruning
        if kept_snapshots:
            kept_snapshots.sort(key=lambda s: s.timestamp)
            preview.oldest_remaining_timestamp = kept_snapshots[0].timestamp

        return preview

    def apply_retention_cleanup(self, profile: BackupProfile) -> Tuple[int, int]:
        """
        Safely prunes expired versions and snapshots.
        Returns (pruned_snapshots_count, freed_bytes).
        """
        preview = self.evaluate_retention(profile)
        pruned_count = 0
        freed_bytes = 0

        for snap in preview.snapshots_to_prune:
            try:
                # Remove manifest file if present
                if snap.manifest_path and os.path.isfile(snap.manifest_path):
                    try:
                        os.unlink(snap.manifest_path)
                    except OSError:
                        pass

                # Delete from database
                with self.db._get_connection() as conn:
                    conn.execute("DELETE FROM file_versions WHERE snapshot_id = ?", (snap.id,))
                    conn.execute("DELETE FROM backup_snapshots WHERE id = ?", (snap.id,))

                pruned_count += 1
                freed_bytes += snap.total_bytes
            except Exception as e:
                logger.warning(f"Failed to prune snapshot {snap.id}: {e}")

        return pruned_count, freed_bytes
