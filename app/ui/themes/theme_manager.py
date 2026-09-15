# -*- coding: utf-8 -*-
"""
SINAX Theme Manager
Handles 3-mode theme switching (System / Light / Dark), Windows OS color scheme tracking,
and unified stylesheet injection across Qt Widgets and QML.
"""

import sys
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QGuiApplication
from app.core.config import config
from app.core.logger import get_logger

logger = get_logger("theme_manager")


def detect_windows_theme() -> str:
    """Detects Windows OS theme ('dark' or 'light') via QStyleHints or Registry fallback."""
    # 1. Qt 6.5+ QStyleHints
    try:
        app = QGuiApplication.instance()
        if app:
            hints = app.styleHints()
            if hasattr(hints, "colorScheme"):
                scheme = hints.colorScheme()
                if scheme == Qt.ColorScheme.Dark:
                    return "dark"
                elif scheme == Qt.ColorScheme.Light:
                    return "light"
    except Exception as e:
        logger.debug(f"QStyleHints color scheme detection failed: {e}")

    # 2. Windows Registry fallback
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if val == 1 else "dark"
    except Exception as e:
        logger.debug(f"Registry theme detection failed: {e}")

    return "dark"


class ThemeManager(QObject):
    theme_changed = Signal(str)       # Emits effective theme ("dark" or "light")
    mode_changed = Signal(str)        # Emits theme mode ("system", "light", "dark")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.themes_dir = Path(__file__).parent
        self._theme_mode: str = config.get("theme_mode", "system").lower()
        if self._theme_mode not in ("system", "light", "dark"):
            # Fallback for legacy "theme" key
            legacy = config.get("theme", "dark").lower()
            self._theme_mode = legacy if legacy in ("light", "dark") else "dark"

        self._effective_theme: str = self._resolve_effective_theme(self._theme_mode)
        self._setup_os_listener()

    def _setup_os_listener(self):
        """Listens for live Windows OS theme changes."""
        try:
            app = QGuiApplication.instance()
            if app:
                hints = app.styleHints()
                if hasattr(hints, "colorSchemeChanged"):
                    hints.colorSchemeChanged.connect(self._on_os_scheme_changed)
        except Exception as e:
            logger.debug(f"Could not hook OS theme listener: {e}")

    def _on_os_scheme_changed(self):
        """Called when Windows theme changes dynamically."""
        if self._theme_mode == "system":
            new_effective = detect_windows_theme()
            if new_effective != self._effective_theme:
                logger.info(f"Windows OS theme changed to: {new_effective}")
                self._apply_stylesheet(new_effective)

    def _resolve_effective_theme(self, mode: str) -> str:
        if mode == "system":
            return detect_windows_theme()
        elif mode == "light":
            return "light"
        else:
            return "dark"

    @property
    def theme_mode(self) -> str:
        return self._theme_mode

    @property
    def current_theme(self) -> str:
        return self._effective_theme

    @property
    def effective_theme(self) -> str:
        return self._effective_theme

    def set_theme_mode(self, mode: str) -> None:
        """Sets the theme mode ('system', 'light', or 'dark') and applies it immediately."""
        mode = mode.lower()
        if mode not in ("system", "light", "dark"):
            mode = "system"

        self._theme_mode = mode
        config.set("theme_mode", mode, auto_save=True)
        config.set("theme", self._resolve_effective_theme(mode), auto_save=True)

        new_effective = self._resolve_effective_theme(mode)
        self._apply_stylesheet(new_effective)
        self.mode_changed.emit(mode)

    def apply_theme(self, theme_name: str) -> None:
        """Sets explicit theme ('dark' or 'light') or 'system'."""
        self.set_theme_mode(theme_name)

    def _apply_stylesheet(self, theme_name: str) -> None:
        """Loads and applies the QSS stylesheet for the effective theme."""
        qss_file = self.themes_dir / f"{theme_name}.qss"
        if not qss_file.exists():
            logger.warning(f"Stylesheet not found: {qss_file}")
            return

        try:
            with open(qss_file, "r", encoding="utf-8") as f:
                stylesheet = f.read()

            app = QApplication.instance()
            if app:
                app.setStyleSheet(stylesheet)
                self._effective_theme = theme_name
                self.theme_changed.emit(theme_name)
                logger.info(f"Theme stylesheet applied: {theme_name} (Mode: {self._theme_mode})")
        except Exception as e:
            logger.error(f"Failed to apply theme {theme_name}: {e}")

    def toggle_theme(self) -> str:
        """Toggles between dark and light themes."""
        next_mode = "light" if self._effective_theme == "dark" else "dark"
        self.set_theme_mode(next_mode)
        return next_mode


# Global singleton instance
theme_manager = ThemeManager()

