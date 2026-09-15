# -*- coding: utf-8 -*-
"""
SINAX High-Performance Video Worker Thread
Handles asynchronous batch video processing, real-time FFmpeg progress streaming
(fps, speed, ETA), cancellation, pause/resume, and undo tracking.
"""

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QMutex, QThread, QWaitCondition, Signal

from app.core.logger import get_logger
from app.core.undo_manager import undo_manager
from app.services.video.video_registry import get_video_tool_by_id
from app.services.video.video_service import video_service
from app.services.video.video_utils import generate_output_path
from app.services.video.video_workflow import VideoWorkflow

logger = get_logger("video_worker")


class VideoWorker(QThread):
    """Asynchronous background worker executing video actions over batches of files."""

    file_started = Signal(int, str)  # (index, filename)
    file_progress = Signal(int, str, float, dict)  # (index, filename, percent, live_metrics)
    file_finished = Signal(int, str, bool, str, int)  # (index, filename, success, message, bytes_saved)
    batch_progress = Signal(int, int, float, float, int)  # (curr, total, pct, speed, eta_sec)
    status_message = Signal(str)
    all_finished = Signal(dict)

    def __init__(
        self,
        files: List[str],
        tool_id: str,
        options: Dict[str, Any],
        output_folder: str,
        base_folder: Optional[str] = None,
        preserve_folders: bool = True,
        workflow: Optional[VideoWorkflow] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.files = files
        self.tool_id = tool_id
        self.options = options
        self.output_folder = Path(output_folder)
        self.base_folder = Path(base_folder) if base_folder else None
        self.preserve_folders = preserve_folders
        self.workflow = workflow

        self._is_cancelled = False
        self._cancel_token = threading.Event()
        self._is_paused = False
        self._pause_mutex = QMutex()
        self._pause_cond = QWaitCondition()

    def cancel(self):
        """Signals worker and active FFmpeg process to cancel immediately."""
        self._is_cancelled = True
        self._cancel_token.set()
        self.resume()

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._pause_mutex.lock()
        self._is_paused = False
        self._pause_cond.wakeAll()
        self._pause_mutex.unlock()

    def run(self):
        total_files = len(self.files)
        if total_files == 0:
            self.all_finished.emit({"success": True, "total": 0, "processed": 0, "failed": 0})
            return

        start_time = time.time()
        processed_count = 0
        failed_count = 0
        total_bytes_saved = 0
        undo_items = []

        tool_def = get_video_tool_by_id(self.tool_id)
        opt_type = tool_def.options_type if tool_def else ""

        logger.info(f"VideoWorker starting: {total_files} files with tool '{self.tool_id}' (type: '{opt_type}')")

        # Special Multi-Input Operations (e.g., merge)
        if self.tool_id in ("video_merge", "merge_videos") or opt_type == "merge":
            self._handle_merge(total_files, start_time)
            return

        # Sequential processing for batch files
        for idx, file_path in enumerate(self.files):
            if self._is_cancelled:
                break

            # Pause handling
            self._pause_mutex.lock()
            while self._is_paused and not self._is_cancelled:
                self._pause_cond.wait(self._pause_mutex)
            self._pause_mutex.unlock()

            if self._is_cancelled:
                break

            src_file = Path(file_path)
            self.file_started.emit(idx + 1, src_file.name)
            self.status_message.emit(f"معالجة ({idx + 1}/{total_files}): {src_file.name}")

            orig_size = src_file.stat().st_size if src_file.exists() else 0

            # Determine output path and extension
            new_ext = self.options.get("target_format") or self.options.get("format")
            if opt_type == "extract_audio" or self.tool_id in ("extract_video_audio", "extract_audio"):
                new_ext = self.options.get("audio_format", "mp3")
            elif opt_type == "gif" or self.tool_id in ("video_to_gif", "video_gif", "create_gif"):
                new_ext = "gif"
            elif opt_type in ("thumbnail", "contact_sheet") or self.tool_id in (
                "video_thumbnail_generator", "video_thumbnail", "thumbnail",
                "contact_sheet_storyboard", "video_contact_sheet", "contact_sheet"
            ):
                new_ext = "jpg"

            dest_path = generate_output_path(
                input_path=str(src_file),
                output_dir=str(self.output_folder),
                prefix=self.options.get("filename_prefix", ""),
                suffix=self.options.get("filename_suffix", ""),
                new_ext=new_ext,
                preserve_dir_structure=self.preserve_folders,
                root_dir=str(self.base_folder) if self.base_folder else None,
            )

            # Live callback for this file
            def on_file_progress(pct: float, info: dict, f_idx=idx, f_name=src_file.name):
                self.file_progress.emit(f_idx + 1, f_name, pct, info)

            try:
                res = self._execute_tool(str(src_file), dest_path, on_file_progress)
                is_success = res.get("success", False)
                msg = res.get("message", "تم بنجاح" if is_success else "فشلت المعالجة")

                if is_success:
                    processed_count += 1
                    new_size = Path(dest_path).stat().st_size if Path(dest_path).exists() else 0
                    bytes_saved = max(0, orig_size - new_size)
                    total_bytes_saved += bytes_saved
                    undo_items.append({"source": str(src_file), "target": str(dest_path)})
                    self.file_finished.emit(idx + 1, src_file.name, True, msg, bytes_saved)
                else:
                    failed_count += 1
                    self.file_finished.emit(idx + 1, src_file.name, False, msg, 0)

            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing video {src_file.name}: {e}", exc_info=True)
                self.file_finished.emit(idx + 1, src_file.name, False, str(e), 0)

            # Progress metrics
            elapsed = max(0.001, time.time() - start_time)
            avg_speed = (idx + 1) / elapsed
            remaining = total_files - (idx + 1)
            eta = int(remaining / avg_speed) if avg_speed > 0 else 0
            overall_pct = round(((idx + 1) / total_files) * 100.0, 1)

            self.batch_progress.emit(idx + 1, total_files, overall_pct, round(avg_speed, 2), eta)

        elapsed_total = time.time() - start_time

        # Record undo
        if undo_items:
            try:
                undo_manager.record_operation(
                    operation_type="video_processing",
                    description=f"معالجة {len(undo_items)} مقطع فيديو في مركز الفيديو",
                    items=undo_items,
                )
            except Exception:
                pass

        summary = {
            "success": True,
            "total": total_files,
            "processed": processed_count,
            "failed": failed_count,
            "cancelled": self._is_cancelled,
            "bytes_saved": total_bytes_saved,
            "elapsed_seconds": round(elapsed_total, 1),
            "output_folder": str(self.output_folder),
        }
        logger.info(f"VideoWorker completed: {processed_count}/{total_files} in {elapsed_total:.1f}s")
        self.all_finished.emit(summary)

    def _handle_merge(self, total_files: int, start_time: float):
        """Special handler for merging all input videos into a single output file."""
        out_filename = self.options.get("output_filename", "merged_video.mp4")
        if not out_filename.lower().endswith((".mp4", ".mkv", ".mov", ".avi")):
            out_filename += ".mp4"
        dest_path = str(self.output_folder / out_filename)

        self.file_started.emit(1, f"دمج {total_files} مقطع فيديو")
        self.status_message.emit(f"دمج {total_files} مقاطع إلى {out_filename}...")

        def on_merge_progress(pct: float, info: dict):
            self.file_progress.emit(1, out_filename, pct, info)
            self.batch_progress.emit(1, 1, pct, 1.0, 0)

        res = video_service.merge_videos(
            self.files,
            dest_path,
            reencode=self.options.get("reencode", False),
            use_gpu=self.options.get("use_gpu", True),
            callback=on_merge_progress,
            cancel_token=self._cancel_token,
        )

        is_success = res.get("success", False)
        msg = res.get("message", "تم دمج المقاطع بنجاح" if is_success else "فشل دمج الفيديو")
        self.file_finished.emit(1, out_filename, is_success, msg, 0)

        elapsed = round(time.time() - start_time, 1)
        summary = {
            "success": is_success,
            "total": total_files,
            "processed": total_files if is_success else 0,
            "failed": 0 if is_success else total_files,
            "cancelled": self._is_cancelled,
            "bytes_saved": 0,
            "elapsed_seconds": elapsed,
            "output_folder": str(self.output_folder),
        }
        self.all_finished.emit(summary)

    def _execute_tool(self, src: str, dest: str, callback) -> Dict[str, Any]:
        """Dispatches execution to the corresponding VideoService method."""
        tool = self.tool_id
        tool_def = get_video_tool_by_id(tool)
        opt_type = tool_def.options_type if tool_def else ""
        opts = self.options
        use_gpu = opts.get("use_gpu", True)

        # 1. Chained Workflow Pipeline
        if self.workflow or opt_type == "workflow" or tool in ("batch_video_workflow_builder", "batch_workflow_builder"):
            wf = self.workflow or opts.get("workflow")
            if wf:
                return wf.execute_on_video(src, dest, callback=callback, cancel_token=self._cancel_token)

        # 2. Target Size Compression
        if opt_type == "target_size" or tool in ("target_size_video_compress", "target_size_compress"):
            return video_service.compress_video(
                src,
                dest,
                target_size_mb=float(opts.get("target_size_mb", 25.0)),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 3. Batch Compression (CRF / Presets)
        elif opt_type == "compress" or tool in ("batch_video_compress", "batch_compress"):
            return video_service.compress_video(
                src,
                dest,
                preset=opts.get("preset", "balanced"),
                crf=opts.get("crf"),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 4. Format Conversion
        elif opt_type == "convert" or tool in ("batch_video_convert", "batch_convert"):
            return video_service.convert_format(
                src,
                dest,
                video_codec=opts.get("video_codec", "auto"),
                audio_codec=opts.get("audio_codec", "auto"),
                preset_speed=opts.get("preset_speed", "medium"),
                crf=opts.get("crf", 23),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 5. Fast Remux (Stream copy without re-encoding)
        elif opt_type in ("remux", "fast_remux") or tool == "fast_remux":
            return video_service.fast_remux(
                src, dest, callback=callback, cancel_token=self._cancel_token
            )

        # 6. Resize / Resolution / Social Presets / Crop
        elif opt_type in ("resize", "social_presets", "crop", "black_bars") or tool in (
            "batch_video_resize", "resize_scale", "social_video_presets", "crop_video", "auto_crop_black_bars"
        ):
            return video_service.resize_resolution(
                src,
                dest,
                resolution=opts.get("resolution", "1080p"),
                mode=opts.get("mode", "fit"),
                custom_w=opts.get("custom_w"),
                custom_h=opts.get("custom_h"),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 7. Trim / Cut
        elif opt_type == "trim" or tool in ("video_trim", "trim_cut"):
            return video_service.trim_video(
                src,
                dest,
                start_time=opts.get("start_time", "00:00:00"),
                end_time=opts.get("end_time"),
                duration=opts.get("duration"),
                mode=opts.get("mode", "accurate"),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 8. Remove middle segment
        elif opt_type in ("remove_segment", "cut_middle") or tool in ("remove_video_segment", "cut_middle", "video_cut_middle"):
            return video_service.cut_middle_and_join(
                src,
                dest,
                cut_start=opts.get("cut_start", "00:00:10"),
                cut_end=opts.get("cut_end", "00:00:20"),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 9. Split
        elif opt_type == "split" or tool in ("video_split", "split_video"):
            return video_service.split_video(
                src,
                str(Path(dest).parent),
                mode=opts.get("mode", "duration"),
                interval_sec=float(opts.get("interval_sec", 60.0)),
                parts_count=int(opts.get("parts_count", 2)),
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 10. Mute Audio
        elif opt_type == "mute" or tool in ("mute_video", "mute_audio"):
            return video_service.mute_audio(
                src, dest, callback=callback, cancel_token=self._cancel_token
            )

        # 11. Extract Audio
        elif opt_type == "extract_audio" or tool in ("extract_video_audio", "extract_audio"):
            return video_service.extract_audio(
                src,
                dest,
                audio_format=opts.get("audio_format", "mp3"),
                bitrate=opts.get("bitrate", "192k"),
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 12. Replace or Mix Audio
        elif opt_type == "replace_audio" or tool in ("replace_add_audio", "replace_audio"):
            return video_service.replace_or_mix_audio(
                src,
                opts.get("audio_path", ""),
                dest,
                mode=opts.get("mode", "replace"),
                bg_volume=float(opts.get("bg_volume", 0.3)),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 13. Volume & Loudnorm
        elif opt_type in ("volume", "volume_normalize") or tool in ("audio_volume_loudnorm", "volume_normalize"):
            return video_service.normalize_volume(
                src,
                dest,
                mode=opts.get("mode", "ebu_r128"),
                factor=float(opts.get("factor", 1.5)),
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 14. Speed & Reverse
        elif opt_type in ("speed", "reverse") or tool in ("video_speed_control", "reverse_video", "video_speed", "speed_reverse"):
            is_rev = opts.get("reverse", False) or opt_type == "reverse" or tool == "reverse_video"
            return video_service.adjust_speed(
                src,
                dest,
                speed_factor=float(opts.get("speed_factor", 2.0)),
                reverse=is_rev,
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 15. Rotate & Flip
        elif opt_type == "rotate" or tool in ("rotate_flip_video", "rotate_flip", "video_rotate_flip"):
            return video_service.rotate_flip(
                src,
                dest,
                rotation=int(opts.get("rotation", 90)),
                flip_h=opts.get("flip_h", False),
                flip_v=opts.get("flip_v", False),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 16. Watermark
        elif opt_type == "watermark" or tool in ("video_watermark", "watermark_text", "watermark_logo", "watermark"):
            return video_service.add_watermark(
                src,
                dest,
                text=opts.get("text", "SINAX"),
                logo_path=opts.get("logo_path"),
                position=opts.get("position", "bottom_right"),
                opacity=float(opts.get("opacity", 0.8)),
                font_size=int(opts.get("font_size", 24)),
                logo_scale_pct=int(opts.get("logo_scale_pct", 15)),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 17. Thumbnail & Frames
        elif opt_type in ("thumbnail", "frames") or tool in ("video_thumbnail_generator", "video_thumbnail", "thumbnail", "extract_video_frames", "extract_frames"):
            return video_service.extract_thumbnail(
                src,
                dest,
                timestamp=opts.get("timestamp", "00:00:02"),
                width=opts.get("width"),
            )

        # 18. Animated GIF
        elif opt_type == "gif" or tool in ("video_to_gif", "video_gif", "create_gif"):
            return video_service.create_gif(
                src,
                dest,
                start_time=opts.get("start_time", "00:00:00"),
                duration=float(opts.get("duration", 5.0)),
                fps=int(opts.get("fps", 15)),
                width=int(opts.get("width", 480)),
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 19. Contact Sheet
        elif opt_type == "contact_sheet" or tool in ("contact_sheet_storyboard", "video_contact_sheet", "contact_sheet"):
            return video_service.create_contact_sheet(
                src,
                dest,
                rows=int(opts.get("rows", 3)),
                cols=int(opts.get("cols", 4)),
                tile_width=int(opts.get("tile_width", 320)),
            )

        # 20. Filters & Enhancement
        elif opt_type in ("filters", "enhance") or tool in ("video_color_filters", "video_filters", "filters_enhance"):
            return video_service.enhance_video(
                src,
                dest,
                brightness=float(opts.get("brightness", 0.0)),
                contrast=float(opts.get("contrast", 1.0)),
                saturation=float(opts.get("saturation", 1.0)),
                denoise=opts.get("denoise", False),
                sharpen=opts.get("sharpen", False),
                use_gpu=use_gpu,
                callback=callback,
                cancel_token=self._cancel_token,
            )

        # 21. Metadata Strip / Inspector
        elif opt_type in ("inspector", "privacy") or tool in ("media_inspector_metadata", "strip_metadata"):
            return video_service.strip_metadata(
                src, dest, callback=callback, cancel_token=self._cancel_token
            )

        else:
            logger.warning(f"Unrecognized tool_id '{tool}', falling back to fast_remux")
            return video_service.fast_remux(
                src, dest, callback=callback, cancel_token=self._cancel_token
            )
