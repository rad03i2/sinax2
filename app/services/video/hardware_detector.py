# -*- coding: utf-8 -*-
"""
SINAX Video Hardware Acceleration Detector
Detects GPU hardware encoders (NVIDIA NVENC, Intel QSV, AMD AMF) supported by FFmpeg,
and verifies runtime usability before selecting them.
"""

import subprocess
from typing import Any, Callable, Dict, List, Optional
from app.services.conversion.dependency_manager import dependency_manager
from app.core.logger import get_logger

logger = get_logger("hardware_detector")


class HardwareDetector:
    _instance = None
    _encoders_cached: Optional[Dict[str, bool]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HardwareDetector, cls).__new__(cls)
        return cls._instance

    def get_ffmpeg_path(self) -> Optional[str]:
        p = dependency_manager.get_tool_path("ffmpeg")
        return str(p) if p else None

    def _test_encoder_usable(self, ffmpeg_exe: str, encoder: str) -> bool:
        """Tests whether an encoder can actually be initialized by the local GPU hardware."""
        try:
            proc = subprocess.run(
                [
                    ffmpeg_exe, "-hide_banner",
                    "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.04",
                    "-c:v", encoder,
                    "-f", "null", "-",
                ],
                capture_output=True,
                timeout=4,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return proc.returncode == 0
        except Exception:
            return False

    def detect_encoders(self, force_refresh: bool = False) -> Dict[str, bool]:
        """Queries FFmpeg for available encoders and tests runtime hardware acceleration support."""
        if self._encoders_cached is not None and not force_refresh:
            return self._encoders_cached

        results = {
            # NVIDIA NVENC
            "h264_nvenc": False,
            "hevc_nvenc": False,
            "av1_nvenc": False,
            # Intel QuickSync
            "h264_qsv": False,
            "hevc_qsv": False,
            # AMD AMF
            "h264_amf": False,
            "hevc_amf": False,
            # CPU Fallbacks
            "libx264": False,
            "libx265": False,
            "libvpx-vp9": False,
            "libaom-av1": False,
        }

        ffmpeg_exe = self.get_ffmpeg_path()
        if not ffmpeg_exe:
            self._encoders_cached = results
            return results

        try:
            # 1. Check compiled encoders via ffmpeg -encoders
            proc = subprocess.run(
                [ffmpeg_exe, "-encoders"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            output = proc.stdout

            compiled_hw = []
            for key in results.keys():
                if f" {key} " in output or f" {key}\n" in output:
                    if any(tag in key for tag in ("nvenc", "qsv", "amf")):
                        compiled_hw.append(key)
                    else:
                        results[key] = True

            # 2. Test candidate hardware encoders for actual runtime GPU support
            for hw_enc in compiled_hw:
                if self._test_encoder_usable(ffmpeg_exe, hw_enc):
                    results[hw_enc] = True
                    logger.info(f"Verified working GPU hardware encoder: {hw_enc}")
                else:
                    logger.debug(f"Hardware encoder {hw_enc} compiled in FFmpeg but not usable on local GPU.")

        except Exception as e:
            logger.warning(f"Failed to query FFmpeg encoders: {e}")

        self._encoders_cached = results
        return results

    def has_gpu_acceleration(self) -> bool:
        """Returns True if any verified GPU hardware encoder is present."""
        encoders = self.detect_encoders()
        gpu_keys = ["h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_qsv", "hevc_qsv", "h264_amf", "hevc_amf"]
        return any(encoders.get(k, False) for k in gpu_keys)

    def get_gpu_vendor(self) -> Optional[str]:
        """Returns the primary GPU vendor detected for video encoding."""
        encoders = self.detect_encoders()
        if encoders.get("h264_nvenc") or encoders.get("hevc_nvenc"):
            return "NVIDIA NVENC"
        if encoders.get("h264_qsv") or encoders.get("hevc_qsv"):
            return "Intel QuickSync"
        if encoders.get("h264_amf") or encoders.get("hevc_amf"):
            return "AMD AMF"
        return None

    def get_best_encoder(self, codec: str = "h264", use_gpu: bool = True) -> str:
        """
        Returns the optimal encoder name for the requested codec format.
        codec: 'h264', 'hevc'/'h265', 'vp9', 'av1'
        """
        encoders = self.detect_encoders()
        codec_lower = codec.lower().replace("h.", "").replace("h", "").strip()
        if codec_lower in ("264", "avc"):
            if use_gpu:
                if encoders.get("h264_nvenc"):
                    return "h264_nvenc"
                if encoders.get("h264_qsv"):
                    return "h264_qsv"
                if encoders.get("h264_amf"):
                    return "h264_amf"
            return "libx264" if encoders.get("libx264") else "h264"

        if codec_lower in ("265", "hevc"):
            if use_gpu:
                if encoders.get("hevc_nvenc"):
                    return "hevc_nvenc"
                if encoders.get("hevc_qsv"):
                    return "hevc_qsv"
                if encoders.get("hevc_amf"):
                    return "hevc_amf"
            return "libx265" if encoders.get("libx265") else "hevc"

        if codec_lower in ("av1",):
            if use_gpu and encoders.get("av1_nvenc"):
                return "av1_nvenc"
            return "libaom-av1" if encoders.get("libaom-av1") else "av1"

        if codec_lower in ("vp9", "webm"):
            return "libvpx-vp9" if encoders.get("libvpx-vp9") else "vp9"

        return codec

    def detect_encoders_async(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """Asynchronously runs encoder detection in a background thread to prevent UI freezing."""
        import threading

        def worker():
            self.detect_encoders(force_refresh=True)
            if callback:
                summary = self.get_status_summary()
                callback(summary)

        t = threading.Thread(target=worker, daemon=True, name="HWDetectorThread")
        t.start()

    def get_status_summary_fast(self) -> Dict[str, Any]:
        """Returns instantaneous acceleration status without executing blocking subprocesses."""
        if self._encoders_cached is not None:
            return self.get_status_summary()

        return {
            "has_gpu": False,
            "vendor": "جاري الكشف...",
            "badge_text": "⚡ فحص تسريع العتاد...",
            "is_accelerated": False,
        }

    def get_status_summary(self) -> Dict[str, Any]:
        """Provides a user-facing dictionary of acceleration status."""
        has_gpu = self.has_gpu_acceleration()
        vendor = self.get_gpu_vendor()
        return {
            "has_gpu": has_gpu,
            "vendor": vendor or "CPU (Software)",
            "badge_text": f"🚀 تسريع العتاد: {vendor}" if has_gpu else "⚡ معالجة المعالج: CPU",
            "is_accelerated": has_gpu,
        }


hardware_detector = HardwareDetector()
