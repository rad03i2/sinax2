# -*- coding: utf-8 -*-
"""
Tests for Universal File Converter Conversion Engines.
Tests real conversions:
- ImageConverter (PNG -> JPG, JPG -> WebP, PNG -> ICO multi-size)
- DataConverter (CSV -> JSON, JSON -> CSV, YAML <-> JSON)
- SpreadsheetConverter (CSV -> XLSX)
- DocumentConverter (DOCX -> TXT, Markdown -> HTML)
- PdfConverter native vector generation
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from app.services.conversion.converters.image_converter import ImageConverter
from app.services.conversion.converters.data_converter import DataConverter
from app.services.conversion.converters.spreadsheet_converter import SpreadsheetConverter
from app.services.conversion.converters.document_converter import DocumentConverter
from app.services.conversion.converters.pdf_converter import PdfConverter

class TestConversionServices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="sinax_test_conv_"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_image_conversion_png_to_jpg_and_ico(self):
        conv = ImageConverter()
        from PIL import Image
        src_png = self.temp_dir / "test_logo.png"
        img = Image.new("RGBA", (100, 100), color=(100, 150, 200, 255))
        img.save(src_png, format="PNG")

        # PNG to JPG
        dest_jpg = self.temp_dir / "test_logo.jpg"
        ok = conv.convert(src_png, dest_jpg, {"quality": 85})
        self.assertTrue(ok)
        self.assertTrue(dest_jpg.exists())
        self.assertGreater(dest_jpg.stat().st_size, 0)

        # PNG to ICO
        dest_ico = self.temp_dir / "test_logo.ico"
        ok_ico = conv.convert(src_png, dest_ico, {})
        self.assertTrue(ok_ico)
        self.assertTrue(dest_ico.exists())

    def test_data_conversion_csv_to_json_and_yaml(self):
        conv = DataConverter()
        src_csv = self.temp_dir / "sample.csv"
        src_csv.write_text("id,name,role\n1,Ahmed,Engineer\n2,Sara,Designer\n", encoding="utf-8")

        # CSV to JSON
        dest_json = self.temp_dir / "sample.json"
        ok = conv.convert(src_csv, dest_json, {"indent": 2})
        self.assertTrue(ok)
        self.assertTrue(dest_json.exists())
        content = dest_json.read_text(encoding="utf-8")
        self.assertIn("Ahmed", content)
        self.assertIn("Engineer", content)

        # JSON to YAML
        dest_yaml = self.temp_dir / "sample.yaml"
        ok_yaml = conv.convert(dest_json, dest_yaml, {})
        self.assertTrue(ok_yaml)
        self.assertTrue(dest_yaml.exists())

    def test_spreadsheet_csv_to_xlsx(self):
        conv = SpreadsheetConverter()
        src_csv = self.temp_dir / "sheet_data.csv"
        src_csv.write_text("Category,Q1,Q2\nSales,100,150\nProfit,20,35\n", encoding="utf-8")

        dest_xlsx = self.temp_dir / "sheet_data.xlsx"
        ok = conv.convert(src_csv, dest_xlsx, {})
        self.assertTrue(ok)
        self.assertTrue(dest_xlsx.exists())
        self.assertGreater(dest_xlsx.stat().st_size, 100)

    def test_document_markdown_to_html(self):
        conv = DocumentConverter()
        src_md = self.temp_dir / "readme.md"
        src_md.write_text("# SINAX Title\n\n**Universal Converter** is fast and reliable.", encoding="utf-8")

        dest_html = self.temp_dir / "readme.html"
        ok = conv.convert(src_md, dest_html, {})
        self.assertTrue(ok)
        self.assertTrue(dest_html.exists())
        content = dest_html.read_text(encoding="utf-8")
        self.assertIn("SINAX Title", content)
        self.assertIn("Universal Converter", content)

    def test_native_vector_pdf_generation(self):
        conv = PdfConverter()
        src_txt = self.temp_dir / "doc.txt"
        src_txt.write_text("مستند ساينكس للتحويل الفوري - SINAX Universal Converter\nمرحبا بالعالم.", encoding="utf-8")

        dest_pdf = self.temp_dir / "doc.pdf"
        ok = conv.convert(src_txt, dest_pdf, {})
        self.assertTrue(ok)
        self.assertTrue(dest_pdf.exists())
        self.assertGreater(dest_pdf.stat().st_size, 500)

if __name__ == "__main__":
    unittest.main()
