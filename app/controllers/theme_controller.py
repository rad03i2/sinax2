# -*- coding: utf-8 -*-
"""
SINAX Theme Controller
Bridges Python ThemeManager state to QML Theme singleton and UI navigation controls.
"""

from PySide6.QtCore import QObject, Signal, Property, Slot
from app.ui.themes.theme_manager import theme_manager
from app.core.logger import get_logger

logger = get_logger("theme_controller")


class ThemeController(QObject):
    themeChanged = Signal(str)
    modeChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_theme = theme_manager.effective_theme
        self._theme_mode = theme_manager.theme_mode
        theme_manager.theme_changed.connect(self._on_theme_changed)
        theme_manager.mode_changed.connect(self._on_mode_changed)

    def _on_theme_changed(self, theme_name: str):
        self._current_theme = theme_name
        self.themeChanged.emit(theme_name)
        logger.debug(f"ThemeController synchronized effective theme: {theme_name}")

    def _on_mode_changed(self, mode: str):
        self._theme_mode = mode
        self.modeChanged.emit(mode)
        logger.debug(f"ThemeController synchronized mode: {mode}")

    @Property(bool, notify=themeChanged)
    def isDark(self) -> bool:
        return self._current_theme.lower() == "dark"

    @Property(str, notify=themeChanged)
    def effectiveTheme(self) -> str:
        return self._current_theme

    @Property(str, notify=themeChanged)
    def currentTheme(self) -> str:
        return self._current_theme

    @Property(str, notify=modeChanged)
    def themeMode(self) -> str:
        return self._theme_mode

    @Property(str, notify=modeChanged)
    def currentIcon(self) -> str:
        if self._theme_mode == "system":
            return "monitor"
        elif self._theme_mode == "light":
            return "sun"
        else:
            return "moon"

    @Slot(str)
    def setThemeMode(self, mode: str):
        theme_manager.set_theme_mode(mode)

    @Slot(str)
    def setTheme(self, theme_name: str):
        theme_manager.apply_theme(theme_name)

    @Slot()
    def toggleTheme(self):
        theme_manager.toggle_theme()


# Global Singleton Instance
theme_controller = ThemeController()

