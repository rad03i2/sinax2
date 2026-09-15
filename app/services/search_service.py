# -*- coding: utf-8 -*-
"""
SINAX Advanced Search Service
Provides deep recursive directory searching, wildcard and regex matching,
metadata filters (size, date, category), and full-text content searching.
"""

import fnmatch
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Generator

from app.core.constants import FILE_CATEGORIES, EXTENSION_TO_CATEGORY
from app.models.file_item import FileItem, format_file_size
from app.core.logger import get_logger

logger = get_logger("search_service")

# Common text extensions suitable for content search
TEXT_EXTENSIONS = {
    '.txt', '.py', '.js', '.ts', '.html', '.htm', '.css', '.json', '.xml',
    '.csv', '.md', '.log', '.ini', '.cfg', '.yaml', '.yml', '.sql', '.sh',
    '.bat', '.cmd', '.ps1', '.c', '.cpp', '.h', '.java', '.cs', '.php',
    '.rb', '.go', '.rs', '.swift', '.kt', '.r', '.tex', '.rtf'
}


@dataclass
class SearchFilter:
    """Encapsulates all search criteria."""
    query: str = ""
    use_regex: bool = False
    case_sensitive: bool = False
    recursive: bool = True
    include_hidden: bool = False
    category: str = "all"
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    content_query: str = ""
    max_results: int = 5000


@dataclass
class SearchResultItem:
    """Represents an individual search result item."""
    path: Path
    filename: str
    extension: str
    category_key: str
    category_label: str
    size_bytes: int
    formatted_size: str
    modified_time: Optional[datetime]
    formatted_date: str
    match_snippet: str = ""
    match_line_num: int = 0


class SearchService:
    """High-performance multi-criteria file search service."""

    @staticmethod
    def search(
        directory: Path,
        search_filter: SearchFilter,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[SearchResultItem]:
        """
        Executes search on directory according to criteria.
        Returns list of SearchResultItem.
        """
        results: List[SearchResultItem] = []
        if not directory or not directory.exists() or not directory.is_dir():
            return results

        # Compile name regex if applicable
        name_regex: Optional[re.Pattern] = None
        if search_filter.query.strip():
            flags = 0 if search_filter.case_sensitive else re.IGNORECASE
            if search_filter.use_regex:
                try:
                    name_regex = re.compile(search_filter.query, flags)
                except re.error as e:
                    logger.warning(f"Invalid regex '{search_filter.query}': {e}")
                    # Fallback to literal search
                    escaped = re.escape(search_filter.query)
                    name_regex = re.compile(escaped, flags)
            else:
                # Support wildcards or simple substring
                pattern = search_filter.query
                if '*' not in pattern and '?' not in pattern:
                    pattern = f"*{pattern}*"
                regex_str = fnmatch.translate(pattern)
                name_regex = re.compile(regex_str, flags)

        # Content search query
        content_term = search_filter.content_query.strip()
        content_case = search_filter.case_sensitive

        # Walk through directory
        count_scanned = 0

        # Generator for file paths
        def walk_dir() -> Generator[Path, None, None]:
            if search_filter.recursive:
                for root, dirs, files in os.walk(directory):
                    if is_cancelled and is_cancelled():
                        break
                    # Filter hidden dirs if requested
                    if not search_filter.include_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for f in files:
                        if not search_filter.include_hidden and f.startswith('.'):
                            continue
                        yield Path(root) / f
            else:
                for p in directory.glob('*'):
                    if is_cancelled and is_cancelled():
                        break
                    if p.is_file():
                        if not search_filter.include_hidden and p.name.startswith('.'):
                            continue
                        yield p

        for file_path in walk_dir():
            if is_cancelled and is_cancelled():
                logger.info("Search operation cancelled by user.")
                break

            count_scanned += 1
            if progress_callback and (count_scanned % 100 == 0):
                progress_callback(len(results), count_scanned, file_path.name)

            # 1. Filename match
            if name_regex and not name_regex.search(file_path.name):
                continue

            # 2. File stats
            try:
                stat = file_path.stat()
                sz = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime)
            except (OSError, PermissionError):
                continue

            # 3. Size Filter
            if search_filter.min_size_bytes is not None and sz < search_filter.min_size_bytes:
                continue
            if search_filter.max_size_bytes is not None and sz > search_filter.max_size_bytes:
                continue

            # 4. Date Filter
            if search_filter.date_from is not None and mtime < search_filter.date_from:
                continue
            if search_filter.date_to is not None and mtime > search_filter.date_to:
                continue

            # 5. Category Filter
            ext = file_path.suffix.lower()
            cat_key = EXTENSION_TO_CATEGORY.get(ext, "other")
            if search_filter.category and search_filter.category != "all":
                if cat_key != search_filter.category:
                    continue

            # 6. Content Search (if query provided)
            snippet = ""
            line_num = 0
            if content_term:
                if ext not in TEXT_EXTENSIONS and sz > 5 * 1024 * 1024:
                    # Skip binary files or oversized files for content search
                    continue

                matched_content, snippet, line_num = SearchService._search_file_content(
                    file_path, content_term, content_case
                )
                if not matched_content:
                    continue

            cat_info = FILE_CATEGORIES.get(cat_key, {"label_ar": "ملفات أخرى"})
            cat_label = cat_info.get("label_ar", "ملفات أخرى")

            res_item = SearchResultItem(
                path=file_path,
                filename=file_path.name,
                extension=ext.upper().lstrip('.'),
                category_key=cat_key,
                category_label=cat_label,
                size_bytes=sz,
                formatted_size=format_file_size(sz),
                modified_time=mtime,
                formatted_date=mtime.strftime("%Y-%m-%d %H:%M"),
                match_snippet=snippet,
                match_line_num=line_num
            )
            results.append(res_item)

            if len(results) >= search_filter.max_results:
                logger.info(f"Reached max results limit ({search_filter.max_results}).")
                break

        if progress_callback:
            progress_callback(len(results), count_scanned, "اكتمل البحث")

        return results

    @staticmethod
    def _search_file_content(
        file_path: Path,
        term: str,
        case_sensitive: bool = False
    ) -> tuple[bool, str, int]:
        """Reads file line by line to locate search term. Returns (found, snippet, line_number)."""
        term_to_match = term if case_sensitive else term.lower()
        encodings = ['utf-8', 'cp1256', 'latin-1']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc, errors='replace') as f:
                    for idx, line in enumerate(f, start=1):
                        target = line if case_sensitive else line.lower()
                        if term_to_match in target:
                            snippet = line.strip()[:150]
                            return True, snippet, idx
                return False, "", 0
            except Exception:
                continue
        return False, "", 0
