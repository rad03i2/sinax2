# -*- coding: utf-8 -*-
"""
SINAX Conversion History & Preferences
Maintains local usage counts, favorites (⭐), and persistent conversion logs.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import config
from app.core.logger import get_logger

logger = get_logger("conversion_history")

HISTORY_FILE = config.config_dir / "conversion_history.json"


class ConversionHistoryManager:
    """Manages conversion logs, favorite cards, and usage metrics locally."""

    @staticmethod
    def _load_history() -> List[Dict[str, Any]]:
        if not HISTORY_FILE.exists():
            return []
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error loading conversion history: {e}")
            return []

    @staticmethod
    def _save_history(records: List[Dict[str, Any]]):
        try:
            # Keep max 500 records
            records = records[-500:]
            HISTORY_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving conversion history: {e}")

    @classmethod
    def record_conversion(
        cls,
        card_id: str,
        source_ext: str,
        target_ext: str,
        total_files: int,
        success_count: int,
        fail_count: int,
        output_dir: str,
        options: Optional[Dict[str, Any]] = None,
        error_details: Optional[List[str]] = None
    ) -> str:
        """Records a completed or partially completed conversion job."""
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "timestamp": datetime.now().isoformat(),
            "card_id": card_id,
            "source_ext": source_ext.lower().lstrip('.'),
            "target_ext": target_ext.lower().lstrip('.'),
            "total_files": total_files,
            "success_count": success_count,
            "fail_count": fail_count,
            "output_dir": output_dir,
            "options": options or {},
            "errors": error_details or []
        }

        history = cls._load_history()
        history.append(record)
        cls._save_history(history)

        # Increment usage counter locally
        cls.increment_usage(card_id)
        return record_id

    @classmethod
    def get_recent_history(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent conversion jobs."""
        records = cls._load_history()
        records.reverse()
        return records[:limit]

    @classmethod
    def clear_history(cls):
        """Clears all conversion history."""
        cls._save_history([])

    # ----------------------------------------------------
    # FAVORITES
    # ----------------------------------------------------
    @staticmethod
    def get_favorites() -> List[str]:
        """Returns list of favorite card IDs."""
        favs = config.get("converter_favorites", ["pdf_word", "jpg_png", "excel_csv", "mp4_mkv"])
        return favs if isinstance(favs, list) else []

    @classmethod
    def is_favorite(cls, card_id: str) -> bool:
        return card_id in cls.get_favorites()

    @classmethod
    def toggle_favorite(cls, card_id: str) -> bool:
        """Toggles favorite state of card_id and returns new state (True=favorited)."""
        favs = set(cls.get_favorites())
        if card_id in favs:
            favs.remove(card_id)
            is_fav = False
        else:
            favs.add(card_id)
            is_fav = True
        config.set("converter_favorites", list(favs), auto_save=True)
        return is_fav

    # ----------------------------------------------------
    # USAGE METRICS (Local Most Used)
    # ----------------------------------------------------
    @staticmethod
    def get_usage_counts() -> Dict[str, int]:
        """Returns map of card_id -> usage count."""
        counts = config.get("converter_usage_counts", {})
        return counts if isinstance(counts, dict) else {}

    @classmethod
    def increment_usage(cls, card_id: str):
        counts = cls.get_usage_counts()
        counts[card_id] = counts.get(card_id, 0) + 1
        config.set("converter_usage_counts", counts, auto_save=True)

    @classmethod
    def get_most_used_card_ids(cls, limit: int = 10) -> List[str]:
        counts = cls.get_usage_counts()
        sorted_cards = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in sorted_cards[:limit]]
