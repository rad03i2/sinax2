# -*- coding: utf-8 -*-
"""
SINAX Backup Verification Service.
Provides multi-tiered integrity verification (Basic, Balanced, Full Integrity)
and generates cryptographic backup manifests (.sinax_manifest.json).
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import random
import time
from typing import Callable, Dict, List, Optional, Tuple

from app.core.logger import get_logger
from app.services.backup_sync.models import VerificationLevel
from app.services.quick_tools.tools.hash_tools import HashTools

logger = get_logger("verification_service")


@dataclass
class ManifestFileEntry:
    relative_path: str
    size_bytes: int
    mtime: float
    sha256: Optional[str] = None


@dataclass
class VerificationReport:
    is_valid: bool = True
    level: VerificationLevel = VerificationLevel.BALANCED
    total_files: int = 0
    verified_files: int = 0
    mismatched_files: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    error_summary: str = ""
    duration_seconds: float = 0.0


class VerificationService:
    """Computes hashes, generates manifests, and verifies destination integrity."""

    @classmethod
    def generate_manifest(
        cls,
        dest_root: str,
        files_map: Dict[str, Tuple[int, float]],  # rel_path -> (size, mtime)
        compute_hashes: bool = False,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> Tuple[str, List[ManifestFileEntry]]:
        """
        Creates and writes .sinax_manifest.json in dest_root.
        Returns (manifest_file_path, entries_list).
        """
        dest = Path(dest_root)
        dest.mkdir(parents=True, exist_ok=True)
        manifest_file = dest / ".sinax_manifest.json"

        entries: List[ManifestFileEntry] = []
        total = len(files_map)
        idx = 0

        for rel_path, (size, mtime) in files_map.items():
            if cancel_check and cancel_check():
                break

            idx += 1
            file_hash = None
            if compute_hashes:
                full_p = dest / rel_path
                if full_p.exists() and full_p.is_file():
                    try:
                        file_hash = HashTools.compute_file_hash(str(full_p), algorithm="SHA-256")
                    except Exception:
                        pass

            entries.append(ManifestFileEntry(
                relative_path=rel_path,
                size_bytes=size,
                mtime=mtime,
                sha256=file_hash
            ))

            if progress_cb and (idx % 10 == 0 or idx == total):
                progress_cb(idx, total)

        manifest_data = {
            "sinax_backup_manifest_version": "1.0",
            "created_at": time.time(),
            "total_files": len(entries),
            "files": [e.__dict__ for e in entries]
        }

        try:
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to write manifest file: {e}")

        return str(manifest_file), entries

    @classmethod
    def verify_manifest(
        cls,
        dest_root: str,
        manifest_path: str,
        level: VerificationLevel = VerificationLevel.BALANCED,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> VerificationReport:
        """Verifies destination directory contents against an existing manifest."""
        report = VerificationReport(level=level)
        start_t = time.time()

        if not os.path.isfile(manifest_path):
            report.is_valid = False
            report.error_summary = "ملف البيان (Manifest) غير موجود بالوجهة."
            return report

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_entries = data.get("files", [])
        except Exception as e:
            report.is_valid = False
            report.error_summary = f"ملف البيان تالف أو غير قابل للقراءة: {e}"
            return report

        entries = [ManifestFileEntry(**e) for e in raw_entries]
        report.total_files = len(entries)
        dest = Path(dest_root)

        # Decide which files to hash based on level
        to_hash_indices = set()
        if level == VerificationLevel.FULL_INTEGRITY:
            to_hash_indices = set(range(len(entries)))
        elif level == VerificationLevel.BALANCED and entries:
            # Sample up to 25 random files or 10%
            sample_size = min(len(entries), max(5, int(len(entries) * 0.10)))
            to_hash_indices = set(random.sample(range(len(entries)), sample_size))

        for idx, entry in enumerate(entries):
            if cancel_check and cancel_check():
                break

            target_p = dest / entry.relative_path

            # 1. Existence check
            if not target_p.exists() or not target_p.is_file():
                report.missing_files.append(entry.relative_path)
                continue

            # 2. Size check
            stat = target_p.stat()
            if stat.st_size != entry.size_bytes:
                report.mismatched_files.append(f"{entry.relative_path} (حجم مختلف)")
                continue

            # 3. Hash check if applicable
            if idx in to_hash_indices and entry.sha256:
                try:
                    h = HashTools.compute_file_hash(str(target_p), algorithm="SHA-256")
                    if h.lower() != entry.sha256.lower():
                        report.mismatched_files.append(f"{entry.relative_path} (تطابق Hash فشل)")
                        continue
                except Exception:
                    report.mismatched_files.append(f"{entry.relative_path} (خطأ قراءة Hash)")
                    continue

            report.verified_files += 1
            if progress_cb and (idx % 10 == 0 or idx == len(entries) - 1):
                progress_cb(idx + 1, len(entries))

        report.duration_seconds = time.time() - start_t
        if report.missing_files or report.mismatched_files:
            report.is_valid = False
            report.error_summary = (
                f"فشل التحقق: تم فقد {len(report.missing_files)} ملفات، وتطابق غير سليم لـ {len(report.mismatched_files)} ملفات."
            )
        else:
            report.is_valid = True

        return report
