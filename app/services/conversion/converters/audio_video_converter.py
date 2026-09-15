# -*- coding: utf-8 -*-
"""
SINAX Audio & Video Converter
High-performance converter powered by FFmpeg.
Supports Fast Remux (lossless stream copy) and Re-encode.
Handles audio codecs, sample rates, bitrates, video resolution, FPS, and MP4 <-> GIF.
Safe process handling with arguments list (NO shell=True) and clean cancellation.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

from app.services.conversion.base_converter import BaseConverter
from app.services.conversion.dependency_manager import dependency_manager
from app.core.logger import get_logger

logger = get_logger("audio_video_converter")


class AudioVideoConverter(BaseConverter):
    converter_id = "audio_video_converter"
    name_ar = "محول الصوت والفيديو"
    category = "media"
    required_tools = ["ffmpeg"]

    def get_options_schema(self) -> Dict[str, Any]:
        return {
            "remux_mode": {
                "type": "select",
                "options": ["إعادة ترميز ذكية (Re-encode)", "نسخ مباشر فائق السرعة بدون إعادة ترميز (Fast Remux)"],
                "default": "إعادة ترميز ذكية (Re-encode)",
                "label": "نمط معالجة الفيديو"
            },
            "video_resolution": {
                "type": "select",
                "options": ["الدقة الأصلية (Original)", "1080p (FHD)", "720p (HD)", "480p (SD)"],
                "default": "الدقة الأصلية (Original)",
                "label": "دقة الفيديو (Resolution)"
            },
            "video_quality": {
                "type": "select",
                "options": ["جودة عالية (CRF 18)", "متوازنة (CRF 23)", "حجم أصغر (CRF 28)"],
                "default": "متوازنة (CRF 23)",
                "label": "جودة الفيديو"
            },
            "audio_bitrate": {
                "type": "select",
                "options": ["320 kbps (أعلى جودة)", "256 kbps", "192 kbps (جودة ممتازة)", "128 kbps (حجم قياسي)"],
                "default": "192 kbps (جودة ممتازة)",
                "label": "معدل بت الصوت (Audio Bitrate)"
            },
            "gif_fps": {
                "type": "select",
                "options": ["15 إطار/ثانية (متوازن)", "10 إطار/ثانية (حجم خفيف)", "24 إطار/ثانية (سلس)"],
                "default": "15 إطار/ثانية (متوازن)",
                "label": "معدل إطارات GIF (FPS)"
            }
        }

    def convert(
        self,
        source: Path,
        destination: Path,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancel_token: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, str]:
        options = options or {}
        valid, msg = self.validate_input(source)
        if not valid:
            return False, msg

        if not self.is_available():
            return False, "يتطلب تحويل ملفات الصوت والفيديو توفر أداة FFmpeg على حاسوبك."

        if cancel_token and cancel_token():
            return False, "تم إلغاء العملية."

        ffmpeg_path = dependency_manager.get_tool_path("ffmpeg")
        if not ffmpeg_path:
            return False, "تعذر العثور على مسار تنفيذ FFmpeg."

        src_ext = source.suffix.lower().lstrip('.')
        dst_ext = destination.suffix.lower().lstrip('.')
        destination.parent.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(10.0, f"تهيئة FFmpeg لمعالجة {source.name}...")

        # Build FFmpeg command arguments list safely (NO shell=True)
        cmd = [str(ffmpeg_path), "-y", "-i", str(source)]

        # Determine if source/target is video or audio
        is_video_target = dst_ext in ["mp4", "mkv", "mov", "avi", "webm", "gif"]
        is_audio_target = dst_ext in ["mp3", "wav", "flac", "aac", "m4a", "ogg", "opus"]

        if dst_ext == "gif":
            # High-quality 2-pass palette GIF creation in single filter
            fps = 15
            fps_opt = options.get("gif_fps", "")
            if "10" in fps_opt:
                fps = 10
            elif "24" in fps_opt:
                fps = 24
            filter_graph = f"fps={fps},scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
            cmd.extend(["-vf", filter_graph])
        elif src_ext == "gif" and dst_ext == "mp4":
            cmd.extend(["-movflags", "faststart", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"])
        elif is_video_target:
            remux_mode = options.get("remux_mode", "")
            if "Fast Remux" in remux_mode:
                cmd.extend(["-c", "copy"])
            else:
                # Video Codec
                if dst_ext == "webm":
                    cmd.extend(["-c:v", "libvpx-vp9", "-c:a", "libopus"])
                else:
                    cmd.extend(["-c:v", "libx264", "-c:a", "aac"])

                # Quality CRF
                q_opt = options.get("video_quality", "")
                crf = "18" if "18" in q_opt else ("28" if "28" in q_opt else "23")
                cmd.extend(["-crf", crf])

                # Resolution
                res_opt = options.get("video_resolution", "")
                if "1080p" in res_opt:
                    cmd.extend(["-vf", "scale=-2:1080"])
                elif "720p" in res_opt:
                    cmd.extend(["-vf", "scale=-2:720"])
                elif "480p" in res_opt:
                    cmd.extend(["-vf", "scale=-2:480"])
        elif is_audio_target:
            # Audio Bitrate
            b_opt = options.get("audio_bitrate", "")
            bitrate = "320k" if "320" in b_opt else ("256k" if "256" in b_opt else ("128k" if "128" in b_opt else "192k"))

            if dst_ext == "mp3":
                cmd.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
            elif dst_ext == "aac":
                cmd.extend(["-c:a", "aac", "-b:a", bitrate])
            elif dst_ext == "m4a":
                cmd.extend(["-c:a", "aac", "-b:a", bitrate])
            elif dst_ext == "flac":
                cmd.extend(["-c:a", "flac"])
            elif dst_ext == "wav":
                cmd.extend(["-c:a", "pcm_s16le"])
            elif dst_ext == "ogg":
                cmd.extend(["-c:a", "libvorbis", "-b:a", bitrate])
            elif dst_ext == "opus":
                cmd.extend(["-c:a", "libopus", "-b:a", bitrate])

        cmd.append(str(destination))

        try:
            if progress_callback:
                progress_callback(30.0, f"جاري التحويل عبر FFmpeg...")

            # Run process with support for responsive cancellation
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            # Monitor process with cancel check
            while proc.poll() is None:
                if cancel_token and cancel_token():
                    proc.kill()
                    if destination.exists():
                        try:
                            destination.unlink()
                        except Exception:
                            pass
                    return False, "تم إلغاء عملية تحويل الوسائط بأمان."
                try:
                    proc.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    pass

            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                err_text = stderr.decode("utf-8", errors="replace") if stderr else "خطأ غير معروف"
                logger.error(f"FFmpeg failed: {err_text}")
                return False, f"فشل تحويل FFmpeg (رمز الخطأ {proc.returncode}): {err_text[-250:]}"

            if destination.exists() and destination.stat().st_size > 0:
                if progress_callback:
                    progress_callback(100.0, f"اكتمل تحويل الوسائط بنجاح: {destination.name}")
                return True, f"تم تحويل الوسائط بنجاح: {destination.name}"

            return False, "فشل إنشاء ملف الوسائط الناتج."

        except Exception as e:
            logger.error(f"FFmpeg exception: {e}")
            if destination.exists():
                try:
                    destination.unlink()
                except Exception:
                    pass
            return False, f"خطأ أثناء تشغيل FFmpeg: {str(e)}"
