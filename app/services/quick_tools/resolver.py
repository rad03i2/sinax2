# -*- coding: utf-8 -*-
"""
SINAX Smart Action Resolver
Inspects arbitrary incoming input (dragged files, folders, pasted strings, URLs, JSON, Hashes)
and resolves the input type, recommending top matching tools and instant one-click actions.
"""

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.quick_tools.models import InputType, QuickToolDefinition
from app.services.quick_tools.quick_tools_db import QuickToolsDatabase
from app.services.quick_tools.registry import QuickToolRegistry


class SmartActionResolver:
    """Intelligent context analyzer matching user input to the most relevant Quick Tools."""

    @staticmethod
    def detect_input_type(raw_input: str) -> Tuple[InputType, str]:
        """
        Determines the semantic nature of an input string or path.
        Returns (InputType, human_friendly_arabic_label).
        """
        clean = raw_input.strip()
        if not clean:
            return InputType.NONE, "فارغ"

        # Check if it is a local filesystem path
        # Remove surrounding quotes if dragged
        unquoted = clean.strip("\"'")
        try:
            p = Path(unquoted)
            if p.is_dir():
                return InputType.FOLDER, f"مجلد: {p.name}"
            elif p.is_file():
                ext = p.suffix.lower()
                if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico", ".svg"):
                    return InputType.IMAGE, f"صورة: {p.name}"
                return InputType.FILE, f"ملف: {p.name}"
        except Exception:
            pass

        # Check URL
        if re.match(r"^(https?://|www\.)\S+$", clean, re.IGNORECASE):
            return InputType.URL, "رابط إنترنت (URL)"

        # Check Hash (32, 40, 56, 64, 96, 128 hex characters)
        if re.match(r"^[0-9a-fA-F]{32,128}$", clean) and len(clean) in (32, 40, 56, 64, 96, 128):
            return InputType.HASH, f"بصمة هاش ({len(clean)} خانة Hex)"

        # Check Number
        if re.match(r"^-?\d+(\.\d+)?$", clean):
            return InputType.NUMBER, "قيمة رقمية"

        # Check JSON
        if (clean.startswith("{") and clean.endswith("}")) or (clean.startswith("[") and clean.endswith("]")):
            try:
                json.loads(clean)
                return InputType.JSON, "بيانات بتنسيق JSON"
            except Exception:
                pass

        return InputType.TEXT, "نص صريح"

    @staticmethod
    def resolve_recommended_tools(
        raw_input: str,
        limit: int = 8
    ) -> Dict[str, Any]:
        """
        Analyzes input and returns classified type, label, and prioritized recommended tools.
        Considers tool relevance, pinned favorites, and local usage frequency.
        """
        input_type, type_label = SmartActionResolver.detect_input_type(raw_input)
        all_tools = QuickToolRegistry.get_all_tools()
        db = QuickToolsDatabase()
        favorites = set(db.get_favorites())
        usage_stats = dict(db.get_most_used_tools(50))

        # Filter tools that accept this input type
        matched_tools: List[Tuple[QuickToolDefinition, int]] = []

        for tool in all_tools:
            # Check compatibility
            is_compatible = (input_type in tool.input_types) or (InputType.TEXT in tool.input_types and input_type in (InputType.URL, InputType.JSON, InputType.NUMBER, InputType.HASH))
            if not is_compatible:
                continue

            score = 0

            # Priority matrix
            if input_type == InputType.FILE:
                if tool.id in ("hash_calculator", "file_inspector", "copy_path_variants", "magic_bytes_inspector", "timestamp_editor"):
                    score += 50
            elif input_type == InputType.FOLDER:
                if tool.id in ("folder_size_stats", "directory_tree", "extract_filenames", "folder_manifest", "compare_folders", "copy_path_variants"):
                    score += 50
            elif input_type == InputType.URL:
                if tool.id in ("qr_generator", "url_encoder"):
                    score += 60
            elif input_type == InputType.HASH:
                if tool.id in ("hash_guesser", "hash_verify"):
                    score += 60
            elif input_type == InputType.JSON:
                if tool.id in ("json_formatter", "base64_tool"):
                    score += 60
            elif input_type == InputType.NUMBER:
                if tool.id in ("data_size_converter", "network_speed_converter", "number_base_converter", "unix_timestamp_converter", "scientific_calculator"):
                    score += 60
            elif input_type == InputType.TEXT:
                if tool.id in ("text_cleaner", "duplicate_lines_remover", "base64_tool", "word_counter", "qr_generator", "sort_lines", "change_case"):
                    score += 40

            # Bonus for user favorites
            if tool.id in favorites:
                score += 15

            # Bonus for frequently used
            score += min(20, usage_stats.get(tool.id, 0) * 2)

            matched_tools.append((tool, score))

        matched_tools.sort(key=lambda x: x[1], reverse=True)
        recommended = [t[0] for t in matched_tools[:limit]]

        return {
            "input_type": input_type,
            "type_label": type_label,
            "raw_input": raw_input,
            "recommended_tools": recommended,
        }
