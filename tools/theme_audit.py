# -*- coding: utf-8 -*-
"""
SINAX Developer Tool - Theme Audit
Scans Python, QML, and QSS files for hardcoded colors and style violations.
Categorizes every match into:
- THEME_VIOLATION: Hardcoded surface/background/text/border color that breaks Light/Dark modes
- BRAND_COLOR: Official SINAX brand blues and accents
- STATUS_COLOR: Universal status indicators (success, warning, error, info, categories)
- INTENTIONAL_PREVIEW_COLOR: Content preview or media presentation colors
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"

# Regex for color patterns
HEX_COLOR_RE = re.compile(r'#[0-9a-fA-F]{8}|#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3,4}')
RGB_COLOR_RE = re.compile(r'rgba?\s*\([^)]+\)', re.IGNORECASE)
STYLE_PROP_RE = re.compile(r'(background(-color)?|color|border(-color)?)\s*:\s*([^;\n"]+)', re.IGNORECASE)
SET_STYLE_RE = re.compile(r'setStyleSheet\s*\(', re.IGNORECASE)

BRAND_HEXES = {
    "#0078d4", "#38bdf8", "#60cdff", "#106ebe", "#004578",
    "#0284c7", "#2563eb", "#1d4ed8", "#3b82f6", "#0369a1",
    "#075985", "#7dd3fc", "#e0f2fe", "#152636"
}

STATUS_HEXES = {
    # Success / Green
    "#34d399", "#52c41a", "#43a047", "#238636", "#2e7d32", "#107c41", "#dcfce7", "#0d2818",
    # Warning / Amber / Orange
    "#fbbf24", "#ffb900", "#ffa940", "#d29922", "#d84315", "#d24726", "#fb8c00", "#fef9c3", "#2a1f08",
    # Danger / Red / Error
    "#f87171", "#e81123", "#e53935", "#f85149", "#fee2e2", "#2e1114",
    # Info / Purple
    "#8950fc", "#8e24aa", "#a855f7", "#00b4d8", "#546e7a", "#757575"
}

PREVIEW_KEYWORDS = [
    "preview", "paper", "canvas", "pdf_page", "document", "sample",
    "extension", "format", "category", "file_categories", "star",
    "transparent", "none", "inherit", "qscrollarea"
]


def classify_match(file_path: Path, line_num: int, line_text: str, token: str) -> str:
    token_lower = token.lower().strip()
    line_lower = line_text.lower()

    # 1. Check if intentional preview / content color
    for kw in PREVIEW_KEYWORDS:
        if kw in line_lower:
            return "INTENTIONAL_PREVIEW_COLOR"

    # 2. Check if brand color
    for bh in BRAND_HEXES:
        if bh in token_lower:
            return "BRAND_COLOR"

    # 3. Check if semantic status / category color
    for sh in STATUS_HEXES:
        if sh in token_lower:
            return "STATUS_COLOR"

    # 4. Check if inside Theme.qml or tokens.py (source of truth definitions)
    if file_path.name in ("Theme.qml", "tokens.py", "dark.qss", "light.qss"):
        return "BRAND_COLOR"

    # 5. Check if theme-aware ternary in QML: (isDark ? "#..." : "#...")
    if "isdark" in line_lower or "theme." in line_lower or "theme_name" in line_lower:
        return "BRAND_COLOR"

    # 6. Hardcoded surface/background/text/border colors in components
    if any(k in line_lower for k in ["background", "color:", "#1", "#2", "#3", "#f", "#0", "white", "black"]):
        return "THEME_VIOLATION"

    return "THEME_VIOLATION"


def run_audit(verbose: bool = True) -> Dict[str, int]:
    extensions = [".py", ".qml", ".qss"]
    counts = {
        "THEME_VIOLATION": 0,
        "BRAND_COLOR": 0,
        "STATUS_COLOR": 0,
        "INTENTIONAL_PREVIEW_COLOR": 0,
        "TOTAL_MATCHES": 0
    }
    violations_list: List[Tuple[str, int, str, str]] = []

    for ext in extensions:
        for file_path in APP_DIR.rglob(f"*{ext}"):
            if "__pycache__" in str(file_path) or ".git" in str(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, start=1):
                        line_stripped = line.strip()
                        if line_stripped.startswith("//") or line_stripped.startswith("#"):
                            continue

                        # Find hex colors
                        hex_matches = HEX_COLOR_RE.findall(line)
                        for hm in hex_matches:
                            category = classify_match(file_path, line_idx, line, hm)
                            counts[category] += 1
                            counts["TOTAL_MATCHES"] += 1
                            if category == "THEME_VIOLATION":
                                violations_list.append((str(file_path.relative_to(ROOT_DIR)), line_idx, hm, line_stripped))

                        # Find setStyleSheet calls
                        if "setStyleSheet" in line and not hex_matches:
                            category = classify_match(file_path, line_idx, line, "setStyleSheet")
                            counts[category] += 1
                            counts["TOTAL_MATCHES"] += 1
                            if category == "THEME_VIOLATION":
                                violations_list.append((str(file_path.relative_to(ROOT_DIR)), line_idx, "setStyleSheet", line_stripped))

            except Exception as e:
                print(f"Error scanning {file_path}: {e}", file=sys.stderr)

    print("=" * 60)
    print("           SINAX THEME ARCHITECTURE AUDIT REPORT           ")
    print("=" * 60)
    print(f"Total potential color tokens checked : {counts['TOTAL_MATCHES']}")
    print(f"Brand & Theme Design Tokens         : {counts['BRAND_COLOR']}")
    print(f"Status & Category Semantic Accents  : {counts['STATUS_COLOR']}")
    print(f"Intentional Preview & Media Colors  : {counts['INTENTIONAL_PREVIEW_COLOR']}")
    print(f"Remaining Potential Violations      : {counts['THEME_VIOLATION']}")
    print("-" * 60)

    if violations_list and verbose:
        print("\n[POTENTIAL VIOLATIONS DETAIL]")
        for rel_path, line_no, token, code in violations_list[:25]:
            print(f"  {rel_path}:{line_no} [{token}] -> {code[:80]}")
        if len(violations_list) > 25:
            print(f"  ... and {len(violations_list) - 25} more.")

    print("=" * 60)
    return counts


if __name__ == "__main__":
    run_audit()
