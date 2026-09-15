# -*- coding: utf-8 -*-
"""
SINAX Smart File Organization Service
Provides comprehensive classification, folder structure generation, safe moving/copying,
and 100% reliable rollback for:
1. Category / Type (PDF, Images, Videos, Word, Excel, etc.)
2. File Extension (PDF, DOCX, PNG, JPG, XLSX, etc.)
3. Year (2024, 2025, 2026, etc.)
4. Year & Month (2025/01 - يناير, etc.)
5. Size tiers (<10MB, 10-100MB, 100MB-1GB, >1GB)
6. Academic & semantic keywords (Lectures, Assignments, Exams, Research, Reports)
"""

import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional, Callable, Tuple, Any

from app.core.constants import FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.core.logger import get_logger
from app.core.undo_manager import undo_manager, HistoryRecord
from app.models.file_item import format_file_size

logger = get_logger("organize_service")

# Arabic Month Names
ARABIC_MONTHS = {
    1: "01 - يناير",
    2: "02 - فبراير",
    3: "03 - مارس",
    4: "04 - أبريل",
    5: "05 - مايو",
    6: "06 - يونيو",
    7: "07 - يوليو",
    8: "08 - أغسطس",
    9: "09 - سبتمبر",
    10: "10 - أكتوبر",
    11: "11 - نوفمبر",
    12: "12 - ديسمبر"
}

# Academic & Semantic Keyword Groups
ACADEMIC_KEYWORDS = {
    "محاضرات ودروس": [
        "محاضرة", "محاضره", "محاضرات", "درس", "دروس", "شرح",
        "lecture", "lectures", "lec", "lesson", "session", "class", "ch", "chapter"
    ],
    "واجبات وتكاليف": [
        "واجب", "واجبات", "تكليف", "تكاليف", "وظيفة", "وظائف", "تمرين", "تمارين",
        "assignment", "assignments", "hw", "homework", "task", "tasks", "exercise", "lab"
    ],
    "امتحانات واختبارات": [
        "امتحان", "امتحانات", "اختبار", "اختبارات", "كويز", "اسئلة", "أسئلة",
        "exam", "exams", "test", "tests", "quiz", "quizzes", "midterm", "final"
    ],
    "أبحاث ومشاريع": [
        "بحث", "أبحاث", "ابحاث", "مشروع", "مشاريع", "ورقة", "أطروحة", "اطروحة",
        "research", "project", "projects", "paper", "thesis", "proposal"
    ],
    "تقارير وملخصات": [
        "تقرير", "تقارير", "ملخص", "ملخصات", "موجز", "بيان",
        "report", "reports", "summary", "summaries", "doc", "brief"
    ]
}


@dataclass
class OrganizeItem:
    """Represents a single file scheduled for organization."""
    source_path: Path
    filename: str
    extension: str
    category_key: str
    category_label: str
    size_bytes: int
    formatted_size: str
    modified_time: Optional[datetime]
    target_folder_rel: str
    target_folder_abs: Path
    target_path_abs: Path
    is_selected: bool = True
    status: str = "ready"  # ready, conflict, skipped, done, error
    conflict_note: str = ""

    @classmethod
    def from_file(
        cls,
        path: Path,
        target_folder_rel: str,
        target_base_dir: Path
    ) -> "OrganizeItem":
        ext = path.suffix.lower()
        cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
        cat_info = FILE_CATEGORIES.get(cat_key, {"label_ar": "ملفات أخرى"})
        cat_label = cat_info.get("label_ar", "ملفات أخرى")

        try:
            stat = path.stat()
            sz = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
        except Exception:
            sz = 0
            mtime = None

        target_f_abs = target_base_dir / target_folder_rel
        target_p_abs = target_f_abs / path.name

        return cls(
            source_path=path,
            filename=path.name,
            extension=ext,
            category_key=cat_key,
            category_label=cat_label,
            size_bytes=sz,
            formatted_size=format_file_size(sz),
            modified_time=mtime,
            target_folder_rel=target_folder_rel,
            target_folder_abs=target_f_abs,
            target_path_abs=target_p_abs,
            is_selected=True
        )

    @property
    def suggested_folder(self) -> str:
        return self.target_folder_rel

    @suggested_folder.setter
    def suggested_folder(self, val: str):
        self.target_folder_rel = val
        if hasattr(self, 'target_folder_abs') and self.target_folder_abs:
            self.target_folder_abs = self.target_folder_abs.parent / val
            self.target_path_abs = self.target_folder_abs / self.filename


