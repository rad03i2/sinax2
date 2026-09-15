# -*- coding: utf-8 -*-
"""
SINAX Text Laboratory
Comprehensive text processing engine: Cleaner pipeline, sorting, case conversions,
word frequency & metrics, Arabic text normalization, invisible character inspector,
line endings, regex tester, text diffing, and entity extraction.
"""

from collections import Counter
import difflib
import math
import re
from typing import Any, Dict, List, Optional, Tuple


class TextTools:
    """Universal text manipulation and extraction engine."""

    # --- Text Cleaner Pipeline ---
    @staticmethod
    def clean_text(
        text: str,
        trim_lines: bool = True,
        remove_empty_lines: bool = True,
        remove_duplicate_lines: bool = False,
        normalize_spaces: bool = False,
        tabs_to_spaces: bool = False,
        spaces_per_tab: int = 4
    ) -> str:
        """Applies configurable multi-step text cleaning pipeline."""
        if not text:
            return ""

        if tabs_to_spaces:
            text = text.replace("\t", " " * spaces_per_tab)

        lines = text.splitlines()

        if trim_lines:
            lines = [l.strip() for l in lines]

        if remove_empty_lines:
            lines = [l for l in lines if l]

        if normalize_spaces:
            lines = [re.sub(r"\s+", " ", l) for l in lines]

        if remove_duplicate_lines:
            seen = set()
            deduped = []
            for l in lines:
                if l not in seen:
                    seen.add(l)
                    deduped.append(l)
            lines = deduped

        return "\n".join(lines)

    # --- Duplicate Line Removal ---
    @staticmethod
    def remove_duplicate_lines(
        text: str,
        case_sensitive: bool = True,
        keep_last: bool = False
    ) -> Tuple[str, int]:
        """Removes duplicate lines while preserving original ordering. Returns (cleaned_text, duplicates_removed)."""
        lines = text.splitlines()
        if keep_last:
            lines.reverse()

        seen = set()
        out = []
        dups = 0

        for l in lines:
            key = l if case_sensitive else l.lower()
            if key in seen:
                dups += 1
            else:
                seen.add(key)
                out.append(l)

        if keep_last:
            out.reverse()

        return "\n".join(out), dups

    # --- Sort Lines ---
    @staticmethod
    def sort_lines(
        text: str,
        order: str = "A_Z" # 'A_Z', 'Z_A', 'NUMERIC', 'NATURAL', 'LENGTH_ASC', 'LENGTH_DESC', 'RANDOM'
    ) -> str:
        lines = text.splitlines()
        if order == "A_Z":
            lines.sort()
        elif order == "Z_A":
            lines.sort(reverse=True)
        elif order == "NUMERIC":
            def num_key(s):
                m = re.search(r"\d+", s)
                return int(m.group(0)) if m else float("inf")
            lines.sort(key=num_key)
        elif order == "NATURAL":
            def natural_key(s):
                return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]
            lines.sort(key=natural_key)
        elif order == "LENGTH_ASC":
            lines.sort(key=len)
        elif order == "LENGTH_DESC":
            lines.sort(key=len, reverse=True)
        elif order == "RANDOM":
            import random
            random.shuffle(lines)
        return "\n".join(lines)

    # --- Line Numbering & Affixes ---
    @staticmethod
    def number_lines(text: str, format_str: str = "{n}. ", start: int = 1) -> str:
        lines = text.splitlines()
        total = len(lines)
        width = len(str(total + start))
        numbered = []
        for idx, l in enumerate(lines):
            n_num = idx + start
            n_str = str(n_num)
            n_padded = str(n_num).zfill(width)
            prefix = format_str.replace("{n}", n_str).replace("{0n}", n_padded)
            numbered.append(f"{prefix}{l}")
        return "\n".join(numbered)

    @staticmethod
    def add_affixes(text: str, prefix: str = "", suffix: str = "") -> str:
        lines = text.splitlines()
        return "\n".join(f"{prefix}{l}{suffix}" for l in lines)

    # --- Case Conversions ---
    @staticmethod
    def change_case(text: str, mode: str) -> str:
        """
        Converts text case:
        UPPERCASE, lowercase, Title, Sentence, camelCase, PascalCase, snake_case, kebab-case, CONSTANT_CASE
        """
        if mode == "UPPERCASE":
            return text.upper()
        elif mode == "lowercase":
            return text.lower()
        elif mode == "Title Case":
            return text.title()
        elif mode == "Sentence case":
            return ". ".join(s.strip().capitalize() for s in text.split("."))
        
        # Word-boundary conversions for code identifiers
        words = re.findall(r"[A-Za-z0-9\u0600-\u06FF]+", text)
        if not words:
            return text

        if mode == "camelCase":
            return words[0].lower() + "".join(w.capitalize() for w in words[1:])
        elif mode == "PascalCase":
            return "".join(w.capitalize() for w in words)
        elif mode == "snake_case":
            return "_".join(w.lower() for w in words)
        elif mode == "kebab-case":
            return "-".join(w.lower() for w in words)
        elif mode == "CONSTANT_CASE":
            return "_".join(w.upper() for w in words)
        return text

    # --- Word Counter & Metrics ---
    @staticmethod
    def calculate_text_metrics(text: str) -> Dict[str, Any]:
        """Calculates rich metrics including words, characters, sentences, and estimated reading time."""
        if not text:
            return {
                "chars": 0, "chars_no_spaces": 0, "words": 0,
                "lines": 0, "paragraphs": 0, "sentences": 0,
                "utf8_bytes": 0, "reading_time_min": 0.0
            }

        chars = len(text)
        chars_no_spaces = len(re.sub(r"\s", "", text))
        words = len(re.findall(r"\S+", text))
        lines = len(text.splitlines())
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])
        sentences = len([s for s in re.split(r"[.!?؟]+", text) if s.strip()])
        utf8_bytes = len(text.encode("utf-8"))
        reading_time = round(words / 200.0, 1) # Standard ~200 WPM

        return {
            "chars": chars,
            "chars_no_spaces": chars_no_spaces,
            "words": words,
            "lines": lines,
            "paragraphs": max(1, paragraphs),
            "sentences": max(1, sentences),
            "utf8_bytes": utf8_bytes,
            "reading_time_min": reading_time,
        }

    @staticmethod
    def analyze_word_frequency(text: str, top_n: int = 15) -> List[Tuple[str, int, float]]:
        """Returns top most frequent words with occurrence counts and percentage."""
        words = [w.lower() for w in re.findall(r"\b\w+\b", text)]
        total = len(words)
        if total == 0:
            return []
        counts = Counter(words).most_common(top_n)
        return [(word, count, round((count / total) * 100, 1)) for word, count in counts]

    # --- Arabic Text Tools ---
    @staticmethod
    def clean_arabic_text(
        text: str,
        remove_tashkeel: bool = True,
        normalize_alef: bool = True,
        remove_tatweel: bool = True,
        normalize_taa_marbuta: bool = False
    ) -> str:
        """Cleans and standardizes Arabic diacritics and letter variants."""
        res = text
        if remove_tashkeel:
            # Range \u064B - \u0652 plus Shadda \u0651
            tashkeel_regex = re.compile(r"[\u064B-\u0652\u0670\u0640]")
            res = tashkeel_regex.sub("", res)
        if remove_tatweel:
            res = res.replace("ـ", "")
        if normalize_alef:
            res = re.sub(r"[إأآا]", "ا", res)
        if normalize_taa_marbuta:
            res = res.replace("ة", "ه").replace("ى", "ي")
        return res

    # --- Invisible Characters Inspector ---
    @staticmethod
    def inspect_invisible_characters(text: str) -> Dict[str, Any]:
        """Detects zero-width, non-breaking, and unusual whitespace characters."""
        INVISIBLES = {
            "\u200B": "Zero Width Space (ZWSP)",
            "\u200C": "Zero Width Non-Joiner (ZWNJ)",
            "\u200D": "Zero Width Joiner (ZWJ)",
            "\u00A0": "Non-Breaking Space (NBSP)",
            "\uFEFF": "Byte Order Mark (BOM) in text",
            "\u202A": "LTR Embedding",
            "\u202B": "RTL Embedding",
            "\u202C": "Pop Directional Format",
        }
        counts = {}
        for char, name in INVISIBLES.items():
            c = text.count(char)
            if c > 0:
                counts[name] = c

        return {
            "total_found": sum(counts.values()),
            "breakdown": counts,
        }

    @staticmethod
    def remove_invisible_characters(text: str) -> str:
        """Strips zero-width and directional control markers safely."""
        return re.sub(r"[\u200B\u200C\u200D\uFEFF\u202A-\u202E]", "", text)

    # --- Line Endings ---
    @staticmethod
    def convert_line_endings(text: str, target_format: str = "CRLF") -> str:
        """Normalizes line endings to CRLF (Windows), LF (Unix), or CR (Classic Mac)."""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if target_format == "CRLF":
            return normalized.replace("\n", "\r\n")
        elif target_format == "CR":
            return normalized.replace("\n", "\r")
        return normalized

    # --- Text Diff Engine ---
    @staticmethod
    def compute_text_diff(original: str, modified: str) -> Dict[str, Any]:
        """Computes line diff between original and modified text."""
        orig_lines = original.splitlines()
        mod_lines = modified.splitlines()
        matcher = difflib.SequenceMatcher(None, orig_lines, mod_lines)

        diff_entries = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for line in orig_lines[i1:i2]:
                    diff_entries.append({"type": "equal", "line": line})
            elif tag == "replace":
                for line in orig_lines[i1:i2]:
                    diff_entries.append({"type": "removed", "line": line})
                for line in mod_lines[j1:j2]:
                    diff_entries.append({"type": "added", "line": line})
            elif tag == "delete":
                for line in orig_lines[i1:i2]:
                    diff_entries.append({"type": "removed", "line": line})
            elif tag == "insert":
                for line in mod_lines[j1:j2]:
                    diff_entries.append({"type": "added", "line": line})

        return {
            "entries": diff_entries,
            "has_differences": any(e["type"] != "equal" for e in diff_entries),
        }

    # --- Entity Extractors ---
    @staticmethod
    def extract_entities(text: str, entity_type: str) -> List[str]:
        """Extracts emails, URLs, IPs, phones, or numbers from text."""
        if entity_type == "emails":
            matches = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        elif entity_type == "urls":
            matches = re.findall(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", text)
        elif entity_type == "ipv4":
            matches = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
        elif entity_type == "phones":
            matches = re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        elif entity_type == "numbers":
            matches = re.findall(r"-?\b\d+(?:\.\d+)?\b", text)
        else:
            matches = []

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for m in matches:
            m_clean = m.strip()
            if m_clean and m_clean not in seen:
                seen.add(m_clean)
                deduped.append(m_clean)
        return deduped

    # --- Regex Tester ---
    @staticmethod
    def test_regex(pattern: str, text: str, ignore_case: bool = False, multiline: bool = False) -> Dict[str, Any]:
        """Tests regular expression against text with safe error handling."""
        flags = 0
        if ignore_case:
            flags |= re.IGNORECASE
        if multiline:
            flags |= re.MULTILINE

        try:
            compiled = re.compile(pattern, flags)
            matches = []
            for m in compiled.finditer(text):
                matches.append({
                    "match": m.group(0),
                    "start": m.start(),
                    "end": m.end(),
                    "groups": list(m.groups()),
                })
            return {
                "is_valid": True,
                "error": "",
                "match_count": len(matches),
                "matches": matches,
            }
        except re.error as e:
            return {
                "is_valid": False,
                "error": str(e),
                "match_count": 0,
                "matches": [],
            }
