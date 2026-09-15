# -*- coding: utf-8 -*-
"""
SINAX Undo & History Manager
Stores operation logs, file state diffs, and executes rollbacks safely.
"""

import json
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import config
from app.core.logger import get_logger

logger = get_logger("undo_manager")

class HistoryRecord:
    """Represents a logged batch operation."""
    def __init__(
        self,
        op_type: str,
        folder: str,
        items: List[Dict[str, str]],
        record_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        success: bool = True,
        status: str = "completed",
        details: Optional[str] = None
    ):
        self.record_id = record_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.op_type = op_type  # 'rename', 'move', 'organize', etc.
        self.folder = folder
        self.items = items  # List of {'original': str, 'target': str}
        self.success = success
        self.status = status  # 'completed', 'reverted', 'failed'
        self.details = details or f"تمت معالجة {len(items)} ملف"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "op_type": self.op_type,
            "folder": self.folder,
            "count": len(self.items),
            "items": self.items,
            "success": self.success,
            "status": self.status,
            "details": self.details
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryRecord":
        return cls(
            op_type=data.get("op_type", "unknown"),
            folder=data.get("folder", ""),
            items=data.get("items", []),
            record_id=data.get("record_id"),
            timestamp=data.get("timestamp"),
            success=data.get("success", True),
            status=data.get("status", "completed"),
            details=data.get("details")
        )

class UndoManager:
    """Manages history persistence and rollback logic."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UndoManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.history_file = config.config_dir / "history.json"
        self._records: List[HistoryRecord] = []
        self.load()

    def load(self) -> None:
        """Loads records from disk."""
        if not self.history_file.exists():
            return
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._records = [HistoryRecord.from_dict(d) for d in data]
            logger.info(f"Loaded {len(self._records)} history records.")
        except Exception as e:
            logger.error(f"Failed to load history: {e}")

    def save(self) -> None:
        """Saves records to disk."""
        try:
            # Keep up to 100 recent operations
            trimmed = self._records[:100]
            data = [r.to_dict() for r in trimmed]
            temp_file = self.history_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.history_file)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def record_operation(self, op_type: str, folder: str, items: List[Dict[str, str]], success: bool = True, details: str = "") -> HistoryRecord:
        """Creates and stores a new history entry."""
        rec = HistoryRecord(op_type=op_type, folder=folder, items=items, success=success, details=details)
        self._records.insert(0, rec)
        self.save()
        logger.info(f"Recorded operation {op_type} with {len(items)} items.")
        return rec

    def get_last_undoable(self) -> Optional[HistoryRecord]:
        """Returns the most recent operation that can be reverted."""
        for rec in self._records:
            if rec.status == "completed" and rec.success and rec.items:
                return rec
        return None

    def get_all_records(self) -> List[HistoryRecord]:
        """Returns full operation history."""
        return list(self._records)

    def get_recent_records(self, limit: int = 50) -> List[HistoryRecord]:
        """Returns recent operation history up to limit."""
        return list(self._records[:limit])

    def mark_reverted(self, record_id: str) -> None:
        """Marks a record as reverted."""
        for r in self._records:
            if r.record_id == record_id:
                r.status = "reverted"
                r.details = f"تم التراجع عن العملية بتاريخ {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                break
        self.save()

    def clear_history(self) -> None:
        """Clears all stored history."""
        self._records.clear()
        self.save()

undo_manager = UndoManager()
