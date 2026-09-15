# -*- coding: utf-8 -*-
"""
SINAX High-Performance Audio Worker Thread
Handles asynchronous batch audio processing, real-time progress streaming,
cancellation, pause/resume, folder tree preservation, and history tracking.
"""

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QMutex, QThread, QWaitCondition, Signal

from app.core.logger import get_logger
from app.core.undo_manager import undo_manager
from app.services.audio.audio_registry import get_audio_tool_by_id
from app.services.audio.audio_service import audio_service
from app.services.audio.audio_workflow import AudioWorkflow, AudioWorkflowRunner

logger = get_logger("audio_worker")


class AudioCancelToken:
    """Thread-safe cancellation token passed to subprocess."""
    def __init__(self):
        self._cancelled = threading.Event()

    def cancel(self):
        self._cancelled.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()


class AudioWorker(QThread):
    """Asynchronous background worker executing audio actions over batches of files."""

    file_started = Signal(int, str)                         # (index, filename)
    file_progress = Signal(int, str, float, dict)           # (index, filename, percent, live_metrics)
    file_finished = Signal(int, str, bool, str, int)         # (index, filename, success, message, bytes_saved)
    batch_progress = Signal(int, int, float, float, int)    # (curr, total, pct, speed, eta_sec)
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
        workflow: Optional[AudioWorkflow] = None,
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

        self._cancel_token = AudioCancelToken()
        self._is_paused = False
        self._pause_mutex = QMutex()
        self._pause_cond = QWaitCondition()

        self._processed_count = 0
        self._success_count = 0
        self._error_count = 0
        self._total_bytes_before = 0
        self._total_bytes_after = 0
        self._start_time = 0.0

    def cancel(self):
        self._cancel_token.cancel()
        self.resume()  # Wake thread if paused so it can exit cleanly

    def pause(self):
        self._is_paused = True

    def resume(self):
        if self._is_paused:
            self._is_paused = False
            self._pause_cond.wakeAll()

    def _check_pause(self):
        self._pause_mutex.lock()
        while self._is_paused and not self._cancel_token.is_cancelled:
            self._pause_cond.wait(self._pause_mutex)
        self._pause_mutex.unlock()

    def _determine_output_path(self, input_path: str, ext_override: Optional[str] = None) -> str:
        in_p = Path(input_path)
        stem = in_p.stem
        ext = ext_override if ext_override else in_p.suffix
        if not ext.startswith("."):
            ext = f".{ext}"

        if self.base_folder and self.preserve_folders:
            try:
                rel_parent = in_p.parent.relative_to(self.base_folder)
                target_dir = self.output_folder / rel_parent
            except Exception:
                target_dir = self.output_folder
        else:
            target_dir = self.output_folder

        target_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{stem}{ext}"
        out_path = target_dir / out_name

        # If source and destination are the same file, avoid overwrite by appending suffix
        if out_path.resolve() == in_p.resolve():
            out_path = target_dir / f"{stem}_processed{ext}"

        return str(out_path)

    def run(self):
        self._start_time = time.time()
        total_files = len(self.files)

        if total_files == 0:
            self.all_finished.emit({"total": 0, "success": 0, "errors": 0, "time": 0})
            return

        self.status_message.emit(f"بدء معالجة {total_files} ملف صوتي...")

        # Case 1: Multi-file Merge / Crossfade into a single output track
        if self.tool_id in ("merge_audio", "crossfade_audio"):
            self._run_merge_operation()
            return

        # Case 2: Standard Batch File-by-File Queue
        for idx, file_path in enumerate(self.files):
            self._check_pause()
            if self._cancel_token.is_cancelled:
                self.status_message.emit("تم إيقاف المعالجة بواسطة المستخدم.")
                break

            fname = Path(file_path).name
            self.file_started.emit(idx, fname)
            self.status_message.emit(f"معالجة ({idx + 1}/{total_files}): {fname}")

            size_before = 0
            try:
                size_before = os.path.getsize(file_path)
                self._total_bytes_before += size_before
            except Exception:
                pass

            # Target extension
            target_ext = None
            if self.tool_id == "batch_audio_convert":
                target_ext = self.options.get("format", "mp3")
            elif self.tool_id == "batch_audio_compress" and self.options.get("preset") == "lossless_flac":
                target_ext = "flac"
            elif self.workflow and self.workflow.steps:
                last_step = [s for s in self.workflow.steps if s.enabled][-1]
                if last_step.action == "batch_audio_convert":
                    target_ext = last_step.params.get("format", "mp3")

            output_path = self._determine_output_path(file_path, target_ext)

            def progress_cb(pct: float, metrics: Dict[str, Any]):
                self.file_progress.emit(idx, fname, pct, metrics)

            # Execution
            try:
                if self.workflow:
                    runner = AudioWorkflowRunner(self.workflow)
                    res = runner.execute(
                        input_path=file_path,
                        final_output_path=output_path,
                        progress_callback=lambda p, desc: self.file_progress.emit(idx, fname, p, {"desc": desc}),
                        cancel_token=self._cancel_token,
                    )
                else:
                    res = audio_service.dispatch_audio_operation(
                        tool_id=self.tool_id,
                        input_path=file_path,
                        output_path=output_path,
                        options=self.options,
                        callback=progress_cb,
                        cancel_token=self._cancel_token,
                    )

                success = res.get("success", False)
                msg = res.get("message", "")
                bytes_saved = 0

                if success:
                    self._success_count += 1
                    try:
                        size_after = os.path.getsize(output_path)
                        self._total_bytes_after += size_after
                        bytes_saved = max(0, size_before - size_after)
                    except Exception:
                        pass
                else:
                    self._error_count += 1

                self.file_finished.emit(idx, fname, success, msg, bytes_saved)

            except Exception as e:
                self._error_count += 1
                logger.error(f"Worker exception on {fname}: {e}", exc_info=True)
                self.file_finished.emit(idx, fname, False, str(e), 0)

            self._processed_count += 1

            # Update batch progress & ETA
            elapsed = time.time() - self._start_time
            avg_time = elapsed / self._processed_count if self._processed_count > 0 else 0
            remaining = total_files - self._processed_count
            eta_sec = int(remaining * avg_time)
            speed = self._processed_count / elapsed if elapsed > 0 else 0.0
            overall_pct = (self._processed_count / total_files) * 100.0
            self.batch_progress.emit(self._processed_count, total_files, overall_pct, speed, eta_sec)

        # Finished summary
        total_time = time.time() - self._start_time
        summary = {
            "total": total_files,
            "processed": self._processed_count,
            "success": self._success_count,
            "errors": self._error_count,
            "total_bytes_before": self._total_bytes_before,
            "total_bytes_after": self._total_bytes_after,
            "bytes_saved": max(0, self._total_bytes_before - self._total_bytes_after),
            "elapsed_seconds": total_time,
            "is_cancelled": self._cancel_token.is_cancelled,
        }

        self.status_message.emit(
            f"اكتملت المعالجة: {self._success_count} نجح، {self._error_count} فشل "
            f"خلال {total_time:.1f} ثانية."
        )
        self.all_finished.emit(summary)

    def _run_merge_operation(self):
        """Dedicated execution path for concat / crossfade."""
        out_name = self.options.get("output_filename", "merged_track.mp3")
        if not any(out_name.endswith(f".{fmt}") for fmt in ("mp3", "wav", "flac", "aac", "m4a", "ogg")):
            out_name = f"{out_name}.mp3"

        out_path = os.path.join(str(self.output_folder), out_name)
        self.file_started.emit(0, out_name)
        self.status_message.emit(f"جارٍ دمج {len(self.files)} مقاطع في {out_name}...")

        def cb(pct: float, metrics: Dict[str, Any]):
            self.file_progress.emit(0, out_name, pct, metrics)

        if self.tool_id == "crossfade_audio":
            dur = float(self.options.get("crossfade_dur", 3.0))
            curve = self.options.get("curve", "tri")
            res = audio_service.crossfade_audio_files(
                input_files=self.files,
                output_file=out_path,
                crossfade_dur=dur,
                curve=curve,
                callback=cb,
                cancel_token=self._cancel_token
            )
        else:
            res = audio_service.merge_audio_files(
                input_files=self.files,
                output_file=out_path,
                callback=cb,
                cancel_token=self._cancel_token
            )

        success = res.get("success", False)
        msg = res.get("message", "")
        self.file_finished.emit(0, out_name, success, msg, 0)

        elapsed = time.time() - self._start_time
        self.batch_progress.emit(1, 1, 100.0, 1.0, 0)
        summary = {
            "total": len(self.files),
            "processed": len(self.files),
            "success": 1 if success else 0,
            "errors": 0 if success else 1,
            "elapsed_seconds": elapsed,
            "is_cancelled": self._cancel_token.is_cancelled,
        }
        self.all_finished.emit(summary)
