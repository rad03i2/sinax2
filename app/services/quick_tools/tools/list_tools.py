# -*- coding: utf-8 -*-
"""
SINAX List Laboratory
List manipulation: deduplication, duplicate counting, set operations (intersect/diff/union),
random picking, shuffling, chunking, joining, and quote wrapping.
"""

from collections import Counter
import random
from typing import Any, Dict, List, Optional, Tuple


class ListTools:
    """Operations on collections of items and multi-line datasets."""

    @staticmethod
    def deduplicate(items: List[str], case_sensitive: bool = True) -> List[str]:
        """Deduplicates items while strictly maintaining original sequence order."""
        seen = set()
        out = []
        for i in items:
            key = i if case_sensitive else i.lower()
            if key not in seen:
                seen.add(key)
                out.append(i)
        return out

    @staticmethod
    def find_duplicates(items: List[str], case_sensitive: bool = True) -> List[Tuple[str, int]]:
        """Finds only items that appear more than once, with occurrence counts."""
        keys = items if case_sensitive else [i.lower() for i in items]
        counts = Counter(keys)
        dups = [(item, cnt) for item, cnt in counts.items() if cnt > 1]
        dups.sort(key=lambda x: x[1], reverse=True)
        return dups

    @staticmethod
    def set_operations(
        list_a: List[str],
        list_b: List[str],
        case_sensitive: bool = True
    ) -> Dict[str, List[str]]:
        """Computes Intersect, Difference (A-B, B-A), and Union."""
        set_a = set(list_a) if case_sensitive else {x.lower() for x in list_a}
        set_b = set(list_b) if case_sensitive else {x.lower() for x in list_b}

        intersection = sorted(list(set_a.intersection(set_b)))
        only_in_a = sorted(list(set_a.difference(set_b)))
        only_in_b = sorted(list(set_b.difference(set_a)))
        union = sorted(list(set_a.union(set_b)))

        return {
            "intersection": intersection,
            "only_in_a": only_in_a,
            "only_in_b": only_in_b,
            "union": union,
        }

    @staticmethod
    def pick_random(items: List[str], pick_count: int = 1) -> List[str]:
        """Picks N random items from list without replacement."""
        if not items:
            return []
        k = min(pick_count, len(items))
        return random.sample(items, k)

    @staticmethod
    def chunk_list(items: List[str], chunk_size: int = 50) -> List[List[str]]:
        """Divides a list into chunks of fixed length."""
        chunk_size = max(1, chunk_size)
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

    @staticmethod
    def join_items(items: List[str], delimiter: str = ", ", quote_char: str = "") -> str:
        """Wraps items with quotes and joins them with delimiter."""
        if quote_char:
            wrapped = [f"{quote_char}{i}{quote_char}" for i in items]
        else:
            wrapped = items
        return delimiter.join(wrapped)
