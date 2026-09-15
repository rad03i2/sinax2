# -*- coding: utf-8 -*-
"""
SINAX High-Performance Streaming Image Worker
Handles non-blocking, multi-threaded batch execution of 1 to 10,000+ images
with O(1) memory consumption, real-time speed/ETA metrics, pause/resume,
safe atomic writes, and folder tree preservation.
"""

import gc
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition

from app.services.image.image_service import image_service
from app.services.image.image_workflow import ImageWorkflow
from app.services.image.image_utils import get_relative_output_path
from app.core.undo_manager import undo_manager
from app.core.logger import get_logger

logger = get_logger(__name__)


class ImageWorker(QThread):
    """Worker thread for executing image operations on batches of any size."""

    file_started = Signal(int, str)             # index, filename
    file_finished = Signal(int, str, bool, str, int)  # index, filename, success, message, bytes_saved
    progress = Signal(int, int, float, float, int, int) # curr, total, pct, speed(img/s), eta(s), bytes_saved
    status_message = Signal(str)
    all_finished = Signal(dict)

    def __init__(
        self,
        files: List[Path],
        tool_id: str,
        options: Dict[str, Any],
        output_folder: Path,
        base_folder: Optional[Path] = None,
        preserve_folders: bool = True,
        overwrite_original: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.files = files
        self.tool_id = tool_id
        self.options = options
        self.output_folder = Path(output_folder)
        self.base_folder = Path(base_folder) if base_folder else None
        self.preserve_folders = preserve_folders
        self.overwrite_original = overwrite_original

        self._is_cancelled = False
        self._is_paused = False
        self._pause_mutex = QMutex()
        self._pause_cond = QWaitCondition()

    def cancel(self):
        """Signals worker to safely cancel remaining queue."""
        self._is_cancelled = True
        self.resume()

    def pause(self):
        """Pauses processing queue."""
        self._is_paused = True

    def resume(self):
        """Resumes processing queue."""
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

        logger.info(f"ImageWorker starting: {total_files} images with tool '{self.tool_id}'")

        # Multi-image combined tools (Contact Sheet, GIF Maker)
        if self.tool_id in ("contact_sheet", "gif_maker_extractor") and self.options.get("mode") != "extract_gif":
            self._handle_multi_image_tool(start_time)
            return

        for idx, src_file in enumerate(self.files):
            # Check cancel request
            if self._is_cancelled:
                self.status_message.emit("تم إلغاء المعالجة بأمان.")
                break

            # Check pause request
            self._pause_mutex.lock()
            while self._is_paused and not self._is_cancelled:
                self.status_message.emit("المعالجة متوقفة مؤقتاً...")
                self._pause_cond.wait(self._pause_mutex)
            self._pause_mutex.unlock()

            if self._is_cancelled:
                break

            self.file_started.emit(idx + 1, src_file.name)

            # Determine target output destination
            suffix = self.options.get("suffix", "_processed")
            new_ext = self.options.get("target_format")
            if self.tool_id == "batch_convert" and new_ext:
                pass
            elif self.tool_id == "heic_to_jpg":
                new_ext = "jpg"
            elif self.tool_id == "smart_transparency":
                new_ext = "png"
            elif self.tool_id == "favicon_ico_generator":
                new_ext = "ico"
            else:
                new_ext = None

            if self.overwrite_original:
                dest_path = src_file
            else:
                base = self.base_folder if self.preserve_folders else None
                dest_path = get_relative_output_path(
                    source_file=src_file,
                    base_folder=base,
                    output_folder=self.output_folder,
                    suffix=suffix,
                    new_ext=new_ext
                )

            # Atomic write via temporary file
            temp_dest = dest_path.parent / f".tmp_{dest_path.name}"

            try:
                # Dispatch tool
                bytes_saved = self._execute_tool(src_file, temp_dest)

                # Atomic rename
                if temp_dest.exists():
                    if dest_path.exists() and not self.overwrite_original:
                        dest_path.unlink()
                    temp_dest.replace(dest_path)

                processed_count += 1
                total_bytes_saved += max(0, bytes_saved)
                undo_items.append({"source": str(src_file), "target": str(dest_path)})
                self.file_finished.emit(idx + 1, src_file.name, True, "تم بنجاح", bytes_saved)

            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing image {src_file.name}: {e}")
                if temp_dest.exists():
                    try:
                        temp_dest.unlink()
                    except Exception:
                        pass
                self.file_finished.emit(idx + 1, src_file.name, False, str(e), 0)

            # Performance & ETA metrics
            elapsed = max(0.001, time.time() - start_time)
            speed = processed_count / elapsed
            remaining = total_files - (idx + 1)
            eta = int(remaining / speed) if speed > 0 else 0
            pct = round(((idx + 1) / total_files) * 100.0, 1)

            self.progress.emit(idx + 1, total_files, pct, round(speed, 1), eta, total_bytes_saved)

            # O(1) Memory optimization: periodic garbage collection
            if (idx + 1) % 50 == 0:
                gc.collect()

        elapsed_total = time.time() - start_time

        # Record undo
        if undo_items and not self.overwrite_original:
            try:
                undo_manager.record_operation(
                    operation_type="image_processing",
                    description=f"معالجة {len(undo_items)} صورة عبر مركز الصور",
                    items=undo_items
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
            "output_folder": str(self.output_folder)
        }
        logger.info(f"ImageWorker completed: {processed_count}/{total_files} processed in {elapsed_total:.1f}s")
        self.all_finished.emit(summary)

    def _execute_tool(self, src: Path, dest: Path) -> int:
        """Executes the specific atomic tool on a single image and returns bytes saved."""
        orig_size = src.stat().st_size
        tool = self.tool_id
        opts = self.options

        if tool == "batch_compress":
            res = image_service.compress_image(
                src, dest,
                preset=opts.get("preset", "balanced"),
                quality=opts.get("quality", 80),
                lossless=opts.get("lossless", False)
            )
            return res.get("savings", 0)

        elif tool == "target_size_compress":
            res = image_service.compress_image(
                src, dest,
                target_size_kb=opts.get("target_size_kb", 500)
            )
            return res.get("savings", 0)

        elif tool in ("batch_resize", "social_resize"):
            image_service.resize_image(
                src, dest,
                mode=opts.get("mode", "fit"),
                width=opts.get("width"),
                height=opts.get("height"),
                percent=opts.get("percent"),
                longest_edge=opts.get("longest_edge"),
                shortest_edge=opts.get("shortest_edge"),
                do_not_enlarge=opts.get("do_not_enlarge", False)
            )
            new_size = dest.stat().st_size if dest.exists() else orig_size
            return orig_size - new_size

        elif tool in ("batch_convert", "heic_to_jpg"):
            target_fmt = "jpg" if tool == "heic_to_jpg" else opts.get("target_format", "webp")
            image_service.convert_image(
                src, dest,
                target_format=target_fmt,
                quality=opts.get("quality", 85),
                bg_color=opts.get("bg_color", "#FFFFFF")
            )
            new_size = dest.stat().st_size if dest.exists() else orig_size
            return orig_size - new_size

        elif tool == "batch_crop":
            image_service.crop_image(
                src, dest,
                aspect_ratio=opts.get("aspect_ratio", "1:1"),
                align=opts.get("align", "center"),
                crop_box=opts.get("crop_box")
            )
            return 0

        elif tool == "rotate_orient":
            image_service.rotate_orient_image(
                src, dest,
                angle=opts.get("angle", 0),
                auto_orient=opts.get("auto_orient", True),
                flip_h=opts.get("flip_h", False),
                flip_v=opts.get("flip_v", False)
            )
            return 0

        elif tool == "smart_transparency":
            image_service.smart_transparency(
                src, dest,
                target_color=opts.get("target_color", "#FFFFFF"),
                tolerance=opts.get("tolerance", 30)
            )
            return 0

        elif tool == "replace_bg_color":
            image_service.convert_image(
                src, dest,
                target_format="jpg",
                bg_color=opts.get("bg_color", "#FFFFFF")
            )
            return 0

        elif tool == "watermark":
            image_service.watermark_image(
                src, dest,
                text=opts.get("text", ""),
                logo_path=opts.get("logo_path"),
                position=opts.get("position", "bottom_right"),
                opacity=opts.get("opacity", 0.8),
                font_size=opts.get("font_size", 36),
                color=opts.get("color", "#FFFFFF")
            )
            return 0

        elif tool == "borders_canvas":
            image_service.border_canvas_image(
                src, dest,
                border_width=opts.get("border_width", 0),
                border_color=opts.get("border_color", "#FFFFFF"),
                canvas_width=opts.get("canvas_width"),
                canvas_height=opts.get("canvas_height"),
                canvas_bg=opts.get("canvas_bg", "#FFFFFF")
            )
            return 0

        elif tool in ("auto_enhance", "color_adjustments"):
            image_service.enhance_filter_image(
                src, dest,
                auto_enhance=opts.get("auto_enhance", False),
                brightness=opts.get("brightness", 1.0),
                contrast=opts.get("contrast", 1.0),
                saturation=opts.get("saturation", 1.0),
                sharpness=opts.get("sharpness", 1.0),
                blur_radius=opts.get("blur_radius", 0),
                grayscale=opts.get("grayscale", False),
                sepia=opts.get("sepia", False),
                invert=opts.get("invert", False)
            )
            return 0

        elif tool in ("strip_metadata_safe", "strip_gps_only", "shift_date"):
            action = "strip_all" if tool == "strip_metadata_safe" else ("strip_gps" if tool == "strip_gps_only" else "shift_date")
            image_service.metadata_image(
                src, dest,
                action=action,
                shift_hours=opts.get("shift_hours", 0),
                shift_days=opts.get("shift_days", 0)
            )
            return 0

        elif tool == "favicon_ico_generator":
            image_service.generate_ico(src, dest, sizes=opts.get("sizes", [16, 32, 48, 64, 128, 256]))
            return 0

        elif tool == "batch_workflow_builder":
            wf: Optional[ImageWorkflow] = opts.get("workflow")
            if wf:
                wf.execute_on_image(src, dest)
            return 0

        else:
            # Fallback
            import shutil
            shutil.copy2(src, dest)
            return 0

    def _handle_multi_image_tool(self, start_time: float):
        """Handles tools that aggregate multiple images into one file (Contact Sheet, GIF)."""
        self.status_message.emit("جاري معالجة وتجميع الصور...")
        self.progress.emit(1, 1, 50.0, 1.0, 1, 0)

        out_name = self.options.get("output_name", "output")
        ext = ".gif" if self.tool_id == "gif_maker_extractor" else ".jpg"
        target_path = self.output_folder / f"{out_name}{ext}"

        success = False
        try:
            if self.tool_id == "contact_sheet":
                res = image_service.contact_sheet(
                    image_paths=self.files,
                    output_path=target_path,
                    cols=self.options.get("cols", 4),
                    spacing=self.options.get("spacing", 12),
                    bg_color=self.options.get("bg_color", "#1E1E1E"),
                    include_names=self.options.get("include_names", True)
                )
                success = res.get("success", False)
            elif self.tool_id == "gif_maker_extractor":
                res = image_service.create_gif(
                    image_paths=self.files,
                    output_path=target_path,
                    duration_ms=self.options.get("duration_ms", 200),
                    loop=self.options.get("loop", 0)
                )
                success = res.get("success", False)
        except Exception as e:
            logger.error(f"Multi-image tool failed: {e}")

        elapsed = time.time() - start_time
        self.progress.emit(1, 1, 100.0, 1.0, 0, 0)
        self.all_finished.emit({
            "success": success,
            "total": len(self.files),
            "processed": len(self.files) if success else 0,
            "failed": 0 if success else len(self.files),
            "cancelled": False,
            "bytes_saved": 0,
            "elapsed_seconds": round(elapsed, 1),
            "output_file": str(target_path)
        })
