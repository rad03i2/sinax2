# -*- coding: utf-8 -*-
"""
SINAX Duplicate File Finder & Perceptual Image Similarity Service
Implements a 3-pass ultra-fast exact detection pipeline (Size -> 64KB Partial Hash -> Full SHA-256)
and Perceptual Image Difference Hashing (dHash) for finding similar/duplicate photos.
Includes smart selection rules, Windows Recycle Bin safe deletion, quarantine, and full undo.
"""

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple, Set

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from app.core.constants import FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.models.file_item import format_file_size
from app.services.file_service import FileService
from app.core.undo_manager import undo_manager
from app.core.logger import get_logger

logger = get_logger("duplicate_service")

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.tif', '.gif'}


@dataclass
class DuplicateItem:
    """Represents a single file inside a duplicate cluster."""
    path: Path
    filename: str
    extension: str
    size_bytes: int
    formatted_size: str
    modified_time: Optional[datetime]
    formatted_date: str
    category_key: str
    category_label: str
    is_selected: bool = False
    group_id: int = 0
    match_detail: str = ""

    @classmethod
    def from_path(cls, p: Path, group_id: int = 0) -> "DuplicateItem":
        ext = p.suffix.lower()
        cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
        cat_info = FILE_CATEGORIES.get(cat_key, {"label_ar": "ملفات أخرى"})
        cat_label = cat_info.get("label_ar", "ملفات أخرى")

        try:
            st = p.stat()
            sz = st.st_size
            mtime = datetime.fromtimestamp(st.st_mtime)
            dt_str = mtime.strftime("%Y-%m-%d %H:%M")
        except Exception:
            sz = 0
            mtime = None
            dt_str = "-"

        return cls(
            path=p,
            filename=p.name,
            extension=ext.upper().lstrip('.'),
            size_bytes=sz,
            formatted_size=format_file_size(sz),
            modified_time=mtime,
            formatted_date=dt_str,
            category_key=cat_key,
            category_label=cat_label,
            is_selected=False,
            group_id=group_id
        )


@dataclass
class DuplicateGroup:
    """Represents a set of identical or similar files."""
    group_id: int
    match_type: str  # 'exact' or 'similar'
    size_bytes: int
    formatted_size: str
    hash_value: str
    files: List[DuplicateItem] = field(default_factory=list)

    @property
    def wasted_size_bytes(self) -> int:
        """Returns wasted disk space (total size minus one copy)."""
        if len(self.files) <= 1:
            return 0
        return self.size_bytes * (len(self.files) - 1)


