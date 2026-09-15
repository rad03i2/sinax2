# -*- coding: utf-8 -*-
"""
SINAX Design System - Tokens & Palette
Unified Windows 11 Fluent-inspired theme constants, colors, typography,
and layout metrics ensuring visual harmony across all application modules.
"""

class ThemeTokens:
    # 1. Backgrounds & Surfaces
    BG_CANVAS = "#0D1117"        # Dark canvas (deepest layer)
    BG_SURFACE = "#161B22"       # Primary card and container surface
    BG_SURFACE_HOVER = "#1F242C" # Hover state on surface cards
    BG_ELEVATED = "#21262D"      # Secondary card, sidebar, elevated panels
    BG_ELEVATED_HOVER = "#2D333B"
    BG_INPUT = "#0F141C"         # Input fields, text areas, dropdowns

    # 2. Borders & Dividers (Subtle, professional - zero ugly harsh lines)
    BORDER_SUBTLE = "#30363D"     # Standard 1px card border
    BORDER_MUTED = "#21262D"      # Very soft divider
    BORDER_FOCUS = "#38BDF8"      # Focus ring
    BORDER_HOVER = "#484F58"      # Card hover outline

    # 3. Text Colors (Clear hierarchy)
    TEXT_PRIMARY = "#F0F6FC"      # Headings, primary titles, emphasized values
    TEXT_SECONDARY = "#8B949E"    # Subtitles, labels, descriptions
    TEXT_MUTED = "#57606A"        # Timestamps, helper text, disabled items
    TEXT_INVERSE = "#0D1117"      # Text on bright badges or primary buttons

    # 4. Brand & Accent (SINAX Tech Blue)
    ACCENT_PRIMARY = "#0078D4"    # Microsoft / SINAX primary blue
    ACCENT_LIGHT = "#38BDF8"      # Vibrant cyan-blue for active highlights
    ACCENT_GLOW = "rgba(56, 189, 248, 0.15)"
    ACCENT_HOVER = "#106EBE"

    # 5. Semantic Status Accents
    SUCCESS = "#34D399"           # Positive status, clean health, passed checks
    SUCCESS_BG = "rgba(52, 211, 153, 0.12)"
    SUCCESS_BORDER = "rgba(52, 211, 153, 0.35)"

    WARNING = "#FBBF24"           # Alerts, warnings, attention needed
    WARNING_BG = "rgba(251, 191, 36, 0.12)"
    WARNING_BORDER = "rgba(251, 191, 36, 0.35)"

    DANGER = "#F87171"            # Errors, critical failures, deletions
    DANGER_BG = "rgba(248, 113, 113, 0.12)"
    DANGER_BORDER = "rgba(248, 113, 113, 0.35)"

    INFO = "#60CDFF"              # Informational badges and tips
    INFO_BG = "rgba(96, 205, 255, 0.12)"
    INFO_BORDER = "rgba(96, 205, 255, 0.35)"

    # 6. Radii & Geometry
    RADIUS_SM = "4px"
    RADIUS_MD = "8px"
    RADIUS_LG = "10px"
    RADIUS_XL = "14px"
    RADIUS_PILL = "999px"

    BUTTON_HEIGHT = 36
    BUTTON_HEIGHT_SM = 28
    INPUT_HEIGHT = 34
    SIDEBAR_WIDTH = 250

    # Compatibility Aliases
    SURFACE_PRIMARY = BG_SURFACE
    SURFACE_SECONDARY = BG_ELEVATED
    BORDER_LIGHT = BORDER_SUBTLE
    PURPLE = "#A855F7"

    @staticmethod
    def is_dark(theme_name=None) -> bool:
        if theme_name is None:
            try:
                from app.ui.themes.theme_manager import theme_manager
                return theme_manager.effective_theme == "dark"
            except Exception:
                return True
        return str(theme_name).lower() == "dark"

    @classmethod
    def get_bg_card(cls, is_dark: bool = True) -> str:
        return "#1E293B" if is_dark else "#FFFFFF"

    @classmethod
    def get_bg_surface(cls, is_dark: bool = True) -> str:
        return "#161B22" if is_dark else "#FFFFFF"

    @classmethod
    def get_bg_elevated(cls, is_dark: bool = True) -> str:
        return "#21262D" if is_dark else "#F8FAFC"

    @classmethod
    def get_border_subtle(cls, is_dark: bool = True) -> str:
        return "#30363D" if is_dark else "#E2E8F0"

    @classmethod
    def get_text_primary(cls, is_dark: bool = True) -> str:
        return "#F0F6FC" if is_dark else "#0F172A"

    @classmethod
    def get_text_secondary(cls, is_dark: bool = True) -> str:
        return "#8B949E" if is_dark else "#64748B"

    @classmethod
    def get_chip_bg(cls, is_dark: bool = True) -> str:
        return "#21262D" if is_dark else "#F1F5F9"

    @classmethod
    def get_chip_border(cls, is_dark: bool = True) -> str:
        return "#30363D" if is_dark else "#CBD5E1"

    @classmethod
    def get_chip_text(cls, is_dark: bool = True) -> str:
        return "#CCCCCC" if is_dark else "#334155"

    @classmethod
    def get_chip_hover_bg(cls, is_dark: bool = True) -> str:
        return "#2D333B" if is_dark else "#E2E8F0"
