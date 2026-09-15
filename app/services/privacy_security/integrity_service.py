# -*- coding: utf-8 -*-
"""
File Integrity Service for SINAX Privacy & Security.
Computes cryptographic digests, compares hashes against expectations,
generates folder integrity manifests (SINAX_integrity_manifest.json),
and verifies folder states against previous baselines.
"""

import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.services.privacy_security.models import IntegrityDiff, IntegrityEntry
from app.services.quick_tools.tools.hash_tools import HashTools

MANIFEST_FILENAME = "SINAX_integrity_manifest.json"


class IntegrityService:
    """File and directory integrity verification engine."""

    @staticmethod
    def calculate_hashes(file_path: str) -> Dict[str, str]:
        """Calculates SHA-256, SHA-512, and BLAKE2b digests."""
        return {
            "SHA-256": HashTools.compute_file_hash(file_path, algorithm="SHA-256"),
            "SHA-512": HashTools.compute_file_hash(file_path, algorithm="SHA-512"),
            "BLAKE2b": HashTools.compute_file_hash(file_path, algorithm="BLAKE2b"),
        }

    @staticmethod
    def verify_hash(file_path: str, expected_hash: str, algorithm: str = "SHA-256") -> Tuple[bool, str, str]:
        """
        Compares computed hash with expected hash.
        Returns: (match: bool, computed_hash: str, message: str)
        """
        computed = HashTools.compute_file_hash(file_path, algorithm=algorithm)
        exp_clean = expected_hash.strip().lower()
        comp_clean = computed.strip().lower()

        if exp_clean == comp_clean:
            return True, computed, "تطابق تام (MATCH): بصمة الهاش مطابقة للقيمة المتوقعة تماماً."
        else:
            return False, computed, "عدم تطابق (MISMATCH): بصمة الهاش الحالية تختلف عن المتوقعة (ربما تم تعديل الملف أو تلف أثناء النقل)."

    @staticmethod
    def create_folder_manifest(
        folder_path: str,
        output_filename: str = MANIFEST_FILENAME,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str, int]:
        """
        Walks directory recursively, hashes all files, and outputs a manifest JSON.
        Returns: (success: bool, manifest_path: str, file_count: int)
        """
        root = Path(folder_path).resolve()
        if not root.exists() or not root.is_dir():
            return False, "المجلد غير موجود.", 0

        manifest_path = root / output_filename
        files = [f for f in root.rglob("*") if f.is_file() and f.name != output_filename]
        total = len(files)

        entries = []
        for idx, f in enumerate(files):
            if cancel_check and cancel_check():
                return False, "تم إلغاء توليد المانيفست.", len(entries)

            try:
                rel = str(f.relative_to(root)).replace("\\", "/")
                stat = f.stat()
                sha = HashTools.compute_file_hash(str(f), algorithm="SHA-256")
                entries.append({
                    "relative_path": rel,
                    "size_bytes": stat.st_size,
                    "sha256": sha,
                    "modified_time": stat.st_mtime,
                })
            except Exception:
                pass

            if progress_cb and total > 0:
                progress_cb((idx + 1) / total, f"فحص الملف {idx + 1} من {total} ({f.name})")

        manifest_data = {
            "version": 1,
            "created_at": time.time(),
            "folder_name": root.name,
            "total_files": len(entries),
            "files": entries,
        }

        try:
            with open(manifest_path, "w", encoding="utf-8") as out:
                json.dump(manifest_data, out, indent=2, ensure_ascii=False)
            return True, str(manifest_path), len(entries)
        except Exception as e:
            return False, f"فشل كتابة ملف المانيفست: {str(e)}", 0

    @staticmethod
    def verify_folder_manifest(
        folder_path: str,
        manifest_file_path: Optional[str] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Tuple[bool, str, IntegrityDiff]:
        """
        Compares current directory contents against the saved manifest.
        Returns: (success: bool, summary_message: str, diff: IntegrityDiff)
        """
        root = Path(folder_path).resolve()
        mpath = Path(manifest_file_path).resolve() if manifest_file_path else root / MANIFEST_FILENAME

        diff = IntegrityDiff()
        if not mpath.exists():
            return False, f"ملف المانيفست غير موجود: {mpath}", diff

        try:
            with open(mpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return False, f"تعذر قراءة ملف المانيفست: {str(e)}", diff

        manifest_map = {item["relative_path"]: item for item in data.get("files", [])}

        current_files = {}
        for f in root.rglob("*"):
            if f.is_file() and f != mpath:
                rel = str(f.relative_to(root)).replace("\\", "/")
                current_files[rel] = f

        total = len(manifest_map) + len(current_files)
        processed = 0

        # Check existing and modified files
        for rel, item in manifest_map.items():
            if cancel_check and cancel_check():
                break

            processed += 1
            if progress_cb:
                progress_cb(processed / total, f"التحقق من {rel}")

            if rel not in current_files:
                diff.deleted_count += 1
                diff.deleted_items.append(rel)
            else:
                curr_file = current_files[rel]
                curr_sha = HashTools.compute_file_hash(str(curr_file), algorithm="SHA-256")
                if curr_sha.lower() == item["sha256"].lower():
                    diff.unchanged_count += 1
                else:
                    diff.changed_count += 1
                    diff.changed_items.append(rel)

        # Check newly created files
        for rel in current_files:
            if rel not in manifest_map:
                diff.new_count += 1
                diff.new_items.append(rel)

        msg = (
            f"الملفات غير المعدلة: {diff.unchanged_count} | "
            f"الملفات المعدلة: {diff.changed_count} | "
            f"المحذوفة: {diff.deleted_count} | "
            f"الجديدة: {diff.new_count}"
        )
        return True, msg, diff
