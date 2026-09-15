# -*- coding: utf-8 -*-
"""
SINAX Quick Tools Local SQLite Database
Manages favorites, tool usage statistics, and optional local clipboard history.
Stored locally in ~/.sinax/quick_tools.db with WAL mode and zero network telemetry.
"""

from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple


class QuickToolsDatabase:
    """Manages local storage for Quick Tools favorites, usage metrics, and recents."""

    _instance: Optional["QuickToolsDatabase"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _get_db_path(self) -> Path:
        base_dir = Path.home() / ".sinax"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "quick_tools.db"

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self._get_db_path()), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")

            # 1. Pinned Favorites
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    tool_id TEXT PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Tool Usage & Recents
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_usage (
                    tool_id TEXT PRIMARY KEY,
                    use_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Optional Local Clipboard History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clipboard_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_type TEXT NOT NULL,
                    content_preview TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    copied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Settings (e.g. clipboard history enabled/disabled)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quick_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

    # --- Favorites API ---
    def get_favorites(self) -> List[str]:
        """Returns list of pinned tool IDs sorted by added_at descending."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT tool_id FROM favorites ORDER BY added_at DESC;")
                return [row["tool_id"] for row in cursor.fetchall()]
        except Exception:
            return []

    def is_favorite(self, tool_id: str) -> bool:
        """Checks if a tool is pinned."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM favorites WHERE tool_id = ?;", (tool_id,))
                return cursor.fetchone() is not None
        except Exception:
            return False

    def toggle_favorite(self, tool_id: str) -> bool:
        """Toggles favorite state. Returns True if now favorite, False otherwise."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM favorites WHERE tool_id = ?;", (tool_id,))
                exists = cursor.fetchone() is not None
                if exists:
                    cursor.execute("DELETE FROM favorites WHERE tool_id = ?;", (tool_id,))
                    return False
                else:
                    cursor.execute("INSERT OR REPLACE INTO favorites (tool_id) VALUES (?);", (tool_id,))
                    return True
        except Exception:
            return False

    # --- Usage & Recents API ---
    def record_tool_usage(self, tool_id: str):
        """Records a tool launch or execution, incrementing count and updating last_used."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tool_usage (tool_id, use_count, last_used)
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(tool_id) DO UPDATE SET
                        use_count = use_count + 1,
                        last_used = CURRENT_TIMESTAMP;
                """, (tool_id,))
        except Exception:
            pass

    def get_recent_tools(self, limit: int = 10) -> List[str]:
        """Returns most recently used tool IDs."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tool_id FROM tool_usage
                    ORDER BY last_used DESC
                    LIMIT ?;
                """, (limit,))
                return [row["tool_id"] for row in cursor.fetchall()]
        except Exception:
            return []

    def get_most_used_tools(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Returns most frequently used tool IDs and their counts."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tool_id, use_count FROM tool_usage
                    ORDER BY use_count DESC, last_used DESC
                    LIMIT ?;
                """, (limit,))
                return [(row["tool_id"], row["use_count"]) for row in cursor.fetchall()]
        except Exception:
            return []

    # --- Optional Clipboard History API ---
    def is_clipboard_history_enabled(self) -> bool:
        """Returns whether clipboard history recording is active (default False for privacy)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM quick_settings WHERE key = 'clipboard_history_enabled';")
                row = cursor.fetchone()
                return row["value"] == "1" if row else False
        except Exception:
            return False

    def set_clipboard_history_enabled(self, enabled: bool):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO quick_settings (key, value)
                    VALUES ('clipboard_history_enabled', ?);
                """, ("1" if enabled else "0",))
        except Exception:
            pass

    def add_clipboard_entry(self, content_type: str, preview: str, char_count: int):
        if not self.is_clipboard_history_enabled():
            return
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO clipboard_history (content_type, content_preview, char_count)
                    VALUES (?, ?, ?);
                """, (content_type, preview[:200], char_count))
        except Exception:
            pass

    def get_clipboard_history(self, limit: int = 30) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, content_type, content_preview, char_count, copied_at
                    FROM clipboard_history
                    ORDER BY copied_at DESC
                    LIMIT ?;
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def clear_clipboard_history(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM clipboard_history;")
        except Exception:
            pass
