# -*- coding: utf-8 -*-
"""
SINAX Audio Service
Industrial-grade, local-first audio processing engine powered by FFmpeg.
Provides 30+ audio operations for single and batch workflows without external cloud dependencies.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.conversion.dependency_manager import dependency_manager
from app.services.audio.audio_utils import (
    calc_target_audio_bitrate,
    format_duration,
    parse_time_str,
    COMPRESS_PRESETS,
    LOUDNORM_PRESETS,
    EQ_PRESETS
)

logger = get_logger("audio_service")


class AudioService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioService, cls).__new__(cls)
        return cls._instance

    def get_ffmpeg_exe(self) -> Optional[str]:
        p = dependency_manager.get_tool_path("ffmpeg")
        if p and os.path.exists(str(p)):
            return str(p)
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass
        return shutil.which("ffmpeg")

    def get_ffprobe_exe(self) -> Optional[str]:
        ffmpeg_exe = self.get_ffmpeg_exe()
        if ffmpeg_exe:
            cand = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe.exe" if os.name == "nt" else "ffprobe")
            if os.path.exists(cand):
                return cand
        return shutil.which("ffprobe")

    def is_available(self) -> bool:
        return self.get_ffmpeg_exe() is not None

    # ---------------------------------------------------------
    # Core Subprocess Runner
    # ---------------------------------------------------------
    def run_ffmpeg(
        self,
        cmd_args: List[str],
        duration_sec: Optional[float] = None,
        progress_callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return False, "محرك FFmpeg غير متوفر. يرجى تثبيته."

        full_cmd = [ffmpeg_exe, "-hide_banner"] + cmd_args
        logger.debug(f"AudioService running command: {' '.join(full_cmd[:12])}...")

        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        process = None
        try:
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=creationflags,
            )

            stderr_lines = []
            time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.?\d*)")

            while True:
                if cancel_token and getattr(cancel_token, "is_cancelled", False):
                    process.kill()
                    return False, "تم إلغاء العملية بواسطة المستخدم."

                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break

                if line:
                    stderr_lines.append(line)
                    if progress_callback and duration_sec and duration_sec > 0:
                        m = time_pattern.search(line)
                        if m:
                            h, mn, s = float(m.group(1)), float(m.group(2)), float(m.group(3))
                            curr_sec = h * 3600 + mn * 60 + s
                            pct = min(99.0, max(0.0, (curr_sec / duration_sec) * 100.0))
                            progress_callback(pct, {"current_sec": curr_sec, "duration_sec": duration_sec})

            rc = process.wait()
            full_stderr = "".join(stderr_lines)

            if rc == 0:
                if progress_callback:
                    progress_callback(100.0, {"finished": True})
                return True, "اكتملت العملية بنجاح."
            else:
                tail = "\n".join(stderr_lines[-10:])
                logger.error(f"FFmpeg returned error code {rc}:\n{tail}")
                return False, f"فشلت العملية (رمز {rc}): {tail[:300]}"

        except Exception as e:
            logger.error(f"Subprocess execution exception: {e}", exc_info=True)
            if process:
                try:
                    process.kill()
                except Exception:
                    pass
            return False, str(e)
        finally:
            if process:
                if process.stdout:
                    try:
                        process.stdout.close()
                    except Exception:
                        pass
                if process.stderr:
                    try:
                        process.stderr.close()
                    except Exception:
                        pass

    def _execute_atomic(
        self,
        cmd_args: List[str],
        temp_out: str,
        final_out: str,
        duration_sec: Optional[float] = None,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Runs ffmpeg command to temp_out and atomically renames to final_out on success."""
        Path(final_out).parent.mkdir(parents=True, exist_ok=True)
        if Path(temp_out).exists():
            try:
                Path(temp_out).unlink()
            except Exception:
                pass

        success, msg = self.run_ffmpeg(
            cmd_args,
            duration_sec=duration_sec,
            progress_callback=callback,
            cancel_token=cancel_token,
        )

        if success and Path(temp_out).exists():
            try:
                if Path(final_out).exists():
                    Path(final_out).unlink()
                shutil.move(temp_out, final_out)
                return {"success": True, "output_path": final_out, "message": "نجحت العملية"}
            except Exception as e:
                return {"success": False, "message": f"خطأ عند نقل الملف النهائي: {e}"}
        else:
            if Path(temp_out).exists():
                try:
                    Path(temp_out).unlink()
                except Exception:
                    pass
            return {"success": False, "message": msg}

    # ---------------------------------------------------------
    # Probing & Audio Metadata
    # ---------------------------------------------------------
    def get_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts duration, sample rate, channels, bit rate, format, tags,
        and embedded cover art directly via ffprobe or ffmpeg inspect.
        """
        meta: Dict[str, Any] = {
            "path": file_path,
            "filename": Path(file_path).name,
            "size_bytes": 0,
            "duration": 0.0,
            "duration_formatted": "00:00",
            "sample_rate": 44100,
            "channels": 2,
            "channel_layout": "stereo",
            "bitrate_kbps": 0,
            "codec": "",
            "format": "",
            "tags": {},
            "has_cover_art": False,
        }

        if not os.path.exists(file_path):
            return meta

        try:
            meta["size_bytes"] = os.path.getsize(file_path)
        except Exception:
            pass

        ffprobe_exe = self.get_ffprobe_exe()
        if ffprobe_exe:
            try:
                startupinfo = None
                creationflags = 0
                if os.name == "nt":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

                cmd = [
                    ffprobe_exe,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    file_path
                ]
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    errors="replace",
                    startupinfo=startupinfo,
                    creationflags=creationflags,
                    timeout=8
                )
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    fmt = data.get("format", {})
                    meta["format"] = fmt.get("format_name", "")
                    meta["duration"] = float(fmt.get("duration", 0.0))
                    meta["duration_formatted"] = format_duration(meta["duration"])
                    meta["bitrate_kbps"] = int(float(fmt.get("bit_rate", 0)) / 1000) if fmt.get("bit_rate") else 0
                    meta["tags"] = fmt.get("tags", {})

                    for stream in data.get("streams", []):
                        if stream.get("codec_type") == "audio":
                            meta["codec"] = stream.get("codec_name", "")
                            meta["sample_rate"] = int(stream.get("sample_rate", 44100))
                            meta["channels"] = int(stream.get("channels", 2))
                            meta["channel_layout"] = stream.get("channel_layout", "stereo")
                            if not meta["bitrate_kbps"] and stream.get("bit_rate"):
                                meta["bitrate_kbps"] = int(float(stream["bit_rate"]) / 1000)
                        elif stream.get("codec_type") == "video":
                            # Possible cover art embedded as attached pic
                            meta["has_cover_art"] = True

                    return meta
            except Exception as e:
                logger.debug(f"ffprobe failed, falling back to ffmpeg -i: {e}")

        # Fallback: run ffmpeg -i and parse stderr
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return meta

        try:
            startupinfo = None
            creationflags = 0
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            res = subprocess.run(
                [ffmpeg_exe, "-hide_banner", "-i", file_path],
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=creationflags,
                timeout=8
            )
            text = res.stderr
            # Format
            fmt_match = re.search(r"Input #0,\s*([^,]+),", text)
            if fmt_match:
                meta["format"] = fmt_match.group(1).strip()
            if not meta["format"]:
                meta["format"] = Path(file_path).suffix.lstrip(".").lower()

            # Duration
            dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", text)
            if dur_match:
                h, m, s = float(dur_match.group(1)), float(dur_match.group(2)), float(dur_match.group(3))
                meta["duration"] = h * 3600 + m * 60 + s
                meta["duration_formatted"] = format_duration(meta["duration"])
            # Bitrate
            br_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", text)
            if br_match:
                meta["bitrate_kbps"] = int(br_match.group(1))
            # Audio Stream
            audio_match = re.search(r"Stream.*Audio:\s*([^,]+),\s*(\d+)\s*Hz,\s*([^,]+)", text)
            if audio_match:
                raw_codec = audio_match.group(1).strip()
                meta["codec"] = raw_codec.split()[0] if raw_codec else ""
                meta["sample_rate"] = int(audio_match.group(2))
                meta["channel_layout"] = audio_match.group(3).strip()
                meta["channels"] = 1 if "mono" in meta["channel_layout"] else 2
        except Exception as e:
            logger.error(f"Error inspecting audio metadata: {e}")

        if not meta["format"]:
            meta["format"] = Path(file_path).suffix.lstrip(".").lower()

        return meta

    # ---------------------------------------------------------
    # Visualizations: Waveform & Spectrogram
    # ---------------------------------------------------------
    def generate_waveform_image(
        self,
        input_file: str,
        output_png: str,
        width: int = 700,
        height: int = 100,
        color: str = "#00A4EF"
    ) -> bool:
        """Renders an audio waveform image natively via FFmpeg showwavespic."""
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe or not os.path.exists(input_file):
            return False

        Path(output_png).parent.mkdir(parents=True, exist_ok=True)
        # showwavespic syntax: showwavespic=s=WxH:colors=color
        cmd = [
            "-y",
            "-i", input_file,
            "-filter_complex", f"showwavespic=s={width}x{height}:colors={color}",
            "-frames:v", "1",
            output_png
        ]
        success, _ = self.run_ffmpeg(cmd)
        return success and os.path.exists(output_png)

    def generate_spectrogram_image(
        self,
        input_file: str,
        output_png: str,
        width: int = 700,
        height: int = 100,
        color: str = "plasma"
    ) -> bool:
        """Renders an audio frequency spectrogram natively via FFmpeg showspectrumpic."""
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe or not os.path.exists(input_file):
            return False

        Path(output_png).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "-y",
            "-i", input_file,
            "-filter_complex", f"showspectrumpic=s={width}x{height}:color={color}:legend=disabled",
            "-frames:v", "1",
            output_png
        ]
        success, _ = self.run_ffmpeg(cmd)
        return success and os.path.exists(output_png)

    # ---------------------------------------------------------
    # Audio Analysis: EBU R128 LUFS & True Peak
    # ---------------------------------------------------------
    def analyze_audio_loudness(self, input_file: str) -> Dict[str, Any]:
        """
        Runs EBU R128 loudness analysis via loudnorm filter print_format=json.
        Returns integrated loudness (LUFS), true peak (dBFS), loudness range (LRA).
        """
        result = {
            "input_i": -99.0,
            "input_tp": -99.0,
            "input_lra": 0.0,
            "input_thresh": -99.0,
            "success": False
        }
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe or not os.path.exists(input_file):
            return result

        cmd = [
            ffmpeg_exe,
            "-hide_banner",
            "-i", input_file,
            "-af", "loudnorm=print_format=json",
            "-f", "null",
            "-"
        ]
        try:
            startupinfo = None
            creationflags = 0
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            res = subprocess.run(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=creationflags,
                timeout=30
            )
            # Find json block in stderr
            match = re.search(r"\{\s*\"input_i\"[\s\S]*?\}", res.stderr)
            if match:
                data = json.loads(match.group(0))
                result["input_i"] = float(data.get("input_i", -99.0))
                result["input_tp"] = float(data.get("input_tp", -99.0))
                result["input_lra"] = float(data.get("input_lra", 0.0))
                result["input_thresh"] = float(data.get("input_thresh", -99.0))
                result["success"] = True
        except Exception as e:
            logger.error(f"Failed to analyze loudness: {e}")

        return result

    # ---------------------------------------------------------
    # Core Operations
    # ---------------------------------------------------------

    def convert_audio(
        self,
        input_file: str,
        output_file: str,
        format_ext: str = "mp3",
        bitrate: str = "192k",
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        vbr_cbr: str = "CBR",
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Convert audio format with custom bitrate, sample rate, and channels."""
        meta = self.get_audio_metadata(input_file)
        temp_out = f"{output_file}.tmp.{format_ext}"

        cmd = ["-y", "-i", input_file, "-vn"]

        # Codec & Bitrate mappings
        ext_lower = format_ext.lower().replace(".", "")
        if ext_lower == "mp3":
            cmd += ["-c:a", "libmp3lame"]
            if vbr_cbr == "VBR":
                cmd += ["-q:a", "2"]
            else:
                cmd += ["-b:a", bitrate]
        elif ext_lower in ("aac", "m4a"):
            cmd += ["-c:a", "aac", "-b:a", bitrate]
        elif ext_lower == "wav":
            cmd += ["-c:a", "pcm_s16le"]
        elif ext_lower == "flac":
            cmd += ["-c:a", "flac", "-compression_level", "8"]
        elif ext_lower == "ogg":
            cmd += ["-c:a", "libvorbis", "-b:a", bitrate]
        elif ext_lower == "opus":
            cmd += ["-c:a", "libopus", "-b:a", bitrate]
        elif ext_lower == "wma":
            cmd += ["-c:a", "wmav2", "-b:a", bitrate]
        elif ext_lower == "aiff":
            cmd += ["-c:a", "pcm_s16be"]
        elif ext_lower == "ac3":
            cmd += ["-c:a", "ac3", "-b:a", bitrate]
        elif ext_lower == "amr":
            cmd += ["-c:a", "libopencore_amrnb", "-ar", "8000", "-ac", "1"]
        else:
            cmd += ["-b:a", bitrate]

        if sample_rate and ext_lower != "amr":
            cmd += ["-ar", str(sample_rate)]
        if channels and ext_lower != "amr":
            cmd += ["-ac", str(channels)]

        cmd.append(temp_out)
        return self._execute_atomic(cmd, temp_out, output_file, meta.get("duration", 0.0), callback, cancel_token)

    def compress_audio(
        self,
        input_file: str,
        output_file: str,
        preset: str = "balanced",
        custom_bitrate: Optional[str] = None,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Compress audio using presets (light, balanced, strong, max, lossless_flac)."""
        cfg = COMPRESS_PRESETS.get(preset, COMPRESS_PRESETS["balanced"])
        bitrate = custom_bitrate or cfg.get("bitrate", "192k")
        _, out_ext = os.path.splitext(output_file)
        ext = out_ext.lstrip(".") or "mp3"

        if preset == "lossless_flac":
            return self.convert_audio(input_file, output_file, format_ext="flac", callback=callback, cancel_token=cancel_token)

        return self.convert_audio(input_file, output_file, format_ext=ext, bitrate=bitrate, callback=callback, cancel_token=cancel_token)

    def compress_target_size(
        self,
        input_file: str,
        output_file: str,
        target_mb: float = 5.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Calculates exact audio bitrate to guarantee final file size below target_mb."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        target_kbps = calc_target_audio_bitrate(target_mb, dur)
        logger.info(f"Target size {target_mb}MB for {dur:.1f}s -> calculated {target_kbps}kbps")

        _, ext = os.path.splitext(output_file)
        fmt = ext.lstrip(".") or "mp3"
        return self.convert_audio(input_file, output_file, format_ext=fmt, bitrate=f"{target_kbps}k", callback=callback, cancel_token=cancel_token)

    def trim_audio(
        self,
        input_file: str,
        output_file: str,
        start_time: str = "00:00:00",
        end_time: Optional[str] = None,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Trim audio by start and end timestamps."""
        s_sec = parse_time_str(start_time)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"

        cmd = ["-y", "-ss", str(s_sec), "-i", input_file]
        dur = 0.0
        if end_time:
            e_sec = parse_time_str(end_time)
            if e_sec > s_sec:
                dur = e_sec - s_sec
                cmd += ["-t", str(dur)]

        cmd += ["-c", "copy", temp_out]
        # If stream copy fails due to codec boundaries, we re-encode
        res = self._execute_atomic(cmd, temp_out, output_file, dur or 10.0, callback, cancel_token)
        if not res.get("success"):
            # Re-encode fallback
            cmd_re = ["-y", "-ss", str(s_sec), "-i", input_file]
            if dur > 0:
                cmd_re += ["-t", str(dur)]
            cmd_re += ["-c:a", "libmp3lame" if output_file.endswith(".mp3") else "aac", temp_out]
            res = self._execute_atomic(cmd_re, temp_out, output_file, dur or 10.0, callback, cancel_token)
        return res

    def split_audio_by_duration(
        self,
        input_file: str,
        output_dir: str,
        segment_seconds: int = 300,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Split audio into segments of N seconds."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        stem = Path(input_file).stem
        ext = Path(input_file).suffix or ".mp3"
        out_pattern = os.path.join(output_dir, f"{stem}_part%03d{ext}")

        cmd = [
            "-y",
            "-i", input_file,
            "-f", "segment",
            "-segment_time", str(segment_seconds),
            "-c", "copy",
            out_pattern
        ]
        success, msg = self.run_ffmpeg(cmd, duration_sec=dur, progress_callback=callback, cancel_token=cancel_token)
        if not success:
            # Fallback re-encode
            cmd_re = [
                "-y",
                "-i", input_file,
                "-f", "segment",
                "-segment_time", str(segment_seconds),
                out_pattern
            ]
            success, msg = self.run_ffmpeg(cmd_re, duration_sec=dur, progress_callback=callback, cancel_token=cancel_token)

        return {"success": success, "message": msg, "output_dir": output_dir}

    def split_audio_by_silence(
        self,
        input_file: str,
        output_dir: str,
        noise_threshold_db: float = -40.0,
        min_silence_dur: float = 1.5,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Detect silence intervals and split audio file accordingly."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        ffmpeg_exe = self.get_ffmpeg_exe()
        if not ffmpeg_exe:
            return {"success": False, "message": "FFmpeg غير متوفر"}

        # Step 1: Detect silence timestamps
        cmd = [
            ffmpeg_exe, "-hide_banner", "-i", input_file,
            "-af", f"silencedetect=noise={noise_threshold_db}dB:d={min_silence_dur}",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding="utf-8", errors="replace")
        split_points = [0.0]
        for line in res.stderr.splitlines():
            m = re.search(r"silence_start:\s*(\d+\.?\d*)", line)
            if m:
                s_time = float(m.group(1))
                if s_time - split_points[-1] > 3.0: # Minimum segment length 3s
                    split_points.append(s_time)

        if dur > 0 and (dur - split_points[-1]) > 1.0:
            split_points.append(dur)
        elif len(split_points) == 1:
            split_points.append(dur)

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        stem = Path(input_file).stem
        ext = Path(input_file).suffix or ".mp3"

        total_segments = len(split_points) - 1
        for i in range(total_segments):
            if cancel_token and getattr(cancel_token, "is_cancelled", False):
                return {"success": False, "message": "تم الإلغاء"}
            start_t = split_points[i]
            end_t = split_points[i+1]
            seg_dur = end_t - start_t
            out_file = os.path.join(output_dir, f"{stem}_track_{i+1:02d}{ext}")
            cut_cmd = ["-y", "-ss", str(start_t), "-i", input_file, "-t", str(seg_dur), "-c", "copy", out_file]
            s_ok, _ = self.run_ffmpeg(cut_cmd)
            if not s_ok:
                cut_cmd_re = ["-y", "-ss", str(start_t), "-i", input_file, "-t", str(seg_dur), out_file]
                self.run_ffmpeg(cut_cmd_re)
            if callback:
                callback(((i + 1) / total_segments) * 100.0, {"segment": i + 1, "total": total_segments})

        return {"success": True, "message": f"تم تقسيم الملف إلى {total_segments} مقطع", "output_dir": output_dir}

    def merge_audio_files(
        self,
        input_files: List[str],
        output_file: str,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Merge/concat multiple audio files into a single track."""
        if not input_files:
            return {"success": False, "message": "لم يتم تحديد ملفات للدمج."}

        temp_list = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        try:
            for f in input_files:
                safe = f.replace("\\", "/")
                temp_list.write(f"file '{safe}'\n")
            temp_list.close()

            temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
            cmd = ["-y", "-f", "concat", "-safe", "0", "-i", temp_list.name, "-c", "copy", temp_out]
            res = self._execute_atomic(cmd, temp_out, output_file, 0.0, callback, cancel_token)
            if not res.get("success"):
                # Fallback: complex filter concat with re-encode
                filter_inputs = []
                for i in range(len(input_files)):
                    filter_inputs.append(f"[{i}:a]")
                filter_str = f"{''.join(filter_inputs)}concat=n={len(input_files)}:v=0:a=1[outa]"
                re_cmd = ["-y"]
                for f in input_files:
                    re_cmd += ["-i", f]
                re_cmd += ["-filter_complex", filter_str, "-map", "[outa]", temp_out]
                res = self._execute_atomic(re_cmd, temp_out, output_file, 0.0, callback, cancel_token)
            return res
        finally:
            if os.path.exists(temp_list.name):
                try:
                    os.unlink(temp_list.name)
                except Exception:
                    pass

    def crossfade_audio_files(
        self,
        input_files: List[str],
        output_file: str,
        crossfade_dur: float = 3.0,
        curve: str = "tri",
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Merge audio files sequentially with acrossfade transition."""
        if len(input_files) < 2:
            return {"success": False, "message": "يتطلب الـ Crossfade ملفين على الأقل."}

        # Build progressive acrossfade filter graph
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        cmd = ["-y"]
        for f in input_files:
            cmd += ["-i", f]

        filter_chain = []
        n = len(input_files)
        # First crossfade
        filter_chain.append(f"[0:a][1:a]acrossfade=d={crossfade_dur}:c1={curve}:c2={curve}[a01]")
        last_out = "[a01]"
        for i in range(2, n):
            nxt_out = f"[a{i}]"
            filter_chain.append(f"{last_out}[{i}:a]acrossfade=d={crossfade_dur}:c1={curve}:c2={curve}{nxt_out}")
            last_out = nxt_out

        filter_complex_str = ";".join(filter_chain)
        cmd += ["-filter_complex", filter_complex_str, "-map", last_out, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, 0.0, callback, cancel_token)

    def fade_audio(
        self,
        input_file: str,
        output_file: str,
        fade_in_sec: float = 2.0,
        fade_out_sec: float = 2.0,
        curve: str = "tri",
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Apply Fade In and Fade Out volume envelope."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"

        filters = []
        if fade_in_sec > 0:
            filters.append(f"afade=t=in:ss=0:d={fade_in_sec}:curve={curve}")
        if fade_out_sec > 0 and dur > fade_out_sec:
            out_start = dur - fade_out_sec
            filters.append(f"afade=t=out:ss={out_start:.2f}:d={fade_out_sec}:curve={curve}")

        af_str = ",".join(filters) if filters else "anull"
        cmd = ["-y", "-i", input_file, "-af", af_str, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def loudness_normalize(
        self,
        input_file: str,
        output_file: str,
        target_lufs: float = -14.0,
        true_peak: float = -1.0,
        lra: float = 11.0,
        dual_pass: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """EBU R128 Loudness Normalization with optional accurate dual-pass."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"

        if dual_pass:
            analysis = self.analyze_audio_loudness(input_file)
            if analysis.get("success"):
                meas_i = analysis["input_i"]
                meas_tp = analysis["input_tp"]
                meas_lra = analysis["input_lra"]
                meas_thresh = analysis["input_thresh"]
                af = (
                    f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:"
                    f"measured_I={meas_i}:measured_TP={meas_tp}:measured_LRA={meas_lra}:"
                    f"measured_thresh={meas_thresh}:linear=true:print_format=summary"
                )
            else:
                af = f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"
        else:
            af = f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"

        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def peak_normalize(
        self,
        input_file: str,
        output_file: str,
        target_db: float = -1.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Peak normalize audio to target_db."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        # Measure peak volume first
        ffmpeg_exe = self.get_ffmpeg_exe()
        vol_cmd = [ffmpeg_exe, "-hide_banner", "-i", input_file, "-af", "volumedetect", "-f", "null", "-"]
        res = subprocess.run(vol_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, encoding="utf-8", errors="replace")
        max_vol = 0.0
        m = re.search(r"max_volume:\s*(-?\d+\.?\d*)\s*dB", res.stderr)
        if m:
            max_vol = float(m.group(1))

        gain_needed = target_db - max_vol
        af = f"volume={gain_needed:+.2f}dB"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def volume_adjust(
        self,
        input_file: str,
        output_file: str,
        gain_db: float = 0.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Boost or attenuate volume by gain_db."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        af = f"volume={gain_db:+.2f}dB"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def apply_compressor(
        self,
        input_file: str,
        output_file: str,
        threshold_db: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 20.0,
        release_ms: float = 250.0,
        makeup_gain_db: float = 0.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Dynamic Range Compressor (acompressor)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        af = f"acompressor=threshold={threshold_db}dB:ratio={ratio}:attack={attack_ms}:release={release_ms}:makeup={makeup_gain_db}dB"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def apply_limiter(
        self,
        input_file: str,
        output_file: str,
        limit_db: float = -1.0,
        attack_ms: float = 5.0,
        release_ms: float = 50.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Audio Peak Limiter (alimiter)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        # alimiter limit value is in linear scale (e.g. 10^(dB/20))
        limit_linear = 10.0 ** (limit_db / 20.0)
        af = f"alimiter=limit={limit_linear:.3f}:attack={attack_ms}:release={release_ms}"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def apply_noise_gate(
        self,
        input_file: str,
        output_file: str,
        threshold_db: float = -40.0,
        range_db: float = -60.0,
        attack_ms: float = 20.0,
        release_ms: float = 250.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Noise Gate (agate)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        af = f"agate=threshold={threshold_db}dB:range={range_db}dB:attack={attack_ms}:release={release_ms}"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def denoise_audio(
        self,
        input_file: str,
        output_file: str,
        nr_level_db: float = -25.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """FFT-based Noise Reduction (afftdn)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        af = f"afftdn=nf={nr_level_db}:tn=1"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def remove_hum(
        self,
        input_file: str,
        output_file: str,
        freq: int = 50,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Remove 50Hz or 60Hz hum and harmonics using notch filters."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        # Filter fundamental and 2 harmonics (e.g. 50, 100, 150 or 60, 120, 180)
        f1, f2, f3 = freq, freq * 2, freq * 3
        af = f"bandreject=f={f1}:w=4,bandreject=f={f2}:w=4,bandreject=f={f3}:w=4"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def declick_declip(
        self,
        input_file: str,
        output_file: str,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """De-click and De-clip restoration (adeclick, adeclip)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        af = "adeclip,adeclick"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def remove_silence(
        self,
        input_file: str,
        output_file: str,
        threshold_db: float = -45.0,
        min_dur_sec: float = 0.8,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Truncate silence periods from audio (silenceremove)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        # Start and middle silence remove
        af = f"silenceremove=start_periods=1:start_duration=0.1:start_threshold={threshold_db}dB:stop_periods=-1:stop_duration={min_dur_sec}:stop_threshold={threshold_db}dB"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def podcast_voice_enhancer(
        self,
        input_file: str,
        output_file: str,
        profile: str = "crisp_podcast",
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        1-Click Podcast Voice Enhancer Pipeline:
        FFT Denoise -> High-pass 80Hz -> Presence EQ -> Compressor -> -16 LUFS Loudness -> Limiter.
        """
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"

        if profile == "warm_speech":
            af = (
                "afftdn=nf=-24,"
                "highpass=f=75,"
                "equalizer=f=250:width_type=h:width=120:g=2,"
                "equalizer=f=3500:width_type=h:width=1500:g=2,"
                "acompressor=threshold=-18dB:ratio=3:attack=15:release=120,"
                "loudnorm=I=-16:TP=-1.5:LRA=10,"
                "alimiter=limit=0.9"
            )
        else: # crisp_podcast default
            af = (
                "afftdn=nf=-25,"
                "highpass=f=80,"
                "equalizer=f=3200:width_type=h:width=1800:g=3,"
                "acompressor=threshold=-19dB:ratio=3.5:attack=10:release=100,"
                "loudnorm=I=-16:TP=-1.2:LRA=9,"
                "alimiter=limit=0.95"
            )

        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def apply_eq(
        self,
        input_file: str,
        output_file: str,
        bass_db: float = 0.0,
        mid_db: float = 0.0,
        treble_db: float = 0.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """3-band Graphic Equalizer (Bass 100Hz, Mid 1kHz, Treble 10kHz)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"

        filters = []
        if abs(bass_db) > 0.1:
            filters.append(f"equalizer=f=100:width_type=o:width=1:g={bass_db}")
        if abs(mid_db) > 0.1:
            filters.append(f"equalizer=f=1000:width_type=o:width=1:g={mid_db}")
        if abs(treble_db) > 0.1:
            filters.append(f"equalizer=f=10000:width_type=o:width=1:g={treble_db}")

        af = ",".join(filters) if filters else "anull"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def apply_filters(
        self,
        input_file: str,
        output_file: str,
        filter_type: str = "highpass",
        cutoff_freq: int = 120,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Acoustic Filter (highpass or lowpass)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        af = f"{filter_type}=f={cutoff_freq}"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def bass_treble_boost(
        self,
        input_file: str,
        output_file: str,
        bass_gain: float = 3.0,
        treble_gain: float = 3.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Tone controls for Bass and Treble."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        af = f"bass=g={bass_gain},treble=g={treble_gain}"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def change_speed_tempo(
        self,
        input_file: str,
        output_file: str,
        speed_factor: float = 1.25,
        preserve_pitch: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Change tempo without pitch shift (atempo) or resample speed."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        target_dur = dur / speed_factor if speed_factor > 0 else dur
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"

        if preserve_pitch:
            # atempo supports 0.5 to 2.0 per filter instance
            factor = max(0.5, min(2.0, speed_factor))
            af = f"atempo={factor}"
        else:
            sr = meta.get("sample_rate", 44100)
            new_sr = int(sr * speed_factor)
            af = f"asetrate={new_sr},aresample={sr}"

        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, target_dur, callback, cancel_token)

    def pitch_shift(
        self,
        input_file: str,
        output_file: str,
        semitones: float = 2.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Shift pitch up or down by semitones."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        # Pitch ratio = 2^(semitones / 12)
        ratio = 2.0 ** (semitones / 12.0)
        sr = meta.get("sample_rate", 44100)
        new_sr = int(sr * ratio)
        # Shift pitch by adjusting sample rate then compensating tempo back
        tempo_comp = 1.0 / ratio
        # Clamp tempo_comp to atempo limit 0.5 - 2.0
        tempo_comp = max(0.5, min(2.0, tempo_comp))
        af = f"asetrate={new_sr},aresample={sr},atempo={tempo_comp}"
        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def reverse_audio(
        self,
        input_file: str,
        output_file: str,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Play audio backwards (areverse)."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"
        cmd = ["-y", "-i", input_file, "-af", "areverse", temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def channel_routing(
        self,
        input_file: str,
        output_file: str,
        mode: str = "stereo_to_mono",
        pan_val: float = 0.0,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Channel operations: stereo to mono downmix, mono to stereo, swap LR, pan."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"

        if mode == "stereo_to_mono":
            af = "pan=mono|c0=0.5*c0+0.5*c1"
        elif mode == "mono_to_stereo":
            af = "pan=stereo|c0=c0|c1=c0"
        elif mode == "swap_lr":
            af = "pan=stereo|c0=c1|c1=c0"
        elif mode == "pan":
            # pan between -1.0 (left) and +1.0 (right)
            left_gain = max(0.0, min(1.0, (1.0 - pan_val)))
            right_gain = max(0.0, min(1.0, (1.0 + pan_val)))
            af = f"pan=stereo|c0={left_gain:.2f}*c0|c1={right_gain:.2f}*c1"
        else:
            af = "anull"

        cmd = ["-y", "-i", input_file, "-af", af, temp_out]
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    def extract_channels(
        self,
        input_file: str,
        output_dir: str,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Extract Left and Right channels as separate audio files."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        stem = Path(input_file).stem
        ext = Path(input_file).suffix or ".mp3"

        left_out = os.path.join(output_dir, f"{stem}_left{ext}")
        right_out = os.path.join(output_dir, f"{stem}_right{ext}")

        # Left channel
        cmd_l = ["-y", "-i", input_file, "-af", "pan=mono|c0=c0", left_out]
        s1, m1 = self.run_ffmpeg(cmd_l, duration_sec=dur, cancel_token=cancel_token)
        # Right channel
        cmd_r = ["-y", "-i", input_file, "-af", "pan=mono|c0=c1", right_out]
        s2, m2 = self.run_ffmpeg(cmd_r, duration_sec=dur, cancel_token=cancel_token)

        success = s1 and s2
        return {"success": success, "message": "تم استخراج القنوات بنجاح" if success else f"{m1}; {m2}", "output_dir": output_dir}

    def update_metadata(
        self,
        input_file: str,
        output_file: str,
        tags: Dict[str, str],
        cover_art_path: Optional[str] = None,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Update ID3 / metadata tags and inject cover art."""
        meta = self.get_audio_metadata(input_file)
        dur = meta.get("duration", 0.0)
        temp_out = f"{output_file}.tmp{Path(output_file).suffix}"

        cmd = ["-y", "-i", input_file]
        if cover_art_path and os.path.exists(cover_art_path):
            cmd += ["-i", cover_art_path, "-map", "0:a", "-map", "1:0", "-c", "copy", "-id3v2_version", "3", "-metadata:s:v", 'title="Album cover"', "-metadata:s:v", 'comment="Cover (front)"']
        else:
            cmd += ["-c", "copy"]

        for k, v in tags.items():
            if v:
                cmd += ["-metadata", f"{k}={v}"]

        cmd.append(temp_out)
        return self._execute_atomic(cmd, temp_out, output_file, dur, callback, cancel_token)

    # ---------------------------------------------------------
    # Generic Single-File Tool Dispatcher
    # ---------------------------------------------------------
    def dispatch_audio_operation(
        self,
        tool_id: str,
        input_path: str,
        output_path: str,
        options: Dict[str, Any],
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Dispatch any registered audio tool ID to its dedicated operation."""
        try:
            if tool_id == "batch_audio_convert":
                fmt = options.get("format", "mp3")
                br = options.get("bitrate", "192k")
                sr = options.get("sample_rate")
                ch = options.get("channels")
                vbr = options.get("vbr_cbr", "CBR")
                return self.convert_audio(input_path, output_path, format_ext=fmt, bitrate=br, sample_rate=sr, channels=ch, vbr_cbr=vbr, callback=callback, cancel_token=cancel_token)

            elif tool_id == "batch_audio_compress":
                preset = options.get("preset", "balanced")
                custom_br = options.get("custom_bitrate")
                return self.compress_audio(input_path, output_path, preset=preset, custom_bitrate=custom_br, callback=callback, cancel_token=cancel_token)

            elif tool_id == "target_size_audio_compress":
                target_mb = float(options.get("target_mb", 5.0))
                return self.compress_target_size(input_path, output_path, target_mb=target_mb, callback=callback, cancel_token=cancel_token)

            elif tool_id == "trim_audio":
                start_t = options.get("start_time", "00:00:00")
                end_t = options.get("end_time")
                return self.trim_audio(input_path, output_path, start_time=start_t, end_time=end_t, callback=callback, cancel_token=cancel_token)

            elif tool_id == "split_audio":
                out_dir = os.path.dirname(output_path)
                seg_s = int(options.get("segment_seconds", 300))
                return self.split_audio_by_duration(input_path, out_dir, segment_seconds=seg_s, callback=callback, cancel_token=cancel_token)

            elif tool_id == "silence_split_audio":
                out_dir = os.path.dirname(output_path)
                thresh = float(options.get("threshold_db", -40.0))
                min_s = float(options.get("min_silence_dur", 1.5))
                return self.split_audio_by_silence(input_path, out_dir, noise_threshold_db=thresh, min_silence_dur=min_s, callback=callback, cancel_token=cancel_token)

            elif tool_id == "fade_audio":
                f_in = float(options.get("fade_in_sec", 2.0))
                f_out = float(options.get("fade_out_sec", 2.0))
                curve = options.get("curve", "tri")
                return self.fade_audio(input_path, output_path, fade_in_sec=f_in, fade_out_sec=f_out, curve=curve, callback=callback, cancel_token=cancel_token)

            elif tool_id == "loudness_normalize_audio":
                t_lufs = float(options.get("target_lufs", -14.0))
                tp = float(options.get("true_peak", -1.0))
                dual = bool(options.get("dual_pass", True))
                return self.loudness_normalize(input_path, output_path, target_lufs=t_lufs, true_peak=tp, dual_pass=dual, callback=callback, cancel_token=cancel_token)

            elif tool_id == "peak_normalize_audio":
                t_db = float(options.get("peak_db", -1.0))
                return self.peak_normalize(input_path, output_path, target_db=t_db, callback=callback, cancel_token=cancel_token)

            elif tool_id == "volume_adjust_audio":
                gain = float(options.get("gain_db", 0.0))
                return self.volume_adjust(input_path, output_path, gain_db=gain, callback=callback, cancel_token=cancel_token)

            elif tool_id == "compressor_audio":
                th = float(options.get("threshold_db", -20.0))
                rat = float(options.get("ratio", 4.0))
                att = float(options.get("attack_ms", 20.0))
                rel = float(options.get("release_ms", 250.0))
                mk = float(options.get("makeup_gain_db", 0.0))
                return self.apply_compressor(input_path, output_path, threshold_db=th, ratio=rat, attack_ms=att, release_ms=rel, makeup_gain_db=mk, callback=callback, cancel_token=cancel_token)

            elif tool_id == "limiter_audio":
                lim = float(options.get("limit_db", -1.0))
                return self.apply_limiter(input_path, output_path, limit_db=lim, callback=callback, cancel_token=cancel_token)

            elif tool_id == "noise_gate_audio":
                th = float(options.get("threshold_db", -40.0))
                rng = float(options.get("range_db", -60.0))
                return self.apply_noise_gate(input_path, output_path, threshold_db=th, range_db=rng, callback=callback, cancel_token=cancel_token)

            elif tool_id == "denoise_audio":
                nr = float(options.get("nr_level_db", -25.0))
                return self.denoise_audio(input_path, output_path, nr_level_db=nr, callback=callback, cancel_token=cancel_token)

            elif tool_id == "hum_removal_audio":
                freq = int(options.get("freq", 50))
                return self.remove_hum(input_path, output_path, freq=freq, callback=callback, cancel_token=cancel_token)

            elif tool_id == "declick_declip_audio":
                return self.declick_declip(input_path, output_path, callback=callback, cancel_token=cancel_token)

            elif tool_id == "silence_remove_audio":
                th = float(options.get("threshold_db", -45.0))
                min_dur = float(options.get("min_dur_sec", 0.8))
                return self.remove_silence(input_path, output_path, threshold_db=th, min_dur_sec=min_dur, callback=callback, cancel_token=cancel_token)

            elif tool_id == "podcast_voice_enhancer":
                prof = options.get("profile", "crisp_podcast")
                return self.podcast_voice_enhancer(input_path, output_path, profile=prof, callback=callback, cancel_token=cancel_token)

            elif tool_id == "graphic_eq_audio":
                b = float(options.get("bass_db", 0.0))
                m = float(options.get("mid_db", 0.0))
                t = float(options.get("treble_db", 0.0))
                return self.apply_eq(input_path, output_path, bass_db=b, mid_db=m, treble_db=t, callback=callback, cancel_token=cancel_token)

            elif tool_id == "filters_audio":
                ft = options.get("filter_type", "highpass")
                freq = int(options.get("cutoff_freq", 120))
                return self.apply_filters(input_path, output_path, filter_type=ft, cutoff_freq=freq, callback=callback, cancel_token=cancel_token)

            elif tool_id == "bass_treble_boost":
                bg = float(options.get("bass_gain", 3.0))
                tg = float(options.get("treble_gain", 3.0))
                return self.bass_treble_boost(input_path, output_path, bass_gain=bg, treble_gain=tg, callback=callback, cancel_token=cancel_token)

            elif tool_id == "speed_tempo_audio":
                spd = float(options.get("speed_factor", 1.25))
                pres = bool(options.get("preserve_pitch", True))
                return self.change_speed_tempo(input_path, output_path, speed_factor=spd, preserve_pitch=pres, callback=callback, cancel_token=cancel_token)

            elif tool_id == "pitch_shift_audio":
                semi = float(options.get("semitones", 2.0))
                return self.pitch_shift(input_path, output_path, semitones=semi, callback=callback, cancel_token=cancel_token)

            elif tool_id == "reverse_audio":
                return self.reverse_audio(input_path, output_path, callback=callback, cancel_token=cancel_token)

            elif tool_id == "channel_routing_audio":
                mode = options.get("mode", "stereo_to_mono")
                pan = float(options.get("pan_val", 0.0))
                return self.channel_routing(input_path, output_path, mode=mode, pan_val=pan, callback=callback, cancel_token=cancel_token)

            elif tool_id == "extract_channels_audio":
                out_dir = os.path.dirname(output_path)
                return self.extract_channels(input_path, out_dir, callback=callback, cancel_token=cancel_token)

            elif tool_id == "metadata_editor_audio":
                tags = options.get("tags", {})
                cover = options.get("cover_art_path")
                return self.update_metadata(input_path, output_path, tags=tags, cover_art_path=cover, callback=callback, cancel_token=cancel_token)

            else:
                return {"success": False, "message": f"الأداة {tool_id} غير معروفة أو لا تدعم المعالجة المباشرة."}
        except Exception as e:
            logger.error(f"Error dispatching tool {tool_id}: {e}", exc_info=True)
            return {"success": False, "message": str(e)}


audio_service = AudioService()
