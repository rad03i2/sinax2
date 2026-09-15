# -*- coding: utf-8 -*-
"""
Unit Tests for SINAX Audio Center (Phase 9: Multimedia - Audio Center)
Tests tool registry, utilities, audio metadata probing, waveform & spectrogram generation,
local FFmpeg operations (convert, compress, target size, trim, merge, fade, normalize, LUFS, EQ,
denoise, speed/tempo, channels), and multi-step chained workflow pipelines.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.services.audio.audio_registry import (
    AUDIO_CATEGORIES,
    AUDIO_TOOLS_REGISTRY,
    get_audio_tool_by_id,
    get_audio_tools_by_category,
    search_audio_tools,
)
from app.services.audio.audio_service import audio_service
from app.services.audio.audio_utils import (
    AUDIO_FORMATS,
    calc_target_audio_bitrate,
    format_duration,
    format_file_size,
    is_audio_file,
    parse_time_str,
)
from app.services.audio.audio_workflow import (
    AudioWorkflow,
    AudioWorkflowRunner,
    AudioWorkflowStep,
    DEFAULT_AUDIO_WORKFLOW_PRESETS,
)


class TestAudioService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="sinax_test_audio_"))
        cls.ffmpeg_exe = audio_service.get_ffmpeg_exe()

        cls.sample_wav = cls.temp_dir / "sample_test.wav"
        cls.sample_mp3 = cls.temp_dir / "sample_test.mp3"
        cls.sample_wav2 = cls.temp_dir / "sample_test_2.wav"

        if cls.ffmpeg_exe:
            # Generate synthetic 3-second 440Hz sine wave audio
            subprocess.run(
                [
                    cls.ffmpeg_exe, "-y", "-hide_banner",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                    "-c:a", "pcm_s16le",
                    str(cls.sample_wav)
                ],
                capture_output=True,
                check=True
            )
            # Generate sample 2: 880Hz
            subprocess.run(
                [
                    cls.ffmpeg_exe, "-y", "-hide_banner",
                    "-f", "lavfi", "-i", "sine=frequency=880:duration=2",
                    "-c:a", "pcm_s16le",
                    str(cls.sample_wav2)
                ],
                capture_output=True,
                check=True
            )
            # Generate MP3 sample
            subprocess.run(
                [
                    cls.ffmpeg_exe, "-y", "-hide_banner",
                    "-i", str(cls.sample_wav),
                    "-c:a", "libmp3lame", "-b:a", "192k",
                    str(cls.sample_mp3)
                ],
                capture_output=True,
                check=True
            )

    @classmethod
    def tearDownClass(cls):
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # 1. Registry & Definitions
    # -------------------------------------------------------------
    def test_registry_populated(self):
        self.assertGreaterEqual(len(AUDIO_TOOLS_REGISTRY), 25)
        self.assertGreaterEqual(len(AUDIO_CATEGORIES), 10)

    def test_get_audio_tool_by_id(self):
        t = get_audio_tool_by_id("batch_audio_convert")
        self.assertIsNotNone(t)
        self.assertEqual(t.category, "convert")
        self.assertTrue(t.supports_batch)

    def test_category_filtering(self):
        conv_tools = get_audio_tools_by_category("convert")
        self.assertTrue(any(t.id == "batch_audio_convert" for t in conv_tools))

        clean_tools = get_audio_tools_by_category("clean")
        self.assertTrue(any(t.id == "denoise_audio" for t in clean_tools))

    def test_search_audio_tools(self):
        results = search_audio_tools("mp3")
        self.assertTrue(len(results) > 0)
        results_podcast = search_audio_tools("بودكاست")
        self.assertTrue(len(results_podcast) > 0)

    # -------------------------------------------------------------
    # 2. Audio Utilities
    # -------------------------------------------------------------
    def test_audio_utils_functions(self):
        self.assertTrue(is_audio_file("music.mp3"))
        self.assertTrue(is_audio_file("track.flac"))
        self.assertTrue(is_audio_file("recording.wav"))
        self.assertFalse(is_audio_file("document.pdf"))
        self.assertFalse(is_audio_file("video.mp4"))

        self.assertEqual(format_duration(65), "01:05")
        self.assertEqual(format_duration(3665), "01:01:05")
        self.assertEqual(parse_time_str("01:30"), 90.0)
        self.assertEqual(parse_time_str("01:00:10"), 3610.0)

        # Target size bitrate calculation
        # 5 MB for 300 seconds -> ~130 kbps
        br = calc_target_audio_bitrate(5.0, 300)
        self.assertGreaterEqual(br, 64)
        self.assertLessEqual(br, 320)

    # -------------------------------------------------------------
    # 3. Probing & Metadata
    # -------------------------------------------------------------
    def test_get_audio_metadata(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        meta = audio_service.get_audio_metadata(str(self.sample_wav))
        self.assertGreater(meta["duration"], 2.5)
        self.assertIn(meta["codec"].lower(), ["pcm_s16le", "wav", "pcm"])
        self.assertGreater(meta["size_bytes"], 0)

    # -------------------------------------------------------------
    # 4. Waveform & Spectrogram Rendering
    # -------------------------------------------------------------
    def test_waveform_generation(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_png = str(self.temp_dir / "waveform_test.png")
        ok = audio_service.generate_waveform_image(str(self.sample_wav), out_png, width=400, height=80)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(out_png))
        self.assertGreater(os.path.getsize(out_png), 100)

    def test_spectrogram_generation(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_png = str(self.temp_dir / "spectrogram_test.png")
        ok = audio_service.generate_spectrogram_image(str(self.sample_wav), out_png, width=400, height=80)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(out_png))
        self.assertGreater(os.path.getsize(out_png), 500)

    # -------------------------------------------------------------
    # 5. Audio Analysis: EBU R128 LUFS
    # -------------------------------------------------------------
    def test_analyze_audio_loudness(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        res = audio_service.analyze_audio_loudness(str(self.sample_wav))
        self.assertTrue(res.get("success"))
        self.assertGreater(res["input_i"], -70.0)
        self.assertGreater(res["input_tp"], -70.0)

    # -------------------------------------------------------------
    # 6. Format Conversion & Compression
    # -------------------------------------------------------------
    def test_convert_audio_mp3_to_flac(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_flac = str(self.temp_dir / "converted.flac")
        res = audio_service.convert_audio(str(self.sample_mp3), out_flac, format_ext="flac")
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_flac))

    def test_compress_audio_presets(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_compressed = str(self.temp_dir / "compressed.mp3")
        res = audio_service.compress_audio(str(self.sample_wav), out_compressed, preset="strong")
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_compressed))
        # Compressed MP3 should be significantly smaller than uncompressed WAV
        self.assertLess(os.path.getsize(out_compressed), os.path.getsize(self.sample_wav))

    def test_compress_target_size(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_target = str(self.temp_dir / "target_size.mp3")
        res = audio_service.compress_target_size(str(self.sample_wav), out_target, target_mb=0.5)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_target))

    # -------------------------------------------------------------
    # 7. Editing: Trimming, Merging & Fading
    # -------------------------------------------------------------
    def test_trim_audio(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_trimmed = str(self.temp_dir / "trimmed.wav")
        res = audio_service.trim_audio(str(self.sample_wav), out_trimmed, start_time="00:00:01", end_time="00:00:02")
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_trimmed))
        meta = audio_service.get_audio_metadata(out_trimmed)
        self.assertAlmostEqual(meta["duration"], 1.0, delta=0.3)

    def test_merge_audio(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_merged = str(self.temp_dir / "merged.wav")
        res = audio_service.merge_audio_files([str(self.sample_wav), str(self.sample_wav2)], out_merged)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_merged))
        meta = audio_service.get_audio_metadata(out_merged)
        # Total duration = 3s + 2s = 5s
        self.assertAlmostEqual(meta["duration"], 5.0, delta=0.5)

    def test_fade_audio(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_faded = str(self.temp_dir / "faded.wav")
        res = audio_service.fade_audio(str(self.sample_wav), out_faded, fade_in_sec=1.0, fade_out_sec=1.0)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_faded))

    # -------------------------------------------------------------
    # 8. Normalization, Volume & Dynamics
    # -------------------------------------------------------------
    def test_loudness_normalize(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_norm = str(self.temp_dir / "loudness_norm.wav")
        res = audio_service.loudness_normalize(str(self.sample_wav), out_norm, target_lufs=-16.0, true_peak=-1.0)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_norm))

    def test_volume_adjust(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_vol = str(self.temp_dir / "vol_gain.wav")
        res = audio_service.volume_adjust(str(self.sample_wav), out_vol, gain_db=3.0)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_vol))

    # -------------------------------------------------------------
    # 9. EQ & Acoustic Filters
    # -------------------------------------------------------------
    def test_graphic_eq(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_eq = str(self.temp_dir / "eq_applied.wav")
        res = audio_service.apply_eq(str(self.sample_wav), out_eq, bass_db=3.0, mid_db=-2.0, treble_db=4.0)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_eq))

    def test_filters(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_filter = str(self.temp_dir / "highpass.wav")
        res = audio_service.apply_filters(str(self.sample_wav), out_filter, filter_type="highpass", cutoff_freq=120)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_filter))

    # -------------------------------------------------------------
    # 10. Speed / Tempo & Channels
    # -------------------------------------------------------------
    def test_speed_tempo(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_fast = str(self.temp_dir / "fast.wav")
        res = audio_service.change_speed_tempo(str(self.sample_wav), out_fast, speed_factor=1.5, preserve_pitch=True)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_fast))
        meta = audio_service.get_audio_metadata(out_fast)
        # 3.0s / 1.5 = 2.0s
        self.assertAlmostEqual(meta["duration"], 2.0, delta=0.4)

    def test_channel_routing(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        out_mono = str(self.temp_dir / "mono.wav")
        res = audio_service.channel_routing(str(self.sample_wav), out_mono, mode="stereo_to_mono")
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_mono))
        meta = audio_service.get_audio_metadata(out_mono)
        self.assertEqual(meta["channels"], 1)

    # -------------------------------------------------------------
    # 11. Workflow Pipeline Runner
    # -------------------------------------------------------------
    def test_audio_workflow_execution(self):
        if not self.ffmpeg_exe:
            self.skipTest("FFmpeg not available")

        # Create 3-step pipeline: Equalizer -> Volume Adjust -> Convert to MP3
        wf = AudioWorkflow(
            name="Test Pipeline",
            steps=[
                AudioWorkflowStep(action="graphic_eq_audio", params={"bass_db": 2.0, "mid_db": 0.0, "treble_db": 2.0}),
                AudioWorkflowStep(action="volume_adjust_audio", params={"gain_db": 1.5}),
                AudioWorkflowStep(action="batch_audio_convert", params={"format": "mp3", "bitrate": "192k"}),
            ]
        )

        out_wf = str(self.temp_dir / "workflow_result.mp3")
        runner = AudioWorkflowRunner(wf)
        res = runner.execute(str(self.sample_wav), out_wf)
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertTrue(os.path.exists(out_wf))
        meta = audio_service.get_audio_metadata(out_wf)
        self.assertIn("mp3", meta["format"].lower())


if __name__ == "__main__":
    unittest.main()
