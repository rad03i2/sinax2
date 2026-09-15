# -*- coding: utf-8 -*-
"""
SINAX Standardized Fluent Buttons
Consistent heights, radii, typography, and interactive hover/press states.
"""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton
from app.ui.design_system.tokens import ThemeTokens
from app.ui.icons import get_icon


class PrimaryButton(QPushButton):
    """Primary action button with SINAX blue accent styling."""

    def __init__(self, text: str, icon_name: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setText(f"  {text}" if icon_name else text)
        self.setFixedHeight(ThemeTokens.BUTTON_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        if icon_name:
            self.setIcon(get_icon(icon_name, "#FFFFFF", 16))

        self.setStyleSheet(f"""
            PrimaryButton, QPushButton#{self.objectName()} {{
                background-color: {ThemeTokens.ACCENT_PRIMARY};
                color: #FFFFFF;
                border: 1px solid {ThemeTokens.ACCENT_PRIMARY};
                border-radius: {ThemeTokens.RADIUS_MD};
                padding: 0 18px;
                font-size: 13px;
                font-weight: bold;
            }}
            PrimaryButton:hover {{
                background-color: {ThemeTokens.ACCENT_HOVER};
                border-color: {ThemeTokens.ACCENT_HOVER};
            }}
            PrimaryButton:pressed {{
                background-color: #004578;
            }}
            PrimaryButton:disabled {{
                background-color: {ThemeTokens.BG_ELEVATED};
                border-color: {ThemeTokens.BORDER_SUBTLE};
                color: {ThemeTokens.TEXT_MUTED};
            }}
        """)


class SecondaryButton(QPushButton):
    """Secondary surface button with subtle border."""

    def __init__(self, text: str, icon_name: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setText(f"  {text}" if icon_name else text)
        self.setFixedHeight(ThemeTokens.BUTTON_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        if icon_name:
            self.setIcon(get_icon(icon_name, ThemeTokens.TEXT_PRIMARY, 16))

        self.setStyleSheet(f"""
            SecondaryButton, QPushButton#{self.objectName()} {{
                background-color: {ThemeTokens.BG_ELEVATED};
                color: {ThemeTokens.TEXT_PRIMARY};
                border: 1px solid {ThemeTokens.BORDER_SUBTLE};
                border-radius: {ThemeTokens.RADIUS_MD};
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            SecondaryButton:hover {{
                background-color: {ThemeTokens.BG_ELEVATED_HOVER};
                border-color: {ThemeTokens.BORDER_HOVER};
            }}
            SecondaryButton:pressed {{
                background-color: {ThemeTokens.BG_SURFACE};
            }}
            SecondaryButton:disabled {{
                color: {ThemeTokens.TEXT_MUTED};
                border-color: {ThemeTokens.BORDER_MUTED};
            }}
        """)


class DangerButton(QPushButton):
    """Destructive or stop action button with subtle red glow."""

    def __init__(self, text: str, icon_name: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setText(f"  {text}" if icon_name else text)
        self.setFixedHeight(ThemeTokens.BUTTON_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        if icon_name:
            self.setIcon(get_icon(icon_name, "#FFFFFF", 16))

        self.setStyleSheet(f"""
            DangerButton, QPushButton#{self.objectName()} {{
                background-color: #B91C1C;
                color: #FFFFFF;
                border: 1px solid #DC2626;
                border-radius: {ThemeTokens.RADIUS_MD};
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            DangerButton:hover {{
                background-color: #DC2626;
                border-color: #EF4444;
            }}
            DangerButton:pressed {{
                background-color: #991B1B;
            }}
        """)
