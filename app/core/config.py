# -*- coding: utf-8 -*-
"""
SINAX Configuration Manager
Handles user preferences, persistence in AppData/JSON, and state persistence.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from app.core.logger import get_logger

logger = get_logger("config")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme": "dark",
    "language": "ar",
    "remember_last_folder": True,
    "last_folder": "",
    "recent_folders": [],
    "window_geometry": {
        "width": 1280,
        "height": 820,
        "is_maximized": False
    },
    "confirm_sensitive_ops": True,
    "use_recycle_bin": True,
    "log_level": "INFO",
    "custom_presets": []
}

class ConfigManager:
    """Singleton Configuration Manager for SINAX."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self):
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "settings.json"
        self._settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self.load()

    def _get_config_dir(self) -> Path:
        """Locates configuration directory in AppData or local fallback."""
        app_data = os.environ.get('APPDATA')
        if app_data:
            path = Path(app_data) / "SINAX"
        else:
            path = Path.home() / ".sinax"
        
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception:
            local = Path("config")
            local.mkdir(parents=True, exist_ok=True)
            return local

    def load(self) -> None:
        """Loads settings from disk, applying defaults for missing keys."""
        if not self.config_file.exists():
            self.save()
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    self._settings.update(saved)
            logger.info("Configuration successfully loaded.")
        except Exception as e:
            logger.error(f"Error loading configuration, using defaults: {e}")

    def save(self) -> None:
        """Persists current settings to disk safely."""
        try:
            temp_file = self.config_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.config_file)
            logger.debug("Configuration saved.")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value."""
        return self._settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Sets a configuration value and optionally persists immediately."""
        self._settings[key] = value
        if auto_save:
            self.save()

    def add_recent_folder(self, folder_path: str) -> None:
        """Adds a folder to recent folders list without duplicates, max 10 entries."""
        if not folder_path or not os.path.isdir(folder_path):
            return
        
        normalized = str(Path(folder_path).resolve())
        recents: List[str] = self.get("recent_folders", [])
        
        # Remove if already present
        if normalized in recents:
            recents.remove(normalized)
        
        recents.insert(0, normalized)
        recents = recents[:10]  # keep top 10
        self.set("recent_folders", recents, auto_save=False)
        self.set("last_folder", normalized, auto_save=True)

    def get_recent_folders(self) -> List[str]:
        """Returns existing recent folders."""
        recents = self.get("recent_folders", [])
        return [f for f in recents if os.path.isdir(f)]

config = ConfigManager()


def get_data_dir() -> Path:
    """Returns the application data directory."""
    return config.config_dir