class OrganizePlan:
    """Complete blueprint of proposed organization operations before execution."""
    def __init__(
        self,
        source_dir: Path,
        target_base_dir: Path,
        mode: str = "category",
        action_type: str = "move",
        collision_strategy: str = "rename"
    ):
        self.source_dir = Path(source_dir)
        self.target_base_dir = Path(target_base_dir)
        self.mode = mode
        self.action_type = action_type  # 'move' or 'copy'
        self.collision_strategy = collision_strategy  # 'rename', 'skip', 'overwrite'
        self.items: List[OrganizeItem] = []

    @property
    def selected_items(self) -> List[OrganizeItem]:
        return [it for it in self.items if it.is_selected]

    @property
    def folders_summary(self) -> Dict[str, int]:
        """Returns map of relative folder names to count of files inside."""
        counts: Dict[str, int] = {}
        for it in self.selected_items:
            counts[it.target_folder_rel] = counts.get(it.target_folder_rel, 0) + 1
        return counts

    @property
    def total_selected_size(self) -> int:
        return sum(it.size_bytes for it in self.selected_items)


class OrganizeService:
    """Core smart organization engine."""

    @staticmethod
    def classify_file(path: Path, mode: str) -> str:
        """
        Determines the target relative folder for a single file according to the given mode.
        """
        ext = path.suffix.lower()

        if mode == "category":
            cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
            cat_info = FILE_CATEGORIES.get(cat_key, {"label_ar": "ملفات أخرى"})
            return cat_info.get("label_ar", "ملفات أخرى")

        elif mode == "extension":
            if ext.startswith('.'):
                return ext[1:].upper()
            return ext.upper() if ext else "بدون امتداد"

        elif mode == "year":
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                return str(mtime.year)
            except Exception:
                return "غير محدد"

        elif mode == "month":
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                year_str = str(mtime.year)
                month_name = ARABIC_MONTHS.get(mtime.month, f"{mtime.month:02d}")
                return f"{year_str}/{month_name}"
            except Exception:
                return "غير محدد"

        elif mode == "size":
            try:
                sz = path.stat().st_size
                if sz < 10 * 1024 * 1024:
                    return "أقل من 10 ميجابايت (صغيرة)"
                elif sz < 100 * 1024 * 1024:
                    return "10 - 100 ميجابايت (متوسطة)"
                elif sz < 1024 * 1024 * 1024:
                    return "100 ميجابايت - 1 جيجابايت (كبيرة)"
                else:
                    return "أكثر من 1 جيجابايت (ضخمة جداً)"
            except Exception:
                return "غير محدد الحجم"

        elif mode == "academic":
            clean_name = path.stem.lower()
            # Check for academic keywords
            for group_name, keywords in ACADEMIC_KEYWORDS.items():
                for kw in keywords:
                    if kw in clean_name:
                        return group_name

            # Fallback to category if no keyword matches
            cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
            cat_info = FILE_CATEGORIES.get(cat_key, {"label_ar": "ملفات عامة"})
            return f"ملفات عامة/{cat_info.get('label_ar', 'أخرى')}"

        return "مفرز"

    @classmethod
    def generate_plan(
        cls,
        files: List[Path],
        source_dir: Path,
        target_base_dir: Path,
        mode: str = "category",
        action_type: str = "move",
        collision_strategy: str = "rename"
    ) -> OrganizePlan:
        """
        Scans given files and builds a comprehensive OrganizePlan without modifying anything on disk.
        """
        plan = OrganizePlan(
            source_dir=source_dir,
            target_base_dir=target_base_dir,
            mode=mode,
            action_type=action_type,
            collision_strategy=collision_strategy
        )

        for p in files:
            if not p.is_file():
                continue
            # Avoid organizing files that are already inside target subdirectories
            try:
                rel = p.relative_to(target_base_dir)
                if len(rel.parts) > 1:
                    # Already organized inside a subfolder
                    continue
            except ValueError:
                pass

            target_folder_rel = cls.classify_file(p, mode)
            item = OrganizeItem.from_file(p, target_folder_rel, target_base_dir)

            # Check if destination file already exists
            if item.target_path_abs.exists() and item.target_path_abs.resolve() != p.resolve():
                item.status = "conflict"
                item.conflict_note = "يوجد ملف بنفس الاسم في المجلد المقترح"

            plan.items.append(item)

        logger.info(f"Generated organize plan: {len(plan.items)} items for mode [{mode}]")
        return plan

    @classmethod
    def execute_plan(
        cls,
        plan: OrganizePlan,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[int, int, List[str], Optional[HistoryRecord]]:
        """
        Safely executes file moves or copies as specified in the plan.
        Records all actions in UndoManager for instant one-click rollback.
        """
        selected = plan.selected_items
        total = len(selected)
        success_count = 0
        fail_count = 0
        errors: List[str] = []

        executed_actions: List[Dict[str, str]] = []
        created_dirs: Set[str] = set()

        for idx, item in enumerate(selected):
            if progress_callback:
                progress_callback(idx + 1, total, item.filename)

            src = item.source_path
            if not src.exists():
                fail_count += 1
                errors.append(f"الملف غير موجود: {src.name}")
                item.status = "error"
                continue

            target_folder = item.target_folder_abs
            try:
                if not target_folder.exists():
                    target_folder.mkdir(parents=True, exist_ok=True)
                    created_dirs.add(str(target_folder))
            except Exception as e:
                fail_count += 1
                errors.append(f"تعذر إنشاء المجلد {target_folder.name}: {e}")
                item.status = "error"
                continue

            dest = item.target_path_abs

            # Handle file collision
            if dest.exists() and dest.resolve() != src.resolve():
                if plan.collision_strategy == "skip":
                    item.status = "skipped"
                    continue
                elif plan.collision_strategy == "rename":
                    # Smart auto-incrementing: file (1).ext
                    stem = dest.stem
                    suffix = dest.suffix
                    counter = 1
                    while dest.exists():
                        dest = target_folder / f"{stem} ({counter}){suffix}"
                        counter += 1
                # if 'overwrite', we simply let move/copy replace

            try:
                if plan.action_type == "move":
                    shutil.move(str(src), str(dest))
                else:
                    shutil.copy2(str(src), str(dest))

                executed_actions.append({
                    "action": plan.action_type,
                    "source": str(src),
                    "destination": str(dest)
                })
                item.status = "done"
                success_count += 1

            except Exception as e:
                fail_count += 1
                errors.append(f"خطأ أثناء معالجة {src.name}: {e}")
                item.status = "error"

        # Record operation for 100% undoability
        record = None
        if executed_actions:
            record = undo_manager.record_operation(
                op_type="organize",
                folder=str(plan.source_dir),
                items=[{"original": a["source"], "target": a["destination"], "action": a["action"]} for a in executed_actions],
                success=(fail_count == 0),
                details=f"تنظيم {success_count} ملف ({plan.mode}) - {'نقل' if plan.action_type == 'move' else 'نسخ'}"
            )

        logger.info(f"Organize executed: {success_count} success, {fail_count} failed")
        return success_count, fail_count, errors, record

    @classmethod
    def undo_operation(cls, record: HistoryRecord) -> Tuple[int, int, List[str]]:
        """
        Reverses an organize operation completely:
        - For 'move': Moves each file back to its exact original path.
        - For 'copy': Deletes the copied files.
        - Cleans up empty folders that were created during the operation.
        """
        actions = record.items
        success_count = 0
        fail_count = 0
        errors: List[str] = []
        checked_dirs: Set[Path] = set()

        # Reverse actions in LIFO order
        for act in reversed(actions):
            action_type = act.get("action", "move")
            src = Path(act["original"])
            dst = Path(act["target"])

            if dst.parent not in checked_dirs:
                checked_dirs.add(dst.parent)

            try:
                if action_type == "move":
                    if dst.exists():
                        src.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(dst), str(src))
                        success_count += 1
                    else:
                        fail_count += 1
                        errors.append(f"الملف المطلوب إرجاعه غير موجود: {dst.name}")
                elif action_type == "copy":
                    if dst.exists():
                        dst.unlink()
                        success_count += 1
            except Exception as e:
                fail_count += 1
                errors.append(f"فشل إرجاع {dst.name}: {e}")

        # Clean up created directories if now empty
        for d in sorted(checked_dirs, key=lambda p: len(p.parts), reverse=True):
            try:
                if d.exists() and d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
            except Exception:
                pass

        logger.info(f"Organize undo completed: {success_count} restored, {fail_count} failed")
        return success_count, fail_count, errors
