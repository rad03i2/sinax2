# -*- coding: utf-8 -*-
"""
SINAX Backup & Sync Models & Data Structures.
Defines typed models for profiles, jobs, snapshots, file versions, sync pairs,
conflicts, retention policies, and preflight health assessments.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class BackupType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class SyncMode(str, Enum):
    ONE_WAY = "one_way"      # A -> B
    TWO_WAY = "two_way"      # A <-> B
    MIRROR = "mirror"        # B becomes identical to A (deletions on B)
    UPDATE = "update"        # A -> B without updating existing newer files


class VerificationLevel(str, Enum):
    BASIC = "basic"                      # Exists + Size
    BALANCED = "balanced"                # Sample hashes + metadata
    FULL_INTEGRITY = "full_integrity"    # Full SHA-256 for all files


class IncrementalMode(str, Enum):
    FAST = "fast"          # size + mtime
    BALANCED = "balanced"  # size + mtime + attributes
    STRICT = "strict"      # SHA-256 hash comparison


class ConflictResolution(str, Enum):
    KEEP_A = "keep_a"
    KEEP_B = "keep_b"
    KEEP_BOTH = "keep_both"
    COMPARE = "compare"
    SKIP = "skip"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass
class RetentionPolicy:
    keep_all: bool = False
    keep_last_n: int = 10
    keep_days: int = 30
    pin_last_good: bool = True       # Never destroy the last good verified backup
    gfs_enabled: bool = False        # Grandfather-Father-Son rotation


@dataclass
class DriveIdentity:
    volume_serial: str               # Volume Serial Number (persistent across letter changes)
    volume_label: str = ""
    filesystem: str = "NTFS"
    device_id: str = ""
    model: str = ""
    drive_letter: str = ""
    total_bytes: int = 0
    free_bytes: int = 0
    is_trusted: bool = False
    is_removable: bool = False


@dataclass
class BackupProfile:
    id: str
    name: str
    sources: List[str]
    destination: str
    backup_type: BackupType = BackupType.INCREMENTAL
    incremental_mode: IncrementalMode = IncrementalMode.FAST
    verification_level: VerificationLevel = VerificationLevel.BALANCED
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    schedule: str = "manual"         # manual, hourly, daily, weekly, monthly, on_connect
    schedule_time: str = "02:00"
    compression: str = "none"        # none, fast, balanced, max
    encryption: str = "none"         # none, vault_aes_gcm
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.tmp", "*.cache", "Thumbs.db", "desktop.ini", "$RECYCLE.BIN",
        "System Volume Information", "node_modules", "__pycache__", ".git"
    ])
    trusted_drive_serial: Optional[str] = None
    eject_after_backup: bool = False
    created_at: float = field(default_factory=time.time)
    last_run_at: Optional[float] = None
    last_status: str = "never_run"


@dataclass
class BackupJob:
    id: str
    profile_id: str
    job_type: str                    # backup, sync, restore, drill
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: JobStatus = JobStatus.PENDING
    files_scanned: int = 0
    files_copied: int = 0
    files_updated: int = 0
    files_deleted: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    bytes_processed: int = 0
    bytes_copied: int = 0
    verification_status: str = "pending"
    error_summary: str = ""


@dataclass
class FileVersion:
    file_id: str
    snapshot_id: str
    relative_path: str
    size_bytes: int
    mtime: float
    sha256: Optional[str] = None
    version_number: int = 1
    stored_path: str = ""


@dataclass
class BackupSnapshot:
    id: str
    profile_id: str
    job_id: str
    timestamp: float = field(default_factory=time.time)
    total_files: int = 0
    total_bytes: int = 0
    manifest_path: str = ""
    is_pinned: bool = False          # Pinned snapshots are kept forever
    note: str = ""


@dataclass
class SyncPair:
    id: str
    name: str
    side_a: str
    side_b: str
    mode: SyncMode = SyncMode.TWO_WAY
    conflict_policy: ConflictResolution = ConflictResolution.KEEP_BOTH
    delete_protection_threshold_pct: float = 10.0   # Warn if deleting > 10%
    delete_protection_threshold_count: int = 50    # Warn if deleting > 50 files
    sync_recycle_days: int = 14                    # Days to retain in .sinax_sync_recycle
    last_sync_at: Optional[float] = None
    last_status: str = "never_run"


@dataclass
class SyncConflict:
    id: str
    sync_id: str
    relative_path: str
    size_a: int
    mtime_a: float
    size_b: int
    mtime_b: float
    resolution: ConflictResolution = ConflictResolution.KEEP_BOTH
    resolved_at: Optional[float] = None


@dataclass
class PreflightCheckResult:
    is_valid: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    source_bytes: int = 0
    destination_free_bytes: int = 0
    is_same_physical_disk: bool = False
    is_fat32_over_4gb: bool = False
    fat32_violating_files: List[str] = field(default_factory=list)
