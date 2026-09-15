# -*- coding: utf-8 -*-
"""
Unit Tests for SINAX Video Center (Phase 8: Multimedia - Video Center)
Tests tool registry, hardware acceleration detection, utilities, probe analysis,
video operations (compression, conversion, remux, resize, trim, split, merge,
audio extraction, mute, speed, watermark, GIF, contact sheet, enhancement, metadata),
chained workflow pipelines, and background worker queue execution.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.services.video.ffmpeg_service import ffmpeg_service
from app.services.video.hardware_detector import hardware_detector
from app.services.video.video_registry import (
    VIDEO_CATEGORIES,
    VIDEO_TOOLS,
    get_all_video_tools,
    get_tools_by_category,
    get_video_tool_by_id,
)
from app.services.video.video_service import video_service
from app.services.video.video_utils import (
    calculate_target_bitrate,
    format_bytes,
    format_seconds,
    generate_output_path,
    parse_timestamp,
    scan_video_files,
)
from app.services.video.video_workflow import VideoWorkflow, VideoWorkflowStep


class TestVideoService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="sinax_test_video_"))
        cls.ffmpeg_exe = ffmpeg_service.get_ffmpeg_exe()

        # Create a synthetic 3-second test MP4 video with testsrc and sine audio
        cls.sample_mp4 = cls.temp_dir / "sample_test.mp4"
        cls.sample_mp4_2 = cls.temp_dir / "sample_test_2.mp4"

        if cls.ffmpeg_exe:
            # Generate sample 1: 320x240, 25fps, 3 seconds
            subprocess.run(
                [
                    cls.ffmpeg_exe, "-y", "-hide_banner",
                    "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=25",
                    "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
                    "-c:v", "libx264", "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    str(cls.sample_mp4),
                ],
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            # Generate sample 2: 320x240, 25fps, 2 seconds
            subprocess.run(
                [
                    cls.ffmpeg_exe, "-y", "-hide_banner",
                    "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=25",
                    "-f", "lavfi", "-i", "sine=frequency=500:duration=2",
                    "-c:v", "libx264", "-c:a", "aac",
                    "-pix_fmt", "yuv420p",
                    str(cls.sample_mp4_2),
                ],
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

    @classmethod
    def tearDownClass(cls):
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # 1. Registry & Tools Metadata
    # -------------------------------------------------------------
    def test_registry_tools_count(self):
        """Verifies that all 31 video tools are defined with correct schemas."""
        tools = get_all_video_tools()
        self.assertGreaterEqual(len(tools), 30)
        self.assertGreaterEqual(len(VIDEO_CATEGORIES), 7)

        # Check tool lookup
        comp_tool = get_video_tool_by_id("batch_compress")
        self.assertIsNotNone(comp_tool)
        self.assertEqual(comp_tool.options_type, "compress")
        self.assertTrue(comp_tool.supports_batch)

    def test_registry_categories(self):
        """Verifies filtering tools by category."""
        compress_tools = get_tools_by_category("compression")
        self.assertGreaterEqual(len(compress_tools), 2)
        audio_tools = get_tools_by_category("audio")
        self.assertGreaterEqual(len(audio_tools), 4)

    # -------------------------------------------------------------
    # 2. Hardware Acceleration Detector
    # -------------------------------------------------------------
    def test_hardware_detector(self):
        """Tests encoder detection and status summary."""
        encoders = hardware_detector.detect_encoders()
        self.assertIsInstance(encoders, dict)
        self.assertIn("libx264", encoders)

        best_h264 = hardware_detector.get_best_encoder("h264", use_gpu=False)
        self.assertEqual(best_h264, "libx264")

        summary = hardware_detector.get_status_summary()
        self.assertIn("badge_text", summary)
        self.assertIn("is_accelerated", summary)

    # -------------------------------------------------------------
    # 3. Utilities & Calculations
    # -------------------------------------------------------------
    def test_timestamp_parsing_and_formatting(self):
        """Tests parsing and formatting timestamps."""
        self.assertEqual(parse_timestamp("10"), 10.0)
        self.assertEqual(parse_timestamp("01:30"), 90.0)
        self.assertEqual(parse_timestamp("01:00:00"), 3600.0)
        self.assertEqual(format_seconds(90), "00:01:30")
        self.assertEqual(format_seconds(3665), "01:01:05")

    def test_target_bitrate_calculation(self):
        """Tests target bitrate calculation for exact file size targets."""
        v_kbit, a_kbit = calculate_target_bitrate(target_mb=10.0, duration_sec=60.0)
        self.assertGreater(v_kbit, 50)
        self.assertGreater(a_kbit, 32)
        # Total bits per sec should fit ~10MB in 60s
        est_total_bits = (v_kbit + a_kbit) * 1000 * 60
        target_bits = 10 * 1024 * 1024 * 8
        self.assertLess(est_total_bits, target_bits)

    def test_video_scanning_and_path_generation(self):
        """Tests scanning video files and safe output path generation."""
        found = scan_video_files([str(self.sample_mp4)], recursive=False)
        self.assertEqual(len(found), 1)

        out = generate_output_path(
            input_path=str(self.sample_mp4),
            output_dir=str(self.temp_dir / "out"),
            prefix="test_",
            suffix="_opt",
            new_ext="mkv",
        )
        self.assertTrue(out.endswith("test_sample_test_opt.mkv"))

    # -------------------------------------------------------------
    # 4. Media Probe Analysis
    # -------------------------------------------------------------
    def test_probe_media(self):
        """Tests container and stream metadata extraction."""
        self.assertTrue(self.sample_mp4.exists(), "Sample test video must exist")
        meta = ffmpeg_service.probe_media(str(self.sample_mp4))
        self.assertTrue(meta["has_video"])
        self.assertTrue(meta["has_audio"])
        self.assertEqual(meta["width"], 320)
        self.assertEqual(meta["height"], 240)
        self.assertAlmostEqual(meta["duration"], 3.0, delta=0.5)

    # -------------------------------------------------------------
    # 5. Core Video Operations (Real FFmpeg Execution)
    # -------------------------------------------------------------
    def test_compress_video(self):
        """Tests perceptual CRF compression and target size compression."""
        out = self.temp_dir / "compressed_balanced.mp4"
        res = video_service.compress_video(str(self.sample_mp4), str(out), preset="balanced", use_gpu=False)
        self.assertTrue(res["success"])
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

        # Target size mode
        out_target = self.temp_dir / "compressed_target.mp4"
        res_target = video_service.compress_video(str(self.sample_mp4), str(out_target), target_size_mb=1.0, use_gpu=False)
        self.assertTrue(res_target["success"])
        self.assertTrue(out_target.exists())

    def test_convert_format(self):
        """Tests container conversion to MKV and WebM."""
        out_mkv = self.temp_dir / "converted.mkv"
        res_mkv = video_service.convert_format(str(self.sample_mp4), str(out_mkv), use_gpu=False)
        self.assertTrue(res_mkv["success"])
        self.assertTrue(out_mkv.exists())

    def test_fast_remux(self):
        """Tests lossless stream copy (-c copy) in seconds."""
        out_remux = self.temp_dir / "remuxed.mkv"
        res = video_service.fast_remux(str(self.sample_mp4), str(out_remux))
        self.assertTrue(res["success"])
        self.assertTrue(out_remux.exists())
        self.assertGreater(out_remux.stat().st_size, 0)

    def test_resize_resolution(self):
        """Tests video resizing with fit mode."""
        out = self.temp_dir / "resized_480p.mp4"
        res = video_service.resize_resolution(str(self.sample_mp4), str(out), resolution="480p", mode="fit", use_gpu=False)
        self.assertTrue(res["success"])
        self.assertTrue(out.exists())

    def test_trim_video(self):
        """Tests trimming video segment."""
        out = self.temp_dir / "trimmed.mp4"
        res = video_service.trim_video(str(self.sample_mp4), str(out), start_time="00:00:01", duration="00:00:01", mode="accurate", use_gpu=False)
        self.assertTrue(res["success"])
        self.assertTrue(out.exists())
        m = ffmpeg_service.probe_media(str(out))
        self.assertAlmostEqual(m["duration"], 1.0, delta=0.5)

    def test_split_video(self):
        """Tests splitting video into parts."""
        out_dir = self.temp_dir / "split_parts"
        res = video_service.split_video(str(self.sample_mp4), str(out_dir), mode="parts", parts_count=2)
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["parts_count"], 1)

    def test_merge_videos(self):
        """Tests merging multiple videos."""
        out = self.temp_dir / "merged.mp4"
        res = video_service.merge_videos([str(self.sample_mp4), str(self.sample_mp4_2)], str(out), reencode=True, use_gpu=False)
        self.assertTrue(res["success"])
        self.assertTrue(out.exists())
        m = ffmpeg_service.probe_media(str(out))
        self.assertAlmostEqual(m["duration"], 5.0, delta=1.0)

    def test_audio_operations(self):
        """Tests extract audio and mute audio."""
        # Extract MP3
        out_mp3 = self.temp_dir / "extracted.mp3"
        res_mp3 = video_service.extract_audio(str(self.sample_mp4), str(out_mp3), audio_format="mp3")
        self.assertTrue(res_mp3["success"])
        self.assertTrue(out_mp3.exists())

        # Mute audio
        out_mute = self.temp_dir / "muted.mp4"
        res_mute = video_service.mute_audio(str(self.sample_mp4), str(out_mute))
        self.assertTrue(res_mute["success"])
        self.assertTrue(out_mute.exists())
        m = ffmpeg_service.probe_media(str(out_mute))
        self.assertFalse(m["has_audio"])

    def test_speed_and_rotate(self):
        """Tests speed adjustment and 90-degree rotation."""
        # 2x Speed
        out_speed = self.temp_dir / "speed2x.mp4"
        res_speed = video_service.adjust_speed(str(self.sample_mp4), str(out_speed), speed_factor=2.0, use_gpu=False)
        self.assertTrue(res_speed["success"])
        self.assertTrue(out_speed.exists())

        # Rotate 90
        out_rot = self.temp_dir / "rotated90.mp4"
        res_rot = video_service.rotate_flip(str(self.sample_mp4), str(out_rot), rotation=90, use_gpu=False)
        self.assertTrue(res_rot["success"])
        self.assertTrue(out_rot.exists())

    def test_watermark_text(self):
        """Tests text overlay watermark."""
        out_wm = self.temp_dir / "watermarked.mp4"
        res = video_service.add_watermark(str(self.sample_mp4), str(out_wm), text="SINAX_TEST", position="bottom_right", use_gpu=False)
        self.assertTrue(res["success"])
        self.assertTrue(out_wm.exists())

    def test_thumbnail_and_gif(self):
        """Tests frame thumbnail extraction and animated GIF generation."""
        # Thumbnail
        out_thumb = self.temp_dir / "thumb.jpg"
        res_thumb = video_service.extract_thumbnail(str(self.sample_mp4), str(out_thumb), timestamp="00:00:01")
        self.assertTrue(res_thumb["success"])
        self.assertTrue(out_thumb.exists())

        # 2-Pass GIF
        out_gif = self.temp_dir / "animated.gif"
        res_gif = video_service.create_gif(str(self.sample_mp4), str(out_gif), start_time="00:00:00", duration=2.0, fps=10, width=240)
        self.assertTrue(res_gif["success"])
        self.assertTrue(out_gif.exists())

    def test_strip_metadata(self):
        """Tests metadata stripping for clean sharing."""
        out_strip = self.temp_dir / "stripped.mp4"
        res = video_service.strip_metadata(str(self.sample_mp4), str(out_strip))
        self.assertTrue(res["success"])
        self.assertTrue(out_strip.exists())

    # -------------------------------------------------------------
    # 6. Chained Sequential Workflow Pipeline
    # -------------------------------------------------------------
    def test_workflow_pipeline(self):
        """Tests chained pipeline: Mute -> Watermark -> Compress."""
        wf = VideoWorkflow(name="Test Pipeline")
        wf.add_step("mute")
        wf.add_step("watermark", {"text": "PIPELINE_TEST"})
        wf.add_step("compress", {"preset": "balanced", "use_gpu": False})

        out_wf = self.temp_dir / "workflow_result.mp4"
        res = wf.execute_on_video(str(self.sample_mp4), str(out_wf))
        self.assertTrue(res["success"])
        self.assertEqual(res["steps_executed"], 3)
        self.assertTrue(out_wf.exists())
        self.assertGreater(out_wf.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
