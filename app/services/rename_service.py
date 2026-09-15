# -*- coding: utf-8 -*-
"""
SINAX Batch Rename Engine
Generates previews, validates Windows filenames, prevents collisions,
and executes safe two-pass renames with complete undo support.
"""

import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

from app.core.constants import (
    ARABIC_INDIC_DIGITS, ARABIC_ALPHABET, ARABIC_ORDINALS, ENGLISH_ORDINALS
)
from app.models.file_item import FileItem
from app.models.rename_rule import RenameConfig
from app.services.file_service import FileService
from app.core.undo_manager import undo_manager, HistoryRecord
from app.core.logger import get_logger

logger = get_logger("rename_service")

class RenamePlan:
    """Holds the validated execution plan for batch renaming."""
    def __init__(self):
        self.items: List[FileItem] = []
        self.valid: bool = True
        self.conflicts_count: int = 0
        self.changed_count: int = 0
        self.rename_map: List[Tuple[Path, Path]] = []  # [(old_path, new_path)]

class RenameService:
    @staticmethod
    def format_index(
        index: int,
        system: str = "western",
        padding: int = 1
    ) -> str:
        """Formats an index into the chosen numbering or alphabetical system."""
        # 0-based to 1-based index calculation
        num = max(1, index)
        
        if system == "western":
            return f"{num:0{padding}d}"
            
        elif system == "arabic_indic":
            western_str = f"{num:0{padding}d}"
            return western_str.translate(ARABIC_INDIC_DIGITS)
            
        elif system == "arabic_alpha":
            # 1 -> أ, 2 -> ب ...
            idx = num - 1
            if idx < len(ARABIC_ALPHABET):
                return ARABIC_ALPHABET[idx]
            else:
                # Wrap around with number
                return f"{ARABIC_ALPHABET[idx % len(ARABIC_ALPHABET)]}_{(idx // len(ARABIC_ALPHABET)) + 1}"
                
        elif system == "arabic_words":
            idx = num - 1
            if idx < len(ARABIC_ORDINALS):
                return ARABIC_ORDINALS[idx]
            return f"الرقم {num}"
            
        elif system == "english_upper":
            # 1 -> A, 2 -> B...
            idx = num - 1
            if idx < 26:
                return chr(ord('A') + idx)
            else:
                return f"{chr(ord('A') + (idx % 26))}_{(idx // 26) + 1}"
                
        elif system == "english_lower":
            idx = num - 1
            if idx < 26:
                return chr(ord('a') + idx)
            else:
                return f"{chr(ord('a') + (idx % 26))}_{(idx // 26) + 1}"
                
        elif system == "english_words":
            idx = num - 1
            if idx < len(ENGLISH_ORDINALS):
                return ENGLISH_ORDINALS[idx]
            return f"Number {num}"
            
        return f"{num:0{padding}d}"

    @staticmethod
    def sort_items(items: List[FileItem], sort_by: str) -> List[FileItem]:
        """Sorts file items before applying sequential numbering."""
        selected = [item for item in items if item.is_selected]
        unselected = [item for item in items if not item.is_selected]

        if sort_by == "smart_numeric":
            selected.sort(key=lambda item: FileService.natural_sort_key(item.original_name))
        elif sort_by == "name_asc":
            selected.sort(key=lambda item: item.original_name.lower())
        elif sort_by == "name_desc":
            selected.sort(key=lambda item: item.original_name.lower(), reverse=True)
        elif sort_by == "date_asc":
            selected.sort(key=lambda item: item.modified_time or datetime.min)
        elif sort_by == "date_desc":
            selected.sort(key=lambda item: item.modified_time or datetime.min, reverse=True)
        elif sort_by == "size_asc":
            selected.sort(key=lambda item: item.size_bytes)
        elif sort_by == "size_desc":
            selected.sort(key=lambda item: item.size_bytes, reverse=True)

        return selected + unselected

    @staticmethod
    def generate_preview(items: List[FileItem], config: RenameConfig) -> RenamePlan:
        """
        Generates proposed new names for all selected items and detects any conflicts.
        """
        plan = RenamePlan()
        plan.items = RenameService.sort_items(items, config.sort_by)

        selected_items = [i for i in plan.items if i.is_selected]
        
        # Determine sequence numbers for selected items
        curr_idx = config.start_number
        proposed_names_in_batch: Dict[Path, Path] = {}  # target_path -> original_path
        
        for item in selected_items:
            # 1. Base Name & Extension
            orig_stem = item.path.stem
            orig_ext = item.extension if config.keep_extension else (
                f".{config.custom_extension.lstrip('.')}" if config.custom_extension else ""
            )

            # 2. Date string if required
            date_str = ""
            if "{date}" in config.pattern or config.include_date:
                dt = item.modified_time or datetime.now()
                if config.date_type == "created" and item.created_time:
                    dt = item.created_time
                elif config.date_type == "current":
                    dt = datetime.now()
                date_str = dt.strftime(config.date_format)

            # 3. Number string
            formatted_num = RenameService.format_index(
                curr_idx,
                system=config.number_system,
                padding=config.padding
            )
            curr_idx += config.step

            # 4. Pattern evaluation
            new_stem = config.pattern
            new_stem = new_stem.replace("{n}", formatted_num)
            new_stem = new_stem.replace("{orig}", orig_stem)
            new_stem = new_stem.replace("{parent}", item.parent_dir.name)
            new_stem = new_stem.replace("{date}", date_str)

            # 5. Text replacements & removals
            if config.find_text:
                if config.case_sensitive_replace:
                    new_stem = new_stem.replace(config.find_text, config.replace_text)
                else:
                    pattern = re.compile(re.escape(config.find_text), re.IGNORECASE)
                    new_stem = pattern.sub(config.replace_text, new_stem)

            if config.remove_text:
                new_stem = new_stem.replace(config.remove_text, "")

            # 6. Prefix and Suffix
            if config.prefix:
                new_stem = f"{config.prefix}{new_stem}"
            if config.suffix:
                new_stem = f"{new_stem}{config.suffix}"

            # 7. Letter casing
            if config.case_transform == "upper":
                new_stem = new_stem.upper()
            elif config.case_transform == "lower":
                new_stem = new_stem.lower()
            elif config.case_transform == "title":
                new_stem = new_stem.title()

            # 8. Clean spaces and assemble full new name
            new_stem = new_stem.strip()
            final_new_name = f"{new_stem}{orig_ext}"
            
            item.new_name = final_new_name
            item.conflict_reason = ""
            item.status = "normal"

            # 9. Validate Windows filename legality
            is_valid, err_msg = FileService.validate_filename(final_new_name)
            if not is_valid:
                item.conflict_reason = err_msg
                item.status = "conflict"
                plan.conflicts_count += 1
                continue

            target_path = item.parent_dir / final_new_name

            # 10. Check duplicate target within current batch
            if target_path in proposed_names_in_batch:
                other_src = proposed_names_in_batch[target_path]
                item.conflict_reason = f"تعارض: ملف آخر سيحصل على نفس الاسم ({final_new_name})"
                item.status = "conflict"
                plan.conflicts_count += 1
                continue

            # 11. Check collision with existing file on disk (not part of selection)
            if target_path.exists() and target_path != item.path:
                # Check if the existing file on disk is being renamed to something else
                existing_in_selection = any(i.path == target_path and i.is_selected for i in plan.items)
                if not existing_in_selection:
                    item.conflict_reason = f"يوجد ملف آخر بالفعل في المجلد بنفس الاسم ({final_new_name})"
                    item.status = "conflict"
                    plan.conflicts_count += 1
                    continue

            proposed_names_in_batch[target_path] = item.path

            if item.is_changed:
                item.status = "changed"
                plan.changed_count += 1
                plan.rename_map.append((item.path, target_path))

        # Reset unselected items
        for item in plan.items:
            if not item.is_selected:
                item.new_name = item.original_name
                item.conflict_reason = ""
                item.status = "normal"

        plan.valid = (plan.conflicts_count == 0)
        return plan

    @staticmethod
    def execute_plan(
        plan: RenamePlan,
        progress_callback: Optional[Any] = None,
        cancel_check: Optional[Any] = None
    ) -> Tuple[int, int, List[str], Optional[HistoryRecord]]:
        """
        Executes renaming using a safe two-pass strategy:
        Pass 1: Rename all source files to temporary unique names (avoids circular collisions).
        Pass 2: Rename all temporary files to final target names.
        Returns: (success_count, fail_count, errors_list, history_record)
        """
        if not plan.rename_map:
            return 0, 0, [], None

        success_count = 0
        fail_count = 0
        errors: List[str] = []
        history_items: List[Dict[str, str]] = []

        total_ops = len(plan.rename_map)
        temp_renamed_map: List[Tuple[Path, Path, Path]] = [] # (original_path, temp_path, final_target)

        # PASS 1: Move sources to unique temporary files
        for idx, (old_path, target_path) in enumerate(plan.rename_map):
            if cancel_check and cancel_check():
                errors.append("تم إلغاء العملية من قبل المستخدم.")
                break

            if old_path == target_path:
                continue

            try:
                temp_name = f"__sinax_tmp_{uuid.uuid4().hex[:8]}_{old_path.name}"
                temp_path = old_path.parent / temp_name
                old_path.rename(temp_path)
                temp_renamed_map.append((old_path, temp_path, target_path))
            except Exception as e:
                err = f"تعذر إعداد الملف '{old_path.name}': {e}"
                logger.error(err)
                errors.append(err)
                fail_count += 1

        # PASS 2: Move from temporary files to final target paths
        for idx, (old_path, temp_path, target_path) in enumerate(temp_renamed_map):
            if cancel_check and cancel_check():
                # Try to rollback temp names back to original if canceled midway
                try:
                    temp_path.rename(old_path)
                except Exception:
                    pass
                continue

            try:
                temp_path.rename(target_path)
                success_count += 1
                history_items.append({
                    "original": str(old_path),
                    "target": str(target_path)
                })
                
                # Update item in plan
                for item in plan.items:
                    if item.path == old_path:
                        item.path = target_path
                        item.original_name = target_path.name
                        item.status = "success"
                        break

            except Exception as e:
                # Rollback temp file to original name
                try:
                    temp_path.rename(old_path)
                except Exception:
                    pass
                err = f"تعذر نقل الملف إلى الاسم الجديد '{target_path.name}': {e}"
                logger.error(err)
                errors.append(err)
                fail_count += 1

            if progress_callback:
                progress_callback(idx + 1, total_ops, target_path.name, success_count, fail_count)

        # Record in Undo Manager
        record = None
        if history_items:
            parent_folder = str(plan.rename_map[0][0].parent)
            record = undo_manager.record_operation(
                op_type="rename",
                folder=parent_folder,
                items=history_items,
                success=(fail_count == 0),
                details=f"تمت إعادة تسمية {success_count} ملف بنجاح"
            )

        return success_count, fail_count, errors, record

    @staticmethod
    def undo_operation(
        record: HistoryRecord,
        progress_callback: Optional[Any] = None
    ) -> Tuple[int, int, List[str]]:
        """
        Reverts a previous rename operation using safe two-pass renaming.
        """
        success = 0
        failed = 0
        errors = []

        items = record.items
        total = len(items)

        # Pass 1: rename targets to temp
        temp_list = []
        for entry in items:
            orig = Path(entry["original"])
            target = Path(entry["target"])
            if not target.exists():
                continue
            try:
                temp = target.parent / f"__sinax_undo_tmp_{uuid.uuid4().hex[:8]}_{target.name}"
                target.rename(temp)
                temp_list.append((orig, temp))
            except Exception as e:
                errors.append(f"تعذر تجهيز التراجع للملف {target.name}: {e}")
                failed += 1

        # Pass 2: rename temp to orig
        for idx, (orig, temp) in enumerate(temp_list):
            try:
                temp.rename(orig)
                success += 1
            except Exception as e:
                # Try to put back to target
                errors.append(f"تعذر استعادة اسم الملف {orig.name}: {e}")
                failed += 1

            if progress_callback:
                progress_callback(idx + 1, total, orig.name, success, failed)

        undo_manager.mark_reverted(record.record_id)
        return success, failed, errors
