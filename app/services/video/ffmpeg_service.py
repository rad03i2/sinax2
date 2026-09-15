# -*- coding: utf-8 -*-
"""
SINAX FFmpeg Execution Service
Manages FFmpeg subprocess execution, real-time stderr progress tracking,
and comprehensive media probe analysis without external dependencies.
"""

import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.conversion.dependency_manager import dependency_manager
from app.services.video.video_utils import format_seconds, parse_timestamp

logger = get_logger("ffmpeg_service")


class FFmpegService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FFmpegService, cls).__new__(cls)
        return cls._instance

    def get_ffmpeg_exe(self) -> Optional[str]:
        p = dependency_manager.get_tool_path("ffmpeg")
        return str(p) if p else None

    def is_available(self) -> bool:
        return self.get_ffmpeg_exe() is not None

    def probe_media(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts container and stream metadata directly via FFmpeg inspection.
        Returns a rich dictionary of video, audio, and container properties.
        """
        meta: Dict[str, Any] = {
            "path": file_path,
            "filename": Path(file_path).name,
            "size_bytes": 0,
            "size_formatted": "0 MB",
            "duration": 0.0,
            "duration_formatted": "00:00:00",
            "bitrate_kbps": 0,
            "format": "",
            "video_codec": "",
            "resolution": "",
            "width": 0,
            "height": 0,
            "aspect_ratio": "",
            "fps": 0.0,
            "audio_codec": "",
            "audio_channels": "",
            "sample_rate_hz": 0,
            "audio_bitrate_kbps": 0,
            "has_video": False,
            "has_audio": False,
            "has_subtitles": False,
            "video_streams": [],
            "audio_streams": [],
            "subtitle_streams": [],
            "error": None,
        }

        p = Path(file_path)
        if not p.exists():
            meta["error"] = "File not found"
            return meta

        try:
            meta["size_bytes"] = p.stat().st_size
            meta["size_formatted"] = f"{meta['size_bytes'] / (1024 * 1024):.2f} MB"
        except Exception:
            pass

        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            meta["error"] = "FFmpeg binary is not available"
            return meta

        try:
            # ffmpeg -i <file> prints metadata to stderr and exits with error code 1 or 0
            proc = subprocess.run(
                [ffmpeg_exe, "-hide_banner", "-i", str(p)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            output = proc.stderr

            # 1. Container duration & bitrate
            # e.g., Duration: 00:01:23.45, start: 0.000000, bitrate: 1542 kb/s
            dur_match = re.search(r"Duration:\s*(\d+:\d+:\d+(?:\.\d+)?)", output)
            if dur_match:
                meta["duration"] = parse_timestamp(dur_match.group(1))
                meta["duration_formatted"] = format_seconds(meta["duration"])

            br_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", output)
            if br_match:
                meta["bitrate_kbps"] = int(br_match.group(1))

            # 2. Streams
            lines = output.splitlines()
            for line in lines:
                line_str = line.strip()
                if "Stream #" not in line_str:
                    continue

                if "Video:" in line_str:
                    meta["has_video"] = True
                    # e.g., Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), 1920x1080 [SAR 1:1 DAR 16:9], 2500 kb/s, 29.97 fps, 29.97 tbr
                    v_codec_match = re.search(r"Video:\s*([a-zA-Z0-9_\-]+)", line_str)
                    v_codec = v_codec_match.group(1) if v_codec_match else "unknown"

                    dim_match = re.search(r"(\d{2,5})x(\d{2,5})", line_str)
                    w, h = (int(dim_match.group(1)), int(dim_match.group(2))) if dim_match else (0, 0)

                    fps_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:fps|tbr)", line_str)
                    fps = float(fps_match.group(1)) if fps_match else 0.0

                    dar_match = re.search(r"DAR\s*(\d+:\d+)", line_str)
                    aspect = dar_match.group(1) if dar_match else (f"{w}:{h}" if w and h else "")

                    stream_info = {
                        "codec": v_codec,
                        "width": w,
                        "height": h,
                        "fps": fps,
                        "aspect_ratio": aspect,
                        "raw_line": line_str,
                    }
                    meta["video_streams"].append(stream_info)

                    # Populate top-level attributes if first video stream
                    if not meta["video_codec"]:
                        meta["video_codec"] = v_codec
                        meta["width"] = w
                        meta["height"] = h
                        meta["resolution"] = f"{w}x{h}" if w and h else ""
                        meta["fps"] = fps
                        meta["aspect_ratio"] = aspect

                elif "Audio:" in line_str:
                    meta["has_audio"] = True
                    # e.g., Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 128 kb/s
                    a_codec_match = re.search(r"Audio:\s*([a-zA-Z0-9_\-]+)", line_str)
                    a_codec = a_codec_match.group(1) if a_codec_match else "unknown"

                    hz_match = re.search(r"(\d+)\s*Hz", line_str)
                    hz = int(hz_match.group(1)) if hz_match else 0

                    ch_match = re.search(r"(mono|stereo|5\.1(?:\(side\))?|7\.1)", line_str, re.IGNORECASE)
                    channels = ch_match.group(1) if ch_match else ""

                    abr_match = re.search(r"(\d+)\s*kb/s", line_str)
                    abr = int(abr_match.group(1)) if abr_match else 0

                    stream_info = {
                        "codec": a_codec,
                        "sample_rate": hz,
                        "channels": channels,
                        "bitrate_kbps": abr,
                        "raw_line": line_str,
                    }
                    meta["audio_streams"].append(stream_info)

                    if not meta["audio_codec"]:
                        meta["audio_codec"] = a_codec
                        meta["sample_rate_hz"] = hz
                        meta["audio_channels"] = channels
                        meta["audio_bitrate_kbps"] = abr

                elif "Subtitle:" in line_str:
                    meta["has_subtitles"] = True
                    s_codec_match = re.search(r"Subtitle:\s*([a-zA-Z0-9_\-]+)", line_str)
                    meta["subtitle_streams"].append({
                        "codec": s_codec_match.group(1) if s_codec_match else "sub",
                        "raw_line": line_str,
                    })

        except Exception as e:
            logger.warning(f"Error probing media {file_path}: {e}")
            meta["error"] = str(e)

        return meta

    def run_ffmpeg(
        self,
        cmd_args: List[str],
        duration_sec: Optional[float] = None,
        progress_callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[threading.Event] = None,
    ) -> Tuple[bool, str]:
        """
        Executes an FFmpeg command with live progress tracking, error detection,
        and cancellation support.
        """
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return False, "محرك FFmpeg غير متوفر. يرجى التأكد من تثبيته."

        full_cmd = [ffmpeg_exe, "-hide_banner", "-y"] + cmd_args

        # Replace non-existent placeholders if any
        cmd_str = " ".join(f'"{a}"' if " " in str(a) else str(a) for a in full_cmd)
        logger.info(f"Executing FFmpeg command: {cmd_str}")

        proc = None
        error_lines = []

        try:
            proc = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            # Regex for progress parsing
            time_re = re.compile(r"time=(\d+:\d+:\d+(?:\.\d+)?)")
            speed_re = re.compile(r"speed=\s*([\d\.]+)x")
            fps_re = re.compile(r"fps=\s*([\d\.]+)")
            bitrate_re = re.compile(r"bitrate=\s*([\d\.]+)kbits/s")

            # Stream stderr line by line
            if proc.stderr:
                for line in proc.stderr:
                    if cancel_token and cancel_token.is_set():
                        logger.info("FFmpeg execution cancelled by user.")
                        try:
                            proc.terminate()
                            proc.wait(timeout=2)
                        except Exception:
                            proc.kill()
                        return False, "تم إلغاء العملية بواسطة المستخدم."

                    error_lines.append(line)
                    if len(error_lines) > 50:
                        error_lines.pop(0)

                    # Parse progress metrics
                    if progress_callback:
                        t_match = time_re.search(line)
                        if t_match:
                            current_sec = parse_timestamp(t_match.group(1))
                            speed_match = speed_re.search(line)
                            fps_match = fps_re.search(line)
                            br_match = bitrate_re.search(line)

                            speed_val = speed_match.group(1) if speed_match else "1.0"
                            fps_val = fps_match.group(1) if fps_match else "0"
                            br_val = br_match.group(1) if br_match else "0"

                            pct = 0.0
                            eta_sec = 0.0
                            if duration_sec and duration_sec > 0:
                                pct = min(99.0, (current_sec / duration_sec) * 100.0)
                                try:
                                    speed_f = float(speed_val)
                                    if speed_f > 0:
                                        eta_sec = max(0.0, (duration_sec - current_sec) / speed_f)
                                except Exception:
                                    pass

                            progress_callback(
                                pct,
                                {
                                    "time_str": t_match.group(1),
                                    "speed": f"{speed_val}x",
                                    "fps": fps_val,
                                    "bitrate": f"{br_val} kb/s",
                                    "eta_formatted": format_seconds(eta_sec) if eta_sec > 0 else "--:--",
                                },
                            )

            proc.wait()

            if proc.returncode == 0:
                if progress_callback:
                    progress_callback(100.0, {"status": "done"})
                return True, "Success"
            else:
                err_msg = "".join(error_lines[-10:]).strip()
                logger.error(f"FFmpeg process returned code {proc.returncode}: {err_msg}")
                return False, f"فشلت معالجة الفيديو: {err_msg or 'رمز الخطأ ' + str(proc.returncode)}"

        except Exception as e:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            logger.error(f"Exception running FFmpeg: {e}", exc_info=True)
            return False, f"خطأ أثناء تشغيل FFmpeg: {str(e)}"


ffmpeg_service = FFmpegService()
