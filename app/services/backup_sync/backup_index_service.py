# -*- coding: utf-8 -*-
"""
SINAX Backup Index & Self-Recovery Service.
Reconstructs the backup database index directly from destination files or manifest,
enabling emergency restoration on a clean Windows machine without prior history.
"""

import json
import os
from pathlib import Path
import time
from typing import Dict, List, Optional, Tuple
import uuid

from app.core.logger import get_logger
from app.services.backup_sync.backup_db import BackupDatabase
from app.services.backup_sync.models import (
    BackupProfile,
    BackupSnapshot,
    BackupType,
    FileVersion,
    IncrementalMode,
    RetentionPolicy,
    VerificationLevel,
)

logger = get_logger("backup_index_service")


class BackupIndexService:
    """Rebuilds backup metadata indices from storage destinations."""

    def __init__(self, db: Optional[BackupDatabase] = None):
        self.db = db or BackupDatabase()

    def rebuild_index_from_destination(self, destination_dir: str) -> Tuple[bool, int, str]:
        """
        Inspects destination_dir for .sinax_manifest.json or files,
        creates a recovered BackupProfile and snapshot, and registers all FileVersions.
        Returns (is_success, cataloged_files_count, message_ar).
        """
        dest_p = Path(destination_dir).resolve()
        if not dest_p.exists() or not dest_p.is_dir():
            return False, 0, f"مجلد النسخة المحددة غير موجود: {destination_dir}"

        manifest_file = dest_p / ".sinax_manifest.json"
        profile_id = f"recovered_{str(uuid.uuid4())[:8]}"
        job_id = f"job_{str(uuid.uuid4())[:8]}"

        # 1. Create a recovered profile
        profile = BackupProfile(
            id=profile_id,
            name=f"نسخة مستعادة ({dest_p.name})",
            sources=[str(dest_p)],
            destination=str(dest_p),
            backup_type=BackupType.FULL,
            incremental_mode=IncrementalMode.FAST,
            verification_level=VerificationLevel.BASIC,
            retention=RetentionPolicy(keep_all=True),
            created_at=time.time(),
            last_run_at=time.time(),
            last_status="recovered"
        )
        self.db.save_profile(profile)

        cataloged_count = 0
        total_bytes = 0

        # Case A: Manifest exists
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                files_list = data.get("files", [])
                snapshot_id = str(uuid.uuid4())

                for entry in files_list:
                    rel = entry.get("relative_path", "")
                    sz = entry.get("size_bytes", 0)
                    mt = entry.get("mtime", time.time())
                    sh = entry.get("sha256")
                    stored_f = dest_p / rel

                    if stored_f.exists():
                        ver = FileVersion(
                            file_id=str(uuid.uuid4()),
                            snapshot_id=snapshot_id,
                            relative_path=rel,
                            size_bytes=sz,
                            mtime=mt,
                            sha256=sh,
                            version_number=1,
                            stored_path=str(stored_f)
                        )
                        self.db.save_file_version(ver, profile_id)
                        cataloged_count += 1
                        total_bytes += sz

                snap = BackupSnapshot(
                    id=snapshot_id,
                    profile_id=profile_id,
                    job_id=job_id,
                    timestamp=time.time(),
                    total_files=cataloged_count,
                    total_bytes=total_bytes,
                    manifest_path=str(manifest_file),
                    is_pinned=True,
                    note="تم إعادة بناء الفهرس من ملف البيان الأصلي (Manifest)."
                )
                self.db.save_snapshot(snap)

                return True, cataloged_count, f"تم استعادة فهرس النسخة بالكامل عبر Manifest: تم قراءة ({cataloged_count}) ملفًا ✓"

            except Exception as e:
                logger.warning(f"Error reading manifest during rebuild: {e}")

        # Case B: No manifest, scan directory files
        snapshot_id = str(uuid.uuid4())
        for root, dirs, files in os.walk(str(dest_p)):
            if ".sinax" in root:
                continue
            for f in files:
                if f.startswith(".sinax"):
                    continue
                full_f = Path(root) / f
                try:
                    stat = full_f.stat()
                    rel = str(full_f.relative_to(dest_p))
                    ver = FileVersion(
                        file_id=str(uuid.uuid4()),
                        snapshot_id=snapshot_id,
                        relative_path=rel,
                        size_bytes=stat.st_size,
                        mtime=stat.st_mtime,
                        version_number=1,
                        stored_path=str(full_f)
                    )
                    self.db.save_file_version(ver, profile_id)
                    cataloged_count += 1
                    total_bytes += stat.st_size
                except OSError:
                    pass

        snap = BackupSnapshot(
            id=snapshot_id,
            profile_id=profile_id,
            job_id=job_id,
            timestamp=time.time(),
            total_files=cataloged_count,
            total_bytes=total_bytes,
            is_pinned=True,
            note="تم إعادة فهرسة المجلد مباشرة عبر المسح السريع."
        )
        self.db.save_snapshot(snap)

        return True, cataloged_count, f"تم مسح وفهرسة مجلد النسخة بنجاح: تم اكتشاف ({cataloged_count}) ملفًا جاهزًا للاستعادة ✓"
