# -*- coding: utf-8 -*-
"""
SINAX Startup Crash Recovery & Safe UI Mode Manager
Tracks startup reliability and manages safe fallback states.
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any

from app.core.config import config
from app.core.logger import get_logger

logger = get_logger("crash_recovery")

RECOVERY_FILE_NAME = ".startup_recovery.json"
MAX_CONSECUTIVE_CRASHES = 2
STARTUP_WINDOW_SECONDS = 30.0


class CrashRecoveryManager:
    """Manages crash detection during startup and handles Safe UI Mode activation."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CrashRecoveryManager, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.recovery_path = config.config_dir / RECOVERY_FILE_NAME
        self._safe_mode_override = "--safe-ui" in sys.argv
        self._state: Dict[str, Any] = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.recovery_path.exists():
            try:
                with open(self.recovery_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read recovery file: {e}")
        return {"consecutive_crashes": 0, "last_startup_timestamp": 0.0, "clean_exit": True}

    def _save_state(self):
        try:
            with open(self.recovery_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write recovery file: {e}")

    def record_startup_begin(self):
        """Called immediately at application start."""
        now = time.time()
        last_time = self._state.get("last_startup_timestamp", 0.0)
        clean = self._state.get("clean_exit", True)

        # If previous run did not finish startup cleanly within reasonable window, count as crash
        if not clean and (now - last_time < 300.0):
            self._state["consecutive_crashes"] = self._state.get("consecutive_crashes", 0) + 1
            logger.warning(f"Detected previous unclean startup. Consecutive crash count: {self._state['consecutive_crashes']}")
        else:
            if clean:
                self._state["consecutive_crashes"] = 0

        self._state["clean_exit"] = False
        self._state["last_startup_timestamp"] = now
        self._save_state()

    def record_startup_success(self):
        """Called once the UI has fully loaded and stabilized."""
        self._state["consecutive_crashes"] = 0
        self._state["clean_exit"] = True
        self._save_state()
        logger.info("Startup marked as successful. Crash recovery counter reset.")

    def should_enter_safe_mode(self) -> bool:
        """Determines if application must start in Safe UI Mode."""
        if self._safe_mode_override:
            logger.info("Safe UI Mode triggered via command-line argument (--safe-ui).")
            return True
        crashes = self._state.get("consecutive_crashes", 0)
        if crashes >= MAX_CONSECUTIVE_CRASHES:
            logger.warning(f"Safe UI Mode automatically triggered due to {crashes} consecutive startup crashes.")
            return True
        return False

    def reset_recovery_state(self):
        """Resets all crash state and flags."""
        self._state = {"consecutive_crashes": 0, "last_startup_timestamp": time.time(), "clean_exit": True}
        self._save_state()

    def perform_self_repair(self) -> Dict[str, Any]:
        """Executes self-repair routines (clearing caches, resetting recovery counters)."""
        repaired_items = []
        try:
            # 1. Reset recovery flags
            self.reset_recovery_state()
            repaired_items.append("تصفير مؤشرات أخطاء الإقلاع المتكررة")

            # 2. Clear temp / cache files in user data
            cache_dir = config.config_dir / "cache"
            if cache_dir.exists():
                for item in cache_dir.glob("*"):
                    try:
                        if item.is_file():
                            item.unlink()
                    except Exception:
                        pass
                repaired_items.append("مسح كاش وذاكرة التخزين المؤقت")

            return {"success": True, "items": repaired_items}
        except Exception as e:
            return {"success": False, "error": str(e)}


crash_recovery_manager = CrashRecoveryManager()
