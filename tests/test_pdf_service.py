# -*- coding: utf-8 -*-
"""
SINAX Core PDF Engine Tests
Validates all 20+ operations of PDFService with real files and zero mocks.
"""

import unittest
import tempfile
import shutil
from pathlib import Path

import fitz
from PIL import Image

from app.services.pdf.pdf_service import pdf_service
from app.services.pdf.pdf_utils import parse_page_ranges, format_page_list


class TestPDFService(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="sinax_pdf_test_"))
        self.sample_pdf = self.test_dir / "sample.pdf"
        self._create_sample_pdf(self.sample_pdf, num_pages=5)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_sample_pdf(self, path: Path, num_pages: int = 5):
        """Creates a real valid multi-page PDF with text and graphics."""
        doc = fitz.open()
        for i in range(num_pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((50, 100), f"SINAX Test Document - Page {i+1}", fontsize=18)
            page.insert_text((50, 150), f"Confidential Data: SECRET_TOKEN_{i+1}", fontsize=14)
            # Add small graphic
            page.draw_rect(fitz.Rect(50, 200, 200, 250), color=(0, 0.4, 0.8), fill=(0.8, 0.9, 1))
        doc.save(str(path))
        doc.close()

    def test_page_range_parsing(self):
        self.assertEqual(parse_page_ranges("1, 3-4", 5), [0, 2, 3])
        self.assertEqual(parse_page_ranges("all", 5), [0, 1, 2, 3, 4])
        self.assertEqual(parse_page_ranges("", 3), [0, 1, 2])
        self.assertEqual(format_page_list([0, 1, 2, 4]), "1-3, 5")

    def test_merge_pdfs(self):
        pdf2 = self.test_dir / "sample2.pdf"
        self._create_sample_pdf(pdf2, num_pages=3)
        out_pdf = self.test_dir / "merged.pdf"

        pdf_service.merge_pdfs([(self.sample_pdf, "1-2"), (pdf2, "all")], out_pdf)
        self.assertTrue(out_pdf.exists())

        doc = fitz.open(str(out_pdf))
        self.assertEqual(len(doc), 5)  # 2 from sample1 + 3 from sample2
        doc.close()

    def test_split_pdf_pages(self):
        split_dir = self.test_dir / "splits"
        files = pdf_service.split_pdf(self.sample_pdf, split_dir, split_mode="pages")
        self.assertEqual(len(files), 5)
        for f in files:
            self.assertTrue(f.exists())
            doc = fitz.open(str(f))
            self.assertEqual(len(doc), 1)
            doc.close()

    def test_extract_pages(self):
        out_pdf = self.test_dir / "extracted.pdf"
        pdf_service.extract_pages(self.sample_pdf, out_pdf, "2, 4")
        self.assertTrue(out_pdf.exists())

        doc = fitz.open(str(out_pdf))
        self.assertEqual(len(doc), 2)
        doc.close()

    def test_delete_pages(self):
        out_pdf = self.test_dir / "deleted.pdf"
        pdf_service.delete_pages(self.sample_pdf, out_pdf, pages_str="1, 3")
        self.assertTrue(out_pdf.exists())

        doc = fitz.open(str(out_pdf))
        self.assertEqual(len(doc), 3)
        doc.close()

    def test_reorder_pages(self):
        out_pdf = self.test_dir / "reordered.pdf"
        pdf_service.reorder_pages(self.sample_pdf, out_pdf, [4, 3, 2, 1, 0])
        self.assertTrue(out_pdf.exists())

        doc = fitz.open(str(out_pdf))
        self.assertEqual(len(doc), 5)
        text_p1 = doc[0].get_text()
        self.assertIn("Page 5", text_p1)
        doc.close()

    def test_rotate_pages(self):
        out_pdf = self.test_dir / "rotated.pdf"
        pdf_service.rotate_pages(self.sample_pdf, out_pdf, angle=90, pages_str="1")
        self.assertTrue(out_pdf.exists())

        doc = fitz.open(str(out_pdf))
        self.assertEqual(doc[0].rotation, 90)
        self.assertEqual(doc[1].rotation, 0)
        doc.close()

    def test_crop_and_halve(self):
        out_pdf = self.test_dir / "cropped.pdf"
        pdf_service.crop_pages(self.sample_pdf, out_pdf, mode="margins", margins=(20, 20, 20, 20))
        self.assertTrue(out_pdf.exists())

        out_halve = self.test_dir / "halved.pdf"
        pdf_service.crop_pages(self.sample_pdf, out_halve, mode="halve_vertical", pages_str="1")
        doc = fitz.open(str(out_halve))
        self.assertEqual(len(doc), 6)  # 2 from page 1 + 4 original remaining
        doc.close()

    def test_compress_pdf(self):
        out_pdf = self.test_dir / "compressed.pdf"
        size = pdf_service.compress_pdf(self.sample_pdf, out_pdf, preset="strong")
        self.assertTrue(out_pdf.exists())
        self.assertGreater(size, 0)

    def test_pdf_to_images_and_back(self):
        img_dir = self.test_dir / "images"
        imgs = pdf_service.pdf_to_images(self.sample_pdf, img_dir, img_format="png", pages_str="1-2")
        self.assertEqual(len(imgs), 2)
        for img in imgs:
            self.assertTrue(img.exists())

        rebuilt_pdf = self.test_dir / "from_imgs.pdf"
        pdf_service.images_to_pdf(imgs, rebuilt_pdf)
        self.assertTrue(rebuilt_pdf.exists())
        doc = fitz.open(str(rebuilt_pdf))
        self.assertEqual(len(doc), 2)
        doc.close()

    def test_watermark_and_numbering(self):
        out_wm = self.test_dir / "watermarked.pdf"
        pdf_service.add_watermark(self.sample_pdf, out_wm, text="DRAFT - مسودة")
        self.assertTrue(out_wm.exists())

        out_nums = self.test_dir / "numbered.pdf"
        pdf_service.add_page_numbers(self.sample_pdf, out_nums, pattern="P.{page}")
        self.assertTrue(out_nums.exists())
        doc = fitz.open(str(out_nums))
        self.assertIn("P.1", doc[0].get_text())
        doc.close()

    def test_protect_and_unlock(self):
        enc_pdf = self.test_dir / "protected.pdf"
        pdf_service.protect_pdf(self.sample_pdf, enc_pdf, user_password="my_password_123")
        self.assertTrue(enc_pdf.exists())

        # Verify encrypted
        doc = fitz.open(str(enc_pdf))
        self.assertTrue(doc.is_encrypted)
        doc.close()

        # Unlock
        unlocked_pdf = self.test_dir / "unlocked.pdf"
        pdf_service.unlock_pdf(enc_pdf, unlocked_pdf, password="my_password_123")
        self.assertTrue(unlocked_pdf.exists())
        doc_u = fitz.open(str(unlocked_pdf))
        self.assertFalse(doc_u.is_encrypted)
        doc_u.close()

    def test_true_redaction(self):
        redacted_pdf = self.test_dir / "redacted.pdf"
        _, count = pdf_service.redact_pdf(self.sample_pdf, redacted_pdf, search_terms=["SECRET_TOKEN_1"])
        self.assertGreater(count, 0)
        self.assertTrue(redacted_pdf.exists())

        doc = fitz.open(str(redacted_pdf))
        text = doc[0].get_text()
        self.assertNotIn("SECRET_TOKEN_1", text)
        doc.close()

    def test_text_and_stats_and_repair(self):
        txt_file = self.test_dir / "extracted_text.txt"
        text = pdf_service.extract_text(self.sample_pdf, txt_file)
        self.assertIn("SINAX Test Document", text)
        self.assertTrue(txt_file.exists())

        stats = pdf_service.inspect_and_repair(self.sample_pdf)
        self.assertTrue(stats["is_valid"])
        self.assertEqual(stats["page_count"], 5)


if __name__ == "__main__":
    unittest.main()
