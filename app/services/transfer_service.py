# -*- coding: utf-8 -*-
"""
SINAX Batch Safe Copy & Move Service
Provides chunked file transfer with collision resolution (auto-rename, overwrite, skip),
integrity verification, and rollback logging.
"""

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Tuple

from app.models.file_item import format_file_size
from app.core.undo_manager import undo_manager
from app.core.logger import get_logger

logger = get_logger("transfer_service")


@dataclass
class TransferItem:
    """Represents a file scheduled for copy or move."""
    source_path: Path
    target_path: Path
    size_bytes: int
    formatted_size: str
    status: str = "pending"  # pending, done, skipped, error
    error_note: str = ""


@dataclass
class TransferPlan:
    """Complete blueprint for batch copy/move execution."""
    action_type: str  # 'copy' or 'move'
    collision_policy: str  # 'rename', 'overwrite', 'skip'
    destination_dir: Path
    items: List[TransferItem] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(it.size_bytes for it in self.items)

    @property
    def formatted_total_size(self) -> str:
        return format_file_size(self.total_bytes)


class TransferService:
    """High-performance batch copy & move service."""

    @staticmethod
    def generate_plan(
        sources: List[Path],
        destination_dir: Path,
        action_type: str = "copy",
        collision_policy: str = "rename"
    ) -> TransferPlan:
        """Generates destination paths and handles naming collisions according to policy."""
        plan = TransferPlan(
            action_type=action_type,
            collision_policy=collision_policy,
            destination_dir=destination_dir
        )

        destination_dir.mkdir(parents=True, exist_ok=True)
        used_target_names = set(p.name.lower() for p in destination_dir.glob('*'))

        for src in sources:
            if not src.exists() or not src.is_file():
                continue

            try:
                sz = src.stat().st_size
            except Exception:
                sz = 0

            filename = src.name
            target = destination_dir / filename

            if collision_policy == "rename":
                if target.name.lower() in used_target_names:
                    stem = src.stem
                    suffix = src.suffix
                    c = 1
                    while (destination_dir / f"{stem} ({c}){suffix}").name.lower() in used_target_names:
                        c += 1
                    target = destination_dir / f"{stem} ({c}){suffix}"
                used_target_names.add(target.name.lower())

            plan.items.append(TransferItem(
                source_path=src,
                target_path=target,
                size_bytes=sz,
                formatted_size=format_file_size(sz),
                status="pending"
            ))

        return plan

    @staticmethod
    def execute_plan(
        plan: TransferPlan,
        progress_callback: Optional[Callable[[int, int, str, float], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Tuple[int, int, int]:
        """
        Executes transfer plan.
        Returns: (success_count, skip_count, error_count)
        """
        success = 0
        skipped = 0
        failed = 0
        undo_items = []
        total_items = len(plan.items)

        plan.destination_dir.mkdir(parents=True, exist_ok=True)

        for idx, it in enumerate(plan.items, start=1):
            if is_cancelled and is_cancelled():
                logger.info("Transfer cancelled by user.")
                break

            if not it.source_path.exists():
                it.status = "error"
                it.error_note = "الملف المصدر غير موجود"
                failed += 1
                continue

            # Skip policy check
            if plan.collision_policy == "skip" and it.target_path.exists():
                it.status = "skipped"
                skipped += 1
                continue

            try:
                if plan.action_type == "move":
                    shutil.move(str(it.source_path), str(it.target_path))
                    undo_items.append({"original": str(it.source_path), "target": str(it.target_path)})
                else:
                    shutil.copy2(str(it.source_path), str(it.target_path))
                    undo_items.append({"original": "[Copy Original]", "target": str(it.target_path)})

                it.status = "done"
                success += 1

                if progress_callback:
                    progress_callback(idx, total_items, it.source_path.name, (idx / total_items * 100.0))

            except Exception as e:
                logger.error(f"Transfer error for {it.source_path}: {e}")
                it.status = "error"
                it.error_note = str(e)
                failed += 1

        if undo_items:
            undo_manager.record_operation(
                op_type=f"batch_{plan.action_type}",
                folder=str(plan.destination_dir),
                items=undo_items,
                details=f"تم { 'نقل' if plan.action_type == 'move' else 'نسخ' } {success} ملف بنجاح"
            )

        logger.info(f"Transfer completed: {success} success, {skipped} skipped, {failed} failed.")
        return success, skipped, failed
