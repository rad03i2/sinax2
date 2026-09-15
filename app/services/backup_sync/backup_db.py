# -*- coding: utf-8 -*-
"""
SINAX Backup & Sync Database Service.
Persistent SQLite storage with WAL mode for profiles, jobs, snapshots,
file versions, sync pairs, tombstones, and trusted device pairing.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional
from app.core.logger import get_logger
from app.services.backup_sync.models import (
    BackupJob,
    BackupProfile,
    BackupSnapshot,
    BackupType,
    ConflictResolution,
    DriveIdentity,
    FileVersion,
    IncrementalMode,
    JobStatus,
    RetentionPolicy,
    SyncMode,
    SyncPair,
    VerificationLevel,
)

logger = get_logger("backup_db")


class BackupDatabase:
    """Thread-safe SQLite manager for SINAX Backup & Sync."""

    _instances: Dict[str, "BackupDatabase"] = {}

    def __new__(cls, db_path: Optional[str] = None):
        target_path = db_path
        if target_path is None:
            base_dir = Path.home() / ".sinax"
            base_dir.mkdir(parents=True, exist_ok=True)
            target_path = str(base_dir / "backup_sync.db")

        if target_path not in cls._instances:
            inst = super(BackupDatabase, cls).__new__(cls)
            inst._initialized = False
            inst.db_path = target_path
            cls._instances[target_path] = inst
        return cls._instances[target_path]

    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:
            return
        self._init_db()
        self._initialized = True

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            # 1. Profiles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backup_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    backup_type TEXT NOT NULL,
                    incremental_mode TEXT NOT NULL,
                    verification_level TEXT NOT NULL,
                    retention_json TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    schedule_time TEXT NOT NULL,
                    compression TEXT NOT NULL,
                    encryption TEXT NOT NULL,
                    exclude_patterns TEXT NOT NULL,
                    trusted_drive_serial TEXT,
                    eject_after_backup INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    last_run_at REAL,
                    last_status TEXT DEFAULT 'never_run'
                )
            """)

            # 2. Jobs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backup_jobs (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    status TEXT NOT NULL,
                    files_scanned INTEGER DEFAULT 0,
                    files_copied INTEGER DEFAULT 0,
                    files_updated INTEGER DEFAULT 0,
                    files_deleted INTEGER DEFAULT 0,
                    files_skipped INTEGER DEFAULT 0,
                    files_failed INTEGER DEFAULT 0,
                    bytes_processed INTEGER DEFAULT 0,
                    bytes_copied INTEGER DEFAULT 0,
                    verification_status TEXT DEFAULT 'pending',
                    error_summary TEXT DEFAULT ''
                )
            """)

            # 3. Snapshots
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backup_snapshots (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    manifest_path TEXT DEFAULT '',
                    is_pinned INTEGER DEFAULT 0,
                    note TEXT DEFAULT ''
                )
            """)

            # 4. File Versions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_versions (
                    file_id TEXT PRIMARY KEY,
                    snapshot_id TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    sha256 TEXT,
                    version_number INTEGER DEFAULT 1,
                    stored_path TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_path ON file_versions(profile_id, relative_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_snapshot ON file_versions(snapshot_id)")

            # 5. Sync Pairs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_pairs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    side_a TEXT NOT NULL,
                    side_b TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    conflict_policy TEXT NOT NULL,
                    delete_threshold_pct REAL DEFAULT 10.0,
                    delete_threshold_count INTEGER DEFAULT 50,
                    sync_recycle_days INTEGER DEFAULT 14,
                    last_sync_at REAL,
                    last_status TEXT DEFAULT 'never_run'
                )
            """)

            # 6. Sync Tombstones (for deletion tracking in 2-way sync)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_tombstones (
                    id TEXT PRIMARY KEY,
                    sync_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    side TEXT NOT NULL,
                    deleted_at REAL NOT NULL
                )
            """)

            # 7. Trusted Drives
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trusted_drives (
                    volume_serial TEXT PRIMARY KEY,
                    volume_label TEXT DEFAULT '',
                    model TEXT DEFAULT '',
                    is_trusted INTEGER DEFAULT 1,
                    paired_at REAL NOT NULL,
                    last_seen_at REAL NOT NULL
                )
            """)

    # ----------------- Profile Operations -----------------
    def save_profile(self, profile: BackupProfile):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO backup_profiles (
                    id, name, sources, destination, backup_type, incremental_mode,
                    verification_level, retention_json, schedule, schedule_time,
                    compression, encryption, exclude_patterns, trusted_drive_serial,
                    eject_after_backup, created_at, last_run_at, last_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.id,
                profile.name,
                json.dumps(profile.sources, ensure_ascii=False),
                profile.destination,
                profile.backup_type.value if hasattr(profile.backup_type, 'value') else str(profile.backup_type),
                profile.incremental_mode.value if hasattr(profile.incremental_mode, 'value') else str(profile.incremental_mode),
                profile.verification_level.value if hasattr(profile.verification_level, 'value') else str(profile.verification_level),
                json.dumps(profile.retention.__dict__, ensure_ascii=False),
                profile.schedule,
                profile.schedule_time,
                profile.compression,
                profile.encryption,
                json.dumps(profile.exclude_patterns, ensure_ascii=False),
                profile.trusted_drive_serial,
                1 if profile.eject_after_backup else 0,
                profile.created_at,
                profile.last_run_at,
                profile.last_status,
            ))

    def get_profile(self, profile_id: str) -> Optional[BackupProfile]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM backup_profiles WHERE id = ?", (profile_id,)).fetchone()
            if not row:
                return None
            return self._row_to_profile(row)

    def list_profiles(self) -> List[BackupProfile]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM backup_profiles ORDER BY created_at DESC").fetchall()
            return [self._row_to_profile(r) for r in rows]

    def delete_profile(self, profile_id: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM backup_profiles WHERE id = ?", (profile_id,))
            conn.execute("DELETE FROM backup_snapshots WHERE profile_id = ?", (profile_id,))
            conn.execute("DELETE FROM file_versions WHERE profile_id = ?", (profile_id,))

    def _row_to_profile(self, r: sqlite3.Row) -> BackupProfile:
        ret_dict = json.loads(r["retention_json"]) if r["retention_json"] else {}
        ret = RetentionPolicy(**ret_dict)
        return BackupProfile(
            id=r["id"],
            name=r["name"],
            sources=json.loads(r["sources"]) if r["sources"] else [],
            destination=r["destination"],
            backup_type=BackupType(r["backup_type"]),
            incremental_mode=IncrementalMode(r["incremental_mode"]),
            verification_level=VerificationLevel(r["verification_level"]),
            retention=ret,
            schedule=r["schedule"],
            schedule_time=r["schedule_time"],
            compression=r["compression"],
            encryption=r["encryption"],
            exclude_patterns=json.loads(r["exclude_patterns"]) if r["exclude_patterns"] else [],
            trusted_drive_serial=r["trusted_drive_serial"],
            eject_after_backup=bool(r["eject_after_backup"]),
            created_at=r["created_at"],
            last_run_at=r["last_run_at"],
            last_status=r["last_status"],
        )

    # ----------------- Job Operations -----------------
    def save_job(self, job: BackupJob):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO backup_jobs (
                    id, profile_id, job_type, start_time, end_time, status,
                    files_scanned, files_copied, files_updated, files_deleted,
                    files_skipped, files_failed, bytes_processed, bytes_copied,
                    verification_status, error_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.profile_id, job.job_type, job.start_time, job.end_time,
                job.status.value if hasattr(job.status, 'value') else str(job.status),
                job.files_scanned, job.files_copied, job.files_updated, job.files_deleted,
                job.files_skipped, job.files_failed, job.bytes_processed, job.bytes_copied,
                job.verification_status, job.error_summary
            ))

    def list_recent_jobs(self, limit: int = 50) -> List[BackupJob]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM backup_jobs ORDER BY start_time DESC LIMIT ?", (limit,)).fetchall()
            jobs = []
            for r in rows:
                jobs.append(BackupJob(
                    id=r["id"], profile_id=r["profile_id"], job_type=r["job_type"],
                    start_time=r["start_time"], end_time=r["end_time"],
                    status=JobStatus(r["status"]) if r["status"] in JobStatus._value2member_map_ else JobStatus.COMPLETED,
                    files_scanned=r["files_scanned"], files_copied=r["files_copied"],
                    files_updated=r["files_updated"], files_deleted=r["files_deleted"],
                    files_skipped=r["files_skipped"], files_failed=r["files_failed"],
                    bytes_processed=r["bytes_processed"], bytes_copied=r["bytes_copied"],
                    verification_status=r["verification_status"], error_summary=r["error_summary"]
                ))
            return jobs

    # ----------------- Snapshot & Version Operations -----------------
    def save_snapshot(self, snapshot: BackupSnapshot):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO backup_snapshots (
                    id, profile_id, job_id, timestamp, total_files, total_bytes,
                    manifest_path, is_pinned, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.id, snapshot.profile_id, snapshot.job_id, snapshot.timestamp,
                snapshot.total_files, snapshot.total_bytes, snapshot.manifest_path,
                1 if snapshot.is_pinned else 0, snapshot.note
            ))

    def list_snapshots(self, profile_id: str) -> List[BackupSnapshot]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM backup_snapshots WHERE profile_id = ? ORDER BY timestamp DESC", (profile_id,)
            ).fetchall()
            return [
                BackupSnapshot(
                    id=r["id"], profile_id=r["profile_id"], job_id=r["job_id"],
                    timestamp=r["timestamp"], total_files=r["total_files"],
                    total_bytes=r["total_bytes"], manifest_path=r["manifest_path"],
                    is_pinned=bool(r["is_pinned"]), note=r["note"]
                ) for r in rows
            ]

    def set_snapshot_pinned(self, snapshot_id: str, is_pinned: bool):
        with self._get_connection() as conn:
            conn.execute("UPDATE backup_snapshots SET is_pinned = ? WHERE id = ?", (1 if is_pinned else 0, snapshot_id))

    def save_file_version(self, version: FileVersion, profile_id: str):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO file_versions (
                    file_id, snapshot_id, profile_id, relative_path, size_bytes,
                    mtime, sha256, version_number, stored_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version.file_id, version.snapshot_id, profile_id, version.relative_path,
                version.size_bytes, version.mtime, version.sha256, version.version_number,
                version.stored_path
            ))

    def get_file_versions(self, profile_id: str, relative_path: str) -> List[FileVersion]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM file_versions 
                WHERE profile_id = ? AND relative_path = ?
                ORDER BY version_number DESC
            """, (profile_id, relative_path)).fetchall()
            return [
                FileVersion(
                    file_id=r["file_id"], snapshot_id=r["snapshot_id"],
                    relative_path=r["relative_path"], size_bytes=r["size_bytes"],
                    mtime=r["mtime"], sha256=r["sha256"], version_number=r["version_number"],
                    stored_path=r["stored_path"]
                ) for r in rows
            ]

    def search_backup_files(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        pattern = f"%{query}%"
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT v.*, p.name as profile_name, s.timestamp as snapshot_time
                FROM file_versions v
                JOIN backup_profiles p ON v.profile_id = p.id
                JOIN backup_snapshots s ON v.snapshot_id = s.id
                WHERE v.relative_path LIKE ?
                ORDER BY v.mtime DESC
                LIMIT ?
            """, (pattern, limit)).fetchall()
            return [dict(r) for r in rows]

    # ----------------- Sync Pairs Operations -----------------
    def save_sync_pair(self, pair: SyncPair):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sync_pairs (
                    id, name, side_a, side_b, mode, conflict_policy,
                    delete_threshold_pct, delete_threshold_count, sync_recycle_days,
                    last_sync_at, last_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pair.id, pair.name, pair.side_a, pair.side_b,
                pair.mode.value if hasattr(pair.mode, 'value') else str(pair.mode),
                pair.conflict_policy.value if hasattr(pair.conflict_policy, 'value') else str(pair.conflict_policy),
                pair.delete_protection_threshold_pct, pair.delete_protection_threshold_count,
                pair.sync_recycle_days, pair.last_sync_at, pair.last_status
            ))

    def list_sync_pairs(self) -> List[SyncPair]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM sync_pairs ORDER BY name ASC").fetchall()
            return [
                SyncPair(
                    id=r["id"], name=r["name"], side_a=r["side_a"], side_b=r["side_b"],
                    mode=SyncMode(r["mode"]), conflict_policy=ConflictResolution(r["conflict_policy"]),
                    delete_protection_threshold_pct=r["delete_threshold_pct"],
                    delete_protection_threshold_count=r["delete_threshold_count"],
                    sync_recycle_days=r["sync_recycle_days"],
                    last_sync_at=r["last_sync_at"], last_status=r["last_status"]
                ) for r in rows
            ]

    def delete_sync_pair(self, pair_id: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM sync_pairs WHERE id = ?", (pair_id,))

    # ----------------- Trusted Drives -----------------
    def register_trusted_drive(self, serial: str, label: str = "", model: str = ""):
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO trusted_drives (
                    volume_serial, volume_label, model, is_trusted, paired_at, last_seen_at
                ) VALUES (?, ?, ?, 1, ?, ?)
            """, (serial, label, model, now, now))

    def get_trusted_drives(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM trusted_drives WHERE is_trusted = 1").fetchall()
            return [dict(r) for r in rows]

    def is_drive_trusted(self, serial: str) -> bool:
        if not serial:
            return False
        with self._get_connection() as conn:
            row = conn.execute("SELECT 1 FROM trusted_drives WHERE volume_serial = ? AND is_trusted = 1", (serial,)).fetchone()
            return bool(row)
