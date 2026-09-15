# -*- coding: utf-8 -*-
"""
SINAX Privacy & Security Database
SQLite-backed persistence for security events, monitored baselines,
registered vaults, and audit history. Operates in WAL mode.
"""

import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional


class PrivacyDatabase:
    """Thread-safe SQLite database manager for Privacy & Security center."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PrivacyDatabase, cls).__new__(cls)
                cls._instance._init_db(db_path)
            return cls._instance

    def _init_db(self, custom_path: Optional[str] = None):
        if custom_path:
            self.db_path = Path(custom_path)
        else:
            base_dir = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / ".sinax"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "privacy_security.db"

        self._local_lock = threading.Lock()
        self._create_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _create_schema(self):
        with self._local_lock:
            with self._get_connection() as conn:
                conn.executescript("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    target_path TEXT,
                    status TEXT NOT NULL,
                    details_json TEXT,
                    timestamp REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS monitored_folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_path TEXT UNIQUE NOT NULL,
                    baseline_manifest TEXT,
                    ignore_patterns TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at REAL NOT NULL,
                    last_checked REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS vault_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vault_path TEXT UNIQUE NOT NULL,
                    mode TEXT NOT NULL,
                    cipher TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    total_files INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS privacy_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scope TEXT NOT NULL,
                    summary_text TEXT NOT NULL,
                    findings_json TEXT NOT NULL,
                    timestamp REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_ts ON security_events(timestamp);
                """)

    def log_event(self, event_type: str, target_path: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Records a security event in the audit log (never logs secret contents)."""
        with self._local_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO security_events (event_type, target_path, status, details_json, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (event_type, target_path, status, json.dumps(details or {}, ensure_ascii=False), time.time())
                )

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves most recent security events."""
        with self._local_lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT id, event_type, target_path, status, details_json, timestamp FROM security_events ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                results = []
                for row in cur.fetchall():
                    results.append({
                        "id": row["id"],
                        "event_type": row["event_type"],
                        "target_path": row["target_path"],
                        "status": row["status"],
                        "details": json.loads(row["details_json"] or "{}"),
                        "timestamp": row["timestamp"],
                    })
                return results

    def add_monitored_folder(self, folder_path: str, baseline_manifest: Dict[str, Any], ignore_patterns: str = "*.tmp;~*;__pycache__;.cache"):
        with self._local_lock:
            with self._get_connection() as conn:
                now = time.time()
                conn.execute(
                    """
                    INSERT INTO monitored_folders (folder_path, baseline_manifest, ignore_patterns, is_active, created_at, last_checked)
                    VALUES (?, ?, ?, 1, ?, ?)
                    ON CONFLICT(folder_path) DO UPDATE SET
                        baseline_manifest = excluded.baseline_manifest,
                        ignore_patterns = excluded.ignore_patterns,
                        last_checked = excluded.last_checked
                    """,
                    (folder_path, json.dumps(baseline_manifest, ensure_ascii=False), ignore_patterns, now, now)
                )

    def get_monitored_folders(self) -> List[Dict[str, Any]]:
        with self._local_lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, folder_path, baseline_manifest, ignore_patterns, is_active, created_at, last_checked FROM monitored_folders WHERE is_active = 1")
                rows = []
                for r in cur.fetchall():
                    rows.append({
                        "id": r["id"],
                        "folder_path": r["folder_path"],
                        "baseline": json.loads(r["baseline_manifest"] or "{}"),
                        "ignore_patterns": r["ignore_patterns"],
                        "created_at": r["created_at"],
                        "last_checked": r["last_checked"]
                    })
                return rows

    def remove_monitored_folder(self, folder_path: str):
        with self._local_lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM monitored_folders WHERE folder_path = ?", (folder_path,))

    def register_vault(self, vault_path: str, mode: str, cipher: str = "AES-256-GCM", total_files: int = 1):
        with self._local_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO vault_registry (vault_path, mode, cipher, created_at, total_files)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(vault_path) DO UPDATE SET
                        mode = excluded.mode,
                        cipher = excluded.cipher,
                        total_files = excluded.total_files
                    """,
                    (vault_path, mode, cipher, time.time(), total_files)
                )

    def get_registered_vaults(self) -> List[Dict[str, Any]]:
        with self._local_lock:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT id, vault_path, mode, cipher, created_at, total_files FROM vault_registry ORDER BY created_at DESC")
                return [dict(r) for r in cur.fetchall()]

    def save_privacy_report(self, scope: str, summary_text: str, findings: Dict[str, Any]) -> int:
        with self._local_lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO privacy_reports (scope, summary_text, findings_json, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (scope, summary_text, json.dumps(findings, ensure_ascii=False), time.time())
                )
                return cur.lastrowid

    def get_recent_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves most recent privacy scan reports."""
        with self._local_lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT id, scope, summary_text, findings_json, timestamp FROM privacy_reports ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                results = []
                for row in cur.fetchall():
                    results.append({
                        "id": row["id"],
                        "scope": row["scope"],
                        "summary_text": row["summary_text"],
                        "findings": json.loads(row["findings_json"] or "{}"),
                        "timestamp": row["timestamp"],
                    })
                return results

