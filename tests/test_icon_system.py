# -*- coding: utf-8 -*-
"""
SINAX Icon System Unit & Regression Test Suite
Validates Microsoft Fluent UI icon assets, IconRegistry, IconService,
dynamic color substitution, RTL mirroring, QIcon generation, and LRU cache.
"""

import os
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtGui import QGuiApplication, QIcon, QPixmap

from app.core.icon_registry import (
    IconRegistry,
    IconService,
    ICON_CATEGORIES,
    RTL_MIRRORABLE_ICONS,
)
from app.ui.icons import get_icon

# Initialize Qt GUI application for pixmap tests
app = QGuiApplication.instance() or QGuiApplication(sys.argv)


class TestIconRegistry(unittest.TestCase):
    """Tests for IconRegistry semantic mappings, aliases, and metadata."""

    def test_canonical_entries_count(self):
        entries = IconRegistry.get_all()
        self.assertGreaterEqual(len(entries), 70, f"Expected at least 70 canonical icons, got {len(entries)}")

    def test_all_categories_present(self):
        categories = IconRegistry.get_categories()
        expected = ["actions", "devices", "files", "media", "navigation", "network", "security", "status", "system", "tools"]
        for cat in expected:
            self.assertIn(cat, categories, f"Missing category: {cat}")

    def test_semantic_resolution(self):
        self.assertEqual(IconRegistry.resolve("folder"), "folder")
        self.assertEqual(IconRegistry.resolve("home"), "home")
        self.assertEqual(IconRegistry.resolve("shield"), "shield")

    def test_alias_resolution(self):
        # Navigation aliases
        self.assertEqual(IconRegistry.resolve("files"), "folder")
        self.assertEqual(IconRegistry.resolve("file_manager"), "folder")
        self.assertEqual(IconRegistry.resolve("directory"), "folder")
        self.assertEqual(IconRegistry.resolve("security"), "shield")
        self.assertEqual(IconRegistry.resolve("protection"), "shield")
        self.assertEqual(IconRegistry.resolve("main"), "home")

        # Action aliases
        self.assertEqual(IconRegistry.resolve("fav"), "star")
        self.assertEqual(IconRegistry.resolve("favorite"), "star")
        self.assertEqual(IconRegistry.resolve("trash"), "delete")
        self.assertEqual(IconRegistry.resolve("remove"), "delete")
        self.assertEqual(IconRegistry.resolve("close"), "dismiss")

    def test_case_insensitivity_and_whitespace(self):
        self.assertEqual(IconRegistry.resolve("  FOLDER  "), "folder")
        self.assertEqual(IconRegistry.resolve("Shield"), "shield")
        self.assertEqual(IconRegistry.resolve("FILES"), "folder")

    def test_rtl_mirroring_metadata(self):
        # Directional icons MUST be mirrored
        for directional in ["back", "forward", "chevron_left", "chevron_right", "undo", "redo"]:
            self.assertTrue(IconRegistry.is_rtl_mirrored(directional), f"{directional} must be RTL mirrored")

        # Non-directional icons MUST NOT be mirrored
        for non_directional in ["folder", "shield", "play", "check", "settings", "search", "lock", "cpu"]:
            self.assertFalse(IconRegistry.is_rtl_mirrored(non_directional), f"{non_directional} must NOT be RTL mirrored")

    def test_all_registered_svg_files_exist_on_disk(self):
        audit = IconService.audit_icons()
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(len(audit["missing_files"]), 0, f"Missing icon SVG files: {audit['missing_files']}")
        self.assertGreaterEqual(audit["total_registered"], 75)


class TestIconSVGAssets(unittest.TestCase):
    """Validates SVG files structure, XML syntax, and viewBox."""

    def setUp(self):
        self.icons_dir = PROJECT_ROOT / "resources" / "icons"

    def test_svg_xml_validity_and_viewbox(self):
        svg_files = list(self.icons_dir.rglob("*.svg"))
        self.assertGreaterEqual(len(svg_files), 90, f"Expected at least 90 SVG files, found {len(svg_files)}")

        for svg_path in svg_files:
            try:
                tree = ET.parse(svg_path)
                root = tree.getroot()
                tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
                self.assertEqual(tag, "svg", f"{svg_path} root tag is <{tag}>, not <svg>")
                self.assertEqual(root.attrib.get("viewBox"), "0 0 24 24", f"{svg_path} viewBox != 0 0 24 24")
            except Exception as e:
                self.fail(f"Failed parsing {svg_path}: {e}")


class TestIconService(unittest.TestCase):
    """Tests for IconService dynamic tinting, pixmap generation, caching, and QIcon provision."""

    def test_get_svg_content_and_tinting(self):
        # Default content
        content_default = IconService.get_svg_content("folder")
        self.assertIsNotNone(content_default)
        self.assertIn("currentColor", content_default)

        # Tinted content
        content_tinted = IconService.get_svg_content("folder", color="#6366F1")
        self.assertIsNotNone(content_tinted)
        self.assertIn("#6366F1", content_tinted)
        self.assertNotIn("currentColor", content_tinted)

    def test_get_pixmap_generation(self):
        pixmap = IconService.get_pixmap("folder", size=32, color="#E2E8F0")
        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.width(), 32)
        self.assertEqual(pixmap.height(), 32)

    def test_get_pixmap_lru_cache(self):
        # First call caches
        pix1 = IconService.get_pixmap("settings", size=24, color="#FFFFFF")
        # Second call returns cached instance
        pix2 = IconService.get_pixmap("settings", size=24, color="#FFFFFF")
        self.assertFalse(pix1.isNull())
        self.assertFalse(pix2.isNull())
        self.assertEqual(pix1.size(), pix2.size())

    def test_get_pixmap_rtl_mirrored(self):
        pix_normal = IconService.get_pixmap("back", size=24, mirrored=False)
        pix_mirrored = IconService.get_pixmap("back", size=24, mirrored=True)
        self.assertFalse(pix_normal.isNull())
        self.assertFalse(pix_mirrored.isNull())

    def test_get_qicon(self):
        qicon = IconService.get_qicon("home", size=20, color="#6366F1")
        self.assertIsInstance(qicon, QIcon)
        self.assertFalse(qicon.isNull())

    def test_fallback_on_unknown_icon(self):
        # Non-existent icon should return fallback without crashing
        pix = IconService.get_pixmap("this_icon_does_not_exist_xyz_123", size=24)
        self.assertFalse(pix.isNull())
        qicon = IconService.get_qicon("this_icon_does_not_exist_xyz_123", size=24)
        self.assertFalse(qicon.isNull())

    def test_legacy_bridge_get_icon(self):
        icon = get_icon("folder", size=24, color="#38BDF8")
        self.assertIsInstance(icon, QIcon)
        self.assertFalse(icon.isNull())


if __name__ == "__main__":
    unittest.main()