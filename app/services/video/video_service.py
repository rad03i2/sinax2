# -*- coding: utf-8 -*-
"""
SINAX Video Service
Comprehensive, local-first video processing engine powered by FFmpeg.
Provides 25+ industrial-grade video operations for single and batch workflows.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.video.ffmpeg_service import ffmpeg_service
from app.services.video.hardware_detector import hardware_detector
from app.services.video.video_utils import (
    calculate_target_bitrate,
    format_seconds,
    parse_timestamp,
)

logger = get_logger("video_service")


class VideoService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VideoService, cls).__new__(cls)
        return cls._instance

    # ---------------------------------------------------------
    # Helper: Atomic file execution wrapper
    # ---------------------------------------------------------
    def _execute_ffmpeg(
        self,
        cmd_args: List[str],
        temp_out: str,
        final_out: str,
        duration_sec: Optional[float] = None,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Runs ffmpeg command to temp_out and atomically moves to final_out upon success."""
        Path(final_out).parent.mkdir(parents=True, exist_ok=True)
        if Path(temp_out).exists():
            try:
                Path(temp_out).unlink()
            except Exception:
                pass

        success, msg = ffmpeg_service.run_ffmpeg(
            cmd_args,
            duration_sec=duration_sec,
            progress_callback=callback,
            cancel_token=cancel_token,
        )

        # Automatic CPU fallback if hardware encoder fails
        if not success:
            hw_encoders = ["h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_qsv", "hevc_qsv", "h264_amf", "hevc_amf"]
            if any(hw in cmd_args for hw in hw_encoders):
                fallback_args = list(cmd_args)
                for i, arg in enumerate(fallback_args):
                    if arg in ("h264_nvenc", "h264_qsv", "h264_amf"):
                        fallback_args[i] = "libx264"
                    elif arg in ("hevc_nvenc", "hevc_qsv", "hevc_amf"):
                        fallback_args[i] = "libx265"
                    elif arg == "av1_nvenc":
                        fallback_args[i] = "libaom-av1"
                logger.info("Hardware encoder failed; retrying with CPU encoder fallback.")
                success, msg = ffmpeg_service.run_ffmpeg(
                    fallback_args,
                    duration_sec=duration_sec,
                    progress_callback=callback,
                    cancel_token=cancel_token,
                )

        if success and Path(temp_out).exists() and Path(temp_out).stat().st_size > 0:
            try:
                if Path(final_out).exists():
                    Path(final_out).unlink()
                shutil.move(temp_out, final_out)
                orig_size = 0
                new_size = Path(final_out).stat().st_size
                return {
                    "success": True,
                    "message": "تمت المعالجة بنجاح",
                    "output_path": str(final_out),
                    "new_size": new_size,
                }
            except Exception as e:
                return {"success": False, "message": f"فشل حفظ الملف النهائي: {e}"}
        else:
            if Path(temp_out).exists():
                try:
                    Path(temp_out).unlink()
                except Exception:
                    pass
            return {"success": False, "message": msg or "فشلت معالجة الفيديو."}

    # ---------------------------------------------------------
    # 1. Video Compression
    # ---------------------------------------------------------
    def compress_video(
        self,
        input_path: str,
        output_path: str,
        preset: str = "balanced",
        crf: Optional[int] = None,
        target_size_mb: Optional[float] = None,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Compresses video using perceptual CRF presets or exact target size calculation.
        """
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"

        # Target size mode
        if target_size_mb and target_size_mb > 0:
            v_kbit, a_kbit = calculate_target_bitrate(target_size_mb, duration)
            encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)
            args = [
                "-i", input_path,
                "-c:v", encoder,
                "-b:v", f"{v_kbit}k",
                "-maxrate", f"{int(v_kbit * 1.3)}k",
                "-bufsize", f"{int(v_kbit * 2)}k",
                "-c:a", "aac",
                "-b:a", f"{a_kbit}k",
                "-movflags", "+faststart",
                temp_out,
            ]
            res = self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)
            res["orig_size"] = meta.get("size_bytes", 0)
            return res

        # Preset mode
        preset_configs = {
            "light": {"crf": 20, "audio_br": "192k", "preset_spd": "faster"},
            "balanced": {"crf": 24, "audio_br": "128k", "preset_spd": "medium"},
            "strong": {"crf": 28, "audio_br": "96k", "preset_spd": "medium"},
            "max": {"crf": 32, "audio_br": "64k", "preset_spd": "slow"},
        }
        cfg = preset_configs.get(preset, preset_configs["balanced"])
        chosen_crf = crf if crf is not None else cfg["crf"]
        encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)

        args = ["-i", input_path]
        if "nvenc" in encoder:
            args.extend(["-c:v", encoder, "-cq", str(chosen_crf), "-preset", "p4"])
        elif "qsv" in encoder:
            args.extend(["-c:v", encoder, "-global_quality", str(chosen_crf)])
        elif "amf" in encoder:
            args.extend(["-c:v", encoder, "-rc", "cqp", "-qp_p", str(chosen_crf)])
        else:
            args.extend(["-c:v", "libx264", "-crf", str(chosen_crf), "-preset", cfg["preset_spd"]])

        # Audio and container optimizations
        args.extend([
            "-c:a", "aac",
            "-b:a", cfg["audio_br"],
            "-movflags", "+faststart",
            temp_out,
        ])

        res = self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)
        res["orig_size"] = meta.get("size_bytes", 0)
        return res

    # ---------------------------------------------------------
    # 2. Format Conversion
    # ---------------------------------------------------------
    def convert_format(
        self,
        input_path: str,
        output_path: str,
        video_codec: str = "auto",
        audio_codec: str = "auto",
        preset_speed: str = "medium",
        crf: int = 23,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Converts video to target format container and codec."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"

        ext = Path(output_path).suffix.lower().replace(".", "")
        args = ["-i", input_path]

        # Video codec resolution
        if video_codec == "copy":
            args.extend(["-c:v", "copy"])
        elif video_codec == "auto":
            if ext in ("webm",):
                args.extend(["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0"])
            else:
                enc = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)
                args.extend(["-c:v", enc, "-crf" if "libx" in enc else "-cq", str(crf)])
        else:
            enc = hardware_detector.get_best_encoder(video_codec, use_gpu=use_gpu)
            args.extend(["-c:v", enc])

        # Audio codec resolution
        if audio_codec == "copy":
            args.extend(["-c:a", "copy"])
        elif audio_codec == "auto":
            if ext in ("webm",):
                args.extend(["-c:a", "libopus"])
            elif ext in ("wav",):
                args.extend(["-c:a", "pcm_s16le"])
            else:
                args.extend(["-c:a", "aac", "-b:a", "192k"])
        else:
            args.extend(["-c:a", audio_codec])

        if ext == "mp4":
            args.extend(["-movflags", "+faststart"])

        args.append(temp_out)
        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 3. Fast Remux (Lossless Stream Copy)
    # ---------------------------------------------------------
    def fast_remux(
        self,
        input_path: str,
        output_path: str,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Transfers streams losslessly into a new container in seconds (-c copy)."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"

        args = ["-i", input_path, "-c", "copy"]
        if output_path.lower().endswith(".mp4"):
            args.extend(["-movflags", "+faststart"])
        args.append(temp_out)

        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 4. Resize Resolution & Social Formats
    # ---------------------------------------------------------
    def resize_resolution(
        self,
        input_path: str,
        output_path: str,
        resolution: str = "1080p",
        mode: str = "fit",
        custom_w: Optional[int] = None,
        custom_h: Optional[int] = None,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Resizes video with fit, letterbox pad, stretch, or vertical 9:16 blurred canvas."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"
        encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)

        std_resolutions = {
            "4k": (3840, 2160),
            "2k": (2560, 1440),
            "1080p": (1920, 1080),
            "720p": (1280, 720),
            "480p": (854, 480),
            "360p": (640, 360),
            "shorts_9_16": (1080, 1920),
            "square_1_1": (1080, 1080),
        }

        w, h = std_resolutions.get(resolution, (custom_w or 1920, custom_h or 1080))

        args = ["-i", input_path]

        if mode == "vertical_blur" or resolution == "shorts_9_16":
            # Blurred background canvas for Shorts / TikTok / Reels
            filter_str = (
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=20:20[bg];"
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
            )
            args.extend(["-filter_complex", filter_str, "-map", "[v]", "-map", "0:a?"])
        elif mode == "pad":
            # Letterbox / pillarbox
            filter_str = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black"
            args.extend(["-vf", filter_str])
        elif mode == "stretch":
            args.extend(["-vf", f"scale={w}:{h}"])
        else:  # fit / preserve aspect
            args.extend(["-vf", f"scale={w}:-2"])

        args.extend(["-c:v", encoder, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", temp_out])
        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 5. Trim & Cut
    # ---------------------------------------------------------
    def trim_video(
        self,
        input_path: str,
        output_path: str,
        start_time: str = "00:00:00",
        end_time: Optional[str] = None,
        duration: Optional[str] = None,
        mode: str = "accurate",
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Trims video between start and end timestamps."""
        start_sec = parse_timestamp(start_time)
        meta = ffmpeg_service.probe_media(input_path)
        total_dur = meta.get("duration", 0.0)

        calc_dur = 0.0
        if end_time:
            end_sec = parse_timestamp(end_time)
            calc_dur = max(0.0, end_sec - start_sec)
        elif duration:
            calc_dur = parse_timestamp(duration)
        else:
            calc_dur = max(0.0, total_dur - start_sec)

        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"
        args = []

        if mode == "fast_copy":
            # Lossless seek & copy
            args.extend(["-ss", str(start_sec), "-i", input_path])
            if calc_dur > 0:
                args.extend(["-t", str(calc_dur)])
            args.extend(["-c", "copy", temp_out])
        else:
            # Frame-accurate re-encode
            encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)
            args.extend(["-ss", str(start_sec), "-i", input_path])
            if calc_dur > 0:
                args.extend(["-t", str(calc_dur)])
            args.extend(["-c:v", encoder, "-c:a", "aac", "-movflags", "+faststart", temp_out])

        return self._execute_ffmpeg(args, temp_out, output_path, calc_dur or total_dur, callback, cancel_token)

    # ---------------------------------------------------------
    # 6. Cut Middle Segment and Join
    # ---------------------------------------------------------
    def cut_middle_and_join(
        self,
        input_path: str,
        output_path: str,
        cut_start: str,
        cut_end: str,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Removes a middle segment [cut_start, cut_end] and seamlessly stitches remaining parts."""
        meta = ffmpeg_service.probe_media(input_path)
        total_dur = meta.get("duration", 0.0)
        c_start = parse_timestamp(cut_start)
        c_end = parse_timestamp(cut_end)

        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"
        encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)

        # Complex filter select: keeps [0, c_start] and [c_end, total]
        filter_str = (
            f"[0:v]trim=0:{c_start},setpts=PTS-STARTPTS[v0];"
            f"[0:a]atrim=0:{c_start},asetpts=PTS-STARTPTS[a0];"
            f"[0:v]trim={c_end}:{total_dur},setpts=PTS-STARTPTS[v1];"
            f"[0:a]atrim={c_end}:{total_dur},asetpts=PTS-STARTPTS[a1];"
            f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
        )

        args = [
            "-i", input_path,
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", encoder,
            "-c:a", "aac",
            "-movflags", "+faststart",
            temp_out,
        ]

        expected_dur = max(0.0, total_dur - (c_end - c_start))
        return self._execute_ffmpeg(args, temp_out, output_path, expected_dur, callback, cancel_token)

    # ---------------------------------------------------------
    # 7. Split Video
    # ---------------------------------------------------------
    def split_video(
        self,
        input_path: str,
        output_dir: str,
        mode: str = "duration",
        interval_sec: float = 60.0,
        parts_count: int = 2,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Splits video into parts by duration or count."""
        meta = ffmpeg_service.probe_media(input_path)
        total_dur = meta.get("duration", 0.0)
        if total_dur <= 0:
            return {"success": False, "message": "تعذر تحديد مدة الفيديو لتقسيمه."}

        out_folder = Path(output_dir)
        out_folder.mkdir(parents=True, exist_ok=True)
        stem = Path(input_path).stem
        ext = Path(input_path).suffix

        segments: List[Tuple[float, float]] = []
        if mode == "parts":
            count = max(1, parts_count)
            step = total_dur / count
            for i in range(count):
                segments.append((i * step, min((i + 1) * step, total_dur)))
        else:
            step = max(1.0, interval_sec)
            cur = 0.0
            while cur < total_dur:
                nxt = min(cur + step, total_dur)
                segments.append((cur, nxt))
                cur = nxt

        created_files = []
        for idx, (st, en) in enumerate(segments, 1):
            if cancel_token and cancel_token.is_set():
                break
            part_path = out_folder / f"{stem}_part{idx:03d}{ext}"
            dur = en - st
            res = self.trim_video(
                input_path,
                str(part_path),
                start_time=format_seconds(st),
                duration=str(dur),
                mode="fast_copy",
                cancel_token=cancel_token,
            )
            if res.get("success"):
                created_files.append(str(part_path))
            if callback:
                callback((idx / len(segments)) * 100.0, {"part": idx, "total": len(segments)})

        return {
            "success": len(created_files) > 0,
            "created_files": created_files,
            "parts_count": len(created_files),
        }

    # ---------------------------------------------------------
    # 8. Merge Videos
    # ---------------------------------------------------------
    def merge_videos(
        self,
        input_paths: List[str],
        output_path: str,
        reencode: bool = False,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Merges multiple video files sequentially."""
        if not input_paths:
            return {"success": False, "message": "لا توجد ملفات فيديو للدمج."}

        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"
        total_dur = 0.0
        for p in input_paths:
            m = ffmpeg_service.probe_media(p)
            total_dur += m.get("duration", 0.0)

        # Build concat list file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            list_file = f.name
            for p in input_paths:
                # Escape single quotes in path
                esc_path = str(p).replace("'", "'\\''")
                f.write(f"file '{esc_path}'\n")

        try:
            if not reencode:
                # Fast concat demuxer
                args = [
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file,
                    "-c", "copy",
                    temp_out,
                ]
                res = self._execute_ffmpeg(args, temp_out, output_path, total_dur, callback, cancel_token)
                if res.get("success"):
                    return res
                logger.info("Fast concat copy failed; falling back to re-encode concat.")

            # Re-encode concat filter
            encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)
            inputs = []
            filter_ins = ""
            for i, p in enumerate(input_paths):
                inputs.extend(["-i", p])
                filter_ins += f"[{i}:v][{i}:a]"
            filter_str = f"{filter_ins}concat=n={len(input_paths)}:v=1:a=1[outv][outa]"

            args = inputs + [
                "-filter_complex", filter_str,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", encoder,
                "-c:a", "aac",
                "-movflags", "+faststart",
                temp_out,
            ]
            return self._execute_ffmpeg(args, temp_out, output_path, total_dur, callback, cancel_token)

        finally:
            if Path(list_file).exists():
                try:
                    Path(list_file).unlink()
                except Exception:
                    pass

    # ---------------------------------------------------------
    # 9. Audio Extraction
    # ---------------------------------------------------------
    def extract_audio(
        self,
        input_path: str,
        output_path: str,
        audio_format: str = "mp3",
        bitrate: str = "192k",
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Extracts audio track into MP3, WAV, AAC, FLAC, OGG, or OPUS."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"

        codec_map = {
            "mp3": "libmp3lame",
            "aac": "aac",
            "m4a": "aac",
            "wav": "pcm_s16le",
            "flac": "flac",
            "ogg": "libvorbis",
            "opus": "libopus",
        }
        codec = codec_map.get(audio_format.lower(), "libmp3lame")

        args = ["-i", input_path, "-vn", "-c:a", codec]
        if audio_format.lower() not in ("wav", "flac"):
            args.extend(["-b:a", bitrate])
        args.append(temp_out)

        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 10. Mute Audio
    # ---------------------------------------------------------
    def mute_audio(
        self,
        input_path: str,
        output_path: str,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Removes all audio streams without re-encoding video."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"

        args = ["-i", input_path, "-an", "-c:v", "copy", temp_out]
        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 11. Replace or Mix Audio
    # ---------------------------------------------------------
    def replace_or_mix_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        mode: str = "replace",
        bg_volume: float = 0.3,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Replaces video audio or mixes new background music with original audio."""
        meta = ffmpeg_service.probe_media(video_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"

        if mode == "mix":
            # Mix original audio with new audio
            filter_str = f"[0:a]volume=1.0[a0];[1:a]volume={bg_volume}[a1];[a0][a1]amix=inputs=2:duration=first[outa]"
            encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)
            args = [
                "-i", video_path,
                "-i", audio_path,
                "-filter_complex", filter_str,
                "-map", "0:v",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                temp_out,
            ]
        else:
            # Pure replace
            args = [
                "-i", video_path,
                "-i", audio_path,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                temp_out,
            ]

        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 12. Volume Normalize / Amplify
    # ---------------------------------------------------------
    def normalize_volume(
        self,
        input_path: str,
        output_path: str,
        mode: str = "ebu_r128",
        factor: float = 1.5,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Standardizes loudness (EBU R128) or scales volume factor."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"

        if mode == "ebu_r128":
            af = "loudnorm=I=-16:TP=-1.5:LRA=11"
        else:
            af = f"volume={factor}"

        args = ["-i", input_path, "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", temp_out]
        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 13. Speed Control & Reverse
    # ---------------------------------------------------------
    def adjust_speed(
        self,
        input_path: str,
        output_path: str,
        speed_factor: float = 2.0,
        reverse: bool = False,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Adjusts playback speed (0.25x - 4x) or reverses video & audio."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"
        encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)

        if reverse:
            args = [
                "-i", input_path,
                "-vf", "reverse",
                "-af", "areverse",
                "-c:v", encoder,
                "-c:a", "aac",
                temp_out,
            ]
            return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

        # Video PTS filter: 1/speed
        spd = max(0.1, min(10.0, speed_factor))
        pts_factor = 1.0 / spd
        vf = f"setpts={pts_factor}*PTS"

        # Audio atempo filter (atempo can only do 0.5 - 2.0 per instance, so chain if needed)
        cur_spd = spd
        atempo_filters = []
        while cur_spd > 2.0:
            atempo_filters.append("atempo=2.0")
            cur_spd /= 2.0
        while cur_spd < 0.5:
            atempo_filters.append("atempo=0.5")
            cur_spd /= 0.5
        atempo_filters.append(f"atempo={cur_spd}")
        af = ",".join(atempo_filters)

        args = [
            "-i", input_path,
            "-vf", vf,
            "-af", af,
            "-c:v", encoder,
            "-c:a", "aac",
            temp_out,
        ]
        return self._execute_ffmpeg(args, temp_out, output_path, duration / spd, callback, cancel_token)

    # ---------------------------------------------------------
    # 14. Rotate & Flip
    # ---------------------------------------------------------
    def rotate_flip(
        self,
        input_path: str,
        output_path: str,
        rotation: int = 90,
        flip_h: bool = False,
        flip_v: bool = False,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Rotates by 90/180/270 degrees and/or mirrors horizontally/vertically."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"
        encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)

        filters = []
        if rotation == 90:
            filters.append("transpose=1")
        elif rotation == 180:
            filters.append("transpose=2,transpose=2")
        elif rotation == 270:
            filters.append("transpose=2")

        if flip_h:
            filters.append("hflip")
        if flip_v:
            filters.append("vflip")

        vf = ",".join(filters) if filters else "null"
        args = [
            "-i", input_path,
            "-vf", vf,
            "-c:v", encoder,
            "-c:a", "copy",
            temp_out,
        ]
        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 15. Watermark Text or Image
    # ---------------------------------------------------------
    def add_watermark(
        self,
        input_path: str,
        output_path: str,
        text: Optional[str] = None,
        logo_path: Optional[str] = None,
        position: str = "bottom_right",
        opacity: float = 0.8,
        font_size: int = 24,
        logo_scale_pct: int = 15,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Overlays text or a logo watermark with position and opacity."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"
        encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)

        pos_coords = {
            "top_left": "x=20:y=20",
            "top_right": "x=W-w-20:y=20",
            "bottom_left": "x=20:y=H-h-20",
            "bottom_right": "x=W-w-20:y=H-h-20",
            "center": "x=(W-w)/2:y=(H-h)/2",
        }
        pos_expr = pos_coords.get(position, pos_coords["bottom_right"])

        if logo_path and Path(logo_path).exists():
            scale_factor = max(0.05, min(1.0, logo_scale_pct / 100.0))
            filter_str = (
                f"[1:v]format=rgba,colorchannelmixer=aa={opacity},"
                f"scale=iw*{scale_factor}:-1[wm];"
                f"[0:v][wm]overlay={pos_expr.replace(':', ':')}[v]"
            )
            args = [
                "-i", input_path,
                "-i", logo_path,
                "-filter_complex", filter_str,
                "-map", "[v]",
                "-map", "0:a?",
                "-c:v", encoder,
                "-c:a", "copy",
                temp_out,
            ]
        else:
            txt = (text or "SINAX").replace(":", "\\:").replace("'", "")
            vf = f"drawtext=text='{txt}':fontsize={font_size}:fontcolor=white@{opacity}:{pos_expr}:shadowcolor=black@0.5:shadowx=2:shadowy=2"
            args = [
                "-i", input_path,
                "-vf", vf,
                "-c:v", encoder,
                "-c:a", "copy",
                temp_out,
            ]

        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 16. Extract Frames & Thumbnails
    # ---------------------------------------------------------
    def extract_thumbnail(
        self,
        input_path: str,
        output_path: str,
        timestamp: str = "00:00:02",
        width: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Grabs a single high-quality frame thumbnail."""
        sec = parse_timestamp(timestamp)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        vf_args = ["-vf", f"scale={width}:-1"] if width else []
        args = ["-ss", str(sec), "-i", input_path, "-vframes", "1"] + vf_args + ["-y", output_path]

        success, msg = ffmpeg_service.run_ffmpeg(args)
        return {"success": success and Path(output_path).exists(), "message": msg, "output_path": output_path}

    def extract_frames_sequence(
        self,
        input_path: str,
        output_dir: str,
        mode: str = "fps",
        fps: float = 1.0,
        interval_sec: float = 5.0,
        img_format: str = "jpg",
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Extracts frame sequence into destination folder."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        out_folder = Path(output_dir)
        out_folder.mkdir(parents=True, exist_ok=True)

        if mode == "interval":
            rate = 1.0 / max(0.1, interval_sec)
        else:
            rate = max(0.01, fps)

        pattern = str(out_folder / f"frame_%05d.{img_format}")
        args = ["-i", input_path, "-vf", f"fps={rate}", "-qscale:v", "2", pattern]

        success, msg = ffmpeg_service.run_ffmpeg(
            args, duration_sec=duration, progress_callback=callback, cancel_token=cancel_token
        )
        return {"success": success, "message": msg, "output_dir": output_dir}

    # ---------------------------------------------------------
    # 17. High Quality Animated GIF Maker (2-Pass Palette)
    # ---------------------------------------------------------
    def create_gif(
        self,
        input_path: str,
        output_path: str,
        start_time: str = "00:00:00",
        duration: float = 5.0,
        fps: int = 15,
        width: int = 480,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Generates crisp animated GIF using 2-pass palettegen and paletteuse."""
        sec = parse_timestamp(start_time)
        temp_out = f"{output_path}.tmp.gif"

        filter_str = f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=256[p];[s1][p]paletteuse=dither=bayer"

        args = [
            "-ss", str(sec),
            "-t", str(duration),
            "-i", input_path,
            "-filter_complex", filter_str,
            temp_out,
        ]

        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 18. Contact Sheet / Storyboard Grid
    # ---------------------------------------------------------
    def create_contact_sheet(
        self,
        input_path: str,
        output_path: str,
        rows: int = 3,
        cols: int = 4,
        tile_width: int = 320,
    ) -> Dict[str, Any]:
        """Generates a storyboard contact sheet of video frames."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        total_tiles = rows * cols
        if duration <= 0 or total_tiles <= 0:
            return {"success": False, "message": "تعذر حساب أبعاد لوحة المعاينة."}

        fps_val = total_tiles / duration
        filter_str = f"fps={fps_val},scale={tile_width}:-1,tile={cols}x{rows}"

        args = [
            "-i", input_path,
            "-vf", filter_str,
            "-frames:v", "1",
            "-qscale:v", "2",
            "-y", output_path,
        ]

        success, msg = ffmpeg_service.run_ffmpeg(args)
        return {"success": success and Path(output_path).exists(), "message": msg, "output_path": output_path}

    # ---------------------------------------------------------
    # 19. Color Filters & Enhancement
    # ---------------------------------------------------------
    def enhance_video(
        self,
        input_path: str,
        output_path: str,
        brightness: float = 0.0,
        contrast: float = 1.0,
        saturation: float = 1.0,
        denoise: bool = False,
        sharpen: bool = False,
        use_gpu: bool = True,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Adjusts brightness, contrast, saturation, and applies denoise / unsharp filters."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"
        encoder = hardware_detector.get_best_encoder("h264", use_gpu=use_gpu)

        filters = [f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"]
        if denoise:
            filters.append("hqdn3d=2:1.5:3:2.5")
        if sharpen:
            filters.append("unsharp=5:5:1.0:5:5:0.0")

        args = [
            "-i", input_path,
            "-vf", ",".join(filters),
            "-c:v", encoder,
            "-c:a", "copy",
            temp_out,
        ]
        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)

    # ---------------------------------------------------------
    # 20. Strip Metadata (Privacy & Clean Sharing)
    # ---------------------------------------------------------
    def strip_metadata(
        self,
        input_path: str,
        output_path: str,
        callback: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        cancel_token: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Cleans all container metadata and tags losslessly."""
        meta = ffmpeg_service.probe_media(input_path)
        duration = meta.get("duration", 0.0)
        temp_out = f"{output_path}.tmp{Path(output_path).suffix}"

        args = [
            "-i", input_path,
            "-map_metadata", "-1",
            "-c", "copy",
            temp_out,
        ]
        return self._execute_ffmpeg(args, temp_out, output_path, duration, callback, cancel_token)


video_service = VideoService()