class DuplicateService:
    """Service for Duplicate Detection and Safe Disposal."""

    @staticmethod
    def find_duplicates(
        directory: Path,
        recursive: bool = True,
        min_size_bytes: int = 1,  # ignore 0-byte files by default
        category_filter: str = "all",
        use_perceptual_hash: bool = False,
        similarity_threshold: int = 5,  # max hamming distance for dHash (0=exact, <=5=very similar)
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[DuplicateGroup]:
        """
        Executes multi-pass duplicate scanning.
        """
        if use_perceptual_hash and HAS_PIL:
            return DuplicateService._find_similar_images(
                directory, recursive, category_filter, similarity_threshold, progress_callback, is_cancelled
            )
        else:
            return DuplicateService._find_exact_duplicates(
                directory, recursive, min_size_bytes, category_filter, progress_callback, is_cancelled
            )

    @staticmethod
    def _find_exact_duplicates(
        directory: Path,
        recursive: bool,
        min_size_bytes: int,
        category_filter: str,
        progress_callback: Optional[Callable[[int, int, str], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> List[DuplicateGroup]:
        """
        Ultra-fast 3-pass exact duplicate detection:
        Pass 1: Size grouping
        Pass 2: 64KB partial hash
        Pass 3: Full SHA-256 chunked streaming
        """
        # --- PASS 1: SIZE CLUSTERING ---
        size_map: Dict[int, List[Path]] = {}
        file_count = 0

        iterator = directory.rglob('*') if recursive else directory.glob('*')
        for p in iterator:
            if is_cancelled and is_cancelled():
                return []
            if not p.is_file():
                continue

            # Category filter
            if category_filter and category_filter != "all":
                ext = p.suffix.lower()
                cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
                if cat_key != category_filter:
                    continue

            try:
                sz = p.stat().st_size
                if sz < min_size_bytes:
                    continue
                size_map.setdefault(sz, []).append(p)
                file_count += 1
                if progress_callback and file_count % 150 == 0:
                    progress_callback(1, file_count, f"فحص الأحجام: {p.name}")
            except (OSError, PermissionError):
                continue

        # Keep only sizes with 2 or more files
        candidate_sizes = {sz: paths for sz, paths in size_map.items() if len(paths) >= 2}
        total_candidates = sum(len(paths) for paths in candidate_sizes.values())
        logger.info(f"Pass 1 complete: {len(candidate_sizes)} size clusters, {total_candidates} candidate files.")

        if not candidate_sizes:
            return []

        # --- PASS 2: PARTIAL HASH (First 64KB) ---
        partial_map: Dict[Tuple[int, str], List[Path]] = {}
        processed = 0

        for sz, paths in candidate_sizes.items():
            for p in paths:
                if is_cancelled and is_cancelled():
                    return []
                processed += 1
                if progress_callback and processed % 50 == 0:
                    progress_callback(2, processed, f"فحص التجزئة المبدئية: {p.name}")

                try:
                    with open(p, 'rb') as f:
                        chunk = f.read(65536)
                        p_hash = hashlib.md5(chunk).hexdigest()
                    partial_map.setdefault((sz, p_hash), []).append(p)
                except Exception:
                    continue

        candidate_partials = {k: paths for k, paths in partial_map.items() if len(paths) >= 2}
        logger.info(f"Pass 2 complete: {len(candidate_partials)} partial hash clusters remaining.")

        if not candidate_partials:
            return []

        # --- PASS 3: FULL SHA-256 ---
        full_map: Dict[str, List[Path]] = {}
        processed = 0
        total_full = sum(len(paths) for paths in candidate_partials.values())

        for (sz, _), paths in candidate_partials.items():
            for p in paths:
                if is_cancelled and is_cancelled():
                    return []
                processed += 1
                if progress_callback and processed % 20 == 0:
                    progress_callback(3, processed, f"التشفير الكامل SHA-256: {p.name}")

                try:
                    h = hashlib.sha256()
                    with open(p, 'rb') as f:
                        while chunk := f.read(65536):
                            h.update(chunk)
                    full_map.setdefault(h.hexdigest(), []).append(p)
                except Exception:
                    continue

        # Build duplicate groups
        groups: List[DuplicateGroup] = []
        group_id = 1

        for full_hash, paths in full_map.items():
            if len(paths) >= 2:
                try:
                    sz = paths[0].stat().st_size
                except Exception:
                    sz = 0

                group = DuplicateGroup(
                    group_id=group_id,
                    match_type="exact",
                    size_bytes=sz,
                    formatted_size=format_file_size(sz),
                    hash_value=full_hash,
                    files=[DuplicateItem.from_path(p, group_id) for p in paths]
                )
                groups.append(group)
                group_id += 1

        # Sort groups by wasted size descending
        groups.sort(key=lambda g: g.wasted_size_bytes, reverse=True)
        logger.info(f"Found {len(groups)} exact duplicate groups.")
        return groups

    @staticmethod
    def _find_similar_images(
        directory: Path,
        recursive: bool,
        category_filter: str,
        threshold: int,
        progress_callback: Optional[Callable[[int, int, str], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> List[DuplicateGroup]:
        """Finds visually identical or similar images via difference hashing (dHash)."""
        images: List[Path] = []
        iterator = directory.rglob('*') if recursive else directory.glob('*')
        for p in iterator:
            if is_cancelled and is_cancelled():
                return []
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(p)

        if len(images) < 2:
            return []

        # Compute dHash for each image
        hashes: List[Tuple[Path, int]] = []
        for idx, img_path in enumerate(images):
            if is_cancelled and is_cancelled():
                return []
            if progress_callback and idx % 20 == 0:
                progress_callback(1, idx, f"تحليل بصمة الصورة: {img_path.name}")

            h = DuplicateService._compute_dhash(img_path)
            if h is not None:
                hashes.append((img_path, h))

        # Cluster images by Hamming distance <= threshold
        clusters: List[List[Path]] = []
        visited: Set[Path] = set()

        for i in range(len(hashes)):
            if hashes[i][0] in visited:
                continue

            current_cluster = [hashes[i][0]]
            for j in range(i + 1, len(hashes)):
                if hashes[j][0] in visited:
                    continue

                dist = bin(hashes[i][1] ^ hashes[j][1]).count('1')
                if dist <= threshold:
                    current_cluster.append(hashes[j][0])
                    visited.add(hashes[j][0])

            if len(current_cluster) >= 2:
                visited.add(hashes[i][0])
                clusters.append(current_cluster)

        groups: List[DuplicateGroup] = []
        for g_id, cluster in enumerate(clusters, 1):
            sz = cluster[0].stat().st_size if cluster[0].exists() else 0
            grp = DuplicateGroup(
                group_id=g_id,
                match_type="similar",
                size_bytes=sz,
                formatted_size=format_file_size(sz),
                hash_value=f"dhash_cluster_{g_id}",
                files=[DuplicateItem.from_path(p, g_id) for p in cluster]
            )
            groups.append(grp)

        logger.info(f"Found {len(groups)} similar image groups.")
        return groups

    @staticmethod
    def _compute_dhash(image_path: Path, hash_size: int = 8) -> Optional[int]:
        """Calculates 64-bit difference hash for image."""
        try:
            with Image.open(image_path) as img:
                # Convert to grayscale and resize to (hash_size + 1, hash_size)
                img = img.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())

            diff = 0
            for row in range(hash_size):
                row_start = row * (hash_size + 1)
                for col in range(hash_size):
                    left = pixels[row_start + col]
                    right = pixels[row_start + col + 1]
                    if left > right:
                        diff |= 1 << (row * hash_size + col)
            return diff
        except Exception:
            return None

    # ----------------------------------------------------
    # SMART AUTO-SELECTION RULES
    # ----------------------------------------------------
    @staticmethod
    def apply_auto_select(groups: List[DuplicateGroup], rule: str) -> None:
        """
        Applies a selection rule to mark duplicates while keeping 1 original unselected.
        Rules:
            'all_except_first': keep first file found in each group
            'all_except_newest': keep newest modified file, select older copies
            'all_except_oldest': keep oldest file, select newer copies
            'all_except_shortest': keep file with shortest path, select deeper ones
            'deselect_all': deselect all
        """
        for grp in groups:
            if not grp.files:
                continue

            if rule == "deselect_all":
                for it in grp.files:
                    it.is_selected = False
                continue

            if rule == "all_except_first":
                grp.files[0].is_selected = False
                for it in grp.files[1:]:
                    it.is_selected = True

            elif rule == "all_except_newest":
                # Find newest file
                newest = max(grp.files, key=lambda it: it.modified_time or datetime.min)
                for it in grp.files:
                    it.is_selected = (it is not newest)

            elif rule == "all_except_oldest":
                # Find oldest file
                oldest = min(grp.files, key=lambda it: it.modified_time or datetime.max)
                for it in grp.files:
                    it.is_selected = (it is not oldest)

            elif rule == "all_except_shortest":
                shortest = min(grp.files, key=lambda it: len(str(it.path)))
                for it in grp.files:
                    it.is_selected = (it is not shortest)

    # ----------------------------------------------------
    # SAFE DISPOSAL & QUARANTINE
    # ----------------------------------------------------
    @staticmethod
    def safe_delete_items(items: List[DuplicateItem]) -> Tuple[int, int]:
        """
        Moves selected items to Windows Recycle Bin.
        Returns: (success_count, fail_count)
        """
        success = 0
        failed = 0
        records_to_undo = []

        for it in items:
            if not it.is_selected or not it.path.exists():
                continue

            src = str(it.path)
            if FileService.send_to_recycle_bin(it.path):
                success += 1
                records_to_undo.append({"original": src, "target": "[Recycle Bin]"})
            else:
                failed += 1

        if records_to_undo:
            undo_manager.record_operation(
                op_type="duplicate_recycle",
                folder=str(Path(records_to_undo[0]["original"]).parent),
                items=records_to_undo,
                details=f"تم إرسال {success} ملف مكرر إلى سلة المحذوفات"
            )

        logger.info(f"Duplicate delete: {success} sent to recycle bin, {failed} failed.")
        return success, failed

    @staticmethod
    def quarantine_items(
        items: List[DuplicateItem],
        quarantine_parent: Path
    ) -> Tuple[int, int, Path]:
        """
        Moves selected items into an isolated timestamped quarantine folder.
        Returns: (success_count, fail_count, quarantine_dir)
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        q_dir = quarantine_parent / f"_SINAX_Quarantine_{ts}"
        q_dir.mkdir(parents=True, exist_ok=True)

        success = 0
        failed = 0
        undo_items = []

        for it in items:
            if not it.is_selected or not it.path.exists():
                continue

            target_path = q_dir / it.path.name
            # Handle collision in quarantine
            counter = 1
            while target_path.exists():
                stem = it.path.stem
                ext = it.path.suffix
                target_path = q_dir / f"{stem}_{counter}{ext}"
                counter += 1

            try:
                shutil.move(str(it.path), str(target_path))
                undo_items.append({"original": str(it.path), "target": str(target_path)})
                success += 1
            except Exception as e:
                logger.error(f"Failed to quarantine {it.path}: {e}")
                failed += 1

        if undo_items:
            undo_manager.record_operation(
                op_type="duplicate_quarantine",
                folder=str(q_dir),
                items=undo_items,
                details=f"تم عزل {success} ملف مكرر في {q_dir.name}"
            )

        return success, failed, q_dir
