# -*- coding: utf-8 -*-
"""
SINAX Conversion Worker
Background QThread handling batch conversion queue, speed metrics,
cancellation tokens, file status updates, collision policies, and history recording.
"""

import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QThread, Signal

from app.services.conversion.registry import ConversionDefinition
from app.services.conversion.conversion_history import ConversionHistoryManager
from app.core.logger import get_logger

logger = get_logger("conversion_worker")


class ConversionWorker(QThread):
    # Signals
    overall_progress = Signal(int, int, float)               # (current_index, total_files, overall_pct)
    file_progress = Signal(float, str)                       # (file_pct, message)
    file_status = Signal(int, str, str, str)                 # (row_index, status_text, output_path, error_msg)
    stats_updated = Signal(float, str)                       # (speed_mb_s, eta_str)
    finished_all = Signal(int, int, int, list)               # (success_count, fail_count, skipped_count, failed_files)
    cancelled = Signal()

    def __init__(
        self,
        files: List[Path],
        direction: ConversionDefinition,
        output_dir: Path,
        options: Optional[Dict[str, Any]] = None,
        collision_policy: str = "rename",
        card_id: str = "generic",
        parent=None
    ):
        super().__init__(parent)
        self.files = files
        self.direction = direction
        self.output_dir = output_dir
        self.options = options or {}
        self.collision_policy = collision_policy
        self.card_id = card_id
        self._is_cancelled = False

    def cancel(self):
        """Requests safe and immediate cancellation."""
        self._is_cancelled = True

    def run(self):
        total = len(self.files)
        if total == 0:
            self.finished_all.emit(0, 0, 0, [])
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        converter = self.direction.get_converter_instance()

        success_count = 0
        fail_count = 0
        skipped_count = 0
        failed_files = []
        bytes_processed = 0
        start_time = time.time()

        for idx, src_path in enumerate(self.files):
            if self._is_cancelled:
                self.cancelled.emit()
                return

            self.overall_progress.emit(idx, total, (idx / total) * 100.0)
            self.file_status.emit(idx, "قيد التحويل", "", "")

            # Resolve destination path with collision policy
            target_name = f"{src_path.stem}.{self.direction.target_ext}"
            dst_path = self.output_dir / target_name

            if dst_path.exists():
                if self.collision_policy == "skip":
                    skipped_count += 1
                    self.file_status.emit(idx, "تم التخطي", str(dst_path), "الملف موجود مسبقاً")
                    continue
                elif self.collision_policy == "rename":
                    dst_path = self._resolve_unique_name(self.output_dir, src_path.stem, self.direction.target_ext)

            # Sub-progress callback for the individual file
            def _sub_cb(pct: float, msg: str):
                self.file_progress.emit(pct, msg)

            try:
                src_sz = src_path.stat().st_size if src_path.exists() else 0
                ok, message = converter.convert(
                    source=src_path,
                    destination=dst_path,
                    options=self.options,
                    progress_callback=_sub_cb,
                    cancel_token=lambda: self._is_cancelled
                )

                if self._is_cancelled:
                    if dst_path.exists():
                        try:
                            dst_path.unlink()
                        except Exception:
                            pass
                    self.file_status.emit(idx, "ملغي", "", "تم إلغاء التحويل")
                    self.cancelled.emit()
                    return

                if ok and dst_path.exists() and dst_path.stat().st_size > 0:
                    success_count += 1
                    bytes_processed += src_sz
                    self.file_status.emit(idx, "مكتمل", str(dst_path), "")
                else:
                    fail_count += 1
                    failed_files.append((src_path.name, message))
                    self.file_status.emit(idx, "فشل", "", message)

            except Exception as e:
                logger.error(f"Error converting {src_path.name}: {e}")
                fail_count += 1
                failed_files.append((src_path.name, str(e)))
                self.file_status.emit(idx, "فشل", "", str(e))

            # Calculate live speed and ETA
            elapsed = time.time() - start_time
            if elapsed > 0.5 and (idx + 1) > 0:
                speed_mb_s = (bytes_processed / (1024 * 1024)) / elapsed
                items_left = total - (idx + 1)
                time_per_item = elapsed / (idx + 1)
                eta_secs = int(items_left * time_per_item)
                if eta_secs < 60:
                    eta_str = f"{eta_secs} ثانية"
                else:
                    eta_str = f"{eta_secs // 60} دقيقة و {eta_secs % 60} ثانية"
                self.stats_updated.emit(speed_mb_s, eta_str)

        self.overall_progress.emit(total, total, 100.0)

        # Record in conversion history
        ConversionHistoryManager.record_conversion(
            card_id=self.card_id,
            source_ext=self.direction.source_ext,
            target_ext=self.direction.target_ext,
            total_files=total,
            success_count=success_count,
            fail_count=fail_count,
            output_dir=str(self.output_dir),
            options=self.options,
            error_details=[f"{fname}: {err}" for fname, err in failed_files]
        )

        self.finished_all.emit(success_count, fail_count, skipped_count, failed_files)

    def _resolve_unique_name(self, folder: Path, base_stem: str, ext: str) -> Path:
        """Generates photo (1).jpg, photo (2).jpg etc."""
        counter = 1
        while True:
            candidate = folder / f"{base_stem} ({counter}).{ext}"
            if not candidate.exists():
                return candidate
            counter += 1
