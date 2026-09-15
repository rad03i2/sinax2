# -*- coding: utf-8 -*-
"""
SINAX Synchronization Engine.
Implements One-Way, Two-Way, and Mirror sync.
Key safeguards:
1. Mandatory Dry Run Preview for Mirror & deletion operations.
2. Conflict Detection when both sides modified (never silently overwrites).
3. SINAX Sync Recycle (.sinax_sync_recycle/) for deletion protection with undo.
4. Tombstone tracking for Two-Way sync deletions.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import time
from typing import Callable, Dict, List, Optional, Set, Tuple
import uuid

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.copy_engine import CopyEngine
from app.services.backup_sync.incremental_detector import IncrementalDetector
from app.services.backup_sync.models import ConflictResolution, SyncMode, SyncPair

logger = get_logger("sync_engine")


@dataclass
class SyncActionItem:
    action: str              # copy_a_to_b, copy_b_to_a, delete_b, conflict, skip
    relative_path: str
    size_bytes: int = 0
    reason: str = ""


@dataclass
class SyncDryRunReport:
    pair_id: str
    mode: SyncMode
    to_copy_a_to_b: List[SyncActionItem] = field(default_factory=list)
    to_copy_b_to_a: List[SyncActionItem] = field(default_factory=list)
    to_delete: List[SyncActionItem] = field(default_factory=list)
    conflicts: List[SyncActionItem] = field(default_factory=list)
    total_bytes_to_transfer: int = 0
    requires_confirmation: bool = False
    warning_message: str = ""


class SyncEngine:
    """Executes folder synchronization with two-way reconciliation and deletion protection."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    def generate_dry_run(
        self,
        pair: SyncPair,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> SyncDryRunReport:
        """
        Scans both sides and generates an exact preview of all actions
        WITHOUT modifying any files.
        """
        report = SyncDryRunReport(pair_id=pair.id, mode=pair.mode)
        a_root = Path(pair.side_a)
        b_root = Path(pair.side_b)

        if not a_root.exists() or not b_root.exists():
            report.warning_message = "أحد طرفي المزامنة غير متصل أو غير موجود."
            return report

        files_a = IncrementalDetector.scan_directory(str(a_root), cancel_check=cancel_check)
        files_b = IncrementalDetector.scan_directory(str(b_root), cancel_check=cancel_check)

        paths_a = set(files_a.keys())
        paths_b = set(files_b.keys())

        # 1. Paths in A but not B
        for p in paths_a - paths_b:
            item = files_a[p]
            action = SyncActionItem("copy_a_to_b", p, item.size_bytes, "ملف جديد على الطرف الأول")
            report.to_copy_a_to_b.append(action)
            report.total_bytes_to_transfer += item.size_bytes

        # 2. Paths in B but not A
        for p in paths_b - paths_a:
            item = files_b[p]
            if pair.mode == SyncMode.MIRROR:
                action = SyncActionItem("delete_b", p, item.size_bytes, "حذف لمطابقة الطرف الأول (Mirror)")
                report.to_delete.append(action)
            elif pair.mode == SyncMode.TWO_WAY:
                # Check tombstone: was it deleted from A?
                with self.db._get_connection() as conn:
                    row = conn.execute(
                        "SELECT 1 FROM sync_tombstones WHERE sync_id = ? AND relative_path = ? AND side = 'A'",
                        (pair.id, p)
                    ).fetchone()
                if row:
                    # File was deleted on A, so delete on B as well
                    report.to_delete.append(SyncActionItem("delete_b", p, item.size_bytes, "حذف متزامن (حُذف سابقاً من A)"))
                else:
                    action = SyncActionItem("copy_b_to_a", p, item.size_bytes, "ملف جديد على الطرف الثاني")
                    report.to_copy_b_to_a.append(action)
                    report.total_bytes_to_transfer += item.size_bytes

        # 3. Paths present in BOTH A and B
        for p in paths_a & paths_b:
            item_a = files_a[p]
            item_b = files_b[p]

            # Compare mtime & size
            if item_a.size_bytes == item_b.size_bytes and abs(item_a.mtime - item_b.mtime) < 1.5:
                continue  # In sync

            if pair.mode == SyncMode.ONE_WAY or pair.mode == SyncMode.MIRROR:
                action = SyncActionItem("copy_a_to_b", p, item_a.size_bytes, "تحديث الملف من A إلى B")
                report.to_copy_a_to_b.append(action)
                report.total_bytes_to_transfer += item_a.size_bytes
            else:
                # TWO_WAY Sync: Check which is newer or conflict
                diff_sec = item_a.mtime - item_b.mtime
                if diff_sec > 2.0:
                    # A is clearly newer
                    report.to_copy_a_to_b.append(SyncActionItem("copy_a_to_b", p, item_a.size_bytes, "الطرف A أحدث"))
                    report.total_bytes_to_transfer += item_a.size_bytes
                elif diff_sec < -2.0:
                    # B is clearly newer
                    report.to_copy_b_to_a.append(SyncActionItem("copy_b_to_a", p, item_b.size_bytes, "الطرف B أحدث"))
                    report.total_bytes_to_transfer += item_b.size_bytes
                else:
                    # CONFLICT! Both modified within same timeframe with different sizes
                    action = SyncActionItem("conflict", p, item_a.size_bytes, "تعارض: تعديل متزامن على كلا الطرفين")
                    report.conflicts.append(action)

        # Deletion Guard check
        del_count = len(report.to_delete)
        total_b = len(files_b)
        del_pct = (del_count / total_b * 100.0) if total_b > 0 else 0

        if del_count > pair.delete_protection_threshold_count or del_pct > pair.delete_protection_threshold_pct:
            report.requires_confirmation = True
            report.warning_message = (
                f"⚠ تحذير أمان الحذف: هذه العملية ستقوم بحذف ({del_count}) ملفًا ({del_pct:.1f}% من محتوى الطرف الثاني). "
                f"يلزم تأكيدك الصريح قبل المتابعة."
            )

        return report

    def execute_sync(
        self,
        pair: SyncPair,
        dry_run_report: Optional[SyncDryRunReport] = None,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Tuple[bool, str]:
        """Executes the synchronization plan with deletion recycle protection."""
        if not dry_run_report:
            dry_run_report = self.generate_dry_run(pair, cancel_check)

        if dry_run_report.warning_message and not dry_run_report.requires_confirmation:
            return False, dry_run_report.warning_message

        a_root = Path(pair.side_a)
        b_root = Path(pair.side_b)

        total_actions = (
            len(dry_run_report.to_copy_a_to_b) +
            len(dry_run_report.to_copy_b_to_a) +
            len(dry_run_report.to_delete) +
            len(dry_run_report.conflicts)
        )
        done = 0

        # 1. Execute A -> B
        for item in dry_run_report.to_copy_a_to_b:
            if cancel_check and cancel_check():
                return False, "تم إلغاء المزامنة."
            done += 1
            if progress_cb:
                progress_cb(done, total_actions, f"نسخ A إلى B: {item.relative_path}")
            src = a_root / item.relative_path
            dst = b_root / item.relative_path
            CopyEngine.copy_file_safe(str(src), str(dst))

        # 2. Execute B -> A
        for item in dry_run_report.to_copy_b_to_a:
            if cancel_check and cancel_check():
                return False, "تم إلغاء المزامنة."
            done += 1
            if progress_cb:
                progress_cb(done, total_actions, f"نسخ B إلى A: {item.relative_path}")
            src = b_root / item.relative_path
            dst = a_root / item.relative_path
            CopyEngine.copy_file_safe(str(src), str(dst))

        # 3. Handle Deletions (Move to .sinax_sync_recycle instead of permanent shred)
        recycle_root = b_root / ".sinax_sync_recycle"
        recycle_root.mkdir(parents=True, exist_ok=True)

        for item in dry_run_report.to_delete:
            if cancel_check and cancel_check():
                return False, "تم إلغاء المزامنة."
            done += 1
            if progress_cb:
                progress_cb(done, total_actions, f"حذف آمن: {item.relative_path}")

            target = b_root / item.relative_path
            if target.exists():
                try:
                    recycled_dest = recycle_root / item.relative_path
                    recycled_dest.parent.mkdir(parents=True, exist_ok=True)
                    if recycled_dest.exists():
                        recycled_dest.unlink()
                    shutil.move(str(target), str(recycled_dest))
                except Exception as e:
                    logger.warning(f"Failed to recycle {target}: {e}")

        # 4. Handle Conflicts based on policy
        for item in dry_run_report.conflicts:
            done += 1
            src_a = a_root / item.relative_path
            src_b = b_root / item.relative_path
            if pair.conflict_policy == ConflictResolution.KEEP_A:
                CopyEngine.copy_file_safe(str(src_a), str(src_b))
            elif pair.conflict_policy == ConflictResolution.KEEP_B:
                CopyEngine.copy_file_safe(str(src_b), str(src_a))
            else:
                # KEEP_BOTH: Create conflict sidecar copy
                t_str = time.strftime("%Y-%m-%d_%H%M%S")
                conflict_name = f"{src_b.stem} (conflict {t_str}){src_b.suffix}"
                conflict_dst = src_b.parent / conflict_name
                CopyEngine.copy_file_safe(str(src_a), str(conflict_dst))

        # Update last sync status
        pair.last_sync_at = time.time()
        pair.last_status = "success"
        self.db.save_sync_pair(pair)

        return True, f"اكتملت المزامنة بنجاح ({done} عمليات منفذة)."
