# -*- coding: utf-8 -*-
"""
SINAX Hardware Database Service (قاعدة بيانات لقطات وتغييرات العتاد)
Stores point-in-time hardware snapshots for before/after upgrade comparisons,
and logs hardware events with automatic connection management.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


class HardwareDatabase:
    """Manages SQLite storage for hardware snapshots and hardware events."""

    _db_path: Optional[Path] = None

    @classmethod
    def get_db_path(cls) -> Path:
        """Returns the path to the hardware database, creating directory if needed."""
        if cls._db_path is None:
            data_dir = Path.home() / ".sinax"
            data_dir.mkdir(parents=True, exist_ok=True)
            cls._db_path = data_dir / "hardware.db"
        return cls._db_path

    @classmethod
    @contextmanager
    def _get_connection(cls) -> Generator[sqlite3.Connection, None, None]:
        """Returns a safely managed SQLite connection with WAL mode."""
        conn = sqlite3.connect(str(cls.get_db_path()), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @classmethod
    def init_db(cls):
        """Initializes database tables for snapshots and events."""
        with cls._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hardware_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    system_summary_json TEXT NOT NULL,
                    full_hardware_json TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS hardware_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_time ON hardware_snapshots(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_time ON hardware_events(timestamp)")
            conn.commit()

    @classmethod
    def save_snapshot(cls, name: str, summary_dict: Dict[str, Any], full_dict: Dict[str, Any]) -> int:
        """Saves a hardware snapshot and returns row ID."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO hardware_snapshots (name, timestamp, system_summary_json, full_hardware_json)
                VALUES (?, ?, ?, ?)
            """, (
                name,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                json.dumps(summary_dict, ensure_ascii=False),
                json.dumps(full_dict, ensure_ascii=False)
            ))
            conn.commit()
            return cur.lastrowid

    @classmethod
    def get_snapshots(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves all saved hardware snapshots ordered by newest first."""
        cls.init_db()
        snapshots = []
        with cls._get_connection() as conn:
            cur = conn.execute("SELECT id, name, timestamp, system_summary_json FROM hardware_snapshots ORDER BY id DESC LIMIT ?", (limit,))
            for row in cur.fetchall():
                try:
                    summary = json.loads(row["system_summary_json"])
                except Exception:
                    summary = {}
                snapshots.append({
                    "id": row["id"],
                    "name": row["name"],
                    "timestamp": row["timestamp"],
                    "summary": summary
                })
        return snapshots

    @classmethod
    def get_snapshot_by_id(cls, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a full hardware snapshot by ID."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("SELECT * FROM hardware_snapshots WHERE id = ?", (snapshot_id,))
            row = cur.fetchone()
            if row:
                try:
                    return {
                        "id": row["id"],
                        "name": row["name"],
                        "timestamp": row["timestamp"],
                        "summary": json.loads(row["system_summary_json"]),
                        "full_hardware": json.loads(row["full_hardware_json"])
                    }
                except Exception:
                    return None
        return None

    @classmethod
    def delete_snapshot(cls, snapshot_id: int) -> bool:
        """Deletes a hardware snapshot by ID."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("DELETE FROM hardware_snapshots WHERE id = ?", (snapshot_id,))
            conn.commit()
            return cur.rowcount > 0

    @classmethod
    def log_event(cls, event_type: str, description: str) -> int:
        """Logs a hardware event (e.g. newly plugged USB, hardware changed)."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO hardware_events (timestamp, event_type, description)
                VALUES (?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                event_type,
                description
            ))
            conn.commit()
            return cur.lastrowid

    @classmethod
    def get_recent_events(cls, limit: int = 30) -> List[Dict[str, Any]]:
        """Returns recent hardware events."""
        cls.init_db()
        events = []
        with cls._get_connection() as conn:
            cur = conn.execute("SELECT * FROM hardware_events ORDER BY id DESC LIMIT ?", (limit,))
            for row in cur.fetchall():
                events.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "event_type": row["event_type"],
                    "description": row["description"]
                })
        return events
