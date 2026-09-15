# -*- coding: utf-8 -*-
"""
SINAX Storage Snapshots & Timeline Service
Tracks drive and folder capacity growth over time using local SQLite storage:
- Stores historical snapshots of analyzed storage
- Compares snapshots (Growth Diff, Category changes, Folder growth)
- Space Exhaustion Forecast (Linear rate calculation of remaining days until disk full)
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_data_dir
from app.core.logger import get_logger
from app.services.system_storage.storage_analyzer import StorageAnalysisReport
from app.services.system_storage.storage_scanner import format_bytes

logger = get_logger("snapshot_service")


class SnapshotService:
    """Manages SQLite storage snapshots, diff analysis, and disk full predictions."""

    @classmethod
    def get_db_path(cls) -> Path:
        data_dir = get_data_dir()
        db_file = data_dir / "storage_snapshots.db"
        return db_file

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        db_path = cls.get_db_path()
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cls._init_db(conn)
        return conn

    @classmethod
    def _init_db(cls, conn: sqlite3.Connection):
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_path TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    date_str TEXT NOT NULL,
                    total_size INTEGER NOT NULL,
                    allocated_size INTEGER NOT NULL,
                    total_files INTEGER NOT NULL,
                    total_folders INTEGER NOT NULL,
                    categories_json TEXT,
                    top_folders_json TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_target ON snapshots(target_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON snapshots(timestamp)")

    @classmethod
    def save_snapshot(cls, report: StorageAnalysisReport) -> int:
        """Save storage analysis report as a point-in-time snapshot."""
        now = time.time()
        date_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")

        cat_dict = {}
        for k, v in report.categories.items():
            cat_dict[k] = {"size": v.size, "count": v.count}

        top_f_list = report.top_folders[:20] if report.top_folders else []

        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO snapshots (
                    target_path, timestamp, date_str, total_size, allocated_size,
                    total_files, total_folders, categories_json, top_folders_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.target_path,
                now,
                date_str,
                report.total_size,
                report.allocated_size,
                report.total_files,
                report.total_folders,
                json.dumps(cat_dict),
                json.dumps(top_f_list)
            ))
            snap_id = cursor.lastrowid or 0
            logger.info(f"Saved snapshot #{snap_id} for path: {report.target_path}")
            return snap_id

    @classmethod
    def list_snapshots(cls, target_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """List historical snapshots, optionally filtered by target directory."""
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            if target_path:
                norm_target = os.path.normpath(target_path).lower()
                cursor.execute("""
                    SELECT id, target_path, timestamp, date_str, total_size, allocated_size,
                           total_files, total_folders FROM snapshots
                    WHERE LOWER(target_path) = ?
                    ORDER BY timestamp DESC
                """, (norm_target,))
            else:
                cursor.execute("""
                    SELECT id, target_path, timestamp, date_str, total_size, allocated_size,
                           total_files, total_folders FROM snapshots
                    ORDER BY timestamp DESC LIMIT 100
                """)

            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "target_path": r["target_path"],
                    "timestamp": r["timestamp"],
                    "date_str": r["date_str"],
                    "total_size": r["total_size"],
                    "total_size_formatted": format_bytes(r["total_size"]),
                    "total_files": r["total_files"],
                    "total_folders": r["total_folders"],
                })
            return results

    @classmethod
    def get_snapshot(cls, snap_id: int) -> Optional[Dict[str, Any]]:
        """Get snapshot details by ID."""
        with cls._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM snapshots WHERE id = ?", (snap_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "target_path": row["target_path"],
                "timestamp": row["timestamp"],
                "date_str": row["date_str"],
                "total_size": row["total_size"],
                "total_size_formatted": format_bytes(row["total_size"]),
                "allocated_size": row["allocated_size"],
                "total_files": row["total_files"],
                "total_folders": row["total_folders"],
                "categories": json.loads(row["categories_json"] or "{}"),
                "top_folders": json.loads(row["top_folders_json"] or "[]"),
            }

    @classmethod
    def compare_snapshots(cls, snap_id_old: int, snap_id_new: int) -> Optional[Dict[str, Any]]:
        """Compare two snapshots and calculate changes in size, files, and categories."""
        old_s = cls.get_snapshot(snap_id_old)
        new_s = cls.get_snapshot(snap_id_new)
        if not old_s or not new_s:
            return None

        # Ensure chronological order
        if old_s["timestamp"] > new_s["timestamp"]:
            old_s, new_s = new_s, old_s

        size_diff = new_s["total_size"] - old_s["total_size"]
        files_diff = new_s["total_files"] - old_s["total_files"]
        days_diff = max(0.001, (new_s["timestamp"] - old_s["timestamp"]) / 86400.0)

        # Growth percentage
        pct_growth = (size_diff / old_s["total_size"] * 100.0) if old_s["total_size"] > 0 else 0.0

        # Category differences
        cat_diffs = {}
        all_cats = set(old_s["categories"].keys()) | set(new_s["categories"].keys())
        for c in all_cats:
            old_c_sz = old_s["categories"].get(c, {}).get("size", 0)
            new_c_sz = new_s["categories"].get(c, {}).get("size", 0)
            c_diff = new_c_sz - old_c_sz
            cat_diffs[c] = {
                "old_size": old_c_sz,
                "new_size": new_c_sz,
                "diff_bytes": c_diff,
                "diff_formatted": ("+" if c_diff > 0 else "") + format_bytes(c_diff)
            }

        return {
            "old_snapshot": old_s,
            "new_snapshot": new_s,
            "days_elapsed": round(days_diff, 1),
            "size_diff_bytes": size_diff,
            "size_diff_formatted": ("+" if size_diff > 0 else "") + format_bytes(size_diff),
            "files_diff": files_diff,
            "percentage_growth": round(pct_growth, 2),
            "category_diffs": cat_diffs
        }

    @classmethod
    def forecast_exhaustion(cls, drive_path: str) -> Dict[str, Any]:
        """Estimate remaining days until drive capacity exhaustion based on historical snapshots."""
        import psutil
        norm_drive = os.path.normpath(drive_path).lower()
        snapshots = cls.list_snapshots(norm_drive)

        # Need at least 2 snapshots to establish a trend
        if len(snapshots) < 2:
            return {
                "available": False,
                "reason_ar": "يلزم حفظ نقطتي فحص (Snapshots) على الأقل لحساب معدل استهلاك المساحة."
            }

        # Take oldest and newest
        sorted_snaps = sorted(snapshots, key=lambda x: x["timestamp"])
        oldest = sorted_snaps[0]
        newest = sorted_snaps[-1]

        time_delta_days = (newest["timestamp"] - oldest["timestamp"]) / 86400.0
        if time_delta_days < 0.01:
            return {
                "available": False,
                "reason_ar": "المدة الزمنية بين نقاط الفحص قصيرة جداً لتوقع الاستهلاك بدقة."
            }

        size_growth_bytes = newest["total_size"] - oldest["total_size"]
        growth_per_day = size_growth_bytes / time_delta_days

        # Get current free space
        try:
            usage = psutil.disk_usage(drive_path)
            free_bytes = usage.free
        except Exception:
            free_bytes = 0

        if growth_per_day <= 0:
            return {
                "available": True,
                "growth_per_day_bytes": growth_per_day,
                "growth_per_day_formatted": format_bytes(int(abs(growth_per_day))) + "/يوم",
                "is_shrinking_or_stable": True,
                "status_ar": "المساحة مستقرة أو في انخفاض إيجابي (لا يوجد خطر امتلاء)."
            }

        days_remaining = free_bytes / growth_per_day if growth_per_day > 0 else 999999
        predicted_date = datetime.now() + timedelta(days=days_remaining)

        return {
            "available": True,
            "growth_per_day_bytes": growth_per_day,
            "growth_per_day_formatted": format_bytes(int(growth_per_day)) + "/يوم",
            "is_shrinking_or_stable": False,
            "free_bytes": free_bytes,
            "free_formatted": format_bytes(free_bytes),
            "days_remaining": int(days_remaining),
            "predicted_full_date": predicted_date.strftime("%Y-%m-%d"),
            "status_ar": f"بمعدل النمو الحالي، يتوقع امتلاء القرص خلال {int(days_remaining)} يوم (قرابة {predicted_date.strftime('%Y-%m-%d')})."
        }
