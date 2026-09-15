# -*- coding: utf-8 -*-
"""
SINAX Software Inventory Snapshots Service
Tracks software installations over time and provides snapshot diffs
(identifies newly installed, removed, and updated applications).
"""

from datetime import datetime
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from app.services.apps_manager.app_model import InstalledApp

logger = logging.getLogger("SINAX.apps_manager.app_snapshot_service")


class AppSnapshotService:
    """Manages application inventory snapshots in SQLite."""

    DB_FILE = os.path.join(os.path.expanduser("~"), r".gemini\antigravity\app_snapshots.db")

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(cls.DB_FILE), exist_ok=True)
        conn = sqlite3.connect(cls.DB_FILE)
        conn.row_factory = sqlite3.Row
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    total_apps INTEGER NOT NULL,
                    total_size INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshot_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    app_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    package_id TEXT,
                    source TEXT,
                    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
                )
            """)
        return conn

    @classmethod
    def save_snapshot(cls, name: str, apps: List[InstalledApp]) -> int:
        """Saves a software state snapshot."""
        total_size = sum(a.effective_size_bytes for a in apps)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with cls._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO snapshots (name, created_at, total_apps, total_size) VALUES (?, ?, ?, ?)",
                (name, now_str, len(apps), total_size),
            )
            snapshot_id = cur.lastrowid

            items = [
                (
                    snapshot_id,
                    a.name,
                    a.version,
                    a.publisher,
                    a.effective_size_bytes,
                    a.package_id,
                    a.source,
                )
                for a in apps
            ]
            cur.executemany(
                """
                INSERT INTO snapshot_items (snapshot_id, app_name, version, publisher, size_bytes, package_id, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                items,
            )

        logger.info(f"Saved snapshot #{snapshot_id} '{name}' with {len(apps)} apps.")
        return snapshot_id

    @classmethod
    def get_all_snapshots(cls) -> List[Dict[str, Any]]:
        """Returns list of all saved snapshots."""
        with cls._get_connection() as conn:
            rows = conn.execute("SELECT * FROM snapshots ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    @classmethod
    def compare_snapshots(cls, old_snapshot_id: int, new_snapshot_id: int) -> Dict[str, Any]:
        """Compares two snapshots and identifies added, removed, and updated software."""
        with cls._get_connection() as conn:
            old_items = conn.execute(
                "SELECT app_name, version, publisher, size_bytes FROM snapshot_items WHERE snapshot_id = ?",
                (old_snapshot_id,),
            ).fetchall()
            new_items = conn.execute(
                "SELECT app_name, version, publisher, size_bytes FROM snapshot_items WHERE snapshot_id = ?",
                (new_snapshot_id,),
            ).fetchall()

        old_map = {r["app_name"].lower(): r for r in old_items}
        new_map = {r["app_name"].lower(): r for r in new_items}

        added = []
        for name, item in new_map.items():
            if name not in old_map:
                added.append(dict(item))

        removed = []
        for name, item in old_map.items():
            if name not in new_map:
                removed.append(dict(item))

        updated = []
        for name, n_item in new_map.items():
            if name in old_map:
                o_item = old_map[name]
                if n_item["version"] != o_item["version"] and n_item["version"] != "غير محدد":
                    updated.append({
                        "name": n_item["app_name"],
                        "old_version": o_item["version"],
                        "new_version": n_item["version"],
                        "publisher": n_item["publisher"],
                    })

        return {
            "added": added,
            "removed": removed,
            "updated": updated,
            "added_count": len(added),
            "removed_count": len(removed),
            "updated_count": len(updated),
        }
