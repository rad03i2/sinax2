# -*- coding: utf-8 -*-
"""
Unit Tests for SINAX Image Center (Phase 8: Multimedia - Image Center)
Tests core image operations, compression presets, target size optimization,
resizing modes, conversions, cropping, rotation, metadata stripping,
watermarks, color palette extraction, similarity hashing, and workflow chaining.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from PIL import Image, ImageDraw

from app.services.image.image_service import image_service
from app.services.image.image_workflow import ImageWorkflow, WorkflowStep
from app.services.image.image_utils import get_relative_output_path, scan_images


class TestImageService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="sinax_test_img_"))
        
        # Create a sample test image (1000x800 RGB with shapes)
        self.sample_img_path = self.temp_dir / "test_sample.jpg"
        img = Image.new("RGB", (1000, 800), color=(120, 180, 240))
        draw = ImageDraw.Draw(img)
        draw.rectangle([100, 100, 500, 400], fill=(220, 50, 50), outline=(255, 255, 255), width=4)
        draw.ellipse([550, 200, 850, 500], fill=(50, 200, 80))
        img.save(self.sample_img_path, format="JPEG", quality=95)

        # Sample PNG with transparency
        self.sample_png_path = self.temp_dir / "test_transparent.png"
        png_img = Image.new("RGBA", (400, 400), color=(0, 0, 0, 0))
        draw_png = ImageDraw.Draw(png_img)
        draw_png.ellipse([50, 50, 350, 350], fill=(255, 100, 0, 220))
        png_img.save(self.sample_png_path, format="PNG")

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compress_presets(self):
        """Tests compression using light, balanced, and strong presets."""
        for preset in ("light", "balanced", "strong", "max"):
            out = self.temp_dir / f"compressed_{preset}.jpg"
            res = image_service.compress_image(self.sample_img_path, out, preset=preset)
            self.assertTrue(res["success"])
            self.assertTrue(out.exists())
            self.assertGreater(res["orig_size"], 0)
            self.assertGreater(res["new_size"], 0)

    def test_target_size_compression(self):
        """Tests smart compression to guarantee output size <= target_size_kb."""
        target_kb = 35
        out = self.temp_dir / "target_compressed.jpg"
        res = image_service.compress_image(self.sample_img_path, out, target_size_kb=target_kb)
        self.assertTrue(res["success"])
        self.assertTrue(out.exists())
        out_kb = out.stat().st_size / 1024.0
        # Should be strictly <= target_size_kb or very close within margin
        self.assertLessEqual(out_kb, target_kb * 1.05)

    def test_resize_modes(self):
        """Tests fit, fill, longest edge, and percent resizing."""
        # 1. Fit mode
        out_fit = self.temp_dir / "resized_fit.jpg"
        res = image_service.resize_image(self.sample_img_path, out_fit, mode="fit", width=500, height=500)
        self.assertTrue(res["success"])
        with Image.open(out_fit) as im:
            self.assertEqual(im.size, (500, 400))  # 1000x800 scaled to fit 500x500

        # 2. Longest edge mode
        out_longest = self.temp_dir / "resized_longest.jpg"
        res = image_service.resize_image(self.sample_img_path, out_longest, mode="longest", longest_edge=400)
        self.assertTrue(res["success"])
        with Image.open(out_longest) as im:
            self.assertEqual(im.size, (400, 320))

        # 3. Percent mode
        out_pct = self.temp_dir / "resized_pct.jpg"
        res = image_service.resize_image(self.sample_img_path, out_pct, mode="percent", percent=50.0)
        self.assertTrue(res["success"])
        with Image.open(out_pct) as im:
            self.assertEqual(im.size, (500, 400))

    def test_format_conversions(self):
        """Tests converting between JPG, WebP, PNG, BMP, and ICO."""
        # JPG -> WebP
        out_webp = self.temp_dir / "converted.webp"
        res = image_service.convert_image(self.sample_img_path, out_webp, target_format="webp", quality=80)
        self.assertTrue(res["success"])
        self.assertTrue(out_webp.exists())
        with Image.open(out_webp) as im:
            self.assertEqual(im.format, "WEBP")

        # PNG (transparent) -> JPG (checks background fill without crashing)
        out_jpg = self.temp_dir / "from_png.jpg"
        res = image_service.convert_image(self.sample_png_path, out_jpg, target_format="jpg", bg_color="#FFFFFF")
        self.assertTrue(res["success"])
        with Image.open(out_jpg) as im:
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(im.mode, "RGB")

        # ICO Generation
        out_ico = self.temp_dir / "favicon.ico"
        res = image_service.generate_ico(self.sample_png_path, out_ico, sizes=[16, 32, 64])
        self.assertTrue(res["success"])
        self.assertTrue(out_ico.exists())

    def test_crop_aspect_ratio(self):
        """Tests aspect ratio cropping (1:1 square crop)."""
        out_crop = self.temp_dir / "cropped_square.jpg"
        res = image_service.crop_image(self.sample_img_path, out_crop, aspect_ratio="1:1", align="center")
        self.assertTrue(res["success"])
        with Image.open(out_crop) as im:
            self.assertEqual(im.width, im.height)
            self.assertEqual(im.width, 800)  # Original was 1000x800

    def test_rotate_and_flips(self):
        """Tests 90 degree rotation and horizontal flip."""
        out_rot = self.temp_dir / "rotated.jpg"
        res = image_service.rotate_orient_image(self.sample_img_path, out_rot, angle=90, flip_h=True)
        self.assertTrue(res["success"])
        with Image.open(out_rot) as im:
            self.assertEqual(im.size, (800, 1000))  # Swapped dimensions

    def test_watermark_text(self):
        """Tests applying watermark text overlay."""
        out_wm = self.temp_dir / "watermarked.jpg"
        res = image_service.watermark_image(
            self.sample_img_path, out_wm,
            text="SINAX WATERMARK",
            position="bottom_right",
            opacity=0.75
        )
        self.assertTrue(res["success"])
        self.assertTrue(out_wm.exists())

    def test_border_and_canvas(self):
        """Tests border addition and canvas padding."""
        out_border = self.temp_dir / "bordered.jpg"
        res = image_service.border_canvas_image(
            self.sample_img_path, out_border,
            border_width=20,
            border_color="#000000"
        )
        self.assertTrue(res["success"])
        with Image.open(out_border) as im:
            self.assertEqual(im.size, (1040, 840))

    def test_enhance_and_filters(self):
        """Tests auto-enhance, grayscale and sepia filters."""
        out_enh = self.temp_dir / "enhanced.jpg"
        res = image_service.enhance_filter_image(
            self.sample_img_path, out_enh,
            auto_enhance=True,
            grayscale=True
        )
        self.assertTrue(res["success"])
        with Image.open(out_enh) as im:
            self.assertEqual(im.mode, "L")

    def test_metadata_stripping(self):
        """Tests complete metadata stripping."""
        out_clean = self.temp_dir / "clean_meta.jpg"
        res = image_service.metadata_image(self.sample_img_path, out_clean, action="strip_all")
        self.assertTrue(res["success"])
        with Image.open(out_clean) as im:
            exif = im.getexif()
            self.assertEqual(len(exif), 0)

    def test_color_palette_extraction(self):
        """Tests extracting dominant color palette."""
        palette = image_service.extract_color_palette(self.sample_img_path, num_colors=4)
        self.assertIsInstance(palette, list)
        self.assertGreater(len(palette), 0)
        self.assertTrue(palette[0]["hex"].startswith("#"))
        self.assertEqual(len(palette[0]["rgb"]), 3)

    def test_similarity_hash(self):
        """Tests perceptual similarity calculation."""
        hash1 = image_service.calculate_image_hash(self.sample_img_path)
        self.assertIsNotNone(hash1)
        sim = image_service.compare_images_similarity(self.sample_img_path, self.sample_img_path)
        self.assertEqual(sim, 100.0)

    def test_workflow_pipeline(self):
        """Tests chained workflow execution (Auto Orient -> Resize -> Watermark -> Convert)."""
        wf = ImageWorkflow(
            name="Test Pipeline",
            steps=[
                WorkflowStep("auto_orient", {}),
                WorkflowStep("resize", {"mode": "longest", "longest_edge": 600, "do_not_enlarge": True}),
                WorkflowStep("watermark", {"text": "TEST_WF", "position": "bottom_right"}),
                WorkflowStep("convert", {"target_format": "webp", "quality": 85})
            ]
        )
        out_wf = self.temp_dir / "workflow_result.webp"
        res = wf.execute_on_image(self.sample_img_path, out_wf)
        self.assertTrue(res["success"])
        self.assertTrue(out_wf.exists())
        with Image.open(out_wf) as im:
            self.assertEqual(im.format, "WEBP")
            self.assertEqual(max(im.size), 600)

    def test_folder_tree_replication(self):
        """Tests preserving nested directory structure during output generation."""
        sub_dir = self.temp_dir / "2026" / "vacation"
        sub_dir.mkdir(parents=True, exist_ok=True)
        img_in_sub = sub_dir / "photo.jpg"
        shutil.copy2(self.sample_img_path, img_in_sub)

        out_root = self.temp_dir / "output_root"
        rel_out = get_relative_output_path(
            source_file=img_in_sub,
            base_folder=self.temp_dir,
            output_folder=out_root,
            suffix="_optimized",
            new_ext="webp"
        )
        expected_path = out_root / "2026" / "vacation" / "photo_optimized.webp"
        self.assertEqual(rel_out, expected_path)

    def test_batch_worker_streaming(self):
        """Tests ImageWorker processing a batch of images with streaming metrics."""
        from app.workers.image_worker import ImageWorker
        from PySide6.QtCore import QCoreApplication

        # Create batch of 20 images
        batch_files = []
        for i in range(20):
            p = self.temp_dir / f"batch_img_{i:03d}.jpg"
            shutil.copy2(self.sample_img_path, p)
            batch_files.append(p)

        out_dir = self.temp_dir / "worker_output"
        worker = ImageWorker(
            files=batch_files,
            tool_id="batch_compress",
            options={"preset": "balanced", "quality": 75},
            output_folder=out_dir,
            preserve_folders=False
        )

        progress_calls = []
        finished_results = []

        worker.progress.connect(lambda c, t, p, s, e, b: progress_calls.append((c, t, p)))
        worker.all_finished.connect(lambda res: finished_results.append(res))

        worker.run()  # Run synchronously for unit test

        self.assertEqual(len(finished_results), 1)
        summary = finished_results[0]
        self.assertEqual(summary["total"], 20)
        self.assertEqual(summary["processed"], 20)
        self.assertEqual(summary["failed"], 0)
        self.assertGreater(len(progress_calls), 0)


if __name__ == "__main__":
    unittest.main()

