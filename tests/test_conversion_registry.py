# -*- coding: utf-8 -*-
"""
Tests for Universal File Converter Registry and Definitions.
Verifies ~54 cards, 105 directions, format index, search, and category filtering.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

from app.services.conversion.registry import conversion_registry

class TestConversionRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = conversion_registry

    def test_total_cards_and_directions(self):
        cards = self.registry.get_all_cards()
        self.assertGreaterEqual(len(cards), 50, "Expected at least 50 conversion cards")
        
        total_directions = sum(1 + (1 if c.backward_dir else 0) for c in cards)
        self.assertGreaterEqual(total_directions, 100, "Expected at least 100 conversion directions")

    def test_all_categories_represented(self):
        cats = ["pdf", "documents", "spreadsheets", "presentations", "images", "audio", "video", "data", "ebooks", "archives"]
        for cat in cats:
            cards = self.registry.search_cards(category=cat)
            self.assertGreater(len(cards), 0, f"Category {cat} should have at least 1 card")

    def test_source_and_target_lookup(self):
        sources = self.registry.get_all_source_formats()
        self.assertIn("PDF", sources)
        self.assertIn("DOCX", sources)
        self.assertIn("PNG", sources)
        self.assertIn("JPG", sources)
        self.assertIn("MP4", sources)
        self.assertIn("CSV", sources)

        # PDF targets
        pdf_targets = self.registry.get_targets_for_source("PDF")
        self.assertIn("DOCX", pdf_targets)
        self.assertIn("TXT", pdf_targets)

        # Direct direction search
        d1 = self.registry.find_direction("PDF", "DOCX")
        self.assertIsNotNone(d1)
        self.assertEqual(d1.source_ext, "pdf")
        self.assertEqual(d1.target_ext, "docx")

        d2 = self.registry.find_direction("DOCX", "PDF")
        self.assertIsNotNone(d2)
        self.assertEqual(d2.source_ext, "docx")
        self.assertEqual(d2.target_ext, "pdf")

    def test_search_functionality(self):
        # Search by format
        pdf_results = self.registry.search_cards(query="PDF")
        self.assertGreaterEqual(len(pdf_results), 3)

        # Search by category
        image_results = self.registry.search_cards(category="images")
        self.assertGreaterEqual(len(image_results), 5)
        for c in image_results:
            self.assertEqual(c.category, "images")

    def test_file_drop_matching(self):
        pdf_file = Path("test_document.pdf")
        matched = self.registry.find_matching_cards_for_file(pdf_file)
        self.assertGreater(len(matched), 0)
        found_pdf_target = any(c.forward_dir.source_ext == "pdf" or (c.backward_dir and c.backward_dir.source_ext == "pdf") for c in matched)
        self.assertTrue(found_pdf_target)

        png_file = Path("sample_image.png")
        matched_png = self.registry.find_matching_cards_for_file(png_file)
        self.assertGreater(len(matched_png), 0)

if __name__ == "__main__":
    unittest.main()
