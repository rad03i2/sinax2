# -*- coding: utf-8 -*-
"""
SINAX Network Database Service (قاعدة بيانات الشبكة المحلية)
Provides persistent SQLite storage for speed test history, network snapshots,
and connection outage logs with automatic schema migrations.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from app.services.network.network_models import SpeedTestResult


class NetworkDatabase:
    """Manages SQLite storage for network metrics, history, and snapshots."""

    _db_path: Optional[Path] = None

    @classmethod
    def get_db_path(cls) -> Path:
        """Returns the path to the network database, creating directories if needed."""
        if cls._db_path is None:
            data_dir = Path.home() / ".sinax"
            data_dir.mkdir(parents=True, exist_ok=True)
            cls._db_path = data_dir / "network.db"
        return cls._db_path

    @classmethod
    @contextmanager
    def _get_connection(cls) -> Generator[sqlite3.Connection, None, None]:
        """Returns an active SQLite connection with row factory and WAL mode, safely closed."""
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
        """Initializes database tables and indices."""
        with cls._get_connection() as conn:
            # Speed Tests table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS speed_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    download_mbps REAL NOT NULL,
                    upload_mbps REAL NOT NULL,
                    ping_ms REAL NOT NULL,
                    jitter_ms REAL NOT NULL,
                    packet_loss_percent REAL NOT NULL,
                    provider_name TEXT,
                    adapter_name TEXT,
                    ssid TEXT,
                    timestamp TEXT NOT NULL
                )
            """)

            # Network Snapshots table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS network_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    config_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Outage History table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS network_outages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    outage_start TEXT NOT NULL,
                    outage_end TEXT,
                    duration_seconds INTEGER,
                    reason TEXT
                )
            """)

            # Indices for quick lookup
            conn.execute("CREATE INDEX IF NOT EXISTS idx_speed_timestamp ON speed_tests(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_outage_start ON network_outages(outage_start)")
            conn.commit()

    @classmethod
    def save_speed_test(cls, result: SpeedTestResult) -> int:
        """Saves a speed test record and returns the new row ID."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO speed_tests (
                    download_mbps, upload_mbps, ping_ms, jitter_ms, packet_loss_percent,
                    provider_name, adapter_name, ssid, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.download_mbps,
                result.upload_mbps,
                result.ping_ms,
                result.jitter_ms,
                result.packet_loss_percent,
                result.provider_name,
                result.adapter_name,
                result.ssid,
                result.timestamp.isoformat()
            ))
            conn.commit()
            return cur.lastrowid

    @classmethod
    def get_recent_speed_tests(cls, limit: int = 20) -> List[SpeedTestResult]:
        """Retrieves recent speed tests ordered by timestamp descending."""
        cls.init_db()
        tests = []
        with cls._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM speed_tests ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            for row in cur.fetchall():
                try:
                    ts = datetime.fromisoformat(row["timestamp"])
                except Exception:
                    ts = datetime.now()
                tests.append(SpeedTestResult(
                    id=row["id"],
                    download_mbps=float(row["download_mbps"]),
                    upload_mbps=float(row["upload_mbps"]),
                    ping_ms=float(row["ping_ms"]),
                    jitter_ms=float(row["jitter_ms"]),
                    packet_loss_percent=float(row["packet_loss_percent"]),
                    provider_name=row["provider_name"] or "Unknown",
                    adapter_name=row["adapter_name"] or "Unknown",
                    ssid=row["ssid"],
                    timestamp=ts
                ))
        return tests

    @classmethod
    def save_snapshot(cls, name: str, config_dict: Dict[str, Any]) -> int:
        """Saves a network configuration snapshot for rollback/comparison."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO network_snapshots (name, config_json, timestamp)
                VALUES (?, ?, ?)
            """, (name, json.dumps(config_dict, ensure_ascii=False), datetime.now().isoformat()))
            conn.commit()
            return cur.lastrowid

    @classmethod
    def get_latest_snapshot(cls) -> Optional[Dict[str, Any]]:
        """Retrieves the latest configuration snapshot if available."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("SELECT * FROM network_snapshots ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                try:
                    return {
                        "id": row["id"],
                        "name": row["name"],
                        "config": json.loads(row["config_json"]),
                        "timestamp": row["timestamp"]
                    }
                except Exception:
                    return None
        return None

    @classmethod
    def log_outage_start(cls, reason: str = "Internet Lost") -> int:
        """Logs the start of a network outage and returns outage row ID."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO network_outages (outage_start, reason)
                VALUES (?, ?)
            """, (datetime.now().isoformat(), reason))
            conn.commit()
            return cur.lastrowid

    @classmethod
    def log_outage_end(cls, outage_id: int):
        """Marks the end of an outage and computes the duration."""
        cls.init_db()
        with cls._get_connection() as conn:
            cur = conn.execute("SELECT outage_start FROM network_outages WHERE id = ?", (outage_id,))
            row = cur.fetchone()
            if row:
                try:
                    start_dt = datetime.fromisoformat(row["outage_start"])
                    end_dt = datetime.now()
                    dur = int((end_dt - start_dt).total_seconds())
                    conn.execute("""
                        UPDATE network_outages
                        SET outage_end = ?, duration_seconds = ?
                        WHERE id = ?
                    """, (end_dt.isoformat(), dur, outage_id))
                    conn.commit()
                except Exception:
                    pass

    @classmethod
    def get_outages(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves recent network outages ordered by start time descending."""
        cls.init_db()
        outages = []
        with cls._get_connection() as conn:
            cur = conn.execute("SELECT * FROM network_outages ORDER BY id DESC LIMIT ?", (limit,))
            for row in cur.fetchall():
                outages.append({
                    "id": row["id"],
                    "outage_start": row["outage_start"],
                    "outage_end": row["outage_end"],
                    "duration_seconds": row["duration_seconds"],
                    "reason": row["reason"],
                })
        return outages
